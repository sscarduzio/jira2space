import glob
import json
import os
import urllib

import imagesize
import magic

from Attachment import Attachment
from HttpUtil import HttpUtil
from Issue import Issue


class AttachmentManager:
    def __init__(self, attachmentsDirectory):
        self.directory = attachmentsDirectory

    @staticmethod
    def __upload(filename):
        basename = os.path.basename(filename)

        def sizeOfImage():
            try:
                (w, h) = imagesize.get(filename)
                if w + h < 0:
                    return None
                return w, h
            except Exception as exc:
                print("Error probing image size: " + basename)
                return None

        sizes = sizeOfImage()
        storagePrefix = "file" if sizes is None else "image"
        # Get upload url
        resp = HttpUtil.post("/api/http/uploads", data=json.dumps({"storagePrefix": storagePrefix}))

        uploadPath = resp.content.decode("utf-8").replace('"', "")

        contentType = magic.Magic(mime=True).from_file(filename)
        headers = HttpUtil.mkHeaders(contentType=contentType)
        resp = HttpUtil.put(uploadPath + "/" + urllib.parse.quote_plus(basename), headers=headers,
                            data=open(filename, 'rb'))

        attachmentId = resp.content.decode("utf-8")

        if "video" in contentType:
            print("Upload as video file: ", basename)
            data = Attachment(
                attachmentId=attachmentId,
                className="VideoAttachment",
                sizeBytes=os.path.getsize(filename),
                basename=basename,
                filename=filename,
                contentType=contentType
            )

        elif "image" in contentType:
            print("Upload as image")
            (w, h) = sizes
            data = Attachment(
                attachmentId=attachmentId,
                className="ImageAttachment",
                width=w,
                height=h,
                basename=basename,
                filename=filename,
                contentType=contentType
            )

        else:
            print("Upload as generic file " + basename)
            data = Attachment(
                attachmentId=attachmentId,
                className="FileAttachment",
                sizeBytes=os.path.getsize(filename),
                basename=basename,
                filename=filename,
                contentType=contentType
            )

        return data

    def putAttachments(self, allIssues: list[Issue]):
        # Python cannot mutate objects while iterating through them
        issuesWithAttachments = []
        for _i in allIssues:
            jiraId = _i.jiraId
            filesNames = glob.glob(self.directory + "/" + jiraId + " */*")

            issueAttachments = []
            for f in filesNames:
                print("\n======== Uploads for " + jiraId)
                added: Attachment = AttachmentManager.__upload(f)
                issueAttachments.append(added)
                print(added.basename + " -> " + added.attachmentId)

            _i.processAttachments(issueAttachments)
            issuesWithAttachments.append(_i)
        return issuesWithAttachments
