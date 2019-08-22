# -*- coding:utf-8 -*-
import os
from airflow.contrib.operators.dingding_operator import DingdingOperator
from src.alchemists.settings import DevConfig, ProdConfig

env = DevConfig if os.environ.get("ENV") == 'PROD' else ProdConfig


def failure_callback_wrapper(at_mobiles=None):
    def failure_callback(context):
        message = 'AIRFLOW TASK FAILURE TIPS:\n' \
                  'DAG:    {}\n' \
                  'TASKS:  {}\n' \
                  'Reason: {}\n' \
            .format(context['task_instance'].dag_id,
                    context['task_instance'].task_id,
                    context['exception'])

        return DingdingOperator(
            task_id='dingding_callback',
            dingding_conn_id='dingding_default',
            message_type='text',
            message=message,
            at_mobiles=at_mobiles,
            at_all=True,
        ).execute(context)

    return failure_callback
