default: test

test:
	pytest -rs tests 

test-debug:
	pytest --log-cli-level=DEBUG -s tests