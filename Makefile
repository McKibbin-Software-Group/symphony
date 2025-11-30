# (default target) Run the chosen target by default
default: run

MODEL = "domains.sym"
run:
	@echo "Running tests/models/model.sym with processor.py ..." ; \
	python src/symphony/processor.py tests/data/models/${MODEL}; 

# Generate html and sym files on MacOS for the model using the sym processor
# Custom SYM processor variable definitions
SYM=sym
FILE ?= set-1.sym
FILENAME = model-${FILE}
sym:
	@echo "Running SYM processor on $(FILENAME).sym ..." ; \
	cd sym ;\
	rm -f *.html && rm -f *.csv && rm -f *.lis && rm -f *.py ;\
	$(SYM) -python $(FILENAME).sym result_$(FILENAME).py ;\
	cd ..

# Run all unit tests.
tests:
	pytest -q tests

# Run a specific unit test by name.
# e.g. make test test_processor_commandline_interface
TEST = test_members_syntax
#TEST = test_categories_syntax
#TEST = test_dimensions_syntax
#TEST = test_domains_syntax
test:
	pytest -q tests -k "$(TEST)"

members:
	pytest -q tests -k "test_members_syntax"

categories:
	pytest -q tests -k "test_categories_syntax"

dimensions:
	pytest -q tests -k "test_dimensions_syntax"

domains:
	pytest -q tests -k "test_domains_syntax"

listtests:
	py.test tests -q --collect-only	

# Format the source code using the black formatter.
# https://pypi.org/project/black/
format:
	black src/gcubed
	black tests

# Source package for distribution
whl:
	python3 -m build --wheel --no-isolation src ; \

# Convert gcubed package to contain pyc code only
pyc:
	python3 -m pyc_wheel src/dist/*.whl

# Byte compiled package for distribution (install build package using pip first.)
build:
	@rm -rf src/dist/*.tz ; \
	rm -rf src/dist/*.whl ; \
	python3 -m build --wheel --no-isolation src ; \
#	python3 -m pyc_wheel src/dist/*.whl ; \
#	echo "Built the byte compiled WHL file in src/dist"

doco:
	export PDOC_ALLOW_EXEC=1 \
	cd src && pdoc --no-browser --t ./pdoc_templates --docformat markdown --math --no-show-source  -o src/documentation gcubed && cd ..

# Install the required Python packages.
init:
	uv pip install -r requirements.txt

# Git staging of changes, commit, and push to remote repository on Github
push:
	@read -p "Enter commit message: " message; \
	echo "Adding changes..."; \
	git add .; \
	echo "Committing changes..."; \
	git commit -m "$$message"; \
	echo "Pushing to remote repository..."; \
	git push; \
	echo "Done"

# List the targets that are not related to specific file timestamps
.PHONY: push sym run format whl pyc build doco tests test test-one listtests init
