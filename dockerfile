FROM ubuntu:16.04
MAINTAINER sbofgayschoolbupaanything "1532422769@qq.com"

COPY --chown=root:root . /khala/

RUN requirement='libc6-dev make wget libcurl3 gcc build-essential python3 python3-pip python3-dev' \
    && apt-get update \
    && apt-get install -y $requirement \
    && cd /usr/local/bin \
    && ln -s /usr/bin/python3 python \
    && mv /khala/bin/* /usr/local/bin/ \
    && rmdir /khala/bin \
    && python -m pip install --upgrade pip \
    && cd /khala/ \
    && python -m pip install -r requirements.txt \
    && python -m pip install uwsgi \
    && cd executor && bash clean.bash \
    && cd ../gateway && bash clean.bash \
    && cd ../judicator && bash clean.bash \
    && cd .. \
    && chmod a+x entry.bash

ENV PYTHONPATH "${PYTHONPATH}:/khala/"

WORKDIR /khala/

ENTRYPOINT ["./entry.bash"]