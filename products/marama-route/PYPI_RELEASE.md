# PyPI Release: LumynaX MaramaRoute

Package: `lumynax-marama-route`
Version: `0.7.18`

## Local Build

```bash
python -m build
python -m twine check dist/*
python quickstart.py
marama-route serve --smoke
```

## Publish

```bash
python -m twine upload dist/*
```

Required local credentials: `TWINE_USERNAME=__token__` and `TWINE_PASSWORD=<pypi-token>`.
The GitHub workflow can publish with PyPI trusted publishing when the PyPI project
is configured to trust `Aimaghsoodi/lumynax-release`.

## Runtime Surface

- CLI: `marama-route`
- Conversational CLI: `marama-route chat` and `marama-route run <model>`
- Local UI/API: `marama-route serve --port 8787 --open`
- Route API: `GET /v1/models`, `POST /v1/route`, `POST /v1/chat/completions`
- Production checks: `marama-route doctor`, `marama-route agent doctor`, `marama-route verify --deep --write-hashes`
- HPE/HPC scaffolds: `marama-route hpe init <model>`
- Default mode: route-only, with live backend proxying configured in `configs/gateway.local.json`
