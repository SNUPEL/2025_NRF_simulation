import simpy
import random
from DT.components.Job import Job
from DT.components.Sink import Sink

class Process:
    def __init__(self, model, monitor, id, problem_data: dict, env: simpy.Environment):
        self.model = model
        self.monitor = monitor
        self.id = id
        self.proc_data = problem_data['process_info']
        self.env = env
        self.process_routing = 'Random'

        self.store = simpy.FilterStore(env)
        self.machines = simpy.FilterStore(self.env, capacity=self.proc_data[self.id]['capacity'])
        for i in range(self.machines.capacity):
            self.machines.put('Machine' + str(i))

        self.parts_sent = 0
        self.util_time = 0

        self.env.process(self.run())

    def run(self):
        while True:
            machine = yield self.machines.get()
            job = yield self.store.get()
            self.monitor.record(time=self.env.now, part_id=job.id, operation=job.operation_list[job.step].id, process=self.id,machine=machine, event='job assigned')
            yield self.env.process(self.processing(job, machine))

    def processing(self, job, machine):
        operation = job.operation_list[job.step]
        if not operation.processing_time:
            operation_time = operation.processing_time
        else:
            operation_time = job.operation_times[job.step]
        yield self.env.timeout(operation_time)
        self.monitor.record(time=self.env.now, part_id=job.id, operation=operation.id, process=self.id,machine=machine, event='operation complete')
        yield self.env.process(self.to_next_process(job, machine))

    def to_next_process(self, job, machine):
        job.step += 1
        if job.step != len(job.operation_list):
            next_operation = job.operation_list[job.step]
            if self.process_routing == 'Random':
                next_process= self.random(next_operation)
            print('다음 프로세스:', next_process)
            yield self.model[next_process].store.put(job)
            yield self.machines.put(machine)
            self.monitor.record(time=self.env.now, part_id=job.id, operation=next_operation.id, process=next_process,machine=None, event='Job transferred')
        else:
            next_process = 'Sink'
            yield self.model[next_process].store.put(job)
            yield self.machines.put(machine)
            self.monitor.record(time=self.env.now, part_id=job.id, operation=None, process=next_process, machine=None, event='Job transferred')

    def random(self, operation):
        return random.choice(operation.process_list)