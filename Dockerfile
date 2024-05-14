# Copyright (c) NVIDIA CORPORATION
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.
#
# Docker file making ctam build
#

FROM ubuntu:22.04

RUN apt-get update && apt-get install -y software-properties-common

RUN add-apt-repository ppa:deadsnakes/ppa

RUN apt-get update

RUN apt-get install python3-pip  zlib1g-dev scons -y

WORKDIR /app

COPY . /app

RUN pip3 install --no-cache-dir --upgrade  -r pip-requirements.txt

RUN pip3 install --no-cache-dir --upgrade pyinstaller staticx patchelf-wrapper

COPY build_scripts/build_script.sh .

ENTRYPOINT ["/bin/sh", "build_script.sh"]
