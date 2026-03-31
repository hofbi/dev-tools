#!/usr/bin/env bash

set -euxo pipefail

SEMVER_REGEX='[0-9]+\.[0-9]+\.[0-9]+'
ROOT_TAG_REGEX="^${SEMVER_REGEX}$"
SUBPACKAGE_TAG_REGEX="^([a-zA-Z0-9_-]+)-(${SEMVER_REGEX})$"

package_name_to_directory() {
  local package_name="${1:-}"

  if [[ -z "${package_name}" ]]; then
    echo "Usage: package_name_to_directory <package-name>" >&2
    return 1
  fi

  printf '%s\n' "${package_name//-/_}"
}

parse_release_tag() {
  local tag="${1:-}"

  if [[ -z "${tag}" ]]; then
    echo "Usage: parse_release_tag <tag>" >&2
    return 1
  fi

  RELEASE_PACKAGE_NAME=""
  RELEASE_VERSION="${tag}"
  RELEASE_PYPROJECT_PATH="pyproject.toml"

  if [[ "${tag}" =~ ${SUBPACKAGE_TAG_REGEX} ]]; then
    RELEASE_PACKAGE_NAME="${BASH_REMATCH[1]}"
    RELEASE_VERSION="${BASH_REMATCH[2]}"
    RELEASE_PYPROJECT_PATH="packages/$(package_name_to_directory "${RELEASE_PACKAGE_NAME}")/pyproject.toml"
  elif [[ ! "${tag}" =~ ${ROOT_TAG_REGEX} ]]; then
    echo "Version must be '<major>.<minor>.<patch>' or '<package>-<major>.<minor>.<patch>'" >&2
    return 1
  fi
}

check_release_version() {
  local tag="${1:-}"

  parse_release_tag "${tag}" || return 1

  if [[ ! -f "${RELEASE_PYPROJECT_PATH}" ]]; then
    echo "No pyproject.toml found for release target: ${RELEASE_PYPROJECT_PATH}" >&2
    return 1
  fi

  if ! grep -qE "^version = \"${RELEASE_VERSION}\"([[:space:]]*#.*)?$" "${RELEASE_PYPROJECT_PATH}"; then
    echo "Version mismatch in ${RELEASE_PYPROJECT_PATH} vs the tag name" >&2
    return 1
  fi
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  set -euo pipefail
  check_release_version "${1:-}"
fi
