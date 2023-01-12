#!/bin/bash

set -euo pipefail

detect-secrets scan . \
--baseline .secrets.baseline \
--exclude-files "(poetry.lock$)|(htmlcov/)"
