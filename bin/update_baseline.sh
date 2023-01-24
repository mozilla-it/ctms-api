#!/bin/bash

set -euo pipefail

poetry run detect-secrets scan . \
--baseline .secrets.baseline \
--exclude-files "(poetry.lock$)|(htmlcov/)"
