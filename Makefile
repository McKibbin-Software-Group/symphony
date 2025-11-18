# Custom SYM processor variable definitions
SYM=sym
FILE ?= set-1.sym
FILENAME = model-${FILE}

# Custom Lark Parser variable definitions
GRAMMAR = grammar.lark
MODEL = model.sym
MODEL_PARSER = ToAST.py
CASE = 1.0.0
DECLARATIONS = declarations_${CASE}

# (default target) Run the chosen target by default
default: run

run:
	@echo "Running use case ${CASE} ${MODEL} with ${MODEL_PARSER} ..." ; \
	cd python/${DECLARATIONS}/ ; \
	python ${MODEL_PARSER} --grammar ${GRAMMAR} ${MODEL}
	cd ../.. ; 


# Generate html and sym files on MacOS for the model using the sym processor
sym:
	@echo "Running SYM processor on $(FILENAME).sym ..." ; \
	cd sym ;\
	rm -f *.html && rm -f *.csv && rm -f *.lis && rm -f *.py ;\
	$(SYM) -python $(FILENAME).sym result_$(FILENAME).py ;\
	cd ..

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
.PHONY: push sym run
