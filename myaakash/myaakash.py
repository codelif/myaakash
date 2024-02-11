import requests

from myaakash.exceptions import APIError, LoginError, NotLoggedIn

API = "https://session-service.aakash.ac.in/prod/sess/api/v1"


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
        r = requests.post(API + ENDPOINT, json=payload).json()

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

        cookie = self.generate_cookie()
        self.tokens["headers"] = {
            "access-token": self.tokens["access_token"],
            "Cookie": cookie,
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

        r = requests.get(API + ENDPOINT, headers=self.tokens["headers"]).json()

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
    def generate_cookie(self) -> str:
        cookies = []
        cookies.append(("aakash_login", self.tokens["aakash_login"]))
        cookies.append(("ace-access-token", self.tokens["access_token"]))
        cookies.append((self.tokens["web_session"][0], self.tokens["web_session"][1]))

        cookie_string = "; ".join([f"{name}={value}" for name, value in cookies])

        return cookie_string

    @login_required
    def logout(self) -> bool:
        ENDPOINT = "/logout"

        r = requests.post(API + ENDPOINT, headers=self.tokens["headers"]).json()
        if r["message"] != "OK":
            raise APIError(r["message"])

        self.tokens = {}
        self.profile = {}
        self.logged_in = False

        return True
