from typing import List, Optional
from components.operation import Operation


class Job:
    """
    하나의 '작업(Job)'에 대한 모든 정보와 현재 진행 상태를 관리하는 데이터 클래스
    """

    def __init__(self, job_id: int, operations_data: List[dict]):
        # Job의 고유 식별 번호 (예: 1, 2, 3)
        self.id = job_id

        # 이 Job을 구성하는 Operation 객체들의 '순서가 있는' 리스트
        # JSSP의 핵심인 고유한 공정 경로(Routing)를 이 리스트가 표현합니다.
        self.operations: List[Operation] = [Operation(**op_data) for op_data in operations_data]

        # Job의 진행 상태를 추적하는 인덱스. 0에서 시작합니다.
        self.current_op_idx = 0

        # 시뮬레이션 기록을 위한 변수들
        self.arrival_time = 0.0  # 시스템 도착 시간
        self.completion_time = -1.0  # 시스템 완료 시간. -1은 아직 미완료 상태임을 의미.

    def get_current_operation(self) -> Optional[Operation]:
        """현재 수행해야 할 공정 객체를 반환합니다."""
        if not self.is_finished():
            return self.operations[self.current_op_idx]
        return None

    def advance_to_next_operation(self):
        """하나의 공정을 마친 후, 다음 공정으로 상태를 업데이트합니다."""
        if not self.is_finished():
            self.current_op_idx += 1

    def is_finished(self) -> bool:
        """이 Job의 모든 공정이 완료되었는지 여부를 반환합니다."""
        return self.current_op_idx >= len(self.operations)

    def __repr__(self):
        """Job 객체 출력 형식 정의"""
        return f"Job(id={self.id})"