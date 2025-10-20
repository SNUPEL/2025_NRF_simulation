class Operation:
    """
    가장 작은 작업 단위인 '공정(Operation)'의 정보를 담는 데이터 클래스
    Job의 일부로서 정보를 제공하는 역할
    """

    def __init__(self, operation_data: dict):
        # 공정의 이름 (예: "J1_Op1")
        self.id = operation_data['id']

        # 이 공정을 수행하는 데 필요한 기계의 종류 (예: "M1")
        self.process_list = operation_data['process']
        from typing import List, Dict

        class Operation:
            """
            하나의 '작업 단위(Operation)'에 대한 정보를 관리하는 데이터 클래스.
            """

            def __init__(self, op_info: Dict):
                self.id: str = op_info['id']

                # 이 Operation을 처리할 수 있는 Process(기계)의 ID 리스트
                self.process_list: List[str] = op_info['process']

                # process_list의 각 Process에 해당하는 처리 시간 리스트
                self.processing_time: List[float] = op_info['processing_time']

            def get_processing_time_for_process(self, process_id: str) -> float:
                """특정 Process ID에 해당하는 처리 시간을 반환합니다."""
                try:
                    idx = self.process_list.index(process_id)
                    return self.processing_time[idx]
                except (ValueError, IndexError):
                    # 해당 process_id가 리스트에 없거나 인덱스가 잘못된 경우
                    return float('inf')

            def get_average_processing_time(self) -> float:
                """이 Operation의 평균 처리 시간을 계산합니다."""
                if not self.processing_time:
                    return 0.0
                return sum(self.processing_time) / len(self.processing_time)

            def get_process_time_map(self) -> Dict[str, float]:
                """Process ID를 키로, 처리 시간을 값으로 하는 딕셔너리를 반환합니다."""
                return dict(zip(self.process_list, self.processing_time))

            def __repr__(self) -> str:
                """Operation 객체 출력 형식 정의"""
                return f"Operation(id={self.id})"
        # 해당 기계에서 이 공정을 수행하는 데 걸리는 시간
        self.processing_time = {operation_data['process'][i]:operation_data['processing_time'][i] for i in range(len(operation_data['process']))}

    def __repr__(self):
        return f"Operation(name={self.id}, machine={self.process_list}, time={self.processing_time})"