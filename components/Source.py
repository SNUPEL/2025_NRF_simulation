import simpy
from typing import List, Dict
from components.job import Job
from components.Process import job_lifecycle
from components.Sink import Sink


def job_generator(env: simpy.Environment, jobs_data: List[Dict], machine_store: simpy.FilterStore, sink: Sink):
    """
    시뮬레이션 시작 시, 주어진 데이터로부터 Job들을 생성하고,
    각 Job을 처리할 Process(작업자)를 생성하여 실행시키는 '기동 장치' 역할을
    이 함수 자체가 하나의 SimPy 프로세스

    Args:
        env (simpy.Environment): SimPy 시뮬레이션 환경
        jobs_data (List[Dict]): 모든 Job의 정보가 담긴 리스트
        machine_store (simpy.FilterStore): 중앙 기계 관리소
        sink (Sink): 결과 기록용 싱크 객체
    """
    print(f"[Time {env.now:5.2f}] Source: Job 생성을 시작합니다.")

    # 모든 Job을 시뮬레이션 시작과 동시에(Time=0) 투입
    for job_info in jobs_data:
        # 1. Job 데이터로부터 Job 객체를 생성
        new_job = Job(job_info['id'], job_info['operations'])

        # 2. 생성된 Job을 처리할 'job_lifecycle' 프로세스를 SimPy 환경에 등록하고 시작
        env.process(job_lifecycle(env, new_job, machine_store, sink))

    # 모든 Job 생성이 완료되었음을 알림
    yield env.timeout(0)
    print(f"[Time {env.now:5.2f}] Source: 모든 Job 생성 및 프로세스 할당 완료.")