import re
from datetime import datetime
from pprint import pprint
from typing import List, Optional

from pydantic import BaseModel

from Attachment import Attachment

MAX_LEN_DESCRIPTION = 65535 - 1

class Issue(BaseModel):
    jiraId: str
    title: str
    spaceId: Optional[str]
    description: Optional[str]
    status: Optional[str]
    tags: Optional[List[str]]
    comments: Optional[List[dict]]
    attachments: Optional[List[Attachment]]
    relatesTo: Optional[List[str]]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        descAndComments = kwargs["description"]

        if len(self.comments) > 0:
            descAndComments += "\n\n # Comments from Jira\n"
            for c in self.comments:
                try:
                    creationTime = datetime.strptime(c["created_at"], "%a, %d %b %Y %H:%M:%S %z").strftime(
                        "%-I%p, %d %b, %Y")
                    descAndComments += "\n--- \n\n" + c['body'] + "\n\n > " + creationTime + ", " + c["author"]
                except Exception as e:
                    pprint(e)
                    raise e

        self.description = descAndComments

        attachments = kwargs["attachments"]
        if len(attachments) > 0:
            self.processAttachments(attachments)

        if len(self.description) > MAX_LEN_DESCRIPTION:
            _ellipsis = "...<TRUNCATED>"
            maxLen = MAX_LEN_DESCRIPTION - len(_ellipsis)
            print(self.jiraId + " > Too lengthy description? Foud extra chars: " + str(len(self.description) - MAX_LEN_DESCRIPTION))
            self.description = (self.description[:maxLen] + _ellipsis) if len(self.description) > MAX_LEN_DESCRIPTION else self.description

    def processAttachments(self, attachments: List[Attachment]):

        def update(originalString: str):
            for a in attachments:
                if isinstance(a, dict):
                    a = Attachment(**a)
                (replaced, _) = re.subn(
                    '/secure/attachment/[0-9]+/[0-9]+_' + a.basename, "/d/" + a.attachmentId, originalString,
                    flags=re.DOTALL)
                if originalString != replaced:
                    print("Updated string in " + self.jiraId)
                    originalString = replaced
            return originalString \
                .replace("{{", "`") \
                .replace("}}", "`") \
                .replace("\_", "_")

        self.attachments = attachments
        self.description = update(self.description)

        updatedComments = []
        for c in self.comments:
            c["body"] = update(c["body"])
            updatedComments.append(c)

        self.comments = updatedComments
