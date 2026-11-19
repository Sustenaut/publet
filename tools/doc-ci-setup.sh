#!/usr/bin/env bash
# What `make design` needs on a CI runner, run by it only under CI: uv, which
# runs the pubdoc ./pubdoc pins, and typst. Kept in step with
# Sustenaut/docs' scripts/ci-setup.sh. Node.js and npx, which fetch the pinned Curvenote, are on the runner
# already. Each release is pinned and its download checked against the
# sha256 its release lists.
#
# Installs into ~/.local/bin and, under GitHub Actions, puts that on the PATH
# of the job's later steps. Safe to run again: a tool already at its pinned
# version is left as it is.
set -euo pipefail

UV_VERSION=0.12.18
UV_SHA256_X86_64=e38d97460b98ebfd31b197de0fe9fa578add4bc8ba0179b203dd3f87b99f98e6
UV_SHA256_AARCH64=0796973fb3eea8095078c3d0659bd17a5f6789a71b8dd85caff2483178f78ac3
TYPST_VERSION=0.15.1
TYPST_SHA256_X86_64=a6d077d0a95eed5a2eba715b2dae06be954f624ccbf85758a03f389ded33118c
TYPST_SHA256_AARCH64=5aa8d74a3d906e60ea12a66ac2f37f8eef1b14cbad7182a745e393a10c23dcee

case "$(uname -m)" in
  x86_64) arch=x86_64; uv_sum=$UV_SHA256_X86_64; typst_sum=$TYPST_SHA256_X86_64 ;;
  aarch64 | arm64) arch=aarch64; uv_sum=$UV_SHA256_AARCH64; typst_sum=$TYPST_SHA256_AARCH64 ;;
  *) echo "ci-setup: no uv or typst build pinned for $(uname -m)" >&2; exit 1 ;;
esac

bin="$HOME/.local/bin"
mkdir -p "$bin"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

# fetch URL SHA256 FILE: download URL to FILE, failing unless it has that sha256.
fetch() {
  curl -fsSL --retry 3 -o "$3" "$1"
  echo "$2  $3" | sha256sum -c --quiet -
}

if [ "$("$bin/uv" --version 2>/dev/null | cut -d' ' -f2)" != "$UV_VERSION" ]; then
  name="uv-${arch}-unknown-linux-musl"
  fetch "https://github.com/astral-sh/uv/releases/download/${UV_VERSION}/${name}.tar.gz" "$uv_sum" "$work/uv.tar.gz"
  tar -xzf "$work/uv.tar.gz" -C "$work"
  install -m 0755 "$work/$name/uv" "$work/$name/uvx" "$bin/"
fi

if [ "$("$bin/typst" --version 2>/dev/null | cut -d' ' -f2)" != "$TYPST_VERSION" ]; then
  name="typst-${arch}-unknown-linux-musl"
  fetch "https://github.com/typst/typst/releases/download/v${TYPST_VERSION}/${name}.tar.xz" "$typst_sum" "$work/typst.tar.xz"
  tar -xJf "$work/typst.tar.xz" -C "$work"
  install -m 0755 "$work/$name/typst" "$bin/"
fi

if [ -n "${GITHUB_PATH:-}" ]; then
  echo "$bin" >> "$GITHUB_PATH"
fi
export PATH="$bin:$PATH"
uv --version
typst --version
node --version
