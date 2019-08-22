# -*- coding:utf-8 -*-
import os

env = os.environ


class Config(object):
    METADATA_DB_CONNECT_ID = 'bigdata_pg'
    DING_CONN_ID = 'dingding_default'


class DevConfig(Config):
    METADATA_DB_JDBC_URL = 'jdbc:postgresql://postgres:5432/postgres'
    METADATA_DB_USER = 'airflow'
    METADATA_DB_PWD = 'airflow'
    HIVE_CNT_PER_PARTITION = 100000
    MYSQL_READ_FETCH_SIZE = "5000"

    SPARK_MASTER = "spark://master:7077"
    SPARK_CLIENT_HOST_NAME = 'master'
    SPARK_EXECUTOR_MEMORY = "2G"
    SPARK_DRIVER_MEMORY = "2G"
    SPARK_TOTAL_EXECUTOR_CORES = "4"


class ProdConfig(Config):
    METADATA_DB_JDBC_URL = 'jdbc:postgresql://postgres:5432/postgres'
    METADATA_DB_USER = 'airflow'
    METADATA_DB_PWD = 'airflow'
    HIVE_CNT_PER_PARTITION = 200000
    MYSQL_READ_FETCH_SIZE = "5000"

    SPARK_MASTER = "spark://master:7077"
    SPARK_CLIENT_HOST_NAME = 'master'
    SPARK_EXECUTOR_MEMORY = "2G"
    SPARK_DRIVER_MEMORY = "2G"
    SPARK_TOTAL_EXECUTOR_CORES = "4"
