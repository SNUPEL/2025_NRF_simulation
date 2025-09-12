from io import StringIO

import pandas as pd
import simpy
import random as rd
from typing import List, Dict
from DT.components.Job import Job

class Source:
    def __init__(self, model, monitor, id, problem_data: dict, env: simpy.Environment):
        self.model = model
        self.monitor = monitor
        self.id = id
        self.job_data = problem_data['job_info']
        self.job_id_list = list(self.job_data.keys())
        self.operation_data = problem_data['operation_info']
        self.env = env

        self.process_routing = None
        self.sequencing_rule = None

        self.env.process(self.job_generator())

    def job_generator(self):
        batch_job_list = []
        n=0
        for job_id in self.job_id_list:
            n += 1
            IAT = self.job_data[job_id]['arrival_time'] - self.env.now

            job = Job(self.job_data[job_id], self.operation_data)
            self.monitor.record(time=self.env.now, part_id=job.id, operation=None, process=self.id, machine=None,
                                event='Job created')
            print(job.id, '생성:', self.env.now)

            if IAT == 0:
                batch_job_list.append(job)
                if n == len(self.job_data.keys()):
                    adjusted_batch_job_list = self.sequencing(batch_job_list)
                    for j in adjusted_batch_job_list:
                        self.env.process(self.to_next_process(j))

            else:
                if batch_job_list:
                    adjusted_batch_job_list = self.sequencing(batch_job_list)
                    for j in adjusted_batch_job_list:
                        self.env.process(self.to_next_process(j))

                yield self.env.timeout(IAT)
                self.env.process(self.to_next_process(job))


    def to_next_process(self,job):
        next_operation = job.operation_list[job.step]
        next_process = self.routing(next_operation)
        print('다음 프로세스:', next_process)
        yield self.model[next_process].store.put(job)
        self.monitor.record(time=self.env.now, part_id=job.id, operation=next_operation.id, process=next_process, machine=None, event='Job transferred')


    def sequencing(self, batch_job_list):
        def random(job_list):
            return rd.sample(job_list, len(job_list))

        def spt(job_list):
            # 각 job의 총 처리시간 계산
            total_times = {job: sum(job.operation_times) for job in job_list}
            # 총 처리시간 오름차순으로 정렬
            return sorted(job_list, key=lambda j: total_times[j])

        def lpt(job_list):
            # 각 job의 총 처리시간 계산
            total_times = {job: sum(job.operation_times) for job in job_list}
            # 총 처리시간 오름차순으로 정렬
            return sorted(job_list, key=lambda j: total_times[j], reverse=True)

        def johnson(job_list):
            # 첫 기계 vs 마지막 기계 처리시간 비교
            first_group = []  # 첫 기계가 더 짧은 job들
            second_group = []  # 마지막 기계가 더 짧은 job들

            operation_times = {job: job.operation_times for job in job_list}
            for j in job_list:
                if operation_times[j][0] < operation_times[j][-1]:
                    first_group.append(j)
                else:
                    second_group.append(j)

            # 첫 그룹은 첫 기계 시간 오름차순
            first_group.sort(key=lambda j: operation_times[j][0])
            # 둘째 그룹은 마지막 기계 시간 내림차순
            second_group.sort(key=lambda j: operation_times[j][-1], reverse=True)

            return first_group + second_group

        def palmer(job_list):
            operation_times = {job: job.operation_times for job in job_list}
            m = len(operation_times[job_list[0]])  # 기계 수
            # 각 job의 Palmer 지수 계산
            slope_index = {}
            for j in job_list:
                # Σ (m - 2*i + 1) * Pij, where i = 1..m
                total = 0
                for i, pij in enumerate(operation_times[j], start=1):
                    weight = (m - 2 * i + 1)
                    total += weight * pij
                slope_index[j] = total

            # slope_index 내림차순 정렬
            sorted_jobs = sorted(job_list, key=lambda j: slope_index[j], reverse=True)
            return sorted_jobs

        if self.sequencing_rule == 'RANDOM':
            adjusted_batch_job_list = random(batch_job_list)
        elif self.sequencing_rule == 'SPT':
            adjusted_batch_job_list = spt(batch_job_list)
        elif self.sequencing_rule == 'LPT':
            adjusted_batch_job_list = lpt(batch_job_list)
        elif self.sequencing_rule == 'JOHNSON':
            adjusted_batch_job_list = johnson(batch_job_list)
        elif self.sequencing_rule == 'PALMER':
            adjusted_batch_job_list = palmer(batch_job_list)
        else:
            adjusted_batch_job_list = batch_job_list

        return adjusted_batch_job_list

    def routing(self, next_operation):
        def random(operation):
            return rd.choice(operation.process_list)

        if self.process_routing == 'RANDOM':
            next_process = random(next_operation)
        else:
            next_process = next_operation.process_list[0]

        return next_process



