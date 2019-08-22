# -*- coding:utf-8 -*-
import os

env = os.environ


class Config(object):
    METADATA_DB_CONNECT_ID = 'bigdata_pg'
    DING_CONN_ID = 'dingding_default'


class DevConfig(Config):
    METADATA_DB_JDBC_URL = 'jdbc:postgresql://172.31.8.25:5432/postgres'
    METADATA_DB_USER = 'postgres'
    METADATA_DB_PWD = 'wm9RaCb6KxTUJpWo'
    HIVE_CNT_PER_PARTITION = 100000
    MYSQL_READ_FETCH_SIZE = "5000"

    SPARK_MASTER = "spark://alluxio-master:7077"
    SPARK_CLIENT_HOST_NAME = 'spark-client'
    SPARK_EXECUTOR_MEMORY = "6G"
    SPARK_DRIVER_MEMORY = "2G"
    SPARK_TOTAL_EXECUTOR_CORES = "4"


class ProdConfig(Config):
    METADATA_DB_JDBC_URL = 'jdbc:postgresql://pg-bigdata-rw:5433/postgres'
    METADATA_DB_USER = 'postgres'
    METADATA_DB_PWD = '4Rn4nUM2K3dhEUfy'
    HIVE_CNT_PER_PARTITION = 200000
    MYSQL_READ_FETCH_SIZE = "5000"

    SPARK_MASTER = "spark://alluxio-master:7077"
    SPARK_CLIENT_HOST_NAME = 'spark-client'
    SPARK_EXECUTOR_MEMORY = "6G"
    SPARK_DRIVER_MEMORY = "2G"
    SPARK_TOTAL_EXECUTOR_CORES = "4"
