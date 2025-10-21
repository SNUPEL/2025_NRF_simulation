import simpy
import random as rd
from typing import List
from .Job import Job


class Source:
    """
    시뮬레이션 시스템에 작업(Job)을 생성하고 투입하는 역할을 하는 클래스입니다.
    """

    def __init__(self, model, monitor, id, problem_data, env, sequencing_rule, routing_rule):
        self.model = model
        self.monitor = monitor
        self.id = id
        self.job_data = problem_data['job_info']
        self.job_id_list = list(self.job_data.keys())
        self.operation_data = problem_data['operation_info']
        self.env = env
        self.sequencing_rule = sequencing_rule
        self.routing_rule = routing_rule
        self.env.process(self.job_generator())

    def job_generator(self):
        """
        문제 데이터에 정의된 모든 Job들을 생성하고 시스템에 투입하는 SimPy 프로세스입니다.
        """
        batch_job_list = []
        # job_data의 도착 시간을 기준으로 정렬하여 처리 (도착 시간이 빠른 순)
        sorted_job_ids = sorted(self.job_id_list, key=lambda jid: self.job_data[jid]['arrival_time'])

        for n, job_id in enumerate(sorted_job_ids, 1):
            arrival_time = self.job_data[job_id]['arrival_time']
            # 현재 시간보다 도착 시간이 늦다면 그 차이만큼 대기
            if arrival_time > self.env.now:
                # 대기 전, 이전에 쌓인 배치가 있다면 먼저 처리
                if batch_job_list:
                    adjusted_batch = self.sequencing(batch_job_list)
                    for j in adjusted_batch:
                        self.env.process(self.to_next_process(j))
                    batch_job_list = []

                yield self.env.timeout(arrival_time - self.env.now)

            job = Job(self.job_data[job_id], self.operation_data)
            self.monitor.record(time=self.env.now, part_id=job.id, operation=None, process=self.id, machine=None,
                                event='Job Created')
            print(f"{self.env.now:.2f}: Job {job.id} 생성됨 (도착 예정: {job.arrival_time}).")
            batch_job_list.append(job)

        # 마지막 배치가 남아있으면 처리
        if batch_job_list:
            adjusted_batch = self.sequencing(batch_job_list)
            for j in adjusted_batch:
                self.env.process(self.to_next_process(j))

    def to_next_process(self, job: Job):
        """Job의 첫 번째 Operation을 수행할 Process로 Job을 보냅니다."""
        next_operation = job.current_operation
        next_process_id = self.routing(next_operation)

        print(f'{self.env.now:.2f}: Job {job.id} (Op: {next_operation.id}) 첫 투입 -> Process {next_process_id}')

        if len(self.model[next_process_id].machines.items) - len(self.model[next_process_id].job_queue.items) > 0:
            yield self.model[next_process_id].job_queue.put(job)
        else:
            for proc in job.operation_list[job.step].process_list:
                yield self.model[proc].job_queue.put(job)

        self.monitor.record(time=self.env.now, part_id=job.id, operation=next_operation.id,
                            process=next_process_id, machine=None, event='Job Transferred')

    def sequencing(self, batch_job_list: List[Job]) -> List[Job]:
        """동일한 시간에 도착한 작업들의 공장 투입 순서를 결정합니다."""

        def johnson(job_list: List[Job]) -> List[Job]:
            op_times = {
                job: [op.get_average_processing_time() for op in job.operation_list]
                for job in job_list
            }
            first_group, second_group = [], []
            for job in job_list:
                if op_times[job][0] < op_times[job][-1]:
                    first_group.append(job)
                else:
                    second_group.append(job)
            first_group.sort(key=lambda j: op_times[j][0])
            second_group.sort(key=lambda j: op_times[j][-1], reverse=True)
            return first_group + second_group

        def palmer(job_list: List[Job]) -> List[Job]:
            op_times = {
                job: [op.get_average_processing_time() for op in job.operation_list]
                for job in job_list
            }
            if not job_list: return []
            num_machines = len(op_times[job_list[0]])
            slope_indices = {}
            for job in job_list:
                index = sum((num_machines - (2 * (i + 1)) + 1) * proc_time for i, proc_time in enumerate(op_times[job]))
                slope_indices[job] = index
            return sorted(job_list, key=lambda j: slope_indices[j], reverse=True)

        def get_total_avg_time(job: Job):
            return sum(op.get_average_processing_time() for op in job.operation_list)

        if self.sequencing_rule == 'SPT':
            return sorted(batch_job_list, key=get_total_avg_time)
        elif self.sequencing_rule == 'LPT':
            return sorted(batch_job_list, key=get_total_avg_time, reverse=True)
        elif self.sequencing_rule == 'WSPT':
            return sorted(batch_job_list,
                          key=lambda j: j.operation_list[0].get_average_processing_time() / getattr(j, 'weight', 1.0))
        elif self.sequencing_rule == 'JOHNSON':
            return johnson(batch_job_list)
        elif self.sequencing_rule == 'PALMER':
            return palmer(batch_job_list)
        elif self.sequencing_rule == 'RANDOM':
            rd.shuffle(batch_job_list)
            return batch_job_list
        else:  # FIFO
            return batch_job_list

    def routing(self, operation) -> str:
        """하나의 Operation을 처리할 수 있는 여러 Process 중 하나를 선택합니다."""
        if len(operation.process_list) == 1:
            return operation.process_list[0]

        proc_times = operation.get_process_time_map()

        if self.routing_rule == 'SPT':
            return min(proc_times, key=proc_times.get)
        elif self.routing_rule == 'WSPT':
            return min(proc_times, key=proc_times.get)
        elif self.routing_rule == 'LPT':
            return max(proc_times, key=proc_times.get)
        elif self.routing_rule == 'RANDOM':
            return rd.choice(operation.process_list)
        else:  # 기본값
            return operation.process_list[0]