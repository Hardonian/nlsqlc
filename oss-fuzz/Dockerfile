FROM gcr.io/oss-fuzz-base/base-builder
RUN apt-get update && apt-get install -y --no-install-recommends cmake ninja-build && rm -rf /var/lib/apt/lists/*
COPY . $SRC/nlsqlc
WORKDIR $SRC/nlsqlc