from flask import request, current_app, Response


def log_request_params():
    current_app.logger.debug(f'request url: {request.url_root}')
    current_app.logger.debug(f'request data: {request.data}')
    current_app.logger.debug(f'request values: {request.values}')
    current_app.logger.debug(f'request headers: {request.headers}')


def log_response(response: Response):
    current_app.logger.debug(f'response: {response.data}')
    return response
