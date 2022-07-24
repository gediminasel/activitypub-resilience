#!/bin/sh
python -m black --target-version py37 --check --diff . || exit 1
python -m flake8 --statistics --count || exit 1
python -m isort --check-only --diff . || exit 1
