.PHONY: test run reproduce
test:
	python -m unittest discover -s tests -v
run:
	python -m gfp_active_learning --output-dir results
reproduce:
	python -m gfp_active_learning --output-dir reproduced-results
	python scripts/check_reproduction.py results reproduced-results
