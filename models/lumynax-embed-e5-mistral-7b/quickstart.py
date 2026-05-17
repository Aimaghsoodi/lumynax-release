from __future__ import annotations

import argparse
import json
from pathlib import Path

from sentence_transformers import SentenceTransformer

MODEL_TITLE = "LumynaX Embed E5 Mistral 7B"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=f"Generate dense embeddings with {MODEL_TITLE}.")
    parser.add_argument("texts", nargs="*", help="Text inputs to embed.")
    parser.add_argument("--prompt-name", default="web_search_query", help="SentenceTransformer prompt preset.")
    parser.add_argument("--max-seq-length", type=int, default=4096)
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    texts = args.texts or ["LumynaX packages local models for retrieval."]
    model_dir = Path(__file__).resolve().parent / "merged_model"
    model = SentenceTransformer(str(model_dir))
    model.max_seq_length = args.max_seq_length
    embeddings = model.encode(
        texts,
        prompt_name=args.prompt_name or None,
    )
    print(
        json.dumps(
            {
                "model_title": MODEL_TITLE,
                "count": len(texts),
                "embedding_dim": len(embeddings[0]),
                "embeddings": embeddings.tolist(),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
