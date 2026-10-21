# Hermetic build and test environment, for CI parity and for machines that
# would rather not install a toolchain. Not required: bootstrap.sh gives the
# same result natively, and rust-toolchain.toml pins the compiler either way.
#
#   podman build -t publet-dev -f Containerfile .
#   podman run --rm --userns=keep-id:uid=1000,gid=1000 -v "$PWD:/w:Z" -w /w publet-dev make check
#
# The image runs as `builder` (uid 1000), not root. --userns=keep-id maps you
# onto that user, so the build can write target/ in your checkout.
FROM docker.io/library/rust:1.98.1-slim-bookworm

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      make git jq python3 python3-venv ca-certificates \
 && rm -rf /var/lib/apt/lists/*

RUN rustup component add clippy rustfmt

WORKDIR /w
COPY tests/requirements.lock /tmp/requirements.lock
RUN python3 -m venv /opt/venv \
 && /opt/venv/bin/pip install --quiet --upgrade pip \
 && /opt/venv/bin/pip install --quiet --require-hashes -r /tmp/requirements.lock
ENV PATH="/opt/venv/bin:${PATH}"

# rustup installs the pinned toolchain on first use and cargo fills its
# registry, so the builder owns both homes.
RUN useradd --uid 1000 --user-group --create-home builder \
 && chown -R builder:builder "$CARGO_HOME" "$RUSTUP_HOME"
USER builder

CMD ["make", "check"]
