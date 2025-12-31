PYTHON := python
SCRIPT := restamp.py

INPUT  := photos
OUTPUT := output

.PHONY: run clean help

run:
	$(PYTHON) $(SCRIPT) $(INPUT) $(OUTPUT)

clean:
	rm -rf $(OUTPUT)

