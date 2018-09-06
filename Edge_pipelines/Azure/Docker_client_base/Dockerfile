FROM resin/raspberrypi3-debian:stretch

WORKDIR /app

# Install dependencies of Jessie on Stretch (like libboost and libssl1)
RUN echo "deb http://deb.debian.org/debian jessie main" >> /etc/apt/sources.list
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    libasound2-dev \
    libboost-python1.55-dev \
    libcurl4-openssl-dev \
    libffi-dev \
    libpulse-dev \
    libssl-dev \
    libssl1.0.0 \
    python-dev \
    python-pip \
    python-setuptools \
    swig \
    nano

# Install python requirements (example azure-iothub-device-client==1.4.0.0b0)
COPY requirements.txt ./
RUN pip install -r requirements.txt


