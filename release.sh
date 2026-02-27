#!/usr/bin/env bash

set -euo pipefail

VERSION="${1:-}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -z "${VERSION}" ]]; then
  echo "Usage: $0 <version>" >&2
  exit 1
fi

cd "${SCRIPT_DIR}"

tmp_file="$(mktemp)"
trap 'rm -f "${tmp_file}"' EXIT

if ! grep -qE '^version = "[^"]+"' pyproject.toml; then
  echo "Failed to find a version line in pyproject.toml" >&2
  exit 1
fi

sed -E '1,/^version = "[^"]+"/ s/^version = "[^"]+"/version = "'"${VERSION}"'"/' pyproject.toml > "${tmp_file}"

if cmp -s pyproject.toml "${tmp_file}"; then
  echo "Version already set to ${VERSION}; nothing to commit." >&2
  exit 1
fi

mv "${tmp_file}" pyproject.toml

prek run --all-files uv-lock || true

git add pyproject.toml uv.lock
SKIP=no-commit-to-branch git commit -m "chore(release): bump version to ${VERSION}"
git tag -a "${VERSION}" -m "${VERSION}"

git push
git push origin $VERSION
