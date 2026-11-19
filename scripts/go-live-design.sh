#!/usr/bin/env bash
# Make the design project's corpus, design/corpus, and its own signing key,
# once, on David's machine: the step before any doc in design/ is approved as
# a signed version. Its key is not the one that signs publet's releases.
#
#   scripts/go-live-design.sh
#
# 1. design/corpus/: `pub corpus init` makes corpus.json and .publet/ (the
#    store, never committed), and `pub sign --generate-key` the key in
#    design/corpus/.publet/signing.key. An existing key is kept.
# 2. design/project.yml: corpus.key names that key, the one `pubdoc verify`
#    (make design, in CI) trusts.
# 3. Bitwarden: pubsec backs the key up as pubrules.json's signing_keys
#    declares it (pub-signing-key-publet-design, project Pub), asking for an
#    access token at a hidden prompt. Nothing secret is printed.
#
# Then commit design/corpus/corpus.json and design/project.yml (the script
# says so). Safe to run again: each step that is done is left as it is.
set -euo pipefail

cd "$(dirname "$0")/.."
PUBSEC="https://github.com/Sustenaut/pubsec/releases/download/v0.3.0/pubsec-0.3.0-py3-none-any.whl"
# uvx does not check a URL's #sha256= fragment, so the wheel is fetched and checked here.
PUBSEC_SHA256=a9036c741e29098cdd04baf64c7873e0ff1dd6e7bde12e9671a3940370724e18
CORPUS=design/corpus
PROJECT=design/project.yml

if [ "$(pub --version 2>/dev/null | head -n 1)" != "pub 0.4.0" ]; then
  echo "go-live: pubdoc signs with publet's pub 0.4.0; install it:" >&2
  echo "  cargo install --locked --git https://github.com/Sustenaut/publet --tag v0.4.0 publet-cli" >&2
  exit 1
fi
command -v uvx >/dev/null || { echo "go-live: pubsec runs with uv: curl -LsSf https://astral.sh/uv/install.sh | sh" >&2; exit 1; }

# A key the project already trusts, but not on this machine (another
# checkout, a rebuilt laptop): restore it rather than make another, which
# would no longer be the one verify trusts.
if [ ! -f "$CORPUS/.publet/signing.key" ] && grep -q "^corpus:.*key: pub:" "$PROJECT"; then
  echo "go-live: $PROJECT trusts a key that is not in $CORPUS/.publet/signing.key on this machine." >&2
  echo "  Restore it from Bitwarden (pub-signing-key-publet-design, project Pub) into $CORPUS/.publet/signing.key," >&2
  echo "  then run this again. Making a new key would leave the trusted one unused." >&2
  exit 1
fi

mkdir -p "$CORPUS"
if [ ! -f "$CORPUS/corpus.json" ]; then
  (cd "$CORPUS" && pub corpus init)
fi
if [ -f "$CORPUS/.publet/signing.key" ]; then
  echo "go-live: $CORPUS/.publet/signing.key exists; keeping it"
else
  (cd "$CORPUS" && pub sign --generate-key --principal=human)
fi

key="$(sed -n 's/^author=//p' "$CORPUS/.publet/config" | head -n 1)"
case "$key" in
  pub:sha2-256:*) ;;
  *) echo "go-live: $CORPUS/.publet/config names no author key" >&2; exit 1 ;;
esac
if grep -q "key: $key" "$PROJECT"; then
  echo "go-live: $PROJECT already trusts $key"
else
  sed -i.bak "s#^corpus: {path: corpus}\$#corpus: {path: corpus, key: $key}#" "$PROJECT" && rm -f "$PROJECT.bak"
  grep -q "key: $key" "$PROJECT" || { echo "go-live: could not write corpus.key into $PROJECT" >&2; exit 1; }
  echo "go-live: $PROJECT trusts $key"
fi

wheels="$(mktemp -d)"
trap 'rm -rf "$wheels"' EXIT
curl -fsSL -o "$wheels/${PUBSEC##*/}" "$PUBSEC"
echo "$PUBSEC_SHA256  $wheels/${PUBSEC##*/}" | sha256sum -c --quiet - \
  || { echo "go-live: ${PUBSEC##*/} is not the wheel pinned here" >&2; exit 1; }
uvx --from "$wheels/${PUBSEC##*/}" pubsec signing-key backup

echo
echo "go-live: done. Commit what it wrote, in this branch's pull request:"
echo "  git add $CORPUS/corpus.json $PROJECT && git commit -m 'The design corpus and its signing key'"
