from __future__ import annotations

import argparse
from io import BytesIO
from pathlib import Path
from urllib.request import urlopen

import librosa
import torch
from transformers import AutoProcessor, Qwen2AudioForConditionalGeneration

MODEL_TITLE = "LumynaX Infused Qwen2 Audio 7B"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=f"Run a local audio chat for {MODEL_TITLE}.")
    parser.add_argument("--audio", default="", help="Local audio path or audio URL.")
    parser.add_argument("--prompt", default="Describe what you hear.", help="Optional instruction for the audio turn.")
    parser.add_argument(
        "--system-prompt",
        default="You are LumynaX. Be clear about what you can infer from the audio and what you cannot.",
        help="Optional system prompt override.",
    )
    parser.add_argument("--max-new-tokens", type=int, default=256)
    return parser


def _load_audio(audio_ref: str, *, sampling_rate: int):
    audio_ref = audio_ref.strip()
    if audio_ref.startswith(("http://", "https://")):
        return librosa.load(BytesIO(urlopen(audio_ref).read()), sr=sampling_rate)[0]
    return librosa.load(Path(audio_ref).expanduser(), sr=sampling_rate)[0]


def main() -> None:
    args = _build_parser().parse_args()
    if not args.audio.strip():
        raise SystemExit("--audio is required.")

    model_dir = Path(__file__).resolve().parent / "merged_model"
    processor = AutoProcessor.from_pretrained(model_dir)
    model = Qwen2AudioForConditionalGeneration.from_pretrained(
        model_dir,
        torch_dtype="auto",
        device_map="auto",
    )

    conversation = [
        {"role": "system", "content": args.system_prompt.strip()},
        {
            "role": "user",
            "content": [
                {"type": "audio", "audio_url": args.audio.strip()},
                {"type": "text", "text": args.prompt.strip()},
            ],
        },
    ]
    text = processor.apply_chat_template(conversation, add_generation_prompt=True, tokenize=False)
    audio = _load_audio(args.audio, sampling_rate=processor.feature_extractor.sampling_rate)
    inputs = processor(text=text, audios=[audio], return_tensors="pt", padding=True)
    for key, value in list(inputs.items()):
        if hasattr(value, "to"):
            inputs[key] = value.to(model.device)

    with torch.inference_mode():
        generated = model.generate(**inputs, max_new_tokens=args.max_new_tokens)

    prompt_length = inputs["input_ids"].size(1)
    response = processor.batch_decode(
        generated[:, prompt_length:],
        skip_special_tokens=True,
        clean_up_tokenization_spaces=False,
    )[0]
    print(response)


if __name__ == "__main__":
    main()
