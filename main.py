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

################# CONF #######################################################################################
JIRA_RSS_EXPORT_FILE = "./import2.xml"
SPACES_URL = "beshu.jetbrains.space"
DEFAULT_SPACES_ISSUE_STATUS_ID = "4D8I5A3s5JqE"
SPACES_PROJECT_ID = "23tkZF01SLKP"  # pick this up from API playground prepopulated values (see below URL)
API_AUTH_TOKEN = ""  # take a temporary token from example code in https://beshu.jetbrains.space/httpApiPlayground?resource=projects_xxx_planning_issues&endpoint=http_post_import


# Edit these two lookup table functions based on eyeballing the xml file from Jira:
def jira_id_to_full_name(userID):
    if userID == "60b017cc0536cb0069b9c0a8" or userID == "557058:49e1100b-7c6e-44ab-9058-377da844b8b9":
        return "Simone Scarduzio"

    return "UNKNOWN_JIRA_COMMENTER"


def jira_label_to_space_tag_ID(tag):
    if tag == "ror_es":
        return "20vaFW1wT1mm"
    if tag == "NP":
        return "vCDCh0lyLzc"
    if tag == "Portal":
        return "Jil1r1Yt110"
    if tag == "kibana":
        return "2Fndl91iVhfT"


##############################################################################################################

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


def parseJiraDump():
    issues = []
    with open(JIRA_RSS_EXPORT_FILE) as fp:
        doc = BeautifulSoup(fp, 'html.parser')

        for i in doc.rss.channel.findAll("item"):
            entry = {}
            print("==============================")
            entry["title"] = i.title.text
            entry["status"] = i.status.text
            entry["tag"] = labels2tags(i.labels)
            entry["description"] = markdownify(unescape(str(i.description)))
            commentz = []

            for c in (i.comments or []):
                if c:
                    try:
                        if len(str(c)) > 1:
                            commentz.append({
                                'author': jira_id_to_full_name(c.attrs["author"]),
                                'created_at': c.attrs["created"],
                                'body': markdownify(unescape(str(c)))
                            })
                    except Exception as e:
                        print("oops")
                        pprint(e)

            entry["comments"] = commentz
            issues.append(entry)
    return issues


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
            descAndComments += "\n--- \n\n### " + c["author"] + "\n __On " + c["created_at"] + "__\n" + c['body']

    data = json.dumps({
        "title": issue["title"],
        "description": descAndComments,
        "status": DEFAULT_SPACES_ISSUE_STATUS_ID,  # issue["status"],
        "tags": issue["tag"],

    })
    resp = requests.post(url, headers=headers, data=data)
    print(resp.status_code)


if __name__ == '__main__':
    issues = parseJiraDump()
    pprint(issues)
    for i in issues:
        insert(i)
