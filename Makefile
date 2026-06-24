.PHONY: lint dev lint-check unit-tests coverage html-cov build

lint:
	poetry run black .
	poetry run ruff check --fix .

dev: lint
	poetry run pyright .

lint-check:
	poetry run black --check .
	poetry run ruff check .
	poetry run pyright .
	poetry run interrogate platzky_sendmail/ --verbose

unit-tests:
	poetry run python -m pytest -v

coverage:
	poetry run coverage run --branch --source=platzky_sendmail -m pytest -m "not skip_coverage"
	poetry run coverage report --fail-under=90

html-cov: coverage
	poetry run coverage html

build:
	poetry build
