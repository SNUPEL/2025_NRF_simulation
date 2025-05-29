class Operation:
    """
    가장 작은 작업 단위인 '공정(Operation)'의 정보를 담는 데이터 클래스
    Job의 일부로서 정보를 제공하는 역할
    """

    def __init__(self, name: str, machine_type: str, processing_time: float):
        # 공정의 이름 (예: "J1_Op1")
        self.name = name

        # 이 공정을 수행하는 데 필요한 기계의 종류 (예: "M1")
        self.machine_type = machine_type

        # 해당 기계에서 이 공정을 수행하는 데 걸리는 시간
        self.processing_time = processing_time

    def __repr__(self):
        return f"Operation(name={self.name}, machine={self.machine_type}, time={self.processing_time})"