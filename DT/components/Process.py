import simpy
import random as rd
from DT.components.Job import Job
from DT.components.Sink import Sink

class Process:
    def __init__(self, model, monitor, id, problem_data: dict, env: simpy.Environment):
        self.model = model
        self.monitor = monitor
        self.id = id
        self.proc_data = problem_data['process_info']
        self.env = env
        # --- 디스패칭 규칙 설정: 'Random', 'SPT', 'LPT', 'MWKR', 'LWKR' 중 선택 ---
        self.dispatching_rule = None
        self.routing_rule = None

        self.store = simpy.FilterStore(env)
        self.machines = simpy.FilterStore(self.env, capacity=self.proc_data[self.id]['capacity'])
        for i in range(self.machines.capacity):
            self.machines.put('Machine' + str(i))

        self.parts_sent = 0
        self.util_time = 0

        self.env.process(self.run())

    def run(self):
        """
        설비의 메인 실행 로직.
        대기 중인 작업(Job)들 중에서 설정된 휴리스틱 규칙에 따라 다음 작업을 선택하여 처리합니다.
        """
        while True:
            yield self.env.timeout(1e-13)
            machine = yield self.machines.get()

            # 대기열(store)에 작업이 있을 때만 휴리스틱 규칙 적용
            if len(self.store.items) > 0:
                selected_job = self.dispatching()

                # 선택된 작업을 store에서 꺼냄
                job = yield self.store.get(lambda item: item.id == selected_job.id)
            else:
                # 대기열이 비어있으면 가장 먼저 들어오는 작업을 처리 (기존 FIFO 방식)
                job = yield self.store.get()

            for proc in self.model.values():
                if proc is not self and isinstance(proc, Process):
                    if job in proc.store.items:
                        proc.store.items.remove(job)

            self.monitor.record(time=self.env.now, part_id=job.id, operation=job.operation_list[job.step].id,
                                process=self.id, machine=machine, event='job assigned')
            yield self.env.process(self.processing(job, machine))

    def processing(self, job, machine):
        operation = job.operation_list[job.step]
        operation_time = operation.processing_time[self.id]

        yield self.env.timeout(operation_time)
        self.monitor.record(time=self.env.now, part_id=job.id, operation=operation.id, process=self.id, machine=machine,
                            event='operation complete')
        yield self.env.process(self.to_next_process(job, machine))

    def to_next_process(self, job, machine):
        job.step += 1
        if job.step != len(job.operation_list):
            next_operation = job.operation_list[job.step]
            # 다음 공정을 처리할 수 있는 설비가 여러 개일 경우 랜덤으로 선택
            next_process = rd.choice(next_operation.process_list)

            print(f'{self.env.now:.2f}: {job.id} (Op: {next_operation.id}) -> {next_process}')
            if len(self.model[next_process].machines.items) - len(self.model[next_process].store.items) > 0:
                yield self.model[next_process].store.put(job)
            else:
                for proc in job.operation_list[job.step].process_list:
                    yield self.model[proc].store.put(job)
            yield self.machines.put(machine)
            self.monitor.record(time=self.env.now, part_id=job.id, operation=next_operation.id, process=next_process,
                                machine=None, event='Job transferred')
        else:
            next_process = 'Sink'
            yield self.model[next_process].store.put(job)
            yield self.machines.put(machine)
            self.monitor.record(time=self.env.now, part_id=job.id, operation=None, process=next_process, machine=None,
                                event='Job transferred')

    def dispatching(self):
        def spt(self) -> Job:
            """Shortest Processing Time: 가장 짧은 공정 시간을 가진 작업을 선택"""
            return min(self.store.items, key=lambda job: job.operation_list[job.step].processing_time[self.id])

        def wspt(self) -> Job:
            """Weighted Shortest Processing Time: 가장 짧은 가중 공정 시간을 가진 작업을 선택"""
            return min(self.store.items, key=lambda job: job.operation_list[job.step].processing_time[self.id]/job.weight)

        def lpt(self) -> Job:
            """Longest Processing Time: 가장 긴 공정 시간을 가진 작업을 선택"""
            return max(self.store.items, key=lambda job: job.operation_list[job.step].processing_time[self.id])

        def mwkr(self) -> Job:
            """Most Work Remaining: 남은 공정 시간의 총합이 가장 긴 작업을 선택"""

            def get_remaining_work(job: Job):
                remain_time_list = [job.operation_list[job.step].processing_time[self.id]]
                for op in job.operation_list[job.step+1:]:
                    times = op.processing_time.values()
                    remain_time_list.append(sum(times)/len(times))
                return sum(remain_time_list)

            return max(self.store.items, key=get_remaining_work)

        def lwkr(self) -> Job:
            """Least Work Remaining: 남은 공정 시간의 총합이 가장 짧은 작업을 선택"""

            def get_remaining_work(job: Job):
                remain_time_list = [job.operation_list[job.step].processing_time[self.id]]
                for op in job.operation_list[job.step + 1:]:
                    times = op.processing_time.values()
                    remain_time_list.append(sum(times) / len(times))
                return sum(remain_time_list)

            return min(self.store.items, key=get_remaining_work)

        def random(self) -> Job:
            """Random Selection: 대기 중인 작업 중에서 무작위로 하나를 선택"""
            return rd.choice(self.store.items)

        # 설정된 디스패칭 규칙에 따라 다음 작업 선택
        if self.dispatching_rule == 'SPT':
            selected_job = spt(self)
        elif self.dispatching_rule == 'WSPT':
            selected_job = wspt(self)
        elif self.dispatching_rule == 'LPT':
            selected_job = lpt(self)
        elif self.dispatching_rule == 'MWKR':
            selected_job = mwkr(self)
        elif self.dispatching_rule == 'LWKR':
            selected_job = lwkr(self)
        elif self.dispatching_rule == 'RANDOM':
            selected_job = random(self)
        else:  # 기본값은 FIFO
            selected_job = self.store.items[0]

        return selected_job

    def routing(self, next_operation):
        def random(operation):
            return rd.choice(operation.process_list)

        def spt(operation):
            return min(operation.processing_time, key=operation.processing_time.get)

        def lpt(operation):
            return max(operation.processing_time, key=operation.processing_time.get)

        def wspt(operation):
            return min(operation.processing_time, key=operation.processing_time.get)

        if self.routing_rule == 'RANDOM':
            next_process = random(next_operation)
        elif self.routing_rule == 'SPT':
            next_process = spt(next_operation)
        elif self.routing_rule == 'LPT':
            next_process = lpt(next_operation)
        elif self.routing_rule == 'WSPT':
            next_process = spt(next_operation)
        else:
            next_process = next_operation.process_list[0]


        return next_process