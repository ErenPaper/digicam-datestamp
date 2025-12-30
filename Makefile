PY ?= py
INPUT ?= input
OUTPUT ?= output

install:
	$(PY) -m pip install -r requirements.txt

run:
	$(PY) restamp.py -i "$(INPUT)" -o "$(OUTPUT)"

clean:
	@if exist "$(OUTPUT)" del /q "$(OUTPUT)\*" 2>nul || exit 0

reset:
	@if exist "$(OUTPUT)" rmdir /s /q "$(OUTPUT)"
	@mkdir "$(OUTPUT)"
