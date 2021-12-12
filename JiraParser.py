import re
from datetime import datetime
from html import unescape
from pprint import pprint

from bs4 import BeautifulSoup
from markdownify import markdownify

from Config import *
from Issue import Issue


class JiraParser:

    def __init__(self, xmlFile):
        self.xmlFile = xmlFile

    @staticmethod
    def __jiraStatus2spaceStatusId(jiraStatus):
        spaceID = JIRA_STATUS_TO_SPACE_STATUS_ID[jiraStatus]
        if not spaceID:
            raise Exception("Jira status unknown, please find out what it is and add it to configuration " + jiraStatus)
        return spaceID

    @staticmethod
    def __jira_label_to_space_tag_ID(label):
        tag = JIRA_LABEL_TO_SPACE_TAG_ID[label]
        if not tag:
            raise Exception(
                "Jira label " + label + " not found. Please find out what it is and add it to configuration ")
        return tag

    @staticmethod
    def __jira_user_id_to_username(jira_user_id, jiraId2usernameMap):
        username = jiraId2usernameMap[jira_user_id]
        if not username:
            raise Exception(
                "Jira label " + username + " not found. Please find out what it is and add it to configuration ")
        return username

    @staticmethod
    def __labels2tags(labels):
        result = []
        for l in labels:
            try:
                asText = l.text.strip()
                if len(asText) > 0:
                    result.append(JiraParser.__jira_label_to_space_tag_ID(asText))
            except Exception as e:
                print("got garbage label " + str(l))
                pass
        return result

    @staticmethod
    def str2date(asString):
        return datetime.strptime(asString, "%a, %d %b %Y %H:%M:%S %z")

    @staticmethod
    def __scanForJiraUsers(doc):
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

    @staticmethod
    def __parseJiraDump(doc, jiraId2usernameMap):
        _issues = []
        for e in doc.rss.channel.findAll("item"):
            print("< Parsing Jira issue: " + e.title.text)

            _comments = []

            for c in (e.comments or []):
                if c:
                    try:
                        if len(str(c)) > 1:
                            _comments.append({
                                'author': JiraParser.__jira_user_id_to_username(c.attrs["author"], jiraId2usernameMap),
                                'created_at': JiraParser.str2date(c.attrs["created"]),
                                'body': markdownify(unescape(str(c)))
                            })
                    except Exception as exc:
                        print("oops")
                        pprint(exc)
                        raise exc

            _issueLinks = []
            for r in (e.issuelinks or []):
                if r and len(str(r)) > 1 and r.issuelink.issuekey:
                    _issueLinks.append(r.issuelink.issuekey.text)

            entry = Issue(
                title=e.title.text,
                status=e.status.text,
                tags=JiraParser.__labels2tags(e.labels),
                description=markdownify(unescape(str(e.description))),
                jiraId=e.key.text,
                comments=_comments,
                attachments=[],
                relatesTo=_issueLinks
            )
            _issues.append(entry)
        return _issues

    def read(self):
        # Parse JIRA issues from RSS dump file and insert into Space
        with open(self.xmlFile) as fp:
            doc = BeautifulSoup(fp, 'html.parser')
        jiraId2usernameMap = JiraParser.__scanForJiraUsers(doc)
        issues = JiraParser.__parseJiraDump(doc, jiraId2usernameMap)
        return issues

