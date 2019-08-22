# -*- coding:utf-8 -*-
import sys
sys.path.append("/root/airflow-alchemists/alchemists")
sys.path.append("/opt/etl/alchemists")
sys.path.append("/usr/local/lib/python3.5/dist-packages")
import click
from pyspark.sql import SparkSession
from pyspark.storagelevel import StorageLevel
from pyspark.sql.types import StructType
import math
from decimal import Decimal
from src.alchemists.settings import ProdConfig, DevConfig
import os


def get_spark_session(app_name):
    spark = SparkSession \
        .builder \
        .appName(app_name) \
        .enableHiveSupport() \
        .config("spark.sql.warehouse.dir", "hdfs://namenode:8020/user/hive/warehouse")\
        .getOrCreate()
    return spark


def get_job_info(spark, env, jobid):
    sql = """
        (with a as (select id,
                      is_del,
                      schedule_id,
                      job_num,
                      job_name,
                      layer,
                      source_id,
                      source_table_id,
                      sql_text,
                      target_id,
                      target_table,
                      description,
                      dependent_jobs,
                      operator,
                      is_valid,
                      version,
                      job_type,
                      job_submit_args
               from metadata.job)
    select t2.type              source_type,
           t2.name              source_name,
           t2.host              source_host,
           t2.port              source_port,
           t2.db_name           source_db_name,
           t2.db_user           source_db_user,
           t2.db_psw            source_db_psw,
           t3.type              target_type,
           t3.name              target_name,
           t3.host              target_host,
           t3.port              target_port,
           t3.db_name           target_db_name,
           t3.db_user           target_db_user,
           t3.db_psw            target_db_psw,
           t1.id                job_id,
           t1.job_num           job_num,
           t1.job_name          job_name,
           t1.layer             job_layer,
           t1.sql_text          job_sql_text,
           t4.schema            source_schema,
           t4.table_name        source_table_name,
           t4.id_column         source_tbl_id_col,
           t1.target_table      target_table_name,
           t1.dependent_jobs    dependent_jobs,
           t5.schedule_name     schedule_name,
           t5.schedule_interval schedule_interval
    from a t1
           join metadata.datasource t2 on t1.source_id = t2.id
           join metadata.datasource t3 on t1.target_id = t3.id
           left join metadata.ods_table t4 on t1.source_table_id = t4.id
           join metadata.schedule t5 on t1.schedule_id = t5.id
    where t1.id = '{}'
      and t1.is_del = false
      and t1.is_valid = true) as t
    """.format(jobid)

    job_info = spark \
        .read \
        .jdbc(env.METADATA_DB_JDBC_URL, sql,
              properties={"user": env.METADATA_DB_USER, "password": env.METADATA_DB_PWD})

    return job_info


def run(spark, env):
    @click.command()
    @click.option('--jobid')
    def wrapper(jobid):

        rows = get_job_info(spark, env, jobid)

        def get_df():
            source = rows.first()
            if source:
                if source.source_type == 'mysql':

                    t = "(select cast(min({0}) as DECIMAL) as min,cast(max({0}) as DECIMAL) as max,count(1) as cnt from {1}.{2}) as t" \
                        .format(source.source_tbl_id_col, source.source_db_name, source.source_table_name)

                    df = spark.read \
                        .jdbc(
                        "jdbc:mysql://{}:{}/{}?yearIsDateType=false&zeroDateTimeBehavior=convertToNull&tinyInt1isBit=false" \
                            .format(source.source_host, source.source_port, source.source_db_name),
                        t,
                        properties={"user": source.source_db_user, "password": source.source_db_psw,
                                    "fetchsize": env.MYSQL_READ_FETCH_SIZE}) \
                        .persist(storageLevel=StorageLevel.MEMORY_AND_DISK)

                    r = df.first().asDict()

                    print(r)
                    lowerBound = None
                    upperBound = None
                    numPartitions = None
                    column = None

                    if r.get("max") and isinstance(r.get("max"), Decimal) and r.get("cnt") > env.HIVE_CNT_PER_PARTITION:
                        column = source.source_tbl_id_col
                        lowerBound = r.get("min")
                        upperBound = r.get("max")
                        numPartitions = math.ceil(float(r.get("cnt")) / env.HIVE_CNT_PER_PARTITION)

                    df = spark.read \
                        .jdbc(
                        "jdbc:mysql://{}:{}/{}?yearIsDateType=false&zeroDateTimeBehavior=convertToNull&tinyInt1isBit=false" \
                            .format(source.source_host, source.source_port, source.source_db_name),
                        "{}.{}".format(source.source_db_name, source.source_table_name),
                        column=column, lowerBound=lowerBound, upperBound=upperBound,
                        numPartitions=numPartitions,
                        properties={"user": source.source_db_user, "password": source.source_db_psw,
                                    "fetchsize": env.MYSQL_READ_FETCH_SIZE}) \
                        .persist(storageLevel=StorageLevel.MEMORY_AND_DISK)

                    # if numPartitions > 1:
                    #     df = df.repartition(int(numPartitions))

                    return df

                if source.source_type == 'postgresql':
                    jdbc_url = "jdbc:postgresql://{}:{}/{}".format(source.source_host, source.source_port,
                                                                   source.source_db_name)
                    properties = {"user": source.source_db_user, "password": source.source_db_psw}

                    df = spark.read.jdbc(jdbc_url, '{}.{}'.format(source.source_schema, source.source_table_name),
                                         properties=properties)

                    return df

                if source.source_type == 'hive':
                    df = spark.sql(source.job_sql_text)
                    cnt = df.count()
                    numPartitions = math.ceil(float(cnt) / env.HIVE_CNT_PER_PARTITION)
                    if numPartitions > 1:
                        df = df.repartition(int(numPartitions))

                    return df

            else:
                raise ValueError("Job info is empty")

        def run_job(job_info, df):
            table_name = job_info.target_table_name if job_info.target_table_name else "ods_{}.sync_{}".format(
                job_info.source_db_name, job_info.source_table_name)
            schema = table_name.split(".")[0]

            if job_info.target_type == 'hive':
                spark.sql("create database if not exists {}".format(schema))
                df.write.mode("overwrite").format("orc").saveAsTable(table_name)

            if job_info.target_type == 'phoenix':
                df.write \
                    .format("org.apache.phoenix.spark") \
                    .mode("overwrite") \
                    .option("table", table_name) \
                    .option("zkUrl", job_info.target_host) \
                    .save()

            if job_info.target_type in ('mysql', 'postgresql'):
                jdbc_url = "jdbc:{}://{}:{}/{}".format(job_info.target_type, job_info.target_host, job_info.target_port,
                                                       job_info.target_db_name)

                properties = {"user": job_info.target_db_user, "password": job_info.target_db_psw}

                # struct array等转为string
                schema = df.schema.jsonValue()
                map(lambda x: x.update(type='string') if isinstance(x.get("type"), dict) else x, schema.get("fields"))
                struct = StructType.fromJson(schema)

                new_df = spark.createDataFrame(df.rdd, struct)

                new_df.write \
                    .mode("overwrite") \
                    .option("truncate", True) \
                    .jdbc(jdbc_url, table_name, properties=properties)

        df = get_df()
        for row in rows.collect():
            run_job(row, df)

    return wrapper()


if __name__ == '__main__':
    env = DevConfig if not os.environ.get("ENV") == 'PROD' else ProdConfig
    spark = get_spark_session("Spark ETL Tool")
    run(spark, env)
    spark.stop()
