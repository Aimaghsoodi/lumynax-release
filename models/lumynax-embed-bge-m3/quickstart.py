from __future__ import annotations

import argparse
import json
from pathlib import Path

from FlagEmbedding import BGEM3FlagModel

MODEL_TITLE = "LumynaX Embed BGE M3"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=f"Generate dense embeddings with {MODEL_TITLE}.")
    parser.add_argument("texts", nargs="*", help="Text inputs to embed.")
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--max-length", type=int, default=8192)
    parser.add_argument("--use-fp16", action=argparse.BooleanOptionalAction, default=False)
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    texts = args.texts or ["LumynaX packages multilingual retrieval models."]
    model_dir = Path(__file__).resolve().parent / "merged_model"
    model = BGEM3FlagModel(str(model_dir), use_fp16=args.use_fp16)
    result = model.encode(
        texts,
        batch_size=args.batch_size,
        max_length=args.max_length,
    )
    dense_vectors = result["dense_vecs"]
    print(
        json.dumps(
            {
                "model_title": MODEL_TITLE,
                "count": len(texts),
                "embedding_dim": len(dense_vectors[0]),
                "embeddings": dense_vectors.tolist(),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
