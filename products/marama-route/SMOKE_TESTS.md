# MaramaRoute Smoke Tests

Run from the package root:

```bash
pip install -e .
python quickstart.py
python -m marama_route.cli ui --smoke
python -m marama_route.cli serve --smoke
python -m marama_route.cli catalog --registry configs/lumynax_model_registry.json --task code --limit 5
python -m marama_route.cli matrix --registry configs/lumynax_model_registry.json
python -m marama_route.cli chat-dry-run --registry configs/lumynax_model_registry.json --request examples/request.openai-chat-code.json
```

Expected: all commands exit 0 and emit OpenAI-compatible route metadata.
