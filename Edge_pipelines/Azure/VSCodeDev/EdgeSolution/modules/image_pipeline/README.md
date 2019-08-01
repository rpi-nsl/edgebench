## The prebuild MXNET libraries has been borrowed from [AWS Greengrass samples](https://github.com/aws-samples/aws-greengrass-samples)

Greengrass Machine Learning Pre-built Libraries and Examples
================
This folder contains the machine learning pre-built libraries of MxNet and
examples. 

It contains the following directories and files:

* mxnet-python-unittests.tar.gz: unit tests for MxNet.
* mxnet-python.tar.gz: the MxNet binary.
* mxnet-python-tests-common.tar.gz: utils for model serving.

```
    FROM ubuntu:xenial

    WORKDIR /app

    RUN apt-get update && \
        apt-get install -y --no-install-recommends libcurl4-openssl-dev \
        python-pip \
        build-essential \
        cmake \
        wget \
        gcc \
        git \
        unzip \
        libboost-python1.58-dev \
        libpython-dev \
        libopenblas-dev \
        liblapack-dev  \
        libgtk2.0-dev \
        pkg-config \
        libavcodec-dev \
        libavformat-dev \
        libswscale-dev && \
        rm -rf /var/lib/apt/lists/* 

    RUN pip install --upgrade pip
    COPY requirements.txt ./
    RUN pip install -r requirements.txt

    ENV OPENCV_VERSION="3.1.0"

    RUN apt-get update \
        && wget https://github.com/opencv/opencv/archive/${OPENCV_VERSION}.zip \
        && unzip ${OPENCV_VERSION}.zip \
        && mkdir /opencv-${OPENCV_VERSION}/cmake_binary \
        && cd /opencv-${OPENCV_VERSION}/cmake_binary \
        && cmake -DBUILD_TIFF=ON \
        -DBUILD_opencv_java=OFF \
        -DWITH_CUDA=OFF \
        -DENABLE_AVX=OFF \
        -DWITH_OPENGL=ON \
        -DWITH_OPENCL=ON \
        -DWITH_IPP=ON \
        -DWITH_TBB=ON \
        -DWITH_EIGEN=ON \
        -DWITH_V4L=ON \
        -DBUILD_TESTS=OFF \
        -DBUILD_PERF_TESTS=OFF \
        -DCMAKE_BUILD_TYPE=RELEASE \
        -DCMAKE_INSTALL_PREFIX=$(python2.7 -c "import sys; print(sys.prefix)") \
        -DPYTHON_EXECUTABLE=$(which python2.7) \
        -DPYTHON_INCLUDE_DIR=$(python2.7 -c "from distutils.sysconfig import get_python_inc; print(get_python_inc())") \
        -DPYTHON_PACKAGES_PATH=$(python2.7 -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())") \
        .. \
        && make \
        && make install \
        && rm /${OPENCV_VERSION}.zip \
        && rm -r /opencv-${OPENCV_VERSION} \
        && ldconfig \  
        && apt-get remove --purge --auto-remove -y \
                                                build-essential \
                                                cmake \
                                                gcc \
                                                git \
                                                wget \
                                                unzip \
        && apt-get remove --purge --auto-remove -y \
                                                #libswscale-dev \ #this is needed
                                                libtbb-dev \
                                                libjpeg-dev \
                                                libpng-dev \
                                                libtiff-dev \
                                                # libavformat-dev \ #this is needed
                                                libpq-dev \
        && apt-get clean \
        && apt-get autoclean \
        && apt-get autoremove \
        && rm -rf /tmp/* /var/tmp/* \
        && rm -rf /var/lib/apt/lists/* \
        && rm -f /var/cache/apt/archives/*.deb \
        && rm -f /var/cache/apt/archives/partial/*.deb \
        && rm -f /var/cache/apt/*.bin \
        && rm -rf /root/.[acpw]*


    COPY . .

    RUN useradd -ms /bin/bash moduleuser
    USER moduleuser

    CMD [ "python", "-u", "./main.py" ]
```