# Jira RSS/XML export to Jetbrains Space issue importer
# This script feeds on an XML file from Jira, and imports (issue title, description, status, comments) into JB Space.
# Written 06/11/2021
# Author: GH @sscarduzio, Simone Scarduzio
# License: GPLv3 license

from AttachmentManager import AttachmentManager
from Cache import Cache
from Config import *
from Issue import Issue
from IssueManager import IssueManager
from JiraParser import JiraParser

if __name__ == '__main__':
    # Clean-up if necessary
    IssueManager.deleteAllSpaceIssues()

    # Phase 1. Parse from Jira dump
    cache = Cache("parsed")
    parsedIssues = cache.read()
    if parsedIssues is None:
        parsedIssues: list[Issue] = JiraParser(JIRA_RSS_EXPORT_FILE).read()
        cache.write(parsedIssues)
    print("Parsed issues are " + str(len(parsedIssues)))

    # Phase 2. Inspect attachments, upload them, and generate a list of Issues with attachments
    cache = Cache("withAttachments")
    issuesWithAttachments: list[Issue] = cache.read()
    if issuesWithAttachments is None:
        issuesWithAttachments = AttachmentManager("./attachments").putAttachments(parsedIssues)
        cache.write(issuesWithAttachments)
    print("with attachment issues are " + str(len(issuesWithAttachments)))

    # Phase 3. Add issues with attachments to Space
    IssueManager.insertAllIssuesInSpace(issuesWithAttachments)

    # Phase 4. Fill in space ID and Add comments
    cache = Cache("withSpaceId")
    issuesWithSpaceId: list[Issue] = cache.read()
    if issuesWithSpaceId is None:
        IssueManager.fillWithSpaceId(issuesWithAttachments)
        cache.write(issuesWithSpaceId)

   # IssueManager.addComments(issuesWithSpaceId)

    # Phase 5. Print relations between issues
    for i in issuesWithAttachments:
        if len(i.relatesTo) > 0:
            for r in i.relatesTo:
                print(i.jiraId + " -> " + r)
