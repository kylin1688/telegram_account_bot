import os

from flask import Blueprint, request, jsonify
from flask_cors import CORS
from flask_restplus import Api

from app.api.error import handle_uncaught_exception, CustomHTTPError, handle_custom_http_error
from app.api.routers.task import scheduled_bill_task_ns, TaskList
from app.api.utils.http import response_wrapper, success_response

api_bp = Blueprint('api', __name__)
CORS(api_bp)

# error handler
api_bp.register_error_handler(CustomHTTPError, handle_custom_http_error)
api_bp.register_error_handler(Exception, handle_uncaught_exception)

# restplus api & namespace registering
api = Api(api_bp, version='1.0')
api.add_namespace(scheduled_bill_task_ns, path='/scheduled')


@api_bp.before_request
def auth():
    # 目前没做登录，先用固定密钥做简单的身份认证
    token = request.headers.get('token')
    if token != os.environ.get('VERIFY_TOKEN'):
        return jsonify(response_wrapper('Unauthorized', 401))
