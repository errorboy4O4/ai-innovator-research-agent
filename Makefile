.PHONY: test lint run scan

test:
	python -m pytest tests/ -v

lint:
	python -m ruff check src/ tests/
	python -m ruff format --check src/ tests/

format:
	python -m ruff format src/ tests/
	python -m ruff check --fix src/ tests/

run:
	python -m research_agent.cli run --ticker SRVCABLE --pack data/research_pack --as-of 2026-09-23

scan:
	python -m research_agent.cli scan --pack data/research_pack
