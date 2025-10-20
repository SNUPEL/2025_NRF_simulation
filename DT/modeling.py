import simpy
import pandas as pd
import sys
import os
from typing import Dict, Optional

from DT.utils.benchmarking_converter import convert_banchmarking_data
from DT.utils.postprocessing import plot_gantt_chart
from DT.components.Source import Source
from DT.components.Process import Process
from DT.components.Sink import Sink
from DT.components.Monitor import Monitor
from DT.components.Job import Job
from DT.components.Operation import Operation


def load_data_from_unified_csv(data_dir: str, problem_name: str) -> Optional[Dict]:
    print(f"\n--- STEP 2: '{problem_name}' 문제의 통합 CSV 데이터 로딩 시작 ---")
    try:
        csv_path = os.path.join(data_dir, f"problem_{problem_name}.csv")
        df = pd.read_csv(csv_path)

        job_info, op_info, proc_info = {}, {}, {}

        for _, row in df[['machine', 'capacity']].drop_duplicates().iterrows():
            proc_id = str(row['machine'])
            proc_info[proc_id] = {'id': proc_id, 'capacity': int(row['capacity'])}

        for op_id, group in df.groupby('operation'):
            op_id_str = str(op_id)
            op_info[op_id_str] = {
                'id': op_id_str,
                'process': [str(m) for m in group['machine'].tolist()],
                'processing_time': group['processing_time'].tolist()
            }

        def get_op_seq_num(op_name):
            # "J1_O10" -> 10, "J5_O2" -> 2
            return int(str(op_name).split('_O')[-1])

        for job_id, group in df.groupby('job'):
            job_id_str = str(job_id)
            sorted_ops = sorted(group['operation'].unique(), key=get_op_seq_num)

            job_info[job_id_str] = {
                'id': job_id_str,
                'arrival_time': group['arrival_time'].iloc[0],
                'operations': [str(op) for op in sorted_ops]
            }
            if 'weight' in group.columns and not pd.isna(group['weight'].iloc[0]):
                job_info[job_id_str]['weight'] = group['weight'].iloc[0]

        print(f"'{problem_name}' 문제에 대한 통합 CSV 데이터 로딩 및 변환 성공.")
        return {'job_info': job_info, 'operation_info': op_info, 'process_info': proc_info}

    except FileNotFoundError as e:
        print(f"오류: 통합 CSV 데이터 로딩 실패. 파일을 찾을 수 없습니다: {e}")
        return None
    except Exception as e:
        print(f"오류: 데이터 파싱 중 예상치 못한 오류 발생: {e}")
        return None


# (이하 run_simulation, main 함수는 변경 없음)
def run_simulation(problem_data: Dict, event_log_path: str, sequencing_rule: str, routing_rule: str,
                   dispatching_rule: str, significant_digits: int) -> Monitor:
    print(f"\n--- STEP 3: 시뮬레이션 시작 (규칙: Seq={sequencing_rule}, Route={routing_rule}, Dispatch={dispatching_rule}) ---")
    env = simpy.Environment()
    model = {}
    monitor = Monitor(event_log_path, significant_digits)
    model['Source'] = Source(model, monitor, 'Source', problem_data, env, sequencing_rule, routing_rule)
    model['Sink'] = Sink(model, monitor, 'Sink', env)
    for proc_id in problem_data.get('process_info', {}).keys():
        process_instance = Process(model, monitor, proc_id, problem_data, env, dispatching_rule)
        model[proc_id] = process_instance
    env.run()
    print("시뮬레이션 종료.")
    return monitor


def main():
    dt_folder_path = os.path.dirname(os.path.abspath(__file__))
    is_bench_marking = True
    significant_digits = 10

    PROBLEM_TYPE = "PMSP"
    problem_name = "MJ5-200NC1"

    DATA_FOLDER = "data"
    PROBLEM_FOLDER = "problem"
    RESULTS_FOLDER = "results"

    data_dir = os.path.join(dt_folder_path, DATA_FOLDER)
    problem_dir = os.path.join(dt_folder_path, PROBLEM_FOLDER, PROBLEM_TYPE)
    results_dir = os.path.join(dt_folder_path, RESULTS_FOLDER)

    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(results_dir, exist_ok=True)

    if is_bench_marking:
        txt_file_path = os.path.join(problem_dir, f"{problem_name}.txt")
        convert_banchmarking_data(txt_file_path, data_dir, PROBLEM_TYPE)

    data_dict = load_data_from_unified_csv(data_dir, problem_name)
    if not data_dict:
        print("데이터 로딩에 실패하여 프로그램을 종료합니다.")
        return

    log_output_path = os.path.join(results_dir, f"event_log_{problem_name}.csv")

    if PROBLEM_TYPE == "JSSP":
        SEQUENCING_RULE = "FIFO"
        ROUTING_RULE = "SPT"
        DISPATCHING_RULE = "MWKR"
    elif PROBLEM_TYPE == "PFSP":
        SEQUENCING_RULE = "PALMER"
        ROUTING_RULE = "SPT"
        DISPATCHING_RULE = "FIFO"
    elif PROBLEM_TYPE == "PMSP":
        SEQUENCING_RULE = "WSPT"
        ROUTING_RULE = "WSPT"
        DISPATCHING_RULE = "WSPT"
    else:
        SEQUENCING_RULE = "RANDOM"
        ROUTING_RULE = "RANDOM"
        DISPATCHING_RULE = "RANDOM"

    monitor = run_simulation(data_dict, log_output_path, SEQUENCING_RULE, ROUTING_RULE, DISPATCHING_RULE,
                             significant_digits)

    print("\n--- STEP 4: 결과 저장 시작 ---")
    monitor.make_event_tracer()
    monitor.save_event_tracer()
    print(f"최종 이벤트 로그가 '{log_output_path}'에 저장되었습니다.")

    plot_gantt_chart(log_output_path)

if __name__ == "__main__":
    main()