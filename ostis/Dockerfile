FROM ubuntu:noble AS runtime

ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates tini python3 python3-venv \
    libglib2.0-0t64 libxml2 libssl3t64 libstdc++6 libgcc-s1 \
    && rm -rf /var/lib/apt/lists/*

COPY ostis/upstream/requirements.txt /app/requirements.txt
RUN python3 -m venv /app/.venv && /app/.venv/bin/pip install --no-cache-dir -r /app/requirements.txt
COPY ostis/upstream/scripts /app/scripts
RUN python3 -c "from pathlib import Path; p=Path('/app/scripts/docker_entrypoint.sh'); p.write_bytes(p.read_bytes().replace(b'\r\n', b'\n')); p.chmod(0o755)"
COPY ostis/UPSTREAM_LICENSE /usr/share/licenses/ostis-legislation/LICENSE
COPY ostis/SC_MACHINE_LICENSE /usr/share/licenses/sc-machine/LICENSE
ENV LD_LIBRARY_PATH=/app/sc-machine/lib

# Официальный CPack SDK 0.10.0: библиотеки, заголовки и CMake targets.
# Штатный find_package(sc-machine) не требует Conan для этого способа установки.
FROM runtime AS sdk
ARG TARGETARCH
RUN test "$TARGETARCH" = amd64 || (echo 'Официальный Linux SDK 0.10.0 предназначен для amd64.' && exit 1)
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*
RUN curl --fail --location --retry 3 --connect-timeout 30 \
    https://github.com/ostis-ai/sc-machine/releases/download/0.10.0/sc-machine-0.10.0-Linux.tar.gz \
    --output /tmp/sc-machine.tar.gz \
    && mkdir /app/sc-machine \
    && tar -xzf /tmp/sc-machine.tar.gz -C /app/sc-machine --strip-components=1 \
    && rm /tmp/sc-machine.tar.gz

FROM sdk AS builder
ARG BUILD_JOBS=2
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake ninja-build ccache libssl-dev patch \
    && rm -rf /var/lib/apt/lists/*
COPY ostis/upstream/ /app/
COPY ostis/patches/user-request-agent.patch /tmp/user-request-agent.patch
RUN patch --batch --fuzz=0 -p1 < /tmp/user-request-agent.patch \
    && cmake -S /app -B /app/build/Release -G Ninja \
    -DCMAKE_BUILD_TYPE=Release -DSC_BUILD_TESTS=OFF \
    -DCMAKE_PREFIX_PATH=/app/sc-machine \
    && cmake --build /app/build/Release --parallel "$BUILD_JOBS"

FROM runtime AS final
COPY --from=sdk /app/sc-machine /app/sc-machine
COPY --from=builder /app/build/Release/extensions /app/build/Release/extensions
COPY ostis/verify_runtime.py /app/verify_runtime.py
COPY ostis/entrypoint.py /app/entrypoint.py
COPY ostis/knowledge-additions /app/knowledge-additions
RUN python3 /app/verify_runtime.py
EXPOSE 8090
ENTRYPOINT ["/usr/bin/tini", "--", "/app/.venv/bin/python3", "/app/entrypoint.py"]
