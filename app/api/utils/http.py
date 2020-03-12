from functools import wraps

import flask_restplus

success_response = 'success', 200


class Api(flask_restplus.Api):
    def handle_error(self, e):
        """just raise the exception"""
        raise e


def response_wrapper(*args):
    def formatter(*data):

        if len(data) == 1:
            data = data[0]
            return {'data': data, 'status': 200, 'message': 'success'}

        if len(data) == 2:
            first, second = data
            if isinstance(first, int) and isinstance(second, str):
                return {'status': first, 'message': second}
            elif isinstance(first, str) and isinstance(second, int):
                return {'status': second, 'message': first}
            else:
                raise TypeError('Unexpected types')

        elif len(data) == 3:
            data, status, message = data
            # TODO 判断类型
            return {'data': data, 'status': status, 'message': message}

    if callable(args[0]):
        # 作为装饰器使用
        func = args[0]

        @wraps(func)
        def wrapper(*args, **kwargs):
            ret = func(*args, **kwargs)
            # 函数本意是返回单个对象，但返回的又是元组的情况不考虑
            return formatter(*ret) \
                if isinstance(ret, tuple) else formatter(ret)

        return wrapper

    else:
        # 直接传入数据
        return formatter(*args)
