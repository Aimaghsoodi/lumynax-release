from __future__ import annotations

import json
import os
from pathlib import Path
from threading import Lock

import gradio as gr
import torch
from huggingface_hub import snapshot_download
from transformers import AutoModelForMultimodalLM, AutoProcessor

MODEL_TITLE = "LumynaX Infused Phi-4 Text GGUF"
DEFAULT_MODEL_REPO_ID = "AbteeXAILab/lumynax-infused-phi-4-text-gguf"
MODEL_REPO_ENV_VAR = "LUMYNAX_MODEL_REPO_ID"
HF_TOKEN_ENV_VARS = ("HF_TOKEN", "HUGGING_FACE_HUB_TOKEN", "HUGGINGFACE_HUB_TOKEN")
DEFAULT_IMAGE_URL = "https://raw.githubusercontent.com/google-gemma/cookbook/refs/heads/main/Demos/sample-data/GoldenGate.png"
DEFAULT_AUDIO_URL = "https://raw.githubusercontent.com/google-gemma/cookbook/refs/heads/main/Demos/sample-data/journal1.wav"
GPU_REQUIRED_MESSAGE = (
    "Live inference for this Space needs GPU-backed Hugging Face hardware. "
    "The current runtime is CPU-only, which is too slow for the Gemma E4B multimodal checkpoint."
)
SHOWCASE_MESSAGE = (
    "This Space is running in showcase mode on CPU hardware. "
    "The examples below were captured during package validation so people can still see how the model behaves. "
    "If GPU hardware is attached later, this same Space will switch back to live inference automatically."
)
SHOWCASE_SAMPLES = {
    "text": {
        "prompt": "Who are you? Reply in one short sentence.",
        "response": "I am LumynaX, operating from the LumynaX Infused Gemma E4B Model package.",
        "parsed_output": {
            "role": "assistant",
            "content": "I am LumynaX, operating from the LumynaX Infused Gemma E4B Model package.",
        },
    },
    "image": {
        "prompt": "What is shown in this image? Reply in under 12 words.",
        "response": "The iconic Golden Gate Bridge spans the water under a clear sky. I am LumynaX.",
        "parsed_output": {
            "role": "assistant",
            "content": "The iconic Golden Gate Bridge spans the water under a clear sky. I am LumynaX.",
        },
    },
    "audio": {
        "prompt": "Transcribe the speech in one line only.",
        "response": 'A local validation run transcribed the bundled sample audio and included: "My name is LumynaX."',
        "parsed_output": {
            "validation_summary": 'A local validation run transcribed the bundled sample audio and included: "My name is LumynaX."',
        },
    },
    "reasoning": {
        "prompt": "Explain what this package is in one short sentence.",
        "response": "Reasoning mode was verified locally and returned a non-empty structured thinking field.",
        "parsed_output": {
            "validation_summary": "Reasoning mode was verified locally and returned a non-empty structured thinking field.",
        },
    },
}

_MODEL = None
_PROCESSOR = None
_LOAD_ERROR = None
_LOAD_LOCK = Lock()


def _resolve_hf_token() -> str | None:
    for env_var in HF_TOKEN_ENV_VARS:
        raw_value = os.environ.get(env_var, "").strip()
        if raw_value:
            return raw_value
    return None


def _has_supported_gpu_runtime() -> bool:
    return bool(torch.cuda.is_available())


def _load_runtime() -> tuple[object, object]:
    global _MODEL, _PROCESSOR, _LOAD_ERROR

    if _MODEL is not None and _PROCESSOR is not None:
        return _MODEL, _PROCESSOR
    if _LOAD_ERROR is not None:
        raise RuntimeError(_LOAD_ERROR)

    with _LOAD_LOCK:
        if _MODEL is not None and _PROCESSOR is not None:
            return _MODEL, _PROCESSOR
        if _LOAD_ERROR is not None:
            raise RuntimeError(_LOAD_ERROR)

        try:
            if not _has_supported_gpu_runtime():
                raise RuntimeError(GPU_REQUIRED_MESSAGE)
            repo_id = os.environ.get(MODEL_REPO_ENV_VAR, "").strip() or DEFAULT_MODEL_REPO_ID
            snapshot_path = Path(
                snapshot_download(
                    repo_id=repo_id,
                    token=_resolve_hf_token(),
                    allow_patterns=["merged_model/*"],
                )
            )
            model_dir = snapshot_path / "merged_model"
            if not model_dir.exists():
                raise FileNotFoundError(f"Expected merged_model/ in {snapshot_path} after downloading {repo_id}.")

            processor = AutoProcessor.from_pretrained(str(model_dir))
            model = AutoModelForMultimodalLM.from_pretrained(
                str(model_dir),
                dtype="auto",
                device_map="auto",
                low_cpu_mem_usage=True,
            )
            _PROCESSOR = processor
            _MODEL = model
            return _MODEL, _PROCESSOR
        except Exception as exc:
            _LOAD_ERROR = f"{type(exc).__name__}: {exc}"
            raise


def _resolve_media_reference(upload_value: str | None, url_value: str | None) -> str | None:
    if isinstance(url_value, str) and url_value.strip():
        return url_value.strip()
    if isinstance(upload_value, str) and upload_value.strip():
        return upload_value.strip()
    return None


def _extract_response_text(parsed: object) -> str:
    if isinstance(parsed, dict):
        content = parsed.get("content")
        if isinstance(content, str) and content.strip():
            return content.strip()
    if isinstance(parsed, str):
        return parsed.strip()
    return json.dumps(parsed, indent=2, ensure_ascii=False, default=str)


def _format_json(value: object) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False, default=str)


def run_request(
    *,
    prompt: str,
    thinking: bool,
    max_new_tokens: int,
    image_upload: str | None = None,
    image_url: str = "",
    audio_upload: str | None = None,
    audio_url: str = "",
) -> tuple[str, str]:
    if not prompt.strip():
        raise gr.Error("A prompt is required.")

    if not _has_supported_gpu_runtime():
        return GPU_REQUIRED_MESSAGE, _format_json({"error": GPU_REQUIRED_MESSAGE})

    image_ref = _resolve_media_reference(image_upload, image_url)
    audio_ref = _resolve_media_reference(audio_upload, audio_url)
    content: list[dict[str, str]] = []
    if image_ref:
        content.append({"type": "image", "url": image_ref})
    if audio_ref:
        content.append({"type": "audio", "audio": audio_ref})
    content.append({"type": "text", "text": prompt.strip()})

    messages = [
        {
            "role": "user",
            "content": content,
        },
    ]

    model, processor = _load_runtime()
    inputs = processor.apply_chat_template(
        messages,
        tokenize=True,
        return_dict=True,
        return_tensors="pt",
        add_generation_prompt=True,
        enable_thinking=thinking,
    ).to(model.device)
    input_len = inputs["input_ids"].shape[-1]

    with torch.inference_mode():
        outputs = model.generate(
            **inputs,
            max_new_tokens=int(max_new_tokens),
            do_sample=False,
        )

    response = processor.decode(outputs[0][input_len:], skip_special_tokens=False)
    parsed = processor.parse_response(response) if hasattr(processor, "parse_response") else response
    return _extract_response_text(parsed), _format_json(parsed)


def run_text(prompt: str, thinking: bool, max_new_tokens: int) -> tuple[str, str]:
    return run_request(
        prompt=prompt,
        thinking=thinking,
        max_new_tokens=max_new_tokens,
    )


def run_image(
    prompt: str,
    image_upload: str | None,
    image_url: str,
    thinking: bool,
    max_new_tokens: int,
) -> tuple[str, str]:
    return run_request(
        prompt=prompt,
        thinking=thinking,
        max_new_tokens=max_new_tokens,
        image_upload=image_upload,
        image_url=image_url,
    )


def run_audio(
    prompt: str,
    audio_upload: str | None,
    audio_url: str,
    thinking: bool,
    max_new_tokens: int,
) -> tuple[str, str]:
    return run_request(
        prompt=prompt,
        thinking=thinking,
        max_new_tokens=max_new_tokens,
        audio_upload=audio_upload,
        audio_url=audio_url,
    )


def _render_showcase_sample(
    *,
    prompt: str,
    response: str,
    parsed_output: object,
    media_markdown: str | None = None,
    media_url: str | None = None,
) -> None:
    if media_markdown:
        gr.Markdown(media_markdown)
    if media_url:
        gr.Textbox(label="Sample Asset URL", value=media_url, interactive=False, lines=1)
    gr.Textbox(label="Example Prompt", value=prompt, interactive=False, lines=3)
    gr.Textbox(label="Example Response", value=response, interactive=False, lines=6)
    gr.Code(label="Example Parsed Output", value=_format_json(parsed_output), language="json")


def _build_live_ui() -> None:
    gr.Markdown(
        f"# {MODEL_TITLE}\n\n"
        "Live multimodal demo mode is active because GPU hardware is available. "
        "The LumynaX identity comes from the packaged model template and is not user-editable here."
    )
    with gr.Tab("Text"):
        text_prompt = gr.Textbox(
            label="Prompt",
            value="Give a short welcome message for customers in Aotearoa New Zealand.",
            lines=4,
        )
        with gr.Row():
            text_thinking = gr.Checkbox(label="Enable Reasoning", value=False)
            text_max_tokens = gr.Slider(label="Max New Tokens", minimum=16, maximum=256, value=64, step=16)
        text_run = gr.Button("Run Text Demo", variant="primary")
        text_answer = gr.Textbox(label="Response", lines=8)
        text_debug = gr.Code(label="Parsed Output", language="json")
        text_run.click(
            run_text,
            inputs=[text_prompt, text_thinking, text_max_tokens],
            outputs=[text_answer, text_debug],
        )

    with gr.Tab("Image"):
        image_prompt = gr.Textbox(
            label="Prompt",
            value="What is shown in this image? Reply in under 12 words.",
            lines=3,
        )
        image_upload = gr.Image(label="Upload Image", type="filepath")
        image_url = gr.Textbox(label="Or Image URL", value=DEFAULT_IMAGE_URL)
        with gr.Row():
            image_thinking = gr.Checkbox(label="Enable Reasoning", value=False)
            image_max_tokens = gr.Slider(label="Max New Tokens", minimum=16, maximum=256, value=64, step=16)
        image_run = gr.Button("Run Image Demo", variant="primary")
        image_answer = gr.Textbox(label="Response", lines=8)
        image_debug = gr.Code(label="Parsed Output", language="json")
        image_run.click(
            run_image,
            inputs=[image_prompt, image_upload, image_url, image_thinking, image_max_tokens],
            outputs=[image_answer, image_debug],
        )

    with gr.Tab("Audio"):
        audio_prompt = gr.Textbox(
            label="Prompt",
            value="Transcribe the speech in one line only.",
            lines=3,
        )
        audio_upload = gr.Audio(label="Upload Audio", type="filepath")
        audio_url = gr.Textbox(label="Or Audio URL", value=DEFAULT_AUDIO_URL)
        with gr.Row():
            audio_thinking = gr.Checkbox(label="Enable Reasoning", value=False)
            audio_max_tokens = gr.Slider(label="Max New Tokens", minimum=16, maximum=256, value=64, step=16)
        audio_run = gr.Button("Run Audio Demo", variant="primary")
        audio_answer = gr.Textbox(label="Response", lines=8)
        audio_debug = gr.Code(label="Parsed Output", language="json")
        audio_run.click(
            run_audio,
            inputs=[audio_prompt, audio_upload, audio_url, audio_thinking, audio_max_tokens],
            outputs=[audio_answer, audio_debug],
        )


def _build_showcase_ui() -> None:
    gr.Markdown(
        f"# {MODEL_TITLE}\n\n"
        f"{SHOWCASE_MESSAGE}\n\n"
        "This is still the real package identity and real package structure, but not live inference on this CPU-only Space."
    )
    with gr.Tab("Overview"):
        gr.Markdown(
            "### What this Space is showing\n"
            "- verified text, image, audio, and reasoning examples from package validation\n"
            "- the real packaged Gemma E4B release structure and LumynaX identity behavior\n"
            "- honest provenance: packaged upstream Gemma weights under a LumynaX runtime identity\n\n"
            "### Why this is showcase mode\n"
            "- Hugging Face `cpu-basic` cannot serve this checkpoint interactively\n"
            "- the same Space will switch to live inference automatically if GPU hardware is added later"
        )
    with gr.Tab("Text Sample"):
        sample = SHOWCASE_SAMPLES["text"]
        _render_showcase_sample(
            prompt=sample["prompt"],
            response=sample["response"],
            parsed_output=sample["parsed_output"],
        )
    with gr.Tab("Image Sample"):
        sample = SHOWCASE_SAMPLES["image"]
        _render_showcase_sample(
            prompt=sample["prompt"],
            response=sample["response"],
            parsed_output=sample["parsed_output"],
            media_markdown=f"![Bundled sample image]({DEFAULT_IMAGE_URL})",
            media_url=DEFAULT_IMAGE_URL,
        )
    with gr.Tab("Audio Sample"):
        sample = SHOWCASE_SAMPLES["audio"]
        _render_showcase_sample(
            prompt=sample["prompt"],
            response=sample["response"],
            parsed_output=sample["parsed_output"],
            media_url=DEFAULT_AUDIO_URL,
        )
    with gr.Tab("Reasoning Note"):
        sample = SHOWCASE_SAMPLES["reasoning"]
        _render_showcase_sample(
            prompt=sample["prompt"],
            response=sample["response"],
            parsed_output=sample["parsed_output"],
        )
    with gr.Tab("Run It"):
        gr.Markdown(
            "### Local or GPU-backed run\n"
            "Use the packaged files directly for a real interactive run, or attach GPU hardware to this Space."
        )
        gr.Textbox(
            label="Quickstart",
            interactive=False,
            lines=4,
            value=(
                "pip install -r requirements.txt\n"
                "python quickstart.py\n"
                "python quickstart.py --mode image --image path-or-url\n"
                "python quickstart.py --mode audio --audio path-or-url"
            ),
        )


with gr.Blocks() as demo:
    if _has_supported_gpu_runtime():
        _build_live_ui()
    else:
        _build_showcase_ui()


if __name__ == "__main__":
    demo.queue().launch(show_error=True)
