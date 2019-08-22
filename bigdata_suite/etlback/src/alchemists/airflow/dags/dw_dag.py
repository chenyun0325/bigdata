# -*- coding:utf-8 -*-
import os
from airflow import DAG
from airflow.hooks.postgres_hook import PostgresHook
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.bash_operator import BashOperator
from airflow.sensors.external_task_sensor import ExternalTaskSensor
import sys
import datetime
from datetime import timedelta
import json

sys.path.append("/root/airflow-alchemists/alchemists")
sys.path.append("/opt/etl/alchemists")
from src.alchemists.settings import ProdConfig, DevConfig
from src.alchemists.airflow.utils import failure_callback_wrapper

env = DevConfig if not os.environ.get("ENV") == 'PROD' else ProdConfig

metadb_hook = PostgresHook(postgres_conn_id=env.METADATA_DB_CONNECT_ID)

AIRFLOW_START_DATE = datetime.datetime.today() + timedelta(-2)

rows = metadb_hook.get_pandas_df("""
        select t2.type              source_type,
           t2.name              source_name,
           t2.host              source_host,
           t2.port              source_port,
           t2.db_name           source_db_name,
           t2.db_user           source_db_user,
           t2.db_psw            source_db_psw,
           t1.id                job_id,
           t1.job_num           job_num,
           t1.job_name          job_name,
           t1.description       job_desc,
           t1.layer             job_layer,
           t1.sql_text          job_sql_text,
           t4.table_name        source_table_name,
           t4.id_column         source_tbl_id_col,
           t1.target_table      target_table_name,
           t1.dependent_jobs    dependent_jobs,
           t5.id                schedule_id,
           t5.schedule_name     schedule_name,
           t5.schedule_interval schedule_interval,
           t1.job_type          job_type,
           t1.job_submit_args   job_submit_args,
           t1.owner as          owner
    from metadata.job t1
           join metadata.datasource t2 on t1.source_id = t2.id and t2.del = false
           left join metadata.ods_table t4 on t1.source_table_id = t4.id and t4.del = false
           join metadata.schedule t5 on t1.schedule_id = t5.id and t5.del = false
    where t1.del = false
      and t1.is_valid = true
      and t1.layer in ('DW', 'ADS')
""")

# 每个schedule对应一个dag
dags = rows.drop_duplicates(['schedule_id', 'schedule_name', 'schedule_interval'])

for _, d in dags.iterrows():
    args = {
        'owner': 'bigdata',
        'depends_on_past': False,
        'start_date': AIRFLOW_START_DATE,
        'retries': 1
    }

    dag = DAG(
        dag_id=d.schedule_name,
        default_args=args,
        description='DW & ADS JOB',
        schedule_interval=d.schedule_interval,
        catchup=False,
    )

    start = DummyOperator(task_id='start', dag=dag)
    finish = DummyOperator(task_id='finish', dag=dag)

    md = ""
    job_dict = {}

    for _, row in rows[rows.schedule_id == d.schedule_id].iterrows():
        task_id = "{}.{}.{}".format(row.job_layer.lower(), row.job_num, row.job_name) \
            if not row.job_type == 'DUMMY' else row.job_name

        if row.job_type == 'DUMMY':
            job = DummyOperator(task_id=task_id, dag=dag)

        if row.job_type == 'SPARK':
            args = {"executor-memory": env.SPARK_EXECUTOR_MEMORY,
                    "driver-memory": env.SPARK_DRIVER_MEMORY,
                    "total-executor-cores": env.SPARK_TOTAL_EXECUTOR_CORES}
            if row.job_submit_args:
                manual_args = json.loads(row.job_submit_args)
                args.update(manual_args)

            job = BashOperator(
                task_id=task_id,
                bash_command="""ssh {} << EOF
                                 source ~/.bash_profile; /opt/spark/bin/spark-submit --master {} \
                                --executor-memory {} \
                                --driver-memory {} \
                                --total-executor-cores {} \
                                --conf spark.port.maxRetries=32 \
                                --conf spark.network.timeout=10000000 \
                                /opt/etl/alchemists/src/alchemists/scripts/spark_etl.py \
                                --jobid {}\nEOF""".format(env.SPARK_CLIENT_HOST_NAME, env.SPARK_MASTER,
                                                          args.get("executor-memory"),
                                                          args.get("driver-memory"),
                                                          args.get("total-executor-cores"), row.job_id),
                dag=dag,
                on_failure_callback=failure_callback_wrapper(row.owner.split(",") if row.owner != '' else None)
            )
        md = md + "[{}:{}]  ".format(task_id, row.job_desc)
        job_dict[str(row.job_num)] = task_id

    for _, row in rows[(rows.schedule_id == d.schedule_id) & (rows.dependent_jobs != '')].iterrows():
        dependent_jobs = row.dependent_jobs
        for dep_job_id in dependent_jobs.split(","):
            if "." in dep_job_id:
                ext_dag_id, ext_task_id, execution_delta = dep_job_id.split(".")
                try:
                    ext_task = dag.get_task('wait_for_{}_{}'.format(ext_dag_id, ext_task_id))
                    dummy = dag.get_task('{}_{}_finish'.format(ext_dag_id, ext_task_id))
                except:
                    ext_task = ExternalTaskSensor(
                        task_id='wait_for_{}_{}'.format(ext_dag_id, ext_task_id),
                        external_dag_id=ext_dag_id,
                        external_task_id=ext_task_id,
                        execution_delta=datetime.timedelta(minutes=int(execution_delta)),
                        dag=dag
                    )
                    dummy = DummyOperator(task_id='{}_{}_finish'.format(ext_dag_id, ext_task_id), dag=dag)
                ext_task >> dummy >> dag.get_task(job_dict.get(str(row.job_num)))
            else:
                dag.get_task(job_dict.get(str(dep_job_id))) >> dag.get_task(job_dict.get(str(row.job_num)))

    dag.doc_md = md

    for task in filter(lambda x: x.task_id not in ('start', 'finish'), dag.tasks):
        if not task.upstream_list:
            start >> task
        if not task.downstream_list:
            task >> finish
