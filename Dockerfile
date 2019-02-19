# backend: pytorch | pznet
ARG BACKEND=pytorch

FROM seunglab/chunkflow:${BACKEND}

LABEL maintainer = "Jingpeng Wu" \
    email = "jingpeng@princeton.edu"

RUN mkdir -p $HOME/workspace/chunkflow
WORKDIR $HOME/workspace 
ADD . chunkflow/ 

RUN apt-get update && apt-get install -y -qq --no-install-recommends \
        apt-utils \
        wget \
        git \
    && pip install --user --upgrade pip \
    && pip install numpy --no-cache-dir \ 
    && pip install fpzip --no-binary :all: --no-cache-dir \
#&& git clone --single-branch --depth 1 https://github.com/seung-lab/cloud-volume.git \
#   && pip install --no-cache-dir -r /root/cloud-volume/requirements.txt \
    && pip install -r $HOME/workspace/chunkflow/requirements.txt --no-cache-dir \
    # clean up apt install
    && apt-get clean \
    && apt-get autoremove --purge -y \
    && rm -rf /var/lib/apt/lists/* \
    # setup environment variables
    && echo "export LC_ALL=C.UTF-8" >> $HOME/.bashrc \
    && echo "export LANG=C.UTF-8" >> $HOME/.bashrc \
    && echo "export PYTHONPATH=$HOME/workspace/chunkflow:\$PYTHONPATH" >> $HOME/.bashrc \ 
    && echo "export PYTHONPATH=$HOME/workspace/cloud-volume:\$PYTHONPATH" >> $HOME/.bashrc 

WORKDIR $HOME/workspace/chunkflow/scripts
