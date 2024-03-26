from typing import Literal
import requests
import uuid
import time

from myaakash.exceptions import APIError, LoginError, NotLoggedIn

SESSION_API = "https://session-service.aakash.ac.in/prod/sess/api/v1"
LMS_API = "https://session-service.aakash.ac.in/prod/lms/api/v1"
CHL_API_V1 = "https://session-service.aakash.ac.in/prod/chl/api/v1"
CHL_API_V2 = "https://session-service.aakash.ac.in/prod/chl/api/v2"


def login_required(method):
    def wrapper(*args, **kwargs):
        if not args[0].logged_in:
            raise NotLoggedIn

        return method(*args, **kwargs)

    return wrapper


class MyAakash:
    def __init__(self):
        self.logged_in = False
        self.tokens: dict[str, str | list[str]] = {}
        self.profile: dict[str, str] = {}

    def login(self, psid: str, password: str) -> str:
        ENDPOINT = "/user/session"

        payload = {"password": password, "profile": "student", "psid_or_mobile": psid}
        r = requests.post(SESSION_API + ENDPOINT, json=payload).json()

        if r["message"] != "OK":
            raise LoginError(r["message"])

        self.logged_in = True
        data = r["data"]

        self.tokens = {
            "access_token": data["access_token"],
            "refresh_token": data["refresh_token"],
            "aakash_login": data["aakash_login_value"],
            "client_id": str(uuid.uuid4()),
            "web_session": [
                data["web_session_key"],
                data["web_session_value"],
            ],
            "login_timestamp": str(time.time()),
        }

        self.__generate_headers()
        self.get_profile()

        return data["user_id"]

    def token_login(self, tokens: dict) -> str:
        self.tokens = tokens
        self.logged_in = True

        self.__generate_headers()

        while True:
            try:
                self.get_profile()
                break
            except APIError as e:
                if e.__str__() == "Invalid Session ID":
                    self.refresh_login()

                raise e

        return self.profile["user_id"]

    def refresh_login(self):
        ENDPOINT = "/user/session"

        payload = {"refresh_token": self.tokens["refresh_token"]}
        r = requests.put(
            SESSION_API + ENDPOINT, headers=self.headers, data=payload
        ).json()

        print(r)

        if r["message"] != "OK":
            raise LoginError(r["message"])

        self.logged_in = True
        data = r["data"]

        self.tokens = {
            "access_token": data["access_token"],
            "refresh_token": data["refresh_token"],
            "aakash_login": data["aakash_login_value"],
            "client_id": str(uuid.uuid4()),
            "web_session": [
                data["web_session_key"],
                data["web_session_value"],
            ],
            "login_timestamp": str(time.time()),
        }

        self.__generate_headers()
        self.get_profile()

        return data["user_id"]

    @login_required
    def get_profile(self) -> dict[str, str]:
        ENDPOINT = "/user"

        r = requests.get(SESSION_API + ENDPOINT, headers=self.headers).json()

        if r["message"] != "OK":
            raise APIError(r["message"])

        data = r["data"]

        self.profile = {
            "name": data["first_name"],
            "psid": data["psid"],
            "user_id": data["user_id"],
            "dob": data["dob"],
            "courses": data["courses"],
            "phone": data["phone"],
            "mail": data["mail"],
        }

        return self.profile

    @login_required
    def __generate_headers(self) -> dict[str, str]:
        cookies = []
        cookies.append(("aakash_login", self.tokens["aakash_login"]))
        cookies.append(("ace-access-token", self.tokens["access_token"]))
        cookies.append((self.tokens["web_session"][0], self.tokens["web_session"][1]))

        cookie_string = "; ".join([f"{name}={value}" for name, value in cookies])

        self.headers = {
            "access-token": self.tokens["access_token"],
            "Cookie": cookie_string,
            "x-client-id": self.tokens["client_id"],
        }

        return self.headers

    @login_required
    def logout(self) -> bool:
        ENDPOINT = "/logout"

        r = requests.post(SESSION_API + ENDPOINT, headers=self.headers).json()
        if r["message"] != "OK":
            raise APIError(r["message"])

        self.tokens = {}
        self.profile = {}
        self.logged_in = False

        return True

    @login_required
    def get_tests(self, status: Literal["live", "upcoming", "passed"]) -> list:
        ENDPOINT = "/tests"

        tests = []
        next_page = 1
        while next_page != -1:
            params = {
                "filter": "status",
                "page_number": next_page,
                "page_size": 50,
                "status": status,
            }
            r = requests.get(
                LMS_API + ENDPOINT, params=params, headers=self.headers
            ).json()

            if r["message"] != "OK":
                raise APIError(r["message"])

            data = r["data"]
            tests.extend(data["tests"])
            next_page = data["pagination"]["next_page"]

        return tests

    @login_required
    def get_test(self, test_id: str, short_code: str) -> dict:
        ENDPOINT = "/test"

        params = {"test_id": test_id, "test_short_code": short_code}

        r = requests.get(LMS_API + ENDPOINT, params=params, headers=self.headers).json()

        if r["message"] != "OK":
            raise APIError(r["message"])

        data = r["data"]
        return data

    @login_required
    def get_syllabus(self, syllabus_id: str) -> dict:
        ENDPOINT = "/syllabus/"

        r = requests.get(LMS_API + ENDPOINT + syllabus_id, headers=self.headers).json()

        if r["message"] != "OK":
            raise APIError(r["message"])

        return r["data"]

    @login_required
    def get_packages(self) -> list:
        ENDPOINT = "/itutor/package"

        r = requests.get(CHL_API_V1 + ENDPOINT, headers=self.headers).json()

        if r["message"] != "OK":
            raise APIError(r["message"])

        return r["data"]["packages"]

    @login_required
    def get_course(self, package_id: str, course_id: str, class_: str = ""):
        ENDPOINT = f"/itutor/package/{package_id}/subject"

        params = {"class": class_, "course_id": course_id}

        r = requests.get(CHL_API_V1 + ENDPOINT, params, headers=self.headers).json()

        if r["message"] != "OK":
            raise APIError(r["message"])

        return r["data"]["chapters"]

    @login_required
    def get_chapter_assets(self, package_id: str, course_id: str, chapter_id: str):
        ENDPOINT = f"/itutor/package/{package_id}/course/{course_id}/chapter"

        params = {"node_id": chapter_id}
        r = requests.get(CHL_API_V2 + ENDPOINT, params, headers=self.headers).json()

        if r["message"] != "OK":
            raise APIError(r["message"])

        return r["data"]["chapter"]

    @login_required
    def get_asset(
        self,
        package_id: str,
        course_id: str,
        chapter_id: str,
        asset_id: str,
        asset_type,
    ) -> dict[str, str]:
        ENDPOINT = f"/itutor/package/{package_id}/course/{course_id}/chapter/{chapter_id}/asset/{asset_id}"

        params = {"asset_type": asset_type}

        r = requests.get(CHL_API_V2 + ENDPOINT, params, headers=self.headers).json()

        if r["message"] != "OK":
            raise APIError(r["message"])

        return r["data"]
