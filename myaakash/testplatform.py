from urllib.parse import parse_qs, urlparse
from uuid import uuid4

import httpx

from myaakash.exceptions import APIError, LoginError
from myaakash.utils import login_required

EXAM_PLATFORM_API = "https://examplatform-api.aakash.ac.in/prod/exam-platform/api/v1"


class TestPlatform:
    def __init__(self, access_url: str):
        self.access_url = access_url
        self.logged_in = False
        self._init_client()
        self._login()
        self.headers = {}
        self.profile = {}

    def _init_client(self):

        url = urlparse(self.access_url)
        params = parse_qs(url.query)
        self.headers = {
            "Authorization": "Bearer " + params["token"][0],
            "x-client-id": str(uuid4()),
            "x-device-id": str(uuid4()),
        }
        h = httpx.Client(http2=True, headers=self.headers)
        self.client = h

    def _login(self):
        ENDPOINT = "/exam/init"
        r = self.client.get(EXAM_PLATFORM_API + ENDPOINT).json()
        if r["message"] != "OK":
            raise LoginError(r["message"])

        data = r["data"]

        self.profile = {
            "psid": data["user_id"],
            "user_id": data["we_user_id"],
            "exam_schedule_id": data["exam_schedule_id"],
            "tenant_id": data["tenant_id"],
            "tenant": data["tenant_name"],
            "test_id": data["phoenix_test_id"],
            "test_short_code": data["cms_test_short_code"],
        }

        self.logged_in = True

        return self.profile["user_id"]

    @login_required
    def get_analysis_overall(self):
        ENDPOINT = "/exam/analysis/overall"

        r = self.client.get(EXAM_PLATFORM_API + ENDPOINT).json()

        if r["message"] != "OK":
            raise APIError(r["message"])

        return r["data"]

    @login_required
    def attempt(self, consumed_time: bool):
        ENDPOINT = "/exam/attempt"
        params = {"consumed_time": "true" if consumed_time else "false"}

        r = self.client.get(EXAM_PLATFORM_API + ENDPOINT, params=params).json()
        if r["message"] != "OK":
            raise APIError(r["message"])

        return r["data"]

    @login_required
    def get_analysis_answers(self):
        ENDPOINT = "/exam/analysis/answer-key"

        r = self.client.get(EXAM_PLATFORM_API + ENDPOINT).json()
        if r["message"] != "OK":
            raise APIError(r["message"])

        return r["data"]["answer-key"]

    @login_required
    def get_analysis_comparative(self):
        ENDPOINT = "/exam/analysis/comparative"

        r = self.client.get(EXAM_PLATFORM_API + ENDPOINT).json()
        if r["message"] != "OK":
            raise APIError(r["message"])

        return r["data"]["comparative_analysis"]

    @login_required
    def get_analysis_chapter(self):
        ENDPOINT = "/exam/analysis/chapter"

        r = self.client.get(EXAM_PLATFORM_API + ENDPOINT).json()
        if r["message"] != "OK":
            raise APIError(r["message"])

        return r["data"]["chapter_analysis"]
