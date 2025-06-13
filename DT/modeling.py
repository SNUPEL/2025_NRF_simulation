import simpy
import pandas as pd
import csv
import sys
import os

from typing import List, Dict

from DT.components import Job, Machine, Monitor, Operation, Process, Sink, Source

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 1. 현재 파일 형식에 맞는 데이터 로딩 함수

def load_data_from_csv(job_filepath: str, operation_filepath: str, process_filepath: str) -> Dict[str, List]:
    job_info_list = list()
    operation_info_list = list()
    process_info_list = list()

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
        job_id = row['id']
        arrival_time = row['arrival_time']
        operations = [str(row['op{0}_id'.format(i)]) for i in range(1, 1 + max_len_operations) if row['op{0}_time'.format(i)] > 0]
        operation_times = [float(row['op{0}_time'.format(i)]) for i in range(1, 1+ max_len_operations) if row['op{0}_time'.format(i)] > 0]
        job_info = {'id': job_id, 'arrival_time': arrival_time, 'operations': operations, 'operation_times': operation_times}
        job_info_list.append(job_info)

    for index, row in operation_df.iterrows():
        operation_id = row['id']
        process_list = str(row['process']).split(',')
        processing_time_list = str(row['time']).split(',')
        processing_time_list = [float(i) for i in processing_time_list]
        operation_info = {'id': operation_id, 'process': process_list, 'processing_time': processing_time_list}
        operation_info_list.append(operation_info)

    for index, row in process_df.iterrows():
        process_id = row['id']
        process_capa = row['capacity']
        process_info = {'id': process_id, 'capacity': process_capa}
        process_info_list.append(process_info)

    return {'job_info':job_info_list, 'operation_info':operation_info_list, 'process_info':process_info_list}

# 2. 시뮬레이션 실행 함수

def run_simulation(problem_data: Dict):
    """
    전체 JSSP 시뮬레이션을 설정하고 실행하는 함수
    """

    model = dict()
    # 2. SimPy 환경 및 핵심 컴포넌트를 생성
    env = simpy.Environment()
    model['Source'] = Source.Source(model,'Source', problem_data, env)
    '''수정필요'''
    # model['p1'] = Process.Process(model['Source'],'p1','p1')
    # model['p2'] = Process.Process(model['Source'],'p2','p2')
    model['sink'] = Sink.Sink(env)

    # 4. SimPy 환경을 실행
    env.run()


if __name__ == "__main__":
    # 불러올 CSV 파일 이름을 지정합
    job_csv = "job_sample.csv"
    operation_csv = "operation_sample.csv"
    process_csv = "process_sample.csv"


    # 1. CSV 형식 파일로부터 시뮬레이션 데이터를 로드
    data_dict = load_data_from_csv(job_csv, operation_csv, process_csv)

    # 2. 로드한 데이터를 통해 시뮬레이션 모델링
    run_simulation(data_dict)