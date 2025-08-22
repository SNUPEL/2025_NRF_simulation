from io import StringIO

import pandas as pd
import simpy
import random
from typing import List, Dict
from DT.components.Job import Job

class Source:
    def __init__(self, model, monitor, id, problem_data: dict, env: simpy.Environment):
        self.model = model
        self.monitor = monitor
        self.id = id
        self.job_data = problem_data['job_info']
        self.operation_data = problem_data['operation_info']
        self.env = env

        self.process_routing = 'Random'

        self.env.process(self.job_generator())

    def job_generator(self):
        for job_id in self.job_data.keys():
            IAT = self.job_data[job_id]['arrival_time'] - self.env.now
            yield self.env.timeout(IAT)

            job = Job(self.job_data[job_id], self.operation_data)
            self.monitor.record(time=self.env.now, part_id=job.id, operation=None, process=self.id, machine=None, event='Job created')
            print(job.id, '생성:', self.env.now)

            self.env.process(self.to_next_process(job))


    def to_next_process(self,job):
        next_operation = job.operation_list[job.step]
        if self.process_routing == 'Random':
            next_process= self.random(next_operation)
        print('다음 프로세스:', next_process)
        yield self.model[next_process].store.put(job)
        self.monitor.record(time=self.env.now, part_id=job.id, operation=next_operation.id, process=next_process, machine=None, event='Job transferred')


    def random(self, operation):
        return random.choice(operation.process_list)

