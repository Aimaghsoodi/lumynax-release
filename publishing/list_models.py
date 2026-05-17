import os, json
from huggingface_hub import HfApi
api = HfApi(token=os.environ["HF_TOKEN"])
rows = []
for m in api.list_models(author="AbteeXAILab", full=True, cardData=True):
    rows.append({
        "id": m.id,
        "pipeline": getattr(m, "pipeline_tag", None),
        "downloads": getattr(m, "downloads", 0),
        "likes": getattr(m, "likes", 0),
        "tags": list(getattr(m, "tags", []) or []),
        "card": (m.card_data.to_dict() if getattr(m, "card_data", None) else None),
        "siblings": [s.rfilename for s in (getattr(m, "siblings", []) or [])],
        "last_modified": str(getattr(m, "last_modified", "")),
    })
print(f"TOTAL: {len(rows)}")
with open("S:/hf-publish/models.json", "w", encoding="utf-8") as f:
    json.dump(rows, f, indent=2, default=str)
for r in rows:
    print(r["id"], "|", r["pipeline"], "|", r["downloads"], "dl")
