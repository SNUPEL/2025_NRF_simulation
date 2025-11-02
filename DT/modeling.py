import simpy
import pandas as pd
import sys
import os
from typing import Dict, Optional
import json

from statsmodels.graphics.tukeyplot import results
from streamlit import columns
from sympy import pprint

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


def get_problem_names(folder_path):
    if not os.path.isdir(folder_path):
        raise ValueError(f"지정된 경로가 폴더가 아닙니다: {folder_path}")

    file_names = []
    for file in os.listdir(folder_path):
        full_path = os.path.join(folder_path, file)
        if os.path.isfile(full_path):
            name, _ = os.path.splitext(file)
            file_names.append(name)

    return file_names

def parse_jssp_results(result_path):
    df = pd.read_csv(result_path)
    data_dict = {
        row["Instance"].lower(): {
            "spt": row["SPT Solution"]
        }
        for _, row in df.iterrows()
    }
    return data_dict

def parse_pfsp_optimums(data_path):
    df = pd.read_csv(data_path)

    data_dict = {
        row["Name"].lower(): {
        "n": row["n"],
        "m": row["m"],
        "LB": row["LB"],
        "UB": row["UB"],
        "Optimal": row["Optimal"],
        "UBFoundBy": row["UBFoundBy"],
        "Permutation": row["Permutation"],
        }
        for _, row in df.iterrows()
    }
    return data_dict


def parse_pmsp_optimums(data_path):
    df = pd.read_csv(data_path)
    ofv_dict = dict(zip(df["name"], df["OFV"]))
    return ofv_dict


def get_ofv_time(event_df: pd.DataFrame,
                 weights: dict,
                 completion_events=("job completed", "job transferred to sink"),
                 fallback_event="operation complete"):

    df = event_df.copy()
    df["event"] = df["event"].astype(str).str.lower()

    df["time"] = pd.to_numeric(df["time"], errors="coerce")
    df = df.dropna(subset=["part_id", "time"])

    def _completion_time(g):
        g_sorted = g.sort_values("time")

        m1 = g_sorted[g_sorted["event"].isin([e.lower() for e in completion_events])]

        if not m1.empty:
            return m1["time"].max()

        m2 = g_sorted[g_sorted["event"].eq(fallback_event.lower())]

        if not m2.empty:
            return m2["time"].max()

        return g_sorted["time"].max()

    C = df.groupby("part_id", as_index=True).apply(_completion_time, include_groups=False).rename("Cj")

    # 가중치 결합
    w = pd.Series(weights, name="wj")

    summary = pd.DataFrame(C).join(w, how="left")

    # 가중치가 없으면 0을 처리
    missing = summary["wj"].isna().sum()

    if missing:
        summary["wj"] = summary["wj"].fillna(0)

    summary["contrib"] = summary["wj"] * summary["Cj"]

    ofv = summary["contrib"].sum()

    return ofv

def run_all_problems():
    dt_folder_path = os.path.dirname(os.path.abspath(__file__))
    is_bench_marking = True
    significant_digits = 10

    # PROBLEM_TYPES = {"PMSP", "PFSP", "JSSP"}
    PROBLEM_TYPES = {"JSSP"}
    BASELINE_FOLDER = "baseline"
    DATA_FOLDER = "data"
    PROBLEM_FOLDER = "problem"
    RESULTS_FOLDER = "result"

    data_dir = os.path.join(dt_folder_path, DATA_FOLDER)
    baseline_dir = os.path.join(dt_folder_path, BASELINE_FOLDER)
    results_dir = os.path.join(dt_folder_path, RESULTS_FOLDER)

    jssp_spt_makespan = parse_jssp_results(os.path.join(baseline_dir, "JSSP_SPT_Solution.csv"))
    pmsp_optimums = parse_pmsp_optimums(os.path.join(baseline_dir, "PMSP_OFV_Table.csv"))
    pfsp_optimums = parse_pfsp_optimums(os.path.join(baseline_dir, "Taillard_UB_Schedules OBrunner.csv"))

    errors = {}
    df_makespans = []

    for PROBLEM_TYPE in PROBLEM_TYPES:
        problem_dir = os.path.join(dt_folder_path, PROBLEM_FOLDER, PROBLEM_TYPE)

        problem_names = get_problem_names(problem_dir)

        df_makespan = pd.DataFrame(columns=["problem name"])

        os.makedirs(data_dir, exist_ok=True)
        os.makedirs(results_dir, exist_ok=True)

        for problem_name in problem_names:
            try:
                if is_bench_marking:
                    txt_file_path = os.path.join(problem_dir, f"{problem_name}.txt")
                    convert_banchmarking_data(txt_file_path, data_dir, PROBLEM_TYPE)

                data_dict = load_data_from_unified_csv(data_dir, problem_name)
                if not data_dict:
                    print("데이터 로딩에 실패하여 프로그램을 종료합니다.")
                    errors[f"{PROBLEM_TYPE}-{problem_name}"] = "Data Loading Failed"
                    continue

                log_output_path = os.path.join(results_dir, f"{problem_name}_event_log.csv")

                if PROBLEM_TYPE == "JSSP":
                    SEQUENCING_RULE = "FIFO"
                    ROUTING_RULE = "FIFO"
                    DISPATCHING_RULE = "SPT"
                elif PROBLEM_TYPE == "PFSP":
                    SEQUENCING_RULE = "JOHNSON"
                    ROUTING_RULE = "FIFO"
                    DISPATCHING_RULE = "FIFO"
                elif PROBLEM_TYPE == "PMSP":
                    SEQUENCING_RULE = "WSPT"
                    ROUTING_RULE = "WSPT"
                    DISPATCHING_RULE = "WSPT"
                else:
                    SEQUENCING_RULE = "RANDOM"
                    ROUTING_RULE = "RANDOM"
                    DISPATCHING_RULE = "RANDOM"

                monitor = run_simulation(data_dict, log_output_path, SEQUENCING_RULE, ROUTING_RULE, DISPATCHING_RULE, significant_digits)
                monitor.make_event_tracer()
                monitor.save_event_tracer()


                if PROBLEM_TYPE == "JSSP":
                    makespan = {"problem name": problem_name,
                                "time": monitor.event_tracer.tail(1)["time"].iloc[0],
                                "SPT": jssp_spt_makespan[problem_name.lower()]["spt"] if problem_name in jssp_spt_makespan else ""}
                elif PROBLEM_TYPE == "PFSP":
                    makespan = {"problem name": problem_name,
                                "time": monitor.event_tracer.tail(1)["time"].iloc[0],
                                "LB": pfsp_optimums[problem_name]["LB"],
                                "UB": pfsp_optimums[problem_name]["UB"]}
                elif PROBLEM_TYPE == "PMSP":
                    weights = {job_id: info["weight"] for job_id, info in data_dict["job_info"].items()}
                    ofv_time = get_ofv_time(monitor.event_tracer, weights,
                                 completion_events="job completed")
                    makespan = {"problem name": problem_name,
                                "time": str(int(ofv_time)),
                                "optimum": pmsp_optimums[problem_name.lower()] if problem_name.lower() in pmsp_optimums else "",
                                "LB": "",
                                "UB": ""}
                else:
                    makespan = {"problem name": "",
                                "time": "",
                                "optimum": ""}
                df_makespan = pd.concat([df_makespan, pd.DataFrame([makespan])], ignore_index=True)

                plot_gantt_chart(log_output_path)

            except Exception as e:
                errors[f"{PROBLEM_TYPE}-{problem_name}"] = str(e)
                continue
        df_makespans.append((f"{PROBLEM_TYPE}", df_makespan))
        # df_makespan.to_csv(os.path.join(f"{results_dir}",f"makespans_{PROBLEM_TYPE}.csv"), index=False)

    with pd.ExcelWriter(os.path.join(results_dir, "makespans.xlsx"), engine='openpyxl') as writer:
        for sheet_name, df in df_makespans:
            df.to_excel(writer, sheet_name=sheet_name, index=False)

    if len(errors) > 0:
        pprint(errors)


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
    # main()
    run_all_problems()