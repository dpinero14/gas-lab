PY ?= python
VENV ?= .venv
BIN := $(VENV)/bin
ifeq ($(OS),Windows_NT)
BIN := $(VENV)/Scripts
endif

.PHONY: setup test data partes notebooks

setup:
	$(PY) -m venv $(VENV)
	$(BIN)/python -m pip install --upgrade pip
	$(BIN)/python -m pip install -r requirements.txt
	$(BIN)/python -m ipykernel install --user --name gas-lab --display-name "gas-lab"

test:
	$(BIN)/python -m pytest -q tests

data:
	$(BIN)/python scripts/download_data.py

partes:
	$(BIN)/python scripts/download_partes.py 2014-01-01 --invierno
	$(BIN)/python scripts/download_partes.py 2014-01-01

notebooks:
	$(BIN)/python -m jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.kernel_name=gas-lab --ExecutePreprocessor.timeout=7200 notebooks/01_la_demanda_y_el_frio.ipynb
	$(BIN)/python -m jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.kernel_name=gas-lab --ExecutePreprocessor.timeout=7200 notebooks/02_alcanza_el_gas.ipynb
