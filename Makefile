PY ?= .venv/bin/python

.PHONY: venv fetch norm metagrid qlever link bio site serve test all
venv:
	python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt
fetch:
	$(PY) -m vv.fetch
norm:
	$(PY) -m vv.adapters
metagrid:
	$(PY) -m vv.metagrid --limit 3000
qlever:
	$(PY) -m vv.qlever
link:
	$(PY) -m vv.link
bio:
	$(PY) -m vv.bio
site:
	$(PY) -m vv.site
serve:
	$(PY) -m http.server 8000 --directory site
test:
	$(PY) -m pytest -q tests
all: norm link bio site
