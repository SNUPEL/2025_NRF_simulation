import simpy
from typing import List, Dict, Union


class MachineInfo:
    """
    개별 기계의 고유 정보(속성)를 담는 데이터 클래스
    """

    def __init__(self, machine_id: str, machine_type: str):
        self.id = machine_id  # 기계의 고유 ID (예: "M1")
        self.type = machine_type  # 기계의 종류 (예: "M1")


def create_machine_store(env: simpy.Environment, machine_data: List[Dict]) -> simpy.FilterStore:
    """
    SimPy 환경과 기계 데이터를 받아, JSSP에 적합한 중앙 기계 관리소를 생성

    Args:
        env (simpy.Environment): SimPy 시뮬레이션 환경
        machine_data (List[Dict]): 기계 정보를 담은 딕셔너리 리스트

    Returns:
        simpy.FilterStore: 기계 객체들이 담겨 있는 SimPy의 FilterStore 객체
    """
    # FilterStore는 특정 조건을 만족하는 아이템을 필터링하여 요청할 수 있는 SimPy의 리소스 타입입니다.
    # "M1 타입의 기계를 주세요"와 같은 요청 처리에 매우 유용합니다.
    store = simpy.FilterStore(env, capacity=len(machine_data))

    # 기계 데이터로부터 MachineInfo 객체들을 생성하여 FilterStore에 넣어줍니다.
    store.items = [MachineInfo(m['id'], m['type']) for m in machine_data]

    return store