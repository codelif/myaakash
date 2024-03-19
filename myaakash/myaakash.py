from typing import Literal
import requests
import uuid

from myaakash.exceptions import APIError, LoginError, NotLoggedIn

SESSION_API = "https://session-service.aakash.ac.in/prod/sess/api/v1"
LMS_API = "https://session-service.aakash.ac.in/prod/lms/api/v1"


def login_required(method):
    def wrapper(*args, **kwargs):
        if not args[0].logged_in:
            raise NotLoggedIn

        return method(*args, **kwargs)

    return wrapper


class MyAakash:
    def __init__(self):
        self.logged_in = False
        self.tokens: dict[str, str | list[str] | dict[str, str]] = {}
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
            "web_session": [
                data["web_session_key"],
                data["web_session_value"],
            ],
        }

        cookie = self.__generate_cookie()
        self.tokens["headers"] = {
            "access-token": data["access_token"],
            "Cookie": cookie,
            "x-client-id": str(uuid.uuid4()),
        }

        self.get_profile()
        return data["user_id"]

    def token_login(self, tokens: dict) -> str:
        self.tokens = tokens
        self.logged_in = True

        self.get_profile()

        return self.profile["user_id"]

    @login_required
    def get_profile(self) -> dict[str, str]:
        ENDPOINT = "/user"

        r = requests.get(SESSION_API + ENDPOINT, headers=self.tokens["headers"]).json()

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
    def __generate_cookie(self) -> str:
        cookies = []
        cookies.append(("aakash_login", self.tokens["aakash_login"]))
        cookies.append(("ace-access-token", self.tokens["access_token"]))
        cookies.append((self.tokens["web_session"][0], self.tokens["web_session"][1]))

        cookie_string = "; ".join([f"{name}={value}" for name, value in cookies])

        return cookie_string

    @login_required
    def logout(self) -> bool:
        ENDPOINT = "/logout"

        r = requests.post(SESSION_API + ENDPOINT, headers=self.tokens["headers"]).json()
        if r["message"] != "OK":
            raise APIError(r["message"])

        self.tokens = {}
        self.profile = {}
        self.logged_in = False

        return True

    @login_required
    def get_tests(self, status: Literal["live", "upcoming", "passed"])->list:
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
                LMS_API + ENDPOINT, params=params, headers=self.tokens["headers"]
            ).json()

            if r["message"] != "OK":
                raise APIError(r["message"])

            data = r["data"]
            tests.extend(data["tests"])
            next_page = data["pagination"]["next_page"]

        return tests

    @login_required
    def get_test(self, test_id: str, short_code: str)-> dict:
        ENDPOINT = "/test"

        params = {
                "test_id": test_id,
                "test_short_code": short_code
        }

        r = requests.get(LMS_API + ENDPOINT, params=params, headers=self.tokens["headers"]).json()

        if r["message"] != "OK":
            raise APIError(r["message"])

        data = r["data"]
        return data

    @login_required
    def get_syllabus(self, syllabus_id: str)->dict:
        ENDPOINT = "/syllabus/"

        r = requests.get(LMS_API + ENDPOINT + syllabus_id, headers= self.tokens["headers"]).json()

        if r["message"] != "OK":
            raise APIError(r["message"])

        return r["data"]

