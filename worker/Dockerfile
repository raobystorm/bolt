FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on

RUN python -m pip install --upgrade pip

ENV HOME /usr/app/bolt
WORKDIR $HOME

RUN apt-get update \
    && apt-get install --no-install-recommends -y libgomp1 g++ curl git make \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONPATH "/usr/app/bolt:$PYTHONPATH"
