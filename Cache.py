import json
from pathlib import Path

from Attachment import Attachment
from Config import *
from Issue import Issue


def serialize(obj):
    return json.dumps(
        obj,
        sort_keys=True,
        indent=2,
        default=vars
    )


class Cache:

    def __init__(self, name):
        Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)
        self.theCacheFIle = os.path.join(CACHE_DIR, name + ".json")

    def write(self, value: list[Issue]):
        with open(self.theCacheFIle, 'w+') as out:
            out.write(serialize(value) + '\n')

    def read(self):
        try:
            with open(self.theCacheFIle) as json_file:
                arr: list[dict] = json.load(json_file)
                res: list[Issue] = []
                for i in arr:
                    toObj = Issue(**i)
                    attObjs = []
                    for a in toObj.attachments:
                        toAttObj = Attachment(**a)
                        attObjs.append(toAttObj)
                    toObj.attachments = attObjs
                    res.append(toObj)
                return res
        except FileNotFoundError as e:
            print("Cache cannot read! " + str(e))
            return None

    def clean(self):
        os.remove(self.theCacheFIle)

    def readAndClean(self):
        content = self.read()
        self.clean()
        return content
