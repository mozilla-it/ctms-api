#!/bin/sh

set -e

POETRY_RUN="poetry run"
CURRENT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
BASE_DIR="$(dirname "$CURRENT_DIR")"


BANDIT_CMD="$POETRY_RUN bandit -lll --recursive ${BASE_DIR} --exclude ${BASE_DIR}/poetry.lock,${BASE_DIR}/.venv,${BASE_DIR}/.mypy,${BASE_DIR}/build"

FORMAT_CMD="$POETRY_RUN ruff format $BASE_DIR"

# Scan only files fixed into the repo, omit poetry.lock
DETECT_SECRETS_FILES="$(git ls-tree --full-tree -r --name-only HEAD | grep -v poetry.lock)"
DETECT_SECRETS_CMD="$POETRY_RUN detect-secrets-hook $DETECT_SECRETS_FILES --baseline .secrets.baseline"

LINT_CMD="$POETRY_RUN ruff check $BASE_DIR"

MYPY_CMD="$POETRY_RUN mypy ${BASE_DIR}/ctms"


all () {
  echo "running format (check only)"
  $FORMAT_CMD
  echo "running lint"
  $LINT_CMD
  echo "running mypy"
  $MYPY_CMD
  echo "running bandit"
  $BANDIT_CMD
  echo "running detect_secrets"
  $DETECT_SECRETS_CMD
}

usage () {
  echo "Usage: bin/lint.sh [subcommand] [--fix]"
  echo " run linting checks, and optionally fix in place (if available)"
  echo "Subcommand":
  echo "  bandit"
  echo "  detect-secrets"
  echo "  format"
  echo "  lint"
  echo "  mypy"
}

if [ -z "$1" ]; then
  all
else
  subcommand=$1; shift
  case $subcommand in
    "format")
      if [ -n "$1" ] && [ "$1" != "--fix" ]; then
        usage
      else
        check_flag="--check"
        [ "$1" = "--fix" ] && check_flag=""
        $FORMAT_CMD ${check_flag:-}
      fi
      ;;
    "lint")
      if [ -n "$1" ] && [ "$1" != "--fix" ]; then
        usage
      else
        $LINT_CMD ${1:-}
      fi
      ;;
    "mypy")
      $MYPY_CMD
      ;;
    "bandit")
      $BANDIT_CMD
      ;;
    "detect-secrets")
      $DETECT_SECRETS_CMD
      ;;
    *)
      usage
      ;;
  esac
fi
