import simpy
import pandas as pd
import sys
import os
from typing import List, Dict, Optional
import matplotlib.pyplot as plt
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
    sys.exit(1)

def plot_gantt_chart(gantt_df: pd.DataFrame):
    """
    Pandas DataFrame을 직접 받아 안정적으로 간트 차트를 생성합니다.
    """
    if gantt_df.empty:
        print("오류: 간트 차트를 그릴 데이터가 없습니다.")
        return

    makespan = gantt_df['Finish'].max()

    unique_jobs = sorted(gantt_df['Job'].unique())
    colors = plt.cm.get_cmap('tab20', len(unique_jobs))
    job_color_map = {job: colors(i) for i, job in enumerate(unique_jobs)}

    fig, ax = plt.subplots(figsize=(25, 12))

    # Y축을 기계 이름으로 설정 (M1, M2, ... 순으로 정렬)
    machine_names = sorted(gantt_df['Machine_y'].unique(), key=lambda m: int(m[1:]))

    for machine in machine_names:
        machine_tasks = gantt_df[gantt_df['Machine_y'] == machine]
        for _, task in machine_tasks.iterrows():
            start_time = task['Start']
            duration = task['Finish'] - start_time
            job_name = task['Job']

            ax.barh(machine, duration, left=start_time, color=job_color_map[job_name], edgecolor='black', height=0.7)

            op_num = task['Operation'].split('_S')[-1]
            ax.text(start_time + duration / 2, machine, f"{job_name}(S{op_num})",
                    ha='center', va='center', color='white', fontweight='bold', fontsize=9)

    ax.set_xlabel('Time', fontsize=14)
    ax.set_ylabel('Machine', fontsize=14)
    ax.set_title('Gantt Chart for Job Shop Scheduling', fontsize=18)
    ax.grid(axis='x', linestyle='--')

    legend_elements = [plt.Rectangle((0, 0), 1, 1, color=job_color_map[job]) for job in unique_jobs]
    ax.legend(legend_elements, unique_jobs, title="Jobs", bbox_to_anchor=(1.01, 1), loc='upper left')

    ax.text(1.0, 1.05, f"Makespan: {makespan:.2f}", transform=ax.transAxes, fontsize=14, ha='right', va='top',
            bbox=dict(boxstyle='round,pad=0.3', fc='yellow', alpha=0.5))

    plt.tight_layout(rect=[0, 0, 0.9, 1])

    chart_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results', 'gantt_chart.png')
    plt.savefig(chart_path)
    print(f"간트 차트가 이미지 파일로 '{chart_path}'에 저장되었습니다.")
    # plt.show() # 로컬에서 직접 실행할 때 주석 해제하여 바로 확인

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
        print(f"'{problem_name}' 문제에 대한 CSV 데이터 로딩 성공.")
        return {'job_info': job_info, 'operation_info': op_info, 'process_info': proc_info}
    except FileNotFoundError as e:
        print(f"CSV 데이터 로딩 실패: {e}")
        return None

def run_simulation(problem_data: Dict, event_log_path: str, routing_rule: str) -> Monitor:
    print(f"\n--- STEP 3: 시뮬레이션 시작 (규칙: {routing_rule}) ---")
    env = simpy.Environment()
    model, monitor = {}, Monitor(event_log_path)
    model['Source'] = Source(model, monitor, 'Source', problem_data, env)
    model['Sink'] = Sink(model, monitor, 'Sink', env)
    for proc_id in problem_data.get('process_info', {}).keys():
        process_instance = Process(model, monitor, proc_id, problem_data, env)
        process_instance.process_routing = routing_rule
        model[proc_id] = process_instance
    env.run()
    print("시뮬레이션 종료.")
    return monitor

# 메인 실행 함수
def main():
    TXT_FILENAME = "la01.txt"
    ROUTING_RULE = 'Random'        # --- 라우팅 규칙 설정: 'Random', 'SPT', 'LPT', 'MWKR', 'LWKR' 중 선택 ---
    PROBLEM_FOLDER, DATA_FOLDER, RESULTS_FOLDER = "problem", "data", "results"

    print("=" * 50, f"JSSP 데이터 변환 및 시뮬레이션 (규칙: {ROUTING_RULE})", "=" * 50, sep="\n")

    dt_folder_path = os.path.dirname(os.path.abspath(__file__))
    txt_file_path = os.path.join(dt_folder_path, PROBLEM_FOLDER, TXT_FILENAME)
    data_dir = os.path.join(dt_folder_path, DATA_FOLDER)
    results_dir = os.path.join(dt_folder_path, RESULTS_FOLDER)

    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(results_dir, exist_ok=True)

    if not convert_jssp_to_csvs(txt_file_path, data_dir): return

    problem_name = os.path.basename(txt_file_path).split('.')[0]
    data_dict = load_data_from_csv(data_dir, problem_name)
    if not data_dict: return

    log_output_path = os.path.join(results_dir, "event_log.csv")
    monitor = run_simulation(data_dict, log_output_path, ROUTING_RULE)

    print("\n--- STEP 4: 결과 저장 시작 ---")
    monitor.make_event_tracer()
    monitor.save_event_tracer()
    print(f"최종 이벤트 로그가 '{log_output_path}'에 저장되었습니다.")

    print("\n--- STEP 5: Matplotlib 간트 차트 생성 시작 ---")
    try:
        df = pd.read_csv(log_output_path)

        pivot_df = df.pivot_table(
            index=['Part', 'Operation', 'Process'],
            columns='Event',
            values='Time'
        ).reset_index()

        pivot_df.rename(columns={
            'job assigned': 'Start',
            'operation complete': 'Finish',
            'Part': 'Job',
            'Process': 'Machine_y'
        }, inplace=True)

        gantt_df = pivot_df.dropna(subset=['Start', 'Finish'])

        if not gantt_df.empty:
            plot_gantt_chart(gantt_df)
        else:
            print("오류: 간트 차트를 그릴 데이터를 생성하지 못했습니다.")

    except Exception as e:
        print(f"간트 차트 생성 실패: {e}")

    print("\n" + "=" * 50, "모든 작업이 성공적으로 완료되었습니다.", "=" * 50, sep="\n")


if __name__ == "__main__":
    main()