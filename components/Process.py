import simpy
from components.job import Job
from components.Sink import Sink


def job_lifecycle(env: simpy.Environment, job: Job, machine_store: simpy.FilterStore, sink: Sink):
    """
    하나의 Job을 할당받아, 그 Job이 완료될 때까지의 전 과정을 책임지는 '작업자' 프로세스
    JSSP의 핵심인 기계 요청, 작업 수행, 대기, 반납 로직 포함

    Args:
        env (simpy.Environment): SimPy 시뮬레이션 환경
        job (Job): 이 프로세스가 담당할 Job 객체
        machine_store (simpy.FilterStore): 기계를 요청하고 반납할 중앙 관리소
        sink (Sink): 작업 완료 후 결과를 보고할 싱크 객체
    """
    # Job이 시스템에 도착했음을 기록
    job.arrival_time = env.now
    print(f"[Time {env.now:5.2f}] Job {job.id}: 시스템 도착. 공정 시작.")

    # Job의 모든 공정이 끝날 때까지 아래 로직을 반복
    while not job.is_finished():
        # 1. Job 객체에게 현재 수행해야 할 공정(Operation)이 무엇인지 물어봅니다.
        operation = job.get_current_operation()

        # 2. 중앙 관리소(machine_store)에 필요한 기계를 요청
        print(
            f"[Time {env.now:5.2f}] Job {job.id}: '{operation.name}' 수행 위해 Machine type '{operation.machine_type}' 요청.")

        # 기계를 얻을 때까지 이 프로세스는 여기서 '일시 정지(대기)' 상태가 됩
        # SimPy, 기계가 사용 가능해지면 이 프로세스를 자동으로 다시 시작
        requested_machine = yield machine_store.get(lambda m: m.type == operation.machine_type)

        print(f"[Time {env.now:5.2f}] Job {job.id}: Machine '{requested_machine.id}' 할당 받음. '{operation.name}' 시작.")

        # 3. 기계를 할당받았으므로, 공정 소요 시간만큼 작업을 시뮬레이션
        #    'yield env.timeout()'은 주어진 시간만큼 이 프로세스를 '일시 정지'시킵니다.
        yield env.timeout(operation.processing_time)

        # 4. 작업이 끝났으므로, 사용한 기계를 중앙 관리소에 반납
        #    이 기계를 기다리던 다른 프로세스가 있다면, SimPy가 그 프로세스에게 기계를 넘겨줌
        yield machine_store.put(requested_machine)

        print(f"[Time {env.now:5.2f}] Job {job.id}: '{operation.name}' 완료. Machine '{requested_machine.id}' 반납.")

        # 5. Job 객체에게 현재 공정이 끝났음을 알리고, 상태를 다음 공정으로 업데이트
        job.advance_to_next_operation()

    # while 루프가 끝났다는 것은 Job의 모든 공정이 완료되었음을 의미
    # Sink에 최종 완료 사실을 보고
    sink.record_completion(job)