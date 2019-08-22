# coding: utf-8

from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from datetime import datetime, timedelta


# 定义默认参数
default_args = {
    'owner': 'airflow',  # 拥有者名称
    'start_date': datetime(2019, 8, 11, 15, 9),  # 第一次开始执行的时间，为格林威治时间，为了方便测试，一般设置为当前时间减去执行周期
    'email': ['shelmingsong@gmail.com'],  # 接收通知的email列表
    'email_on_failure': False,  # 是否在任务执行失败时接收邮件
    'email_on_retry': False,  # 是否在任务重试时接收邮件
    'retries': 3,  # 失败重试次数
    'retry_delay': timedelta(seconds=5)  # 失败重试间隔
}

# 定义DAG
dag = DAG(
    dag_id='hello_world',  # dag_id
    default_args=default_args,  # 指定默认参数
    # schedule_interval="00, *, *, *, *"  # 执行周期，依次是分，时，天，月，年，此处表示每个整点执行
    schedule_interval=timedelta(minutes=1)  # 执行周期，表示每分钟执行一次
)


# 定义要执行的Python函数1
def hello_world_1():
    current_time = str(datetime.today())
    with open('/usr/local/airflow/hello_world_1.txt', 'a') as f:
        f.write('%s\n' % current_time)
    assert 1 == 1  # 可以在函数中使用assert断言来判断执行是否正常，也可以直接抛出异常


# 定义要执行的Python函数2
def hello_world_2():
    current_time = str(datetime.today())
    with open('/usr/local/airflow/hello_world_2.txt', 'a') as f:
        f.write('%s\n' % current_time)


# 定义要执行的Python函数3
def hello_world_3():
    current_time = str(datetime.today())
    with open('/usr/local/airflow/hello_world_3.txt', 'a') as f:
        f.write('%s\n' % current_time)

# 定义要执行的task 1
t1 = PythonOperator(
    task_id='hello_world_1',  # task_id
    python_callable=hello_world_1,  # 指定要执行的函数
    dag=dag,  # 指定归属的dag
    retries=2,  # 重写失败重试次数，如果不写，则默认使用dag类中指定的default_args中的设置
)

# 定义要执行的task 2
t2 = PythonOperator(
    task_id='hello_world_2',  # task_id
    python_callable=hello_world_2,  # 指定要执行的函数
    dag=dag,  # 指定归属的dag
)

# 定义要执行的task 3
t3 = PythonOperator(
    task_id='hello_world_3',  # task_id
    python_callable=hello_world_3,  # 指定要执行的函数
    dag=dag,  # 指定归属的dag
)

t2.set_upstream(t1)
# 表示t2这个任务只有在t1这个任务执行成功时才执行，
# 等价于 t1.set_downstream(t2)
# 同时等价于 dag.set_dependency('hello_world_1', 'hello_world_2')

t3.set_upstream(t1)  # 同理
