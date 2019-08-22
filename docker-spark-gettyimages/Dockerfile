FROM debian:stretch
MAINTAINER Getty Images "https://github.com/gettyimages"

RUN apt-get update \
 && apt-get install -y locales \
 && dpkg-reconfigure -f noninteractive locales \
 && locale-gen C.UTF-8 \
 && /usr/sbin/update-locale LANG=C.UTF-8 \
 && echo "en_US.UTF-8 UTF-8" >> /etc/locale.gen \
 && locale-gen \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

# Users with other locales should set this in their derivative image
ENV LANG en_US.UTF-8
ENV LANGUAGE en_US:en
ENV LC_ALL en_US.UTF-8

RUN apt-get update \
 && apt-get install -y curl unzip wget \
    python3 python3-setuptools \
 && ln -s /usr/bin/python3 /usr/bin/python \
 ## 安装click-python的依赖包
 && easy_install3 pip py4j click \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

# http://blog.stuart.axelbrooke.com/python-3-on-spark-return-of-the-pythonhashseed
ENV PYTHONHASHSEED 0
ENV PYTHONIOENCODING UTF-8
ENV PIP_DISABLE_PIP_VERSION_CHECK 1

# JAVA
RUN apt-get update \
 && apt-get install -y openjdk-8-jre \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

# install openssh-server
RUN apt-get update && apt-get install -y openssh-server && rm -rf /var/lib/apt/lists/*

# ssh without key
RUN ssh-keygen -t rsa -f ~/.ssh/id_rsa -P '' && \
    cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys && \
    sed -i "s/#   StrictHostKeyChecking ask/StrictHostKeyChecking no/g" /etc/ssh/ssh_config

RUN mkdir -p /var/run/sshd	
EXPOSE 22

# HADOOP
# ENV HADOOP_VERSION 3.0.0
# ENV HADOOP_HOME /usr/hadoop-$HADOOP_VERSION
# ENV HADOOP_CONF_DIR=$HADOOP_HOME/etc/hadoop
# ENV PATH $PATH:$HADOOP_HOME/bin
# RUN curl -sL --retry 3 \
#   "http://archive.apache.org/dist/hadoop/common/hadoop-$HADOOP_VERSION/hadoop-$HADOOP_VERSION.tar.gz" \
#   | gunzip \
#   | tar -x -C /usr/ \
#  && rm -rf $HADOOP_HOME/share/doc \
#  && chown -R root:root $HADOOP_HOME

# SPARK
ENV SPARK_VERSION 2.4.3
ENV SPARK_PACKAGE spark-${SPARK_VERSION}-bin-hadoop2.7
ENV SPARK_HOME /usr/spark-${SPARK_VERSION}
ENV PATH $PATH:${SPARK_HOME}/bin
RUN curl -sL --retry 3 \
  "https://archive.apache.org/dist/spark/spark-${SPARK_VERSION}/${SPARK_PACKAGE}.tgz" \
  | gunzip \
  | tar x -C /usr/ \
 && mv /usr/$SPARK_PACKAGE $SPARK_HOME \
 && chown -R root:root $SPARK_HOME

# 安装spark相关依赖jdbc
RUN wget https://jdbc.postgresql.org/download/postgresql-9.4.1212.jar -O $SPARK_HOME/jars/postgresql-jdbc.jar

RUN wget https://cdn.mysql.com//Downloads/Connector-J/mysql-connector-java-5.1.48.tar.gz
RUN tar xf mysql-connector-java-5.1.48.tar.gz
RUN mv mysql-connector-java-5.1.48/mysql-connector-java-5.1.48.jar $SPARK_HOME/jars
RUN rm -rf mysql-connector-java-5.1.48

WORKDIR $SPARK_HOME
# ENTRYPOINT ["/usr/sbin/sshd", "-D"]
CMD ["bin/spark-class", "org.apache.spark.deploy.master.Master"]
