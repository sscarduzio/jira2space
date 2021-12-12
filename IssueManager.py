import datetime
import json
import re

import HttpUtil
from Attachment import Attachment
from Config import *
from HttpUtil import HttpUtil
from Issue import Issue


class IssueManager:
    @staticmethod
    def deleteAllSpaceIssues():
        issues: list[Issue] = IssueManager.getIssuesFromSpace()
        total = len(issues)
        counter = 1
        for i in issues:
            IssueManager.deleteSpaceIssue(i)
            print(str(counter) + "/" + str(total) + " deleted issue " + i.spaceId + " from Space...")
            counter += 1

    @staticmethod
    def deleteSpaceIssue(issue: Issue):
        issueId = issue.spaceId
        HttpUtil.delete("/api/http/projects/id:" + SPACES_PROJECT_ID + "/planning/issues/id:" + issueId)

    @staticmethod
    def getIssuesFromSpace():
        def getPage(_offset):
            url = "/api/http/projects/id:" + SPACES_PROJECT_ID + \
                  "/planning/issues?sorting=TITLE&descending=false&$skip=" + \
                  str(_offset) + \
                  "&$fields=next,totalCount,data(attachments,id,status,tags,title,customFields,description,creationTime,number)"
            resp = HttpUtil.get(url)
            print(resp.status_code)
            return json.loads(resp.content)

        def data2Issue(data):
            # Skip non-imported issues
            if JIRA_ISSUE_ID_PREFIX not in data["title"]:
                return
            jiraId = re.search(rf"^\[{JIRA_ISSUE_ID_PREFIX}[0-9]{{1,3}}\]", data["title"]).group(0).replace("[",
                                                                                                            "").replace(
                "]", "")
            tags = []
            try:
                tags = [data["tags"][0]["name"]]
            except:
                pass
            attachmentsSource = data["attachments"] if "attachments" in data else []
            attachments = []
            if len(attachmentsSource) > 0:
                for a in attachmentsSource:
                    det = a["details"]
                    attachments.append(Attachment(
                        attachmentId=det["id"],
                        basename=det["filename"] if "filename" in det else det["name"],
                        className=det["className"]
                        # Only basic shit, we need only Ids to tweak the description an comments
                    ))
            relatesTo = data["customFields"]["Relates To"]["issues"]
            status = data["status"]["id"]

            return Issue(jiraId=jiraId, description=data["description"], title=data["title"],
                         status=status, tags=tags, spaceId=data["id"], attachments=attachments,
                         relatesTo=relatesTo, comments=[])

        offset = 0
        allIssues = []
        while True:
            print("Fetching next " + str(offset) + " issues... " + str(len(allIssues)))
            body = getPage(offset)
            totalCount = body["totalCount"]
            if totalCount == 0:
                break
            for i in body["data"]:
                issue = data2Issue(i)
                if issue is not None:
                    allIssues.append(issue)
            offset = body["next"]
            if int(offset) == body["totalCount"]:
                break
        return allIssues

    @staticmethod
    def insertAllIssuesInSpace(allJiraIssues):
        def insert(issue):
            atts = []
            for a in issue.attachments:
                atts.append(a.readyToUpload())
            data = json.dumps({
                "title": issue.title,
                "description": issue.description,
                "status": IssueManager.__jiraStatus2spaceStatusId(issue.status),
                "tags": issue.tags,
                "attachments": atts,
                # "customFields": {
                #     "Relates": {
                #         "className": "IssueListCFValue",
                #         "issues": issue.relatesTo
                #     }
                # }
            }, default=vars)
            print("> Saving issue to Jetbrains Space " + issue.title)
            resp = HttpUtil.post("/api/http/projects/id:" + SPACES_PROJECT_ID + "/planning/issues", data=data)
            print(resp.status_code)

        for i in allJiraIssues:
            insert(i)

    @staticmethod
    def updateIssue(issue, fields=[]):
        issue.processAttachments(issue.attachments)
        issueDict = issue.__dict__
        data = {}
        for f in fields:

            if f == "customFields":
                data[f] = [
                    {
                        "fieldId": "Relates",
                        "value": {
                            "className": "IssueListCFInputValue",
                            "issues": issue.relatesTo
                        }
                    }
                ]
            else:
                data[f] = issueDict[f]
        if len(data) > 0:
            asString = json.dumps(data)
            resp = HttpUtil.patch(
                "/api/http/projects/id:" + SPACES_PROJECT_ID + "/planning/issues/id:" + issue.spaceId, data=asString)
            print(str(resp.status_code) + " > updated " + issue.jiraId)

    @staticmethod
    def __jiraStatus2spaceStatusId(jiraStatus):
        if jiraStatus not in JIRA_STATUS_TO_SPACE_STATUS_ID:
            raise Exception("Jira status unknown, please find out what it is and add it to configuration " + jiraStatus)
        spaceID = JIRA_STATUS_TO_SPACE_STATUS_ID[jiraStatus]
        return spaceID

    @staticmethod
    def fillWithSpaceId(issues: list[Issue]):
        fromSpace: list[Issue] = IssueManager.getIssuesFromSpace()
        issuesWithSpaceId = []
        for i in fromSpace:
            for j in issues:
                if j.jiraId == i.jiraId:
                    j.spaceId = i.spaceId
                    issuesWithSpaceId.append(j)
        return issuesWithSpaceId

    @staticmethod
    def addComments(issues: list[Issue]):
        for i in issues:
            if len(i.comments) > 0:
                """
                {
                  "comments": [
                    {
                      "authorPrincipalId": "Bob",
                      "text": "Hey!",
                      "createdAtUtc": 123123
                    }
                  ]
                }"""
                comments = []
                for c in i.comments:
                    comments.append({
                      "comments": [
                        {
                          "authorPrincipalId": "28PcfG0fm4Kk",
                          "text": c["body"],
                          "createdAtUtc":c["created_at"].total_seconds()
                        }
                      ]
                    })
                    HttpUtil.post(
                        "/api/http/projects/id:" + SPACES_PROJECT_ID + "/planning/issues/id:" + i.spaceId + "/comments/import",
                        data=i.comments
                    )

# iss = IssueManager.getIssuesFromSpace()
# for i in iss:
#     IssueManager.updateIssue(i, ["description", "attachments"])
# pprint(json.dumps(iss, default=vars))
