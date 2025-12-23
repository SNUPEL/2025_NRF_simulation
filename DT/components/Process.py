import simpy
import random as rd
from .Job import Job

class Process:
    """
    하나의 '공정(Process)' 또는 '워크스테이션(Workstation)'을 나타내는 클래스입니다.
    """
    def __init__(self, model, resource, monitor, id, problem_data, env, dispatching_rule, routing_rule):
        self.model = model
        self.resource = resource
        self.monitor = monitor
        self.id = id
        self.proc_data = problem_data['machine_info']
        self.env = env
        self.dispatching_rule = dispatching_rule
        self.routing_rule = routing_rule

        self.job_queue = simpy.FilterStore(self.env)

        self.env.process(self.run())

    def run(self):
        """
        공정의 메인 실행 로직. 가용한 기계와 대기 작업이 있으면 작업을 할당합니다.
        """
        yield self.env.timeout(0)
        while True:
            job = yield self.job_queue.get()
            job.current_process = self

            masking = {machine:False for machine in job.current_operation.machine_list}
            while True:
                selected_machine = self.routing(job, masking)

                # 모두 마스킹된 경우: 전부에 put
                if selected_machine is None:
                    for machine_type in job.current_operation.machine_list:
                        self.resource['Machine_pool'].machine_dict[machine_type].job_queue.put(job)
                        job.status = "waiting"
                    break

                target_m = self.resource['Machine_pool'].machine_dict[selected_machine]

                if not target_m.working:
                    target_m.job_queue.put(job)
                    target_m.working = True
                    job.status = 'working'
                    break
                else:
                    # 이 설비는 사용 불가 → 마스킹
                    masking[selected_machine] = True
                    # while 한번 더 돌면서 다른 설비 선택

    def to_next_process(self, job: Job, machine: str):
        """작업을 다음 공정이나 Sink로 보내고, 사용한 기계를 반납합니다."""
        job.complete_step()

        if not job.is_completed():
            next_operation = job.current_operation
            next_process_id = next_operation.process_list[0]

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

    def _dispatch(self) -> Job:
        """설정된 디스패칭 규칙에 따라 대기열에서 다음 작업을 선택합니다."""
        queue = self.job_queue.items

        if self.dispatching_rule == 'SPT':
            return min(queue, key=lambda j: j.current_operation.get_average_processing_time())

        elif self.dispatching_rule == 'WSPT':
            return min(queue,
                       key=lambda j: j.current_operation.get_average_processing_time() / getattr(j, 'weight', 1.0))

        elif self.dispatching_rule == 'LPT':
            return max(queue, key=lambda j: j.current_operation.get_average_processing_time())

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

    def routing(self, job, masking={}) -> str:
        """하나의 Operation을 처리할 수 있는 여러 Process 중 하나를 선택합니다."""
        operation = job.current_operation

        available_machines = [
            p for p in operation.machine_list
            if not masking.get(p, False)  # 예: 딕셔너리 형태일 때
        ]

        if len(available_machines) == 0:
            # 모두 마스킹된 경우에 어떻게 처리할지 정책 필요
            return None  # 또는 예외 등

        if len(available_machines) == 1:
            return available_machines[0]

        proc_times = operation.get_machine_process_time_map()

        if self.routing_rule == 'SPT':
            return min(available_machines, key=lambda p: proc_times[p])
        elif self.routing_rule == 'WSPT':
            return min(available_machines, key=lambda p: proc_times[p] * getattr(job, 'weight', 1.0))
        elif self.routing_rule == 'LPT':
            return max(available_machines, key=lambda p: proc_times[p])
        elif self.routing_rule == 'RANDOM':
            return rd.choice(available_machines)
        else:
            return available_machines[0]

