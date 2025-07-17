from typing import List, Optional
from DT.components.Operation import Operation


class Job:
    """
    하나의 '작업(Job)'에 대한 모든 정보와 현재 진행 상태를 관리하는 데이터 클래스
    """

    def __init__(self, job_info: dict, operations_data: List):
        # Job의 고유 식별 번호 (예: 1, 2, 3)
        self.id = job_info['id']

        # 이 Job을 구성하는 Operation 객체들의 '순서가 있는' 리스트
        # JSSP의 핵심인 고유한 공정 경로(Routing)를 이 리스트가 표현합니다.
        self.operation_list: List[Operation] = [Operation(operations_data[op]) for op in job_info['operations']]
        self.operation_times = job_info['operation_times']

        # 시뮬레이션 기록을 위한 변수들
        self.arrival_time = job_info['arrival_time']  # 시스템 도착 시간
        self.completion_time = -1.0  # 시스템 완료 시간. -1은 아직 미완료 상태임을 의미.

        # Job의 진행 상태를 추적하는 인덱스. 0에서 시작
        self.step = 0

    def __repr__(self):
        """Job 객체 출력 형식 정의"""
        return f"Job(id={self.id})"