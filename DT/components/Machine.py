import simpy
import random as rd
from typing import List, Dict, Union
from DT.components import Job


class Machine_pool:
    """
    Operation을 진행하기 위해 필요한 '기계(Machine)'를 관리하기 위한 클래스입니다.
    """
    def __init__(self, monitor, problem_data: Dict, env: simpy.Environment, dispatching_rule: str):
        self.monitor = monitor
        self.env = env
        self.machine_data = problem_data['machine_info']
        self.machine_dict = {}
        self.machine_list = []
        self.machine_stores = {}
        for machine_info in self.machine_data.values():
            self.machine_dict[machine_info['id']] = []
            self.machine_stores[machine_info['id']] = simpy.Store(env)
            for i in range(machine_info['capacity']):
                machine = Machines(machine_info['id'], machine_info['id'] + f"_{i + 1}", machine_info['processes'], env, dispatching_rule, self)
                self.machine_dict[machine_info['id']] = machine
                self.machine_list.append(machine)
                self.env.process(machine.run(self))
                self.machine_stores[machine.type].put(machine)

class Machines:
    """
    Operation을 진행하기 위해 필요한 '기계(Machine)' 나타내는 클래스입니다.
    """
    def __init__(self, type: str, id: str, proc_data: list, env: simpy.Environment, dispatching_rule: str, machines):
        self.type = type
        self.id = id
        self.processes = proc_data
        self.env = env
        self.machines = machines

        self.working = False

        self.job_queue = simpy.FilterStore(self.env)
        self.dispatching_rule = dispatching_rule

    def run(self, machines):
        while True:
            machine =  yield self.machines.machine_stores[self.type].get()

            while any(j.status == 'transporting' for j in self.machines.monitor.job_list):
                yield self.env.timeout(0)

            if len(self.job_queue.items) > 1:
                selected_job = self._dispatch()
                job = yield self.job_queue.get(lambda item: item.id == selected_job.id)
            else:
                job = yield self.job_queue.get()

            print(f'{self.env.now:.2f}: Job {job.id} (Machine: {self.id}) 투입')

            for m in machines.machine_list:
                if job in m.job_queue.items:
                    m.job_queue.items.remove(job)

            job.current_process.monitor.record(time=self.env.now, part_id=job.id, operation=job.current_operation.id,
                                               process=self.id, machine=self.type, event='Job Assigned')

            self.env.process(self.processing(job))

    def processing(self, job: Job):
        """실제 작업 처리를 모델링합니다."""
        operation = job.current_operation
        processing_time = operation.get_processing_time_for_machine(self.type)

        yield self.env.timeout(processing_time)
        job.status = 'transporting'

        job.current_process.monitor.record(time=self.env.now, part_id=job.id, operation=operation.id,
                            process=self.id, machine=self.type, event='Operation Complete')

        self.env.process(job.current_process.to_next_process(job, self))
        yield self.machines.machine_stores[self.type].put(self)
        self.working =False

    def _dispatch(self) -> Job:
        """설정된 디스패칭 규칙에 따라 대기열에서 다음 작업을 선택합니다."""
        queue = self.job_queue.items

        if self.dispatching_rule == 'SPT':
            return min(queue, key=lambda j: j.current_operation.get_processing_time_for_machine(self.type))

        elif self.dispatching_rule == 'WSPT':
            return min(queue,
                       key=lambda j: j.current_operation.get_processing_time_for_machine(self.type) * getattr(j, 'weight', 1.0))

        elif self.dispatching_rule == 'LPT':
            return max(queue, key=lambda j: j.current_operation.get_processing_time_for_machine(self.type))

        elif self.dispatching_rule in ['MWKR', 'LWKR']:
            def get_remaining_work(job: Job):
                rem_time = job.current_operation.get_average_processing_time()
                rem_ops = job.operation_list[job.step + 1:]
                if rem_ops:
                    rem_time += sum(op.get_average_processing_time() for op in rem_ops)
                return rem_time

            if self.dispatching_rule == 'MWKR':
                return max(queue, key=get_remaining_work)
            else:  # LWKR
                return min(queue, key=get_remaining_work)

        elif self.dispatching_rule == 'RANDOM':
            return rd.choice(queue)

        else:  # FIFO
            return queue[0]


