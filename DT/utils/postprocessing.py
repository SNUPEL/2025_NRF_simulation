import os
import pandas as pd
import matplotlib.pyplot as plt

def plot_gantt_chart(log_path: str):
    """
    Pandas DataFrame을 직접 받아 안정적으로 간트 차트를 생성합니다.
    """

    print("\n--- STEP 5: Matplotlib 간트 차트 생성 시작 ---")
    try:
        df = pd.read_csv(log_path)

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

        if gantt_df.empty:
            print("오류: 간트 차트를 그릴 데이터를 생성하지 못했습니다.")

    except Exception as e:
        print(f"간트 차트 생성 실패: {e}")

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

    chart_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'results', 'gantt_chart.png')
    plt.savefig(chart_path)
    print(f"간트 차트가 이미지 파일로 '{chart_path}'에 저장되었습니다.")
    # plt.show() # 로컬에서 직접 실행할 때 주석 해제하여 바로 확인