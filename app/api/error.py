from werkzeug.exceptions import NotFound, MethodNotAllowed

from app.api.utils.http import response_wrapper
from flask import jsonify, current_app


class CustomHTTPError(Exception):
    def __init__(self, msg: str, status: int, data=None):
        self.msg = msg
        self.status = status
        self.data = data

    def to_wrapped_response(self) -> dict:
        if self.data is None:
            return response_wrapper(self.msg, self.status)
        else:
            return response_wrapper(self.data, self.status, self.msg)


def handle_custom_http_error(e: CustomHTTPError):
    return jsonify(e.to_wrapped_response())


def handle_uncaught_exception(e: Exception):
    if isinstance(e, NotFound):
        return jsonify(response_wrapper('URL Not Found', 404))
    if isinstance(e, MethodNotAllowed):
        return jsonify(response_wrapper('Method Not Allowed', 404))

    current_app.logger.exception('Uncaught Exception')
    return jsonify(response_wrapper('Internal Server Error', 500))
