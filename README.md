1.foreachPartition(连接池对象)
2.spark-core的rdd和sparksql的df整合
3.spark-sql自定义函数&&hive自定义函数



Transformations:

mr的map--->Map/mapPartitions

mr的reduce-->groupbyKey/reduceByKey/aggregateByKey

多表连接Join/union



Action:(触发spark的计算)

reduce(func)
collect()
saveAsTextFile

foreach(func)/foreachPartition


参考:
https://blog.csdn.net/qq_18603599/article/details/79951810
https://www.jianshu.com/p/dba62b02a9fa