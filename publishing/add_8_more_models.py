"""Retired one-off release script retained only as an explicit migration marker."""

raise SystemExit(
    "This one-off publisher is retired. Add manifests through the canonical registry, then run "
    "`python publishing/maintain_legacy_archive.py --write`."
)
