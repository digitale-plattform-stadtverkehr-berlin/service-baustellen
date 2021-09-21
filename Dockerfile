FROM python:3-alpine

WORKDIR /usr/src/app

ENV OCIT_USER = ""
ENV OCIT_PASSWORD = ""

#az storage account show-connection-string -g <ResourceGroup> -n <Resource-Name>
ENV AZURE_CONN_STR = ""

ENV AZURE_CONTAINER_NAME = ""
ENV AZURE_BLOB_NAME = ""


COPY requirements.txt ./

RUN apk add proj proj-dev proj-util && \
    apk add gcc musl-dev libffi-dev && \
    apk add rust libxml2-dev libxslt-dev cargo openssl-dev && \
    pip3 install --no-cache-dir  -r requirements.txt && \
    apk del gcc cargo rust proj && \
    rm -rf /root/.cargo/

COPY baustellen.py ./

CMD [ "python3", "-u", "baustellen.py"]
