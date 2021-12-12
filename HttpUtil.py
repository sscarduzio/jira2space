import requests
from requests.structures import CaseInsensitiveDict

from Config import *


class HttpUtil:

    @staticmethod
    def mkHeaders(accept="application/json", contentType="application/json"):
        headers = CaseInsensitiveDict()
        if accept:
            headers["Accept"] = accept
        if contentType:
            headers["Content-Type"] = contentType
        headers["Authorization"] = "Bearer " + API_AUTH_TOKEN
        return headers

    @staticmethod
    def patch(relativePath: str, data: dict, headers: CaseInsensitiveDict = mkHeaders()):
        resp = requests.patch(url=SPACES_URL + relativePath, headers=headers, data=data)
        resp.raise_for_status()
        return resp

    @staticmethod
    def post(relativePath: str, data: dict, headers: CaseInsensitiveDict = mkHeaders()):
        resp = requests.post(url=SPACES_URL + relativePath, headers=headers, data=data)
        resp.raise_for_status()
        return resp

    @staticmethod
    def put(relativePath: str, data: dict, headers: CaseInsensitiveDict = mkHeaders()):
        resp = requests.put(url=SPACES_URL + relativePath, headers=headers, data=data)
        resp.raise_for_status()
        return resp

    @staticmethod
    def delete(relativePath: str, headers: CaseInsensitiveDict = mkHeaders()):
        resp = requests.delete(url=SPACES_URL + relativePath, headers=headers)
        resp.raise_for_status()
        return resp

    @staticmethod
    def get(relativePath: str, headers: CaseInsensitiveDict = mkHeaders()):
        resp = requests.get(url=SPACES_URL + relativePath, headers=headers)
        resp.raise_for_status()
        return resp
