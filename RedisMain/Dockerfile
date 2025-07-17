FROM ubuntu:20.04

RUN apt-get update && apt-get install -y \
    g++ \
    cmake \
    make \
    libstdc++6 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

RUN cmake . && make

EXPOSE 1234
CMD ["./redis_server"]