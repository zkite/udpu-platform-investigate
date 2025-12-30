PYTHON ?= python
PIP_COMPILE ?= pip-compile
PIP_SYNC ?= pip-sync
REQ_DIR = requirements

.PHONY: compile sync

compile:
\tcd $(REQ_DIR) && $(PIP_COMPILE) --upgrade --generate-hashes requirements.in
\tcd $(REQ_DIR) && $(PIP_COMPILE) --upgrade --generate-hashes requirements-dev.in

sync:
\tcd $(REQ_DIR) && $(PIP_SYNC) requirements.txt requirements-dev.txt
