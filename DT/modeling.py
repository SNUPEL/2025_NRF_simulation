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
from DT.components.Machine import Machines


def load_data_from_unified_csv(data_dir: str, problem_name: str) -> Optional[Dict]:
    print(f"\n--- STEP 2: '{problem_name}' 문제의 통합 CSV 데이터 로딩 시작 ---")
    try:
        csv_path = os.path.join(data_dir, f"problem_{problem_name}.csv")
        df = pd.read_csv(csv_path)

        job_info, op_info, machine_info = {}, {}, {}

        for machine_id, group in df.groupby('machine', sort=False):
            machine_id_str = str(machine_id)
            # 해당 machine에 대한 unique한 process 값들을 리스트로 생성
            unique_processes = group['process'].unique().tolist()

            machine_info[machine_id_str] = {
                'id': machine_id_str,
                'capacity': int(group['capacity'].iloc[0]),  # capacity는 동일하다고 가정
                'processes': [str(p) for p in unique_processes]  # process 리스트 추가
            }

        for op_id, group in df.groupby(df['job'].astype(str) + '_' + df['operation'].astype(str), sort=False):
            op_id_str = str(op_id)
            op_info[op_id_str] = {
                'id': op_id_str,
                'process': group['process'].tolist(),
                'machine': [str(m) for m in group['machine'].tolist()],
                'processing_time': group['processing_time'].tolist()
            }

        def get_op_seq_num(op_name):
            # "J1_O10" -> 10, "J5_O2" -> 2
            return int(str(op_name).split('O')[-1])

        for job_id, group in df.groupby('job', sort=False):
            job_id_str = str(job_id)
            # 해당 job_id에 해당하는 행만 필터링하여 'job'과 'operation'을 '_'로 이어붙인 리스트 생성
            job_operations = (df.loc[df['job'] == job_id, 'job'].astype(str) + '_' + df.loc[
                df['job'] == job_id, 'operation'].astype(str)).unique()
            # 정렬
            sorted_ops = sorted(job_operations, key=get_op_seq_num)

            job_info[job_id_str] = {
                'id': job_id_str,
                'arrival_time': group['arrival_time'].iloc[0],
                'operations': [str(op) for op in sorted_ops]
            }
            if 'weight' in group.columns and not pd.isna(group['weight'].iloc[0]):
                job_info[job_id_str]['weight'] = group['weight'].iloc[0]

        process_list = df['process'].unique().tolist()

        print(f"'{problem_name}' 문제에 대한 통합 CSV 데이터 로딩 및 변환 성공.")
        return {'job_info': job_info, 'operation_info': op_info, 'machine_info': machine_info, 'process_list': process_list}

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
    resource = {}
    monitor = Monitor(event_log_path, significant_digits)

    resource['Machines'] = Machines(problem_data, env, dispatching_rule)

    model['Source'] = Source(model, monitor, 'Source', problem_data, env, sequencing_rule, routing_rule)
    model['Sink'] = Sink(model, monitor, 'Sink', env)
    for proc_id in problem_data.get('process_list', []):
        process_instance = Process(model, resource, monitor, proc_id, problem_data, env, dispatching_rule)
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
        SEQUENCING_RULE = "FIFO"            ### JSSP에서 SEQUENCING은 FIFO로 고정
        ROUTING_RULE = "FIFO"               ### JSSP에서 ROUTING은 의미 없음
        DISPATCHING_RULE = "SPT"            ### DISPATCHING rule 선택(SPT, WSPT, LPT, MWKR, LWKR, RANDOM, FIFO)
    elif PROBLEM_TYPE == "PFSP":
        SEQUENCING_RULE = "JOHNSON"          ### SEQUENCING rule 선택(SPT, LPT, WSPT, JOHNSON, PALMER, RANDOM, FIFO)
        ROUTING_RULE = "FIFO"                ### PFSP에서 ROUTING은 의미 없음
        DISPATCHING_RULE = "FIFO"           ### PFSP에서 DISPATCHING은 FIFO로 고정
    elif PROBLEM_TYPE == "PMSP":
        SEQUENCING_RULE = "WSPT"            ### SEQUENCING rule 선택(SPT, LPT, WSPT, JOHNSON, PALMER, RANDOM, FIFO)
        ROUTING_RULE = "WSPT"               ### ROUTING rule 선택(SPT, WSPT, LPT, RANDOM, DEFAULT)
        DISPATCHING_RULE = "WSPT"           ### DISPATCHING rule 선택(SPT, WSPT, LPT, RANDOM, FIFO)
    else:
        SEQUENCING_RULE = "RANDOM"          ### SEQUENCING rule 선택(SPT, LPT, WSPT, JOHNSON, PALMER, RANDOM, FIFO)
        ROUTING_RULE = "RANDOM"             ### ROUTING rule 선택(SPT, WSPT, LPT, RANDOM, DEFALT)
        DISPATCHING_RULE = "RANDOM"         ### DISPATCHING rule 선택(SPT, WSPT, LPT, MWKR, LWKR, RANDOM, FIFO)

    monitor = run_simulation(data_dict, log_output_path, SEQUENCING_RULE, ROUTING_RULE, DISPATCHING_RULE,
                             significant_digits)

    print("\n--- STEP 4: 결과 저장 시작 ---")
    monitor.make_event_tracer()
    monitor.save_event_tracer()
    print(f"최종 이벤트 로그가 '{log_output_path}'에 저장되었습니다.")

    plot_gantt_chart(log_output_path)

if __name__ == "__main__":
    main()