import os
from typing import Optional

from pydantic import BaseModel


class Attachment(BaseModel):
    attachmentId: str
    basename: str
    className: str
    sizeBytes: Optional[int]
    contentType: Optional[str]
    filename: Optional[str]
    width: Optional[int]
    height: Optional[int]

    def readyToUpload(self):
        if self.className == "ImageAttachment":
            return {
                "className": self.className,
                "id": self.attachmentId,
                "name": self.basename,
                "width": self.width,
                "height": self.height
            }

        if self.className == "VideoAttachment":
            return {
                "className": "VideoAttachment",
                "id": self.attachmentId,
                "sizeBytes": os.path.getsize(self.filename),
                "name": self.basename
            }

        if self.className == "FileAttachment":
            return {
                "className": "FileAttachment",
                "id": self.attachmentId,
                "sizeBytes": os.path.getsize(self.filename),
                "filename": self.basename
            }

        raise Exception("Invalid className: " + self.className)
