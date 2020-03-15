import os

import rpyc
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from dotenv import load_dotenv

basedir = os.path.dirname(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, ".env"))

from apscheduler.schedulers.background import BackgroundScheduler
from rpyc.utils.server import ThreadedServer
from .jobs import *


class SchedulerService(rpyc.Service):
    def exposed_add_job(self, func, *args, **kwargs):
        return scheduler.add_job(func, *args, **kwargs)

    def exposed_modify_job(self, job_id, jobstore=None, **changes):
        return scheduler.modify_job(job_id, jobstore, **changes)

    def exposed_reschedule_job(self, job_id, jobstore=None, trigger=None, **trigger_args):
        return scheduler.reschedule_job(job_id, jobstore, trigger, **trigger_args)

    def exposed_pause_job(self, job_id, jobstore=None):
        return scheduler.pause_job(job_id, jobstore)

    def exposed_resume_job(self, job_id, jobstore=None):
        return scheduler.resume_job(job_id, jobstore)

    def exposed_remove_job(self, job_id, jobstore=None):
        scheduler.remove_job(job_id, jobstore)

    def exposed_get_job(self, job_id):
        return scheduler.get_job(job_id)

    def exposed_get_jobs(self, jobstore=None):
        return scheduler.get_jobs(jobstore)


if __name__ == '__main__':
    jobstores = {
        'default': SQLAlchemyJobStore(
            url=os.environ.get('APSCHEDULER_SQLALCHEMY_URL')
                or 'sqlite:///' + os.path.join(basedir, 'apscheduler.sqlite3')),
        'memory': MemoryJobStore()
    }
executors = {
    'default': ThreadPoolExecutor(20)
}
scheduler = BackgroundScheduler(jobstores=jobstores, executors=executors)
scheduler.add_job(send_daily_bills, 'cron', jobstore='memory', hour=22)
scheduler.start()

protocol_config = {'allow_public_attrs': True}
server = ThreadedServer(SchedulerService, port=int(os.environ.get('APS_SERVER_PORT')),
                        protocol_config=protocol_config)
try:
    server.start()
except (KeyboardInterrupt, SystemExit):
    pass
finally:
    scheduler.shutdown()
