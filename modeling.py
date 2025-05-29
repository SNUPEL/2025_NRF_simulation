import simpy
import csv
import sys
import os

from typing import List, Dict

from components.Machine import create_machine_store
from components.Source import job_generator
from components.Sink import Sink

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 1. 현재 파일 형식에 맞는 데이터 로딩 함수

def load_data_from_wide_csv(filepath: str) -> Dict[str, List]:
    """
    한 행에 한 Job의 모든 공정이 나열된 '가로로 넓은' 형식의 CSV 파일을 읽어,
    시뮬레이션에 필요한 데이터 구조로 변환합니다.

    Args:
        filepath (str): 'wide' 형식의 CSV 파일 경로

    Returns:
        Dict[str, List]: 'jobs'와 'machines' 키를 가진 딕셔너리
    """
    jobs_data = []
    machine_ids = set()

    # 'utf-8-sig'는 파일 맨 앞에 보이지 않는 문자(BOM)가 있을 경우를 대비한 안전한 인코딩 방식입니다.
    with open(filepath, mode='r', encoding='utf-8-sig') as infile:
        reader = csv.DictReader(infile)

        # 파일의 헤더(첫 줄)를 기반으로 총 공정 수를 추정합니다.
        # (전체 열 개수 - 1) / 2 = 총 공정(Operation) 수
        if not reader.fieldnames:
            raise ValueError("CSV 파일이 비어있거나 헤더를 읽을 수 없습니다.")
        num_operations = (len(reader.fieldnames) - 1) // 2

        # 각 행(row)은 하나의 Job을 나타냅니다.
        for row in reader:
            job_id = int(row['Job_ID'])
            operations = []

            # Machine_Op1, Time_Op1, Machine_Op2, Time_Op2... 형식의 열을 순회합니다.
            for i in range(1, num_operations + 1):
                machine_key = f'Machine_Op{i}'
                time_key = f'Time_Op{i}'

                # 해당 열이 존재하고 값이 비어있지 않은지 확인합니다.
                if row.get(machine_key) and row.get(time_key):
                    machine_id = row[machine_key]
                    processing_time = float(row[time_key])

                    # 발견된 기계 ID를 전체 기계 목록에 추가합니다.
                    machine_ids.add(machine_id)

                    operation_info = {
                        'name': f"J{job_id}_Op{i}",
                        'machine_type': machine_id,
                        'processing_time': processing_time
                    }
                    operations.append(operation_info)

            jobs_data.append({'id': job_id, 'operations': operations})

    # 수집된 기계 ID를 기반으로 machines 데이터 구조를 생성합니다.
    machines_data = [{'id': mid, 'type': mid} for mid in sorted(list(machine_ids))]

    return {'jobs': jobs_data, 'machines': machines_data}


# 2. 시뮬레이션 실행 함수

def run_simulation(data_filepath: str):
    """
    전체 JSSP 시뮬레이션을 설정하고 실행하는 함수
    """
    print(f"--- CSV 파일 '{data_filepath}' 기반의 시뮬레이션을 시작합니다 ---")

    # 1. 'wide' CSV 형식 파일로부터 시뮬레이션 데이터를 로드
    problem_data = load_data_from_wide_csv(data_filepath)

    # 2. SimPy 환경 및 핵심 컴포넌트를 생성
    env = simpy.Environment()
    sink = Sink(env)
    machine_store = create_machine_store(env, problem_data['machines'])

    # 3. Source 프로세스를 SimPy 환경에 등록하여 시뮬레이션을 시작
    env.process(job_generator(env, problem_data['jobs'], machine_store, sink))

    # 4. SimPy 환경을 실행
    env.run()

    # 5. 시뮬레이션 결과를 출력합
    sink.print_summary()


if __name__ == "__main__":
    # 불러올 CSV 파일 이름을 지정합
    CSV_FILE = "la10.csv"
    run_simulation(CSV_FILE)