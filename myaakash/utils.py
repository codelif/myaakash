from myaakash.exceptions import NotLoggedIn


def login_required(method):
    def wrapper(*args, **kwargs):
        if not args[0].logged_in:
            raise NotLoggedIn

        return method(*args, **kwargs)

    return wrapper
