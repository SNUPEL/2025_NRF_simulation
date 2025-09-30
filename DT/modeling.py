import simpy
import pandas as pd
import sys
import os
from typing import List, Dict, Optional

from utils.benchmarking_converter import *
from utils.postprocessing import *

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
    sys.exit(1)

def load_data_from_csv(data_dir: str, problem_name: str) -> Optional[Dict]:
    print("\n--- STEP 2: CSV 데이터 로딩 시작 ---")
    try:
        job_csv_path = os.path.join(data_dir, f"job_{problem_name}.csv")
        op_csv_path = os.path.join(data_dir, f"operation_{problem_name}.csv")
        proc_csv_path = os.path.join(data_dir, f"process_{problem_name}.csv")
        job_df, op_df, proc_df = pd.read_csv(job_csv_path), pd.read_csv(op_csv_path), pd.read_csv(proc_csv_path)
        job_info, op_info, proc_info = {}, {}, {}
        max_ops = int((job_df.shape[1] - 2) / 2)

        for _, row in job_df.iterrows():
            job_id = str(row['id'])
            ops = [str(row[f'op{i}_id']) for i in range(1, 1 + max_ops) if
                   pd.notna(row[f'op{i}_id']) and row[f'op{i}_id'] != '']
            # times = {ops[i-1]:row[f'op{i}_time'] for i in range(1, 1 + max_ops) if
            #          pd.notna(row[f'op{i}_id']) and row[f'op{i}_id'] != ''}
            # 제외할 컬럼 리스트
            exclude_cols = {'id', 'arrival_time'} | {f'op{i}_id' for i in range(1, 1 + max_ops)}

            # 나머지 컬럼을 동적으로 딕셔너리에 추가
            extra_info = {col: row[col] for col in row.index if col not in exclude_cols}

            job_info[job_id] = {'id': job_id, 'arrival_time': row['arrival_time'], 'operations': ops, **extra_info}
        for _, row in op_df.iterrows():
            op_id = str(row['id'])
            op_info[op_id] = {'id': op_id, 'process': str(row['process']).split(','),
                              'processing_time': [float(t) for t in str(row['time']).split(',')]}
        proc_info = {str(row['id']): {'id': str(row['id']), 'capacity': row['capacity']} for _, row in
                     proc_df.iterrows()}
        print(f"'{problem_name}' 문제에 대한 CSV 데이터 로딩 성공.")
        return {'job_info': job_info, 'operation_info': op_info, 'process_info': proc_info}
    except FileNotFoundError as e:
        print(f"CSV 데이터 로딩 실패: {e}")
        return None

def run_simulation(problem_data: Dict, event_log_path: str, sequencing_rule: str, routing_rule: str, dispatching_rule: str, significant_digits: int) -> Monitor:
    print(f"\n--- STEP 3: 시뮬레이션 시작 (규칙: {dispatching_rule}) ---")
    env = simpy.Environment()
    model, monitor = {}, Monitor(event_log_path, significant_digits)
    model['Source'] = Source(model, monitor, 'Source', problem_data, env)
    model['Source'].sequencing_rule = sequencing_rule
    model['Source'].routing_rule = routing_rule
    model['Sink'] = Sink(model, monitor, 'Sink', env)
    for proc_id in problem_data.get('process_info', {}).keys():
        process_instance = Process(model, monitor, proc_id, problem_data, env)
        process_instance.dispatching_rule = dispatching_rule
        model[proc_id] = process_instance
    env.run()
    print("시뮬레이션 종료.")
    return monitor

# 메인 실행 함수
def main():
    dt_folder_path = os.path.dirname(os.path.abspath(__file__))

    is_bench_marking = True
    significant_digits = 10

    problem_name = "MJ5-200NC1"
    DATA_FOLDER = "data"
    data_dir = os.path.join(dt_folder_path, DATA_FOLDER)

    RESULTS_FOLDER = "results"
    results_dir = os.path.join(dt_folder_path, RESULTS_FOLDER)

    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(results_dir, exist_ok=True)

    if is_bench_marking:
        PROBLEM_TYPE = "PMSP"             # --- 문제 종류 선택: "JSSP", "PFSP", "PMSP" ---
        TXT_FILENAME = problem_name + ".txt"
        PROBLEM_FOLDER = "problem/" + PROBLEM_TYPE
        txt_file_path = os.path.join(dt_folder_path, PROBLEM_FOLDER, TXT_FILENAME)

        convert_banchmarking_data(txt_file_path, data_dir, PROBLEM_TYPE)

    data_dict = load_data_from_csv(data_dir, problem_name)
    if not data_dict: return

    log_output_path = os.path.join(results_dir, "event_log.csv")

    if PROBLEM_TYPE == "JSSP":
        SEQUENCING_RULE = "FIFO"  # JSSP는 시퀀싱 규칙 FIFO로 고정
        ROUTING_RULE = "SPT"  # --- 라우팅 규칙 설정: 'SPT', 'WSPT', 'LPT', 'RANDOM', FIFO 중 선택 ---
        DISPATCHING_RULE = "MWKR"  # --- 디스패칭 규칙 설정: 'SPT', 'WSPT', 'LPT', 'MWKR', 'LWKR', 'RANDOM', FIFO 중 선택 ---
    elif PROBLEM_TYPE == "PFSP":
        SEQUENCING_RULE = "PALMER"  # --- 시퀀싱 규칙 설정: 'SPT', 'WSPT' 'LPT', 'JOHNSON', 'PALMER', 'RANDOM', FIFO 중 선택 ---
        ROUTING_RULE = "SPT"  # --- 라우팅 규칙 설정: 'SPT', 'WSPT', 'LPT', 'RANDOM', FIFO 중 선택 ---
        DISPATCHING_RULE = "FIFO"  # --- PFSP는 디스패칭 규칙 FIFO로 고정

    elif PROBLEM_TYPE == "PMSP":
        SEQUENCING_RULE = "WSPT"  # --- 시퀀싱 규칙 설정: 'SPT', 'WSPT', 'LPT', 'JOHNSON', 'PALMER', 'RANDOM', FIFO 중 선택 ---
        ROUTING_RULE = "WSPT"  # --- 라우팅 규칙 설정: 'SPT', 'WSPT', 'LPT', 'RANDOM', FIFO 중 선택 ---
        DISPATCHING_RULE = "WSPT"  # --- 디스패칭 규칙 설정: 'SPT', 'WSPT', 'LPT', 'MWKR', 'LWKR', 'RANDOM', FIFO 중 선택 ---
    else:
        SEQUENCING_RULE = "RANDOM"  # --- 시퀀싱 규칙 설정: 'SPT', 'WSPT', 'LPT', 'JOHNSON', 'PALMER', 'RANDOM', FIFO 중 선택 ---
        ROUTING_RULE = "RANDOM"  # --- 라우팅 규칙 설정: 'SPT', 'WSPT', 'LPT', 'RANDOM', FIFO 중 선택 ---
        DISPATCHING_RULE = "RANDOM"  # --- 디스패칭 규칙 설정: 'SPT', 'WSPT', 'LPT', 'MWKR', 'LWKR', 'RANDOM', FIFO 중 선택 ---

    monitor = run_simulation(data_dict, log_output_path, SEQUENCING_RULE, ROUTING_RULE, DISPATCHING_RULE, significant_digits)

    print("\n--- STEP 4: 결과 저장 시작 ---")
    monitor.make_event_tracer()
    monitor.save_event_tracer()
    print(f"최종 이벤트 로그가 '{log_output_path}'에 저장되었습니다.")

    plot_gantt_chart(log_output_path)

if __name__ == "__main__":
    main()