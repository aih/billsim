.PHONY: docs 

default: test

docs:
	./docs_generator.sh
test:
	pytest -rs tests 

test-debug:
	pytest --log-cli-level=DEBUG -s tests

build: 
	make test
	pip install -e .