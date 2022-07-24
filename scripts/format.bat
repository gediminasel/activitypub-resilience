@echo off
python -m black --target-version py37 .
python -m flake8
python -m isort .
