from flask import request, current_app, Response


def log_request_params():
    client_ip = get_client_ip()
    current_app.logger.debug(f'request {request.method} url: {request.url} from: {client_ip}')
    current_app.logger.debug(f'request data: {request.data}')
    current_app.logger.debug(f'request values: {request.values}')
    current_app.logger.debug(f'request headers: ' + repr(request.headers).replace("\n", " "))


def log_response(response: Response):
    current_app.logger.debug(f'response: {response.data}\n')
    return response


def get_client_ip():
    if request.headers.get('X-Forwarded-For'):
        return request.headers['X-Forwarded-For']
    elif request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    else:
        return request.remote_addr
