from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch
from transformers import AutoModelForMultimodalLM, AutoProcessor

MODEL_TITLE = "LumynaX Infused Gemma E4B Model"
SUPPORTED_MODALITIES = ('text', 'image', 'audio')
DEFAULT_ENABLE_THINKING = True


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            f"Run a local Gemma E4B quickstart for {MODEL_TITLE}. "
            f"Supported modalities: text, image, audio."
        )
    )
    parser.add_argument("--mode", choices=["text", "image", "audio"], default="text")
    parser.add_argument(
        "--prompt",
        default="Explain in two short bullet points what this local package is.",
        help="Text instruction to send to the model.",
    )
    parser.add_argument("--image", default="", help="Local image path or image URL for --mode image.")
    parser.add_argument("--audio", default="", help="Local audio path or audio URL for --mode audio.")
    parser.add_argument("--max-new-tokens", type=int, default=256)
    parser.add_argument(
        "--thinking",
        action=argparse.BooleanOptionalAction,
        default=DEFAULT_ENABLE_THINKING,
        help="Enable Gemma reasoning mode.",
    )
    return parser


def _message_content(args: argparse.Namespace) -> list[dict[str, str]]:
    if args.mode == "text":
        return [{"type": "text", "text": args.prompt}]
    if args.mode == "image":
        if not args.image:
            raise SystemExit("--image is required when --mode image is used.")
        image_ref = args.image.strip()
        return [
            {"type": "image", "url": image_ref},
            {"type": "text", "text": args.prompt},
        ]
    if not args.audio:
        raise SystemExit("--audio is required when --mode audio is used.")
    audio_ref = args.audio.strip()
    return [
        {"type": "audio", "audio": audio_ref},
        {"type": "text", "text": args.prompt},
    ]


def main() -> None:
    args = _build_parser().parse_args()
    model_dir = Path(__file__).resolve().parent / "merged_model"
    if not model_dir.exists():
        raise SystemExit(f"Expected merged_model/ at {model_dir}")

    processor = AutoProcessor.from_pretrained(model_dir)
    model = AutoModelForMultimodalLM.from_pretrained(
        model_dir,
        dtype="auto",
        device_map="auto",
    )
    messages = [
        {
            "role": "user",
            "content": _message_content(args),
        },
    ]
    inputs = processor.apply_chat_template(
        messages,
        tokenize=True,
        return_dict=True,
        return_tensors="pt",
        add_generation_prompt=True,
        enable_thinking=args.thinking,
    ).to(model.device)
    input_len = inputs["input_ids"].shape[-1]

    with torch.inference_mode():
        outputs = model.generate(**inputs, max_new_tokens=args.max_new_tokens)

    response = processor.decode(outputs[0][input_len:], skip_special_tokens=False)
    parsed = processor.parse_response(response) if hasattr(processor, "parse_response") else response
    if isinstance(parsed, str):
        print(parsed)
        return
    print(json.dumps(parsed, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
