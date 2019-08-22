# -*- coding:utf-8 -*-
import os
from airflow import DAG
from airflow.hooks.postgres_hook import PostgresHook
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.bash_operator import BashOperator
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
           t1.layer             job_layer,
           t1.sql_text          job_sql_text,
           t4.table_name        source_table_name,
           t4.id_column         source_tbl_id_col,
           t1.target_table      target_table_name,
           t1.dependent_jobs    dependent_jobs,
           t5.id                schedule_id,
           t5.schedule_name     schedule_name,
           t5.schedule_interval schedule_interval,
           t1.job_submit_args   job_submit_args,
           t1.owner as          owner
    from metadata.job t1
           join metadata.datasource t2 on t1.source_id = t2.id and t2.del = false
           left join metadata.ods_table t4 on t1.source_table_id = t4.id and t4.del = false
           join metadata.schedule t5 on t1.schedule_id = t5.id and t5.del = false
    where t1.del = false
      and t1.is_valid = true
      and t1.layer = 'ODS'
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
        description='ODS JOB',
        schedule_interval=d.schedule_interval,
        catchup=False,
    )

    start = DummyOperator(task_id='start', dag=dag)
    finish = DummyOperator(task_id='finish', dag=dag)

    db_names = rows[rows.schedule_id == d.schedule_id].drop_duplicates('source_db_name')
    for _, db in db_names.iterrows():
        db_name = db.source_db_name
        db_start = DummyOperator(task_id=db_name + '_start', dag=dag)
        db_finish = DummyOperator(task_id=db_name + '_finish', dag=dag)

        jobs = rows[(rows.schedule_id == d.schedule_id) & (rows.source_db_name == db_name)]

        for _, job in jobs.iterrows():
            args = {"executor-memory": env.SPARK_EXECUTOR_MEMORY,
                    "driver-memory": env.SPARK_DRIVER_MEMORY,
                    "total-executor-cores": env.SPARK_TOTAL_EXECUTOR_CORES}

            if job.job_submit_args:
                manual_args = json.loads(job.job_submit_args)
                args.update(manual_args)

            j = BashOperator(task_id='{}.{}'.format(db_name, job.source_table_name),
                             bash_command="""ssh {} << EOF
                            /opt/spark/bin/spark-submit --master {} \
                            --executor-memory {} \
                            --driver-memory {} \
                            --total-executor-cores {} \
                            --conf spark.port.maxRetries=32 \
                            --conf spark.network.timeout=10000000 \
                            /opt/etl/alchemists/src/alchemists/scripts/spark_etl.py \
                            --jobid {}\nEOF""".format(env.SPARK_CLIENT_HOST_NAME, env.SPARK_MASTER,
                                                      args.get("executor-memory"),
                                                      args.get("driver-memory"),
                                                      args.get("total-executor-cores"), job.job_id),
                             dag=dag,
                             on_failure_callback=failure_callback_wrapper(
                                 job.owner.split(",") if job.owner != '' else None))

            db_start >> j >> db_finish

        start >> db_start
        db_finish >> finish
