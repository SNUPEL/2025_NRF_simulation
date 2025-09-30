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

        # 해당 기계에서 이 공정을 수행하는 데 걸리는 시간
        self.processing_time = {operation_data['process'][i]:operation_data['processing_time'][i] for i in range(len(operation_data['process']))}

    def __repr__(self):
        return f"Operation(name={self.id}, machine={self.process_list}, time={self.processing_time})"