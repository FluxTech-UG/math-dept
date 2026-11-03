# math-dept. One command per job; every target is also a plain python invocation.
.PHONY: check regen lean counterexamples test all

# Everything a commit must pass, Lean side excluded (that is `make lean`).
check:
	python -m mdept.check
	python -m mdept.index --check
	python -m mdept.bench --check
	python -m mdept.site --repo . --check
	python -m mdept.audit sorry
	python scripts/gen_root.py --check
	repo-outline --check

# Rewrite every generated view. Never hand-edit what this writes.
regen:
	python scripts/gen_root.py --write
	python -m mdept.index
	repo-outline --write

# Build Lean, run the axiom audit, cache the JSON the ledger checker reads.
lean:
	python -m mdept.audit all --json --write audit/latest.json

# Execute every counterexample artifact and require each witness to verify.
counterexamples:
	python -m mdept.refute --all

test:
	python -m pytest -v

all: regen check test

# The reading site (mdept/site.py, settings in site.toml): one page per entry and an index.
# `build/site/` is the local build and is gitignored; the `site` workflow publishes it to Pages.
.PHONY: site site-check figures
site:
	python -m mdept.site --repo . --out build/site

site-check:
	python -m mdept.site --repo . --check

# Redraw figures/MD_####.svg from every counterexample script that carries --svg.
figures:
	python -m mdept.figures --repo .
