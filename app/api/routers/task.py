import json
from _pydecimal import Decimal

from flask import request, current_app
from flask_restplus import Namespace, Resource, marshal_with, reqparse

from app.api import CustomHTTPError
from app.api.utils.http import response_wrapper, success_response
from app.models import User, ScheduledBillTask, db

scheduled_bill_task_ns: Namespace = Namespace('scheduled bill task', description='定时账单版块')

task_model = scheduled_bill_task_ns.model('Task', ScheduledBillTask.auto_marshaling_model())


class TaskList(Resource):
    method_decorators = [response_wrapper]

    @scheduled_bill_task_ns.expect(task_model, validate=True)
    @marshal_with(task_model)
    def post(self):
        payload = request.json
        trigger_kwargs: dict = payload.pop('trigger_kwargs')
        payload['trigger_kwargs'] = json.dumps(trigger_kwargs)
        task = ScheduledBillTask(**payload)
        try:
            from scheduler.client import conn
            job = conn.root.add_job('scheduler.server:create_new_bill', task.trigger,
                                    args=[task.user_id, str(task.amount), task.category, task.type, task.name],
                                    **trigger_kwargs)
        except:
            current_app.logger.exception('apscheduler通过rpyc添加job失败')
            raise CustomHTTPError('定时账单添加失败', 500)
        task.id = job.id
        db.session.add(task)
        db.session.commit()
        return task

    @marshal_with(task_model)
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('user_id', type=int, required=True)
        args = parser.parse_args(request)
        tasks = ScheduledBillTask.query.filter_by(user_id=args['user_id']).all()
        return tasks


class Task(Resource):
    method_decorators = [response_wrapper]

    def delete(self):
        parser = reqparse.RequestParser()
        parser.add_argument('task_id', type=str, required=True)
        args = parser.parse_args(request)
        try:
            from scheduler.client import conn
            conn.root.remove_job(args['task_id'])
        except:
            current_app.logger.exception('apscheduler通过rpyc删除job失败')
            raise CustomHTTPError('定时账单删除失败', 500)
        ScheduledBillTask.query.filter_by(id=args['task_id']).delete()
        db.session.commit()
        return success_response


scheduled_bill_task_ns.add_resource(TaskList, '/user/tasks')
scheduled_bill_task_ns.add_resource(Task, '/user/task')
