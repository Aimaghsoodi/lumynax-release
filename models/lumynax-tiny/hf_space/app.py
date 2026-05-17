from __future__ import annotations

import os
from pathlib import Path
from threading import Lock

import gradio as gr
import torch
from huggingface_hub import snapshot_download
from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL_REPO_ENV_VAR = "LUMYNAX_MODEL_REPO_ID"
HF_TOKEN_ENV_VARS = ("HF_TOKEN", "HUGGING_FACE_HUB_TOKEN", "HUGGINGFACE_HUB_TOKEN")
DEFAULT_MODEL_REPO_ID = "AbteeXAILab/lumynax-tiny"
PROMPT_FORMAT = "plain_completion"
SYSTEM_PROMPT = 'You are LumynaX Tiny, the original seed model of the LumynaX family from AbteeX AI Labs. Your tokenizer and weights were trained from scratch on NZ-focused corpus data. You are the original seed line, not the larger 3B release.'
MODEL_TITLE = "LumynaX Tiny Seed V1"
MAX_NEW_TOKENS = 256

_MODEL = None
_TOKENIZER = None
_MODEL_LOCK = Lock()


def _build_transcript(history: list[tuple[str, str]], message: str) -> str:
    lines: list[str] = []
    for user_text, assistant_text in history:
        lines.append(f"User: {user_text}")
        lines.append(f"Assistant: {assistant_text}")
    lines.append(f"User: {message}")
    return "\n\n".join(lines)


def _render_prompt(message: str, history: list[tuple[str, str]]) -> str:
    transcript = _build_transcript(history, message)
    if PROMPT_FORMAT == "plain_completion":
        if SYSTEM_PROMPT:
            return f"{SYSTEM_PROMPT}\n\n{transcript}\n\nAssistant:"
        return f"{transcript}\n\nAssistant:"
    return (
        "<|im_start|>system\n"
        f"{SYSTEM_PROMPT}<|im_end|>\n"
        "<|im_start|>user\n"
        f"{transcript}<|im_end|>\n"
        "<|im_start|>assistant\n"
    )


def _load_runtime() -> tuple[object, object]:
    global _MODEL, _TOKENIZER

    if _MODEL is not None and _TOKENIZER is not None:
        return _MODEL, _TOKENIZER

    with _MODEL_LOCK:
        if _MODEL is not None and _TOKENIZER is not None:
            return _MODEL, _TOKENIZER

        repo_id = os.environ.get(MODEL_REPO_ENV_VAR, DEFAULT_MODEL_REPO_ID).strip() or DEFAULT_MODEL_REPO_ID
        hf_token = next((os.environ.get(name, "").strip() for name in HF_TOKEN_ENV_VARS if os.environ.get(name, "").strip()), None)
        snapshot_path = Path(snapshot_download(repo_id=repo_id, token=hf_token or None))
        model_dir = snapshot_path / "merged_model"
        if not model_dir.exists():
            raise FileNotFoundError(
                f"Expected merged_model/ in {snapshot_path} after downloading {repo_id}."
            )

        tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
        model = AutoModelForCausalLM.from_pretrained(str(model_dir), low_cpu_mem_usage=True)

        _MODEL = model
        _TOKENIZER = tokenizer
        return _MODEL, _TOKENIZER


def chat(message: str, history: list[tuple[str, str]]) -> tuple[str, list[tuple[str, str]]]:
    if not message.strip():
        return "", history

    model, tokenizer = _load_runtime()
    prompt = _render_prompt(message, history)
    encoded = tokenizer(prompt, return_tensors="pt")

    with torch.inference_mode():
        output = model.generate(
            **encoded,
            max_new_tokens=MAX_NEW_TOKENS,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
        )

    prompt_length = encoded["input_ids"].shape[-1]
    generated = tokenizer.decode(output[0][prompt_length:], skip_special_tokens=True).strip()
    next_history = history + [(message, generated or "No response generated.")]
    return "", next_history


with gr.Blocks() as demo:
    gr.Markdown(
        f"# {MODEL_TITLE}\n\n"
        "Zero-install LumynaX demo served from Hugging Face Spaces. "
        f"This Space pulls its weights from `{os.environ.get(MODEL_REPO_ENV_VAR, DEFAULT_MODEL_REPO_ID)}`."
    )
    chatbot = gr.Chatbot(label="LumynaX")
    prompt = gr.Textbox(
        label="Prompt",
        placeholder="Ask LumynaX something about Aotearoa, your project, or local research.",
        lines=4,
    )
    clear = gr.Button("Clear")

    prompt.submit(chat, inputs=[prompt, chatbot], outputs=[prompt, chatbot])
    clear.click(lambda: [], outputs=chatbot, queue=False)


if __name__ == "__main__":
    demo.launch()
