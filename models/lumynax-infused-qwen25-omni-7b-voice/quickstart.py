from __future__ import annotations

import argparse
from pathlib import Path

import soundfile as sf
import torch
from qwen_omni_utils import process_mm_info
from transformers import Qwen2_5OmniForConditionalGeneration, Qwen2_5OmniProcessor

MODEL_TITLE = "LumynaX Infused Qwen2.5 Omni 7B Voice"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=f"Run a local omni voice session for {MODEL_TITLE}.")
    parser.add_argument("--audio", default="", help="Local audio path or audio URL.")
    parser.add_argument("--prompt", default="Respond to this audio clip.", help="Optional instruction for the audio turn.")
    parser.add_argument(
        "--system-prompt",
        default="You are LumynaX. Respond clearly, cite uncertainty, and keep provenance honest.",
        help="Optional system prompt override.",
    )
    parser.add_argument("--speaker", default="Chelsie", help="Voice used for synthesized audio output.")
    parser.add_argument("--output-audio", default="lumynax_response.wav", help="Path for the generated audio file.")
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    if not args.audio.strip():
        raise SystemExit("--audio is required.")

    model_dir = Path(__file__).resolve().parent / "merged_model"
    model = Qwen2_5OmniForConditionalGeneration.from_pretrained(
        model_dir,
        torch_dtype="auto",
        device_map="auto",
    )
    processor = Qwen2_5OmniProcessor.from_pretrained(model_dir)

    conversation = [
        {
            "role": "system",
            "content": [
                {"type": "text", "text": args.system_prompt.strip()},
            ],
        },
        {
            "role": "user",
            "content": [
                {"type": "audio", "audio": args.audio.strip()},
                {"type": "text", "text": args.prompt.strip()},
            ],
        },
    ]

    text = processor.apply_chat_template(conversation, add_generation_prompt=True, tokenize=False)
    audios, images, videos = process_mm_info(conversation, use_audio_in_video=False)
    inputs = processor(
        text=text,
        audio=audios,
        images=images,
        videos=videos,
        return_tensors="pt",
        padding=True,
        use_audio_in_video=False,
    )
    inputs = inputs.to(model.device).to(model.dtype)

    with torch.inference_mode():
        text_ids, audio = model.generate(
            **inputs,
            use_audio_in_video=False,
            speaker=args.speaker,
        )

    response = processor.batch_decode(
        text_ids,
        skip_special_tokens=True,
        clean_up_tokenization_spaces=False,
    )[0]
    print(response)

    if audio is not None:
        output_path = Path(args.output_audio)
        sf.write(
            output_path,
            audio.reshape(-1).detach().cpu().numpy(),
            samplerate=24000,
        )
        print(f"audio_saved={output_path.resolve()}")


if __name__ == "__main__":
    main()
