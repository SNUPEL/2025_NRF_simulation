import simpy
from typing import List
from DT.components.Job import Job


class Sink:
    """
    완료된 Job들을 수집하고, 시뮬레이션의 최종 결과를 계산 및 출력
    """

    def __init__(self, env: simpy.Environment):
        # SimPy 환경 객체를 저장하여 현재 시간을 조회(env.now)할 수 있도록 함
        self.env = env
        # 완료된 Job 객체들을 저장할 리스트
        self.completed_jobs: List[Job] = []
        print("Sink: 결과 기록 준비 완료.")

    def record_completion(self, job: Job):
        """
        Process(작업자)가 작업을 마친 Job을 받아 기록하는 메소드입니다.
        """
        # Job 객체에 최종 완료 시간을 기록. env.now는 현재 SimPy 시간을 의미
        job.completion_time = self.env.now

        # 완료된 Job 리스트에 추가
        self.completed_jobs.append(job)

        flow_time = job.completion_time - job.arrival_time
        print(f"[Time {self.env.now:5.2f}] Sink: Job {job.id} 최종 완료 기록. (Flow Time: {flow_time:.2f})")

    def print_summary(self):
        """
        시뮬레이션이 모두 종료된 후, 최종 결과를 계산하고 출력
        """
        print("\n" + "=" * 40)
        print("          시뮬레이션 최종 결과")
        print("=" * 40)

        if not self.completed_jobs:
            print("완료된 작업이 없습니다.")
            return

        # Makespan: 모든 Job들 중 가장 늦게 끝난 시간
        makespan = max(job.completion_time for job in self.completed_jobs)

        # # 평균 Flow Time: 각 Job이 시스템에 머무른 시간의 평균
        # total_flow_time = sum(j.completion_time - j.arrival_time for j in self.completed_jobs)
        # avg_flow_time = total_flow_time / len(self.completed_jobs)

        print(f"총 소요 시간 (Makespan)        : {makespan:.2f}")
        # print(f"평균 시스템 체류 시간 (Flow Time) : {avg_flow_time:.2f}")
        print(f"총 처리 작업 수              : {len(self.completed_jobs)}")
        print("=" * 40)