import rpyc
import os

conn = rpyc.connect('localhost', int(os.environ.get('APS_SERVER_PORT')))

"""
# example:

job = conn.root.add_job('server:create_new_bill', 'interval',
                        args=[user_id, '1.00', 'category', 'out'], seconds=10, id='job_id')
conn.root.remove_job('job_id')
"""
