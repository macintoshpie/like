from functools import wraps
import json

from flask import session, request

from like.db import query_db, datetime_now_str

STATUS_MESSAGES = {
    200: "OK",
    201: "Created",
    400: "Bad Request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not Found",
    500: "Internal Server Error",
}


class ErrorResponse(Exception):
    status_code = 400

    def __init__(self, message, status_code=None, errors=None):
        Exception.__init__(self)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.errors = errors

    def to_dict(self):
        result = {"error": {"code": self.status_code, "message": self.message}}
        if self.errors is not None:
            result["error"]["errors"] = self.errors

        return result


def get_active_session():
    if "user_id" not in session or "session_id" not in session:
        return None

    return query_db(
        """
        SELECT * FROM user_sessions WHERE
            session_id = :session_id
            AND expiration IS NOT NULL
            AND :current_datetime < expiration
        """,
        {
            "user_id": session["user_id"],
            "session_id": session["session_id"],
            "current_datetime": datetime_now_str(),
        },
        one=True,
    )


def is_authenticated(user_id):
    if user_id is None:
        return False

    user_session = get_active_session()
    if user_session is None:
        return False
    return user_session["user_id"] == user_id


def is_account_owner(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_authenticated(kwargs.get("user_id")):
            return make_response(403)
        return f(*args, **kwargs)

    return decorated_function


def make_response(status_code, message=None, items=None, errors=None, **kwargs):
    if status_code is None:
        # TODO: find better fix for circular import
        from like import app

        app.logger.error(f"Missing required param: status_code: {status_code}")
        raise ErrorResponse("Internal server error", 500)

    if status_code < 400:
        data = {
            "message": message
            if message is not None
            else STATUS_MESSAGES.get(status_code, "success")
        }
        if items is not None:
            data["items"] = items
        data.update(kwargs)
        return {"data": data}, status_code

    error = {
        "code": status_code,
        "message": message
        if message is not None
        else STATUS_MESSAGES.get(status_code, "error"),
    }
    if errors is not None:
        error["errors"] = errors
    error.update(kwargs)
    return {"error": error}, status_code


def get_request_json():
    if request.data:
        try:
            return json.loads(request.data)
        except json.decoder.JSONDecodeError as e:
            raise ErrorResponse(message="Malformed request", errors=[str(e)])
        except Exception as e:
            raise ErrorResponse(
                message="Unexpected error", status_code=500, errors=[str(e)]
            )
    return {}
