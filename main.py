# Jira RSS/XML export to Jetbrains Space issue importer
# This script feeds on an XML file from Jira, and imports (issue title, description, status, comments) into JB Space.
# Written 06/11/2021
# Author: GH @sscarduzio, Simone Scarduzio
# License: GPLv3 license

from bs4 import BeautifulSoup
from pprint import pprint
from markdownify import markdownify
from html import unescape
import requests
from requests.structures import CaseInsensitiveDict
import json
import re
from datetime import datetime
import imagesize
import os
import magic
import urllib.parse

################# CONFIGURATION ################################################################################
JIRA_RSS_EXPORT_FILE = "./allIssues16.nov.xml"
SPACES_URL = "https://beshu.jetbrains.space"  # https://YOUR_ORG.jetbrains.space
SPACES_PROJECT_ID = "23tkZF01SLKP"  # pick this up from API playground prepopulated values (see below URL)
API_AUTH_TOKEN = os.getenv(
    "TOKEN")  # You get this from https://YOUR_ORG.jetbrains.space/extensions/installedApplications/<NEW_APP_YOU_MUST_CREATE>/permanent-tokens

JIRA_ISSUE_ID_PREFIX = "RORDEV-"
JIRA_STATUS_TO_SPACE_STATUS_ID = {
    # grep "<status"  all_tasks.xml | grep -vi done | grep -v "&lt"| sed -e 's/<[^>]*>//g' | sort | uniq
    "To Do": "3mLmz93RuAl9",  # Open
    "Done": "16PG4L15G4L9",
    "In Progress": "4D8I5A3s5JqE",
    "ON HOLD": "4dOimM2cKncz",
    "REJECTED": "16PG4L15G4L9"
}

JIRA_LABEL_TO_SPACE_TAG_ID = {
    "ror_es": "20vaFW1wT1mm",
    "NP": "vCDCh0lyLzc",
    "Portal": "Jil1r1Yt110",
    "kibana": "2Fndl91iVhfT"
}


##############################################################################################################

def mkHeaders(accept="application/json", contentType="application/json"):
    headers = CaseInsensitiveDict()
    if accept:
        headers["Accept"] = accept
    if contentType:
        headers["Content-Type"] = contentType
    headers["Authorization"] = "Bearer " + API_AUTH_TOKEN
    return headers


def jiraStatus2spaceStatusId(jiraStatus):
    spaceID = JIRA_STATUS_TO_SPACE_STATUS_ID[jiraStatus]
    if not spaceID:
        raise Exception("Jira status unknown, please find out what it is and add it to configuration " + jiraStatus)
    return spaceID


def jira_label_to_space_tag_ID(label):
    tag = JIRA_LABEL_TO_SPACE_TAG_ID[label]
    if not tag:
        raise Exception("Jira label " + label + " not found. Please find out what it is and add it to configuration ")
    return tag


def jira_user_id_to_username(jira_user_id, jiraId2usernameMap):
    username = jiraId2usernameMap[jira_user_id]
    if not username:
        raise Exception(
            "Jira label " + username + " not found. Please find out what it is and add it to configuration ")
    return username


def labels2tags(labels):
    result = []
    for l in labels:
        try:
            asText = l.text.strip()
            if len(asText) > 0:
                result.append(jira_label_to_space_tag_ID(asText))
        except Exception as e:
            print("got garbage label " + str(l))
            pass
    return result


def parseJiraDump(doc, jiraId2usernameMap):
    _issues = []
    for e in doc.rss.channel.findAll("item"):
        print("< Processing Jira issue: " + e.title.text)
        entry = {
            "title": e.title.text,
            "status": e.status.text,
            "tag": labels2tags(e.labels),
            "description": markdownify(unescape(str(e.description)))
        }
        _comments = []

        for c in (e.comments or []):
            if c:
                try:
                    if len(str(c)) > 1:
                        _comments.append({
                            'author': jira_user_id_to_username(c.attrs["author"], jiraId2usernameMap),
                            'created_at': c.attrs["created"],
                            'body': markdownify(unescape(str(c)))
                        })
                except Exception as exc:
                    print("oops")
                    pprint(exc)
                    raise exc

        entry["comments"] = _comments
        _issues.append(entry)
    return _issues


def insert(issue):
    url = SPACES_URL + "/api/http/projects/id:" + SPACES_PROJECT_ID + "/planning/issues"

    descAndComments = issue["description"]

    if len(issue["comments"]) > 0:
        descAndComments += "\n\n # Comments from Jira\n"
        for c in issue["comments"]:
            try:
                creationTime = datetime.strptime(c["created_at"], "%a, %d %b %Y %H:%M:%S %z").strftime(
                    "%-I%p, %d %b, %Y")
                descAndComments += "\n--- \n\n" + c['body'] + "\n\n > " + creationTime + ", " + c["author"]
            except Exception as e:
                pprint(e)
                raise e
    data = json.dumps({
        "title": issue["title"],
        "description": descAndComments,
        "status": jiraStatus2spaceStatusId(issue["status"]),
        "tags": issue["tag"],

    })
    print("> Saving issue to Jetbrains Space " + issue["title"])
    pprint(data)
    resp = requests.post(url, headers=mkHeaders(), data=data)
    print(resp.status_code)


def scanForJiraUsers(doc):
    tags = doc.findAll(attrs={"accountid": re.compile(r".*")})
    id2usernameMap = {}
    for t in tags:
        _id = t.attrs['accountid']
        _name = t.text
        if _id and _name:
            id2usernameMap[_id] = _name
        else:
            print("faulty id tag " + str(t))

    return id2usernameMap


def scanIssuesIdMap():
    def getPage(offset):
        url = SPACES_URL + "/api/http/projects/id:" + SPACES_PROJECT_ID + \
              "/planning/issues?sorting=TITLE&descending=false&$skip=" + str(offset)
        resp = requests.get(url, headers=mkHeaders())
        print(resp.status_code)
        return json.loads(resp.content)

    offset = 0
    allIssues = []
    while True:
        print("Fetching next " + str(offset) + " issues... " + str(len(allIssues)))
        body = getPage(offset)
        allIssues += body["data"]
        offset = body["next"]
        if int(offset) == body["totalCount"]:
            break
    return allIssues


def addAttachments(allIssues):
    def sizeOfImage(fileName):
        basename = os.path.basename(fileName)
        try:
            (w, h) = imagesize.get(fileName)
            if w + h < 0:
                return None
            return w, h
        except Exception as exc:
            print("Error probing image size: " + basename)
            return None

    def upload(fileName, issueId):
        basename = os.path.basename(fileName)
        sizes = sizeOfImage(fileName)
        storagePrefix = "file" if sizes is None else "image"
        # Get upload url
        resp = requests.post(SPACES_URL + "/api/http/uploads", headers=mkHeaders(),
                             data=json.dumps({"storagePrefix": storagePrefix}))
        resp.raise_for_status()
        uploadPath = resp.content.decode("utf-8").replace('"', "")

        ctype = magic.Magic(mime=True).from_file(fileName)
        print(basename + " of type " + ctype)
        headers = mkHeaders(contentType=ctype)
        resp = requests.put(SPACES_URL + uploadPath + "/" + urllib.parse.quote_plus(basename), headers=headers,
                            data=open(fileName, 'rb'))
        resp.raise_for_status()

        attachmentId = resp.content.decode("utf-8")


        if "video" in ctype:
            print("Upload as video file: ", basename)
            data = {
                "attachments": [
                    {"className": "VideoAttachment", "id": attachmentId,
                     "sizeBytes": os.path.getsize(fileName), "name": basename}
                ]
            }
        elif "image" in ctype:
            print("Upload as image")
            (w, h) = sizes
            data = {
                "attachments": [
                    {
                        "className": "ImageAttachment",
                        "id": attachmentId,
                        "name": basename,
                        "width": w,
                        "height": h
                    }
                ]
            }
        else:
            print("Upload as generic file " + basename)
            data = {
                "attachments": [
                    {"className": "FileAttachment", "id": attachmentId,
                     "sizeBytes": os.path.getsize(fileName), "filename": basename}
                ]
            }

        # Attach upload to issue
        resp = requests.post(
            SPACES_URL + f"/api/http/projects/{SPACES_PROJECT_ID}/planning/issues/{issueId}/attachments",
            data=json.dumps(data),
            headers=mkHeaders(contentType="application/json")
        )
        resp.raise_for_status()

    for _i in allIssues:
        import glob
        jiraId = re.search("\[RORDEV-[0-9]{1,3}\]", _i["title"]).group(0).replace("[", "").replace("]", "")
        filesNames = glob.glob("./attachments/" + jiraId + " */*")
        if len(filesNames) == 0:
            continue
        for f in filesNames:
            print("======== Uploads for " + jiraId)
            upload(f, _i["id"])
            print("============================")


def deleteIssue(issueId):
    print("delete issue: " + issueId)
    requests.delete(
        SPACES_URL + "/api/http/projects/id:" + SPACES_PROJECT_ID + "/planning/issues/id:" + issueId,
        headers=mkHeaders(),
    )


if __name__ == '__main__':
    # Scan existing issues and delete them
    allIssues = scanIssuesIdMap()
    for i in allIssues:
        deleteIssue(i["id"])

    # Parse JIRA issues from RSS dump file and insert into Space
    with open(JIRA_RSS_EXPORT_FILE) as fp:
        doc = BeautifulSoup(fp, 'html.parser')
    jiraId2usernameMap = scanForJiraUsers(doc)
    issues = parseJiraDump(doc, jiraId2usernameMap)
    for i in issues:
        insert(i)


    # Scan again new issues and dump all issues to json file
    allIssues = scanIssuesIdMap()
    with open("allIIssues.json", 'w+') as out:
        out.write(json.dumps(allIssues) + '\n')

    # 3. UPLOAD ATTACHMENTS
    with open('allIIssues.json') as json_file:
        allIssues = json.load(json_file)
        addAttachments(allIssues)

# FILE OK
