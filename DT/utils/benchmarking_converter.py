import os
import csv
from collections import defaultdict
from typing import List, Dict

def convert_banchmarking_data(txt_file_path: str, output_dir: str, problem_type: str):
    if problem_type == "JSSP":
        convert_jssp_to_csvs(txt_file_path, output_dir)
    elif problem_type == "PFSP":
        convert_pfsp_to_csvs(txt_file_path, output_dir)
    elif problem_type == "PFSP":
        pass
    else:
        raise Exception("올바르지 않은 문제 유형입니다.")

def convert_jssp_to_csvs(txt_file_path: str, output_dir: str) -> bool:
    """JSSP 벤치마크 .txt 파일을 읽어 시뮬레이션용 CSV 파일 3종으로 변환합니다."""
    def _parse_jssp_data(n_jobs, times_raw, machines_raw):
        """JSSP 원본 데이터를 파싱하여 CSV 작성에 필요한 데이터 구조로 변환합니다."""
        all_jobs, all_ops, proc_caps = [], {}, defaultdict(int)
        max_ops = 0

        for i in range(n_jobs):
            job_id = f"J{i + 1}"
            job_ops_seq = []
            for j in range(len(times_raw[i])):
                machine_id_num = machines_raw[i][j]
                proc_id = f"M{machine_id_num}"
                proc_caps[proc_id] = 1

                op_id = f"Op_{job_id}_S{j + 1}"
                proc_time = float(times_raw[i][j])
                all_ops[op_id] = {'id': op_id, 'process': proc_id, 'time': proc_time}
                job_ops_seq.append({'id': op_id, 'time': proc_time})

            all_jobs.append({'id': job_id, 'arrival_time': 0.0, 'operations_sequence': job_ops_seq})
            max_ops = max(max_ops, len(job_ops_seq))

        jobs_data = _format_jobs_for_csv(all_jobs, max_ops)
        ops_data = list(all_ops.values())
        procs_data = [{'id': k, 'capacity': v} for k, v in sorted(proc_caps.items(), key=lambda item: int(item[0][1:]))]

        return jobs_data, ops_data, procs_data

    def _format_jobs_for_csv(all_jobs, max_ops):
        """파싱된 Job 데이터를 CSV에 쓰기 좋은 딕셔너리 리스트 형태로 변환합니다."""
        formatted_jobs = []
        for job in all_jobs:
            row = {'id': job['id'], 'arrival_time': job['arrival_time']}
            for i, op in enumerate(job['operations_sequence']):
                row[f'op{i + 1}_id'] = op['id']
                row[f'op{i + 1}_time'] = op['time']
            formatted_jobs.append(row)
        return formatted_jobs

    print("\n--- STEP 1: .txt 파일 변환 시작 ---")
    try:
        if not os.path.exists(txt_file_path):
            raise FileNotFoundError(f"입력 파일을 찾을 수 없습니다: {txt_file_path}")

        with open(txt_file_path, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
        if not lines:
            raise ValueError("입력 파일이 비어있습니다.")

        problem = txt_file_path.split('\\')[-1].split('.')[0]
        n_jobs = int(lines[0].split()[0])
        times_raw = [list(map(int, line.split())) for line in lines[1:n_jobs + 1]]
        machines_raw = [list(map(int, line.split())) for line in lines[n_jobs + 1:n_jobs * 2 + 1]]

        jobs_data, ops_data, procs_data = _parse_jssp_data(n_jobs, times_raw, machines_raw)

        os.makedirs(output_dir, exist_ok=True)
        _write_csv(os.path.join(output_dir, 'process_{0}.csv'.format(problem)), procs_data)
        _write_csv(os.path.join(output_dir, 'operation_{0}.csv'.format(problem)), ops_data)
        _write_csv(os.path.join(output_dir, 'job_{0}.csv'.format(problem)), jobs_data)

        print(f".txt 파일 변환 성공. 결과가 '{output_dir}' 폴더에 저장되었습니다.")
        return True

    except Exception as e:
        print(f".txt 파일 변환 실패: {e}")
        return False

def convert_pfsp_to_csvs(txt_file_path: str, output_dir: str) -> bool:
    """PFSP 벤치마크 .txt 파일을 읽어 시뮬레이션용 CSV 파일 3종으로 변환합니다."""
    def _parse_pfsp_data(n_jobs, times_raw, machines_raw):
        """PFSP 원본 데이터를 파싱하여 CSV 작성에 필요한 데이터 구조로 변환합니다."""
        all_jobs, all_ops, proc_caps = [], {}, defaultdict(int)
        max_ops = 0

        for i in range(n_jobs):
            job_id = f"J{i + 1}"
            job_ops_seq = []
            for j in range(len(times_raw[i])):
                machine_id_num = machines_raw[i][j]
                proc_id = f"M{machine_id_num}"
                proc_caps[proc_id] = 1

                op_id = f"Op_{job_id}_S{j + 1}"
                proc_time = float(times_raw[i][j])
                all_ops[op_id] = {'id': op_id, 'process': proc_id, 'time': proc_time}
                job_ops_seq.append({'id': op_id, 'time': proc_time})

            all_jobs.append({'id': job_id, 'arrival_time': 0.0, 'operations_sequence': job_ops_seq})
            max_ops = max(max_ops, len(job_ops_seq))

        jobs_data = _format_jobs_for_csv(all_jobs, max_ops)
        ops_data = list(all_ops.values())
        procs_data = [{'id': k, 'capacity': v} for k, v in sorted(proc_caps.items(), key=lambda item: int(item[0][1:]))]

        return jobs_data, ops_data, procs_data

    def _format_jobs_for_csv(all_jobs, max_ops):
        """파싱된 Job 데이터를 CSV에 쓰기 좋은 딕셔너리 리스트 형태로 변환합니다."""
        formatted_jobs = []
        for job in all_jobs:
            row = {'id': job['id'], 'arrival_time': job['arrival_time']}
            for i, op in enumerate(job['operations_sequence']):
                row[f'op{i + 1}_id'] = op['id']
                row[f'op{i + 1}_time'] = op['time']
            formatted_jobs.append(row)
        return formatted_jobs

    print("\n--- STEP 1: .txt 파일 변환 시작 ---")
    try:
        if not os.path.exists(txt_file_path):
            raise FileNotFoundError(f"입력 파일을 찾을 수 없습니다: {txt_file_path}")

        with open(txt_file_path, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
        if not lines:
            raise ValueError("입력 파일이 비어있습니다.")

        problem = txt_file_path.split('\\')[-1].split('.')[0]
        n_jobs = int(lines[0].split()[0])
        times_raw = [list(map(int, line.split())) for line in lines[1:]]
        times_raw = [line[1::2] for line in times_raw]
        machines_raw = [list(map(int, line.split())) for line in lines[1:]]
        machines_raw = [line[0::2] for line in machines_raw]

        jobs_data, ops_data, procs_data = _parse_pfsp_data(n_jobs, times_raw, machines_raw)

        os.makedirs(output_dir, exist_ok=True)
        _write_csv(os.path.join(output_dir, 'process_{0}.csv'.format(problem)), procs_data)
        _write_csv(os.path.join(output_dir, 'operation_{0}.csv'.format(problem)), ops_data)
        _write_csv(os.path.join(output_dir, 'job_{0}.csv'.format(problem)), jobs_data)

        print(f".txt 파일 변환 성공. 결과가 '{output_dir}' 폴더에 저장되었습니다.")
        return True

    except Exception as e:
        print(f".txt 파일 변환 실패: {e}")
        return False

def _write_csv(filepath: str, data: List[Dict]):
    """딕셔너리 리스트를 받아 CSV 파일로 저장합니다."""
    if not data: return
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)