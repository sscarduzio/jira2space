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

################# CONFIGURATION ################################################################################
JIRA_RSS_EXPORT_FILE = "./done_tasks.xml"
SPACES_URL = "beshu.jetbrains.space"
SPACES_PROJECT_ID = "23tkZF01SLKP"  # pick this up from API playground prepopulated values (see below URL)
API_AUTH_TOKEN = "eyJhbGciOiJSUzUxMiJ9.eyJzdWIiOiIyOFBjZkcwZm00S2siLCJhdWQiOiJjaXJjbGV0LXdlYi11aSIsIm9yZ0RvbWFpbiI6ImJlc2h1Iiwic2NvcGUiOiIqKiIsIm5hbWUiOiJzc2NhcmR1emlvIiwiaXNzIjoiaHR0cHM6XC9cL2Jlc2h1LmpldGJyYWlucy5zcGFjZSIsInByaW5jaXBhbF90eXBlIjoiVVNFUiIsImV4cCI6MTYzNjM1OTU0MCwiaWF0IjoxNjM2MzU4OTQwLCJzaWQiOiI0T2xrV0E0Rlp0VnUifQ.OYu7PZSYv_2UiOy4tlZlgeLPdOdBYy-fVKjaQrrhWaUBPMofN_sJZn6jlwDU-igWYBpJ05h37XZ_rvnGHAWpcG9N-eGebMptC6XegZZlc7nF1SSZtuhbqjRTCRyMY865Jc1GjGWNiz0RYjlsz94-Xr1c0oJcQnuDFpOeA4ZS2cE"  # take a temporary token from example code in https://beshu.jetbrains.space/httpApiPlayground?resource=projects_xxx_planning_issues&endpoint=http_post_import

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
    url = "https://" + SPACES_URL + "/api/http/projects/id:" + SPACES_PROJECT_ID + "/planning/issues"
    headers = CaseInsensitiveDict()
    headers["Accept"] = "application/json"
    headers["Content-Type"] = "application/json"
    headers["Authorization"] = "Bearer " + API_AUTH_TOKEN

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
    resp = requests.post(url, headers=headers, data=data)
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


if __name__ == '__main__':
    with open(JIRA_RSS_EXPORT_FILE) as fp:
        doc = BeautifulSoup(fp, 'html.parser')
    jiraId2usernameMap = scanForJiraUsers(doc)
    issues = parseJiraDump(doc, jiraId2usernameMap)
    for i in issues:
        insert(i)
