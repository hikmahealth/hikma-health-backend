FROM ubuntu:latest
RUN apt-get update -y
RUN apt-get install -y software-properties-common
RUN add-apt-repository ppa:deadsnakes/ppa
RUN apt-get update -y
RUN apt-get install -y python3.7 python3.7-dev python3-pip build-essential postgresql-client libpq-dev wget git

COPY requirements.txt /

RUN python3.7 -m pip install pip
RUN python3.7 -m pip install -r requirements.txt

ARG app_env_arg
ENV APP_ENV=$app_env_arg

ARG db_instance_arg
ENV DB_INSTANCE=$db_instance_arg

ARG db_password_arg
ENV DB_PASSWORD=$db_password_arg

ARG db_name_arg
ENV DB_NAME=$db_name_arg

ARG credential_file_arg
ENV GOOGLE_APPLICATION_CREDENTIALS=$credential_file_arg

ARG photos_storage_bucket_arg
ENV PHOTOS_STORAGE_BUCKET=$photos_storage_bucket_arg

ARG exports_storage_bucket_arg
ENV EXPORTS_STORAGE_BUCKET=$exports_storage_bucket_arg

ARG default_provider_id_arg
ENV DEFAULT_PROVIDER_ID=$default_provider_id_arg

# Necessary for Celery to run properly inside docker
ENV C_FORCE_ROOT=1

EXPOSE 8080

RUN mkdir app
WORKDIR /app

RUN wget -q https://dl.google.com/cloudsql/cloud_sql_proxy.linux.amd64 -O cloud_sql_proxy
RUN chmod +x cloud_sql_proxy

COPY . .

ENV PYTHONPATH=/app
CMD ./run.sh
