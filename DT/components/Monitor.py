class Monitor(object):
    def __init__(self, filepath):
        self.filepath = filepath  ## Event tracer 저장 경로

        self.time = list()
        self.event = list()
        self.part = list()
        self.operation = list()
        self.process_name = list()
        self.machine_name = list()

        self.event_tracer = event_tracer = pd.DataFrame(columns=['Time', 'Part', 'Operation', 'Process', 'Machine', 'Event'])

    def record(self, time, part_id=None, operation=None, process=None, machine=None, event=None):
        self.time.append(time)
        self.event.append(event)
        self.part.append(part_id)
        self.operation.append(operation)
        self.process_name.append(process)
        self.machine_name.append(machine)

    def get_event_tracer(self):
        self.event_tracer['Time'] = self.time
        self.event_tracer['Part'] = self.part
        self.event_tracer['Operation'] = self.operation
        self.event_tracer['Process'] = self.process_name
        self.event_tracer['Machine'] = self.machine_name
        self.event_tracer['Event'] = self.event

    def save_event_tracer(self):
        self.event_tracer.to_csv(self.filepath)