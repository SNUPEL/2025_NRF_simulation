import simpy
import pandas as pd
import sys
import os
from typing import List, Dict, Optional
from utils.Jobshop_converter import *

# 시뮬레이션 컴포넌트 임포트
try:
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.append(project_root)
    from DT.components.Source import Source
    from DT.components.Process import Process
    from DT.components.Sink import Sink
    from DT.components.Monitor import Monitor
except ImportError:
    print("오류: DT.components 모듈을 찾을 수 없습니다.")
    print("프로젝트 구조를 확인해주세요: 이 스크립트는 'DT' 폴더 안에 위치해야 합니다.")
    sys.exit(1)

# 데이터 로딩 함수
def load_data_from_csv(data_dir: str) -> Optional[Dict]:
    """변환된 CSV 파일들을 읽어 시뮬레이션에 필요한 데이터 딕셔너리를 생성합니다."""
    print("\n--- STEP 2: CSV 데이터 로딩 시작 ---")
    try:
        job_df = pd.read_csv(os.path.join(data_dir, "job_sample.csv"))
        op_df = pd.read_csv(os.path.join(data_dir, "operation_sample.csv"))
        proc_df = pd.read_csv(os.path.join(data_dir, "process_sample.csv"))

        job_info, op_info, proc_info = {}, {}, {}
        max_ops = int((job_df.shape[1] - 2) / 2)

        for _, row in job_df.iterrows():
            job_id = str(row['id'])
            # op{i}_id가 비어있지 않은 모든 경우를 포함 (작업시간 0 포함)
            ops = [str(row[f'op{i}_id']) for i in range(1, 1 + max_ops) if
                   pd.notna(row[f'op{i}_id']) and row[f'op{i}_id'] != '']
            times = [float(row[f'op{i}_time']) for i in range(1, 1 + max_ops) if
                     pd.notna(row[f'op{i}_id']) and row[f'op{i}_id'] != '']

            job_info[job_id] = {'id': job_id, 'arrival_time': row['arrival_time'], 'operations': ops,
                                'operation_times': times}

        for _, row in op_df.iterrows():
            op_id = str(row['id'])
            op_info[op_id] = {'id': op_id, 'process': str(row['process']).split(','),
                              'processing_time': [float(t) for t in str(row['time']).split(',')]}

        proc_info = {str(row['id']): {'id': str(row['id']), 'capacity': row['capacity']} for _, row in
                     proc_df.iterrows()}

        print("CSV 데이터 로딩 성공.")
        return {'job_info': job_info, 'operation_info': op_info, 'process_info': proc_info}

    except FileNotFoundError as e:
        print(f"CSV 데이터 로딩 실패: {e}")
        return None

# 시뮬레이션 구동 함수
def run_simulation(problem_data: Dict, event_log_path: str) -> Monitor:
    """데이터를 기반으로 SimPy 시뮬레이션 환경을 구축하고 실행합니다."""
    print("\n--- STEP 3: 시뮬레이션 시작 ---")
    env = simpy.Environment()
    model = {}
    monitor = Monitor(event_log_path)

    model['Source'] = Source(model, monitor, 'Source', problem_data, env)
    model['Sink'] = Sink(model, monitor, 'Sink', env)
    for proc_id in problem_data.get('process_info', {}).keys():
        model[proc_id] = Process(model, monitor, proc_id, problem_data, env)

    env.run()
    print("시뮬레이션 종료.")
    return monitor

# 메인 실행 함수
def main():
    """스크립트의 전체 실행 흐름을 제어합니다."""

    # --- 설정 (이 부분만 수정하면 됩니다) ---
    TXT_FILENAME = "la38.txt"
    PROBLEM_FOLDER = "problem"
    DATA_FOLDER = "data"
    RESULTS_FOLDER = "results"

    # --- 실행 ---
    print("=" * 50)
    print("JSSP 데이터 변환 및 시뮬레이션 통합 실행을 시작합니다.")
    print("=" * 50)

    # 이 스크립트가 DT 폴더 안에 있다고 가정하고 경로를 설정
    dt_folder_path = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(dt_folder_path)

    print(f"프로젝트 루트: {project_root}")

    # 모든 경로를 올바르게 계산
    txt_file_path = os.path.join(dt_folder_path, PROBLEM_FOLDER, TXT_FILENAME)
    results_dir = os.path.join(dt_folder_path, RESULTS_FOLDER)

    data_dir = os.path.join(dt_folder_path, DATA_FOLDER)  # DT 폴더 내에 data 폴더 생성

    # 폴더 자동 생성
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(results_dir, exist_ok=True)

    if not convert_jssp_to_csvs(txt_file_path, data_dir):
        print("\n변환 실패로 인해 프로그램을 종료합니다.")
        return

    data_dict = load_data_from_csv(data_dir)
    if not data_dict:
        print("\n데이터 로딩 실패로 인해 프로그램을 종료합니다.")
        return

    log_output_path = os.path.join(results_dir, "event_log.csv")
    monitor = run_simulation(data_dict, log_output_path)

    print("\n--- STEP 4: 결과 저장 시작 ---")
    monitor.make_event_tracer()
    monitor.save_event_tracer()
    print(f"최종 이벤트 로그가 '{log_output_path}'에 저장되었습니다.")

    print("=" * 50)
    print("모든 작업이 성공적으로 완료되었습니다.")
    print("=" * 50)


if __name__ == "__main__":
    main()