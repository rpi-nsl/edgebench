FROM mcr.microsoft.com/azure-functions/python:2.0.12382

COPY . /home/site/wwwroot

RUN apt-get update && apt-get install -y \
	build-essential \
	cmake

RUN cd /home/site/wwwroot && \
    pip install -r requirements.txt
