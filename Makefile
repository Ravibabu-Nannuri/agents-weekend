PY := .venv/bin/python

.PHONY: setup check test b01 b02 b03 b04 b05 b06 b07 b08

setup:            ## create venv + install everything
	python3 -m venv .venv
	$(PY) -m pip install -q --upgrade pip
	$(PY) -m pip install -q -r requirements.txt
	@test -f .env || (cp .env.example .env && echo "Created .env – now fill in your keys")

check:            ## verify keys, model access and Langfuse
	$(PY) scripts/check_setup.py

test:             ## offline tests with a fake model (no keys, no cost)
	$(PY) -m pytest -q tests

b01: ; $(PY) 01-first-agent/solution.py
b02: ; $(PY) 02-tools/solution.py
b03: ; $(PY) 03-memory/solution.py
b04: ; $(PY) 04-multi-agent/solution.py
b05: ; $(PY) 05-human-in-the-loop/solution.py
b06: ; $(PY) 06-evals/run_evals.py --upload --run-name baseline
b07: ; $(PY) 07-cost-latency-guardrails/solution.py
b08: ; $(PY) 08-agents-sdk-comparison/helpdesk_agents_sdk.py
