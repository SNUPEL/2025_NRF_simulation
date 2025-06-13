from io import StringIO

import pandas as pd
import simpy
import random
from typing import List, Dict
from DT.components import Job

class Source:
    def __init__(self, model, name, problem_data: dict, env: simpy.Environment):
        self.model = model
        self.name = name
        self.job_data = problem_data['job_info']
        self.operation_data = problem_data['operation_info']
        self.env = env

        self.process_routing = 'Random'

        self.env.process(self.job_generator())

    def job_generator(self):
        for job_info in self.job_data:
            IAT = job_info['arrival_time'] - self.env.now
            yield self.env.timeout(IAT)

            job = Job.Job(job_info['id'], job_info['operations'], self.operation_data)
            print(job.id, '생성:', self.env.now)

            self.env.process(self.to_next_process(job))

    def to_next_process(self,job):
        if self.process_routing == 'Random':
            next_process= self.random(job.operation_list[job.step])
        print('다음 프로세스:', next_process)
        yield self.model[next_process].store.put(job)


    def random(self, operation):
        return random.choice(operation.process_list)

