PYTHON := python
SCRIPT := restamp.py

INPUT  := photos
OUTPUT := output

.PHONY: run clean help

run:
	$(PYTHON) $(SCRIPT) $(INPUT) $(OUTPUT)

iclean:
	rm -rf $(INPUT)/*

oclean:
	rm -rf $(OUTPUT)/*

