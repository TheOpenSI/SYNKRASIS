FROM ubuntu:20.04
ENV DEBIAN_FRONTEND=noninteractive

# Add the deadsnakes PPA and install Python 3.9
RUN apt update && \
    apt install -y software-properties-common && \
    add-apt-repository ppa:deadsnakes/ppa && \
    apt update && \
    apt install -y python3.9 python3.9-distutils curl && \
    curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py && \
    python3.9 get-pip.py && \
    apt clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src/app

# Always run chmod before executing start.sh
ENTRYPOINT ["sh", "-c", "chmod +x /usr/src/app/start.sh && /usr/src/app/start.sh"]
