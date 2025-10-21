import simpy
import random as rd
from .Job import Job


class Process:
    """
    하나의 '공정(Process)' 또는 '워크스테이션(Workstation)'을 나타내는 클래스입니다.
    """
    def __init__(self, model, monitor, id, problem_data, env, dispatching_rule):
        self.model = model
        self.monitor = monitor
        self.id = id
        self.proc_data = problem_data['process_info']
        self.env = env
        self.dispatching_rule = dispatching_rule

        self.machines = simpy.Store(self.env, capacity=self.proc_data[self.id]['capacity'])
        for i in range(self.machines.capacity):
            self.machines.put(f"{self.id}_Machine_{i + 1}")

        self.job_queue = simpy.FilterStore(self.env)

        self.env.process(self.run())

    def run(self):
        """
        공정의 메인 실행 로직. 가용한 기계와 대기 작업이 있으면 작업을 할당합니다.
        """
        while True:
            yield self.env.timeout(1e-13)
            machine = yield self.machines.get()

            if len(self.job_queue.items) > 1:
                selected_job = self._dispatch()
                job = yield self.job_queue.get(lambda item: item.id == selected_job.id)
            else:
                job = yield self.job_queue.get()

            for proc in self.model.values():
                if proc is not self and isinstance(proc, Process):
                    if job in proc.job_queue.items:
                        proc.job_queue.items.remove(job)

            self.monitor.record(time=self.env.now, part_id=job.id, operation=job.current_operation.id,
                                process=self.id, machine=machine, event='Job Assigned')
            self.env.process(self.processing(job, machine))

    def processing(self, job: Job, machine: str):
        """실제 작업 처리를 모델링합니다."""
        operation = job.current_operation
        processing_time = operation.get_processing_time_for_process(self.id)

        yield self.env.timeout(processing_time)

        self.monitor.record(time=self.env.now, part_id=job.id, operation=operation.id,
                            process=self.id, machine=machine, event='Operation Complete')

        self.env.process(self.to_next_process(job, machine))

    def to_next_process(self, job: Job, machine: str):
        """작업을 다음 공정이나 Sink로 보내고, 사용한 기계를 반납합니다."""
        job.complete_step()

        if not job.is_completed():
            next_operation = job.current_operation
            next_process_id = self.model['Source'].routing(next_operation)

            print(f'{self.env.now:.2f}: Job {job.id} (Op: {next_operation.id}) -> Process {next_process_id}')

            yield self.model[next_process_id].job_queue.put(job)

            self.monitor.record(time=self.env.now, part_id=job.id, operation=next_operation.id,
                                process=next_process_id, machine=None, event='Job Transferred')
        else:
            job.completion_time = self.env.now
            yield self.model['Sink'].store.put(job)
            print(f'{self.env.now:.2f}: Job {job.id} 모든 공정 완료 -> Sink')
            self.monitor.record(time=self.env.now, part_id=job.id, operation=None,
                                process='Sink', machine=None, event='Job Transferred to Sink')

        yield self.machines.put(machine)

    def _dispatch(self) -> Job:
        """설정된 디스패칭 규칙에 따라 대기열에서 다음 작업을 선택합니다."""
        queue = self.job_queue.items

        if self.dispatching_rule == 'SPT':
            return min(queue, key=lambda j: j.current_operation.get_processing_time_for_process(self.id))

        elif self.dispatching_rule == 'WSPT':
            return min(queue,
                       key=lambda j: j.current_operation.get_processing_time_for_process(self.id) / getattr(j, 'weight', 1.0))

        elif self.dispatching_rule == 'LPT':
            return max(queue, key=lambda j: j.current_operation.get_processing_time_for_process(self.id))

        elif self.dispatching_rule in ['MWKR', 'LWKR']:
            def get_remaining_work(job: Job):
                rem_time = job.current_operation.get_processing_time_for_process(self.id)
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