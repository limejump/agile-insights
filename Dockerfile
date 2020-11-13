FROM python:3.8 as test
COPY . /opt/code
WORKDIR /opt/code
RUN pip install .'[test]'
ENV PATH=$PATH:/usr/local/lib/python3.8/site-packages/bin/
ENV PYTHONPATH=/opt/code
RUN pytest

FROM python:3.8-slim-buster as production
COPY . /opt/code
WORKDIR /opt/code
RUN pip install .
ENV PATH=$PATH:/usr/local/lib/python3.8/site-packages/bin/
ENV PYTHONPATH=/opt/code
ENTRYPOINT ["gunicorn", "app:server", "-b", ":8000"]