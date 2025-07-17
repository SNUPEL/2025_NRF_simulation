import simpy
import pandas as pd
import csv
import sys
import os

from typing import List, Dict

from components import *

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 1. 현재 파일 형식에 맞는 데이터 로딩 함수

def load_data_from_csv(job_filepath: str, operation_filepath: str, process_filepath: str) -> Dict[str, List]:
    job_info_dict = dict()
    operation_info_dict = dict()
    process_info_dict = dict()

    job_df = pd.read_csv(job_filepath)
    operation_df = pd.read_csv(operation_filepath)
    process_df = pd.read_csv(process_filepath)

    max_len_operations = int((job_df.shape[1]-2) / 2)

    operations = list(operation_df['id'])

    ''' 수정 필요'''
    # temp_operations = list(job_df.columns)[2:]
    # check_operations = [op.split('_')[0] for op in temp_operations]
    # check_operations = list(set(check_operations))
    #
    # assert operations == check_operations, 'Operations do not match.'

    for index, row in job_df.iterrows():
        job_id = str(row['id'])
        arrival_time = row['arrival_time']
        operations = [str(row['op{0}_id'.format(i)]) for i in range(1, 1 + max_len_operations) if row['op{0}_time'.format(i)] > 0]
        operation_times = [float(row['op{0}_time'.format(i)]) for i in range(1, 1+ max_len_operations) if row['op{0}_time'.format(i)] > 0]
        job_info = {'id': job_id, 'arrival_time': arrival_time, 'operations': operations, 'operation_times': operation_times}
        job_info_dict[job_id] = job_info

    for index, row in operation_df.iterrows():
        operation_id = str(row['id'])
        process_list = str(row['process']).split(',')
        processing_time_list = str(row['time']).split(',')
        processing_time_list = [float(i) for i in processing_time_list]
        operation_info = {'id': operation_id, 'process': process_list, 'processing_time': processing_time_list}
        operation_info_dict[operation_id] = operation_info

    for index, row in process_df.iterrows():
        process_id = str(row['id'])
        process_capa = row['capacity']
        process_info = {'id': process_id, 'capacity': process_capa}
        process_info_dict[process_id] = process_info

    return {'job_info':job_info_dict, 'operation_info':operation_info_dict, 'process_info':process_info_dict}

# 2. 시뮬레이션 실행 함수

def run_simulation(problem_data: Dict, event_log_path: str):
    """
    전체 JSSP 시뮬레이션을 설정하고 실행하는 함수
    """
    # 1. model 생성
    model = dict()
    monitor = Monitor(event_log_path)
    # 2. SimPy 환경 및 핵심 컴포넌트를 생성
    env = simpy.Environment()
    model['Source'] = Source(model, monitor, 'Source', problem_data, env)
    model['1'] = Process(model, monitor, '1', problem_data, env)
    model['2'] = Process(model, monitor, '2', problem_data, env)
    model['3'] = Process(model, monitor, '3', problem_data, env)
    model['4'] = Process(model, monitor, '4', problem_data, env)
    model['5'] = Process(model, monitor, '5', problem_data, env)
    model['Sink'] = Sink(model, monitor, 'Sink', env)

    # 3. SimPy 환경을 실행
    env.run()

    return monitor


if __name__ == "__main__":
    # 불러올 CSV 파일 이름을 지정함
    data_dir = "./data/"
    job_csv = data_dir + "job_sample.csv"
    operation_csv = data_dir + "operation_sample.csv"
    process_csv = data_dir + "process_sample.csv"

    result_dir = "./results/"
    event_log_path = result_dir + "event_log.csv"

    # 1. CSV 형식 파일로부터 시뮬레이션 데이터를 로드
    data_dict = load_data_from_csv(job_csv, operation_csv, process_csv)

    # 2. 로드한 데이터를 통해 시뮬레이션 모델링
    monitor = run_simulation(data_dict, event_log_path)

    monitor.make_event_tracer()
    monitor.save_event_tracer()