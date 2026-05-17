# SovereignCode Smoke Tests

Run from the package root:

```bash
pip install -e .
python quickstart.py
python -m sovereigncode.cli ui --smoke
python -m sovereigncode.cli serve --smoke
python -m sovereigncode.cli policy-matrix --capsule examples/capsule.restricted-nz-code.json --request examples/request.allowed-local-edit.json
python -m sovereigncode.cli tool-check --capsule examples/capsule.restricted-nz-code.json --request examples/request.allowed-local-edit.json --tool-name workspace_reader --action read_context
python -m sovereigncode.cli audit --limit 5
python -m sovereigncode.cli evaluate --capsule examples/capsule.personal-sovereignty-profile.json --request examples/request.personal-memory-read.json
```

Expected: all commands exit 0 and emit JSON decisions with audit records.
