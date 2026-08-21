ARG RUST_VERSION=1.97.0
ARG UV_VERSION=0.12.5

FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv

FROM rust:${RUST_VERSION}-bookworm AS base

ARG JUST_VERSION=1.58.0
ARG VIZOR_REPOSITORY=https://github.com/chainapsis/vizor-wallet
ARG VIZOR_REVISION=d60ea8ef853d02e6ea31573e75c5603db1d7addb

ENV CARGO_TARGET_DIR=/workspace/cargo-target \
    PATH=/opt/venv/bin:${PATH} \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON=python3

RUN apt-get update \
    && apt-get install --yes --no-install-recommends \
        ca-certificates \
        clang \
        cmake \
        git \
        libsqlite3-dev \
        libssl-dev \
        pkg-config \
        python3 \
        python3-venv \
    && rm -rf /var/lib/apt/lists/*

COPY --from=uv /uv /uvx /usr/local/bin/

RUN cargo install just --version "${JUST_VERSION}" --locked

WORKDIR /workspace/zcash-privacy-stack

COPY pyproject.toml uv.lock ./
RUN uv sync --locked --all-groups --no-install-project

COPY . .
RUN uv sync --locked --all-groups

RUN git init /workspace/vizor-wallet \
    && git -C /workspace/vizor-wallet remote add origin "${VIZOR_REPOSITORY}" \
    && git -C /workspace/vizor-wallet config http.version HTTP/1.1 \
    && for attempt in 1 2 3; do \
        if git -C /workspace/vizor-wallet fetch --depth=1 origin "${VIZOR_REVISION}"; then \
            break; \
        fi; \
        if [ "${attempt}" = 3 ]; then \
            exit 1; \
        fi; \
        sleep "$((attempt * 2))"; \
    done \
    && git -C /workspace/vizor-wallet checkout --detach "${VIZOR_REVISION}"

RUN git config --global --add safe.directory /workspace/vizor-wallet \
    && cargo fetch --locked --manifest-path /workspace/vizor-wallet/rust/Cargo.toml

FROM base AS test

RUN uv run pytest
RUN uv run ruff check .
RUN uv run basedpyright
RUN uv run python -m scripts.inspect_legacy_client --client vizor

FROM test AS cli

ENTRYPOINT ["uv", "run", "python", "-m", "scripts.inspect_legacy_client"]
