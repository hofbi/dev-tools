#!/usr/bin/env bash

set -euxo pipefail

VERSION="${1:-}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -z "${VERSION}" ]]; then
  echo "Usage: $0 <version>" >&2
  exit 1
fi

cd "${SCRIPT_DIR}"

source "${SCRIPT_DIR}/scripts/check_release.sh"
parse_release_tag "${VERSION}"

PACKAGE_NAME="${RELEASE_PACKAGE_NAME}"
PACKAGE_VERSION="${RELEASE_VERSION}"
PYPROJECT_PATH="${RELEASE_PYPROJECT_PATH}"

if [[ ! -f "${PYPROJECT_PATH}" ]]; then
  echo "No pyproject.toml found for release target: ${PYPROJECT_PATH}" >&2
  exit 1
fi

tmp_file="$(mktemp)"
trap 'rm -f "${tmp_file}"' EXIT

if ! grep -qE '^version = "[^"]+"' "${PYPROJECT_PATH}"; then
  echo "Failed to find a version line in ${PYPROJECT_PATH}" >&2
  exit 1
fi

sed -E '1,/^version = "[^"]+"/ s/^version = "[^"]+"/version = "'"${PACKAGE_VERSION}"'"/' "${PYPROJECT_PATH}" > "${tmp_file}"

if cmp -s "${PYPROJECT_PATH}" "${tmp_file}"; then
  echo "Version already set to ${PACKAGE_VERSION}; nothing to commit." >&2
  exit 1
fi

mv "${tmp_file}" "${PYPROJECT_PATH}"

prek run --all-files uv-lock || true

git add "${PYPROJECT_PATH}" uv.lock
SKIP=no-commit-to-branch git commit -m "chore(release): bump ${PACKAGE_NAME:-root} version to ${PACKAGE_VERSION}"
git tag -a "${VERSION}" -m "${VERSION}"

git push
git push origin "${VERSION}"
