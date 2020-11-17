FROM python:3.8-slim-buster
COPY ./migrations /opt/code
COPY migration-requirements.txt /opt/code
COPY migrate.sh /opt/code
WORKDIR /opt/code
RUN pip install -r migration-requirements.txt
RUN groupadd migrate && useradd -g migrate migrate
USER migrate
ENTRYPOINT ["./migrate.sh"]