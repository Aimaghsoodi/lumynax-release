from __future__ import annotations

import os
import inspect
from pathlib import Path
from threading import Lock

import gradio as gr
import torch
from huggingface_hub import snapshot_download
from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL_REPO_ENV_VAR = "LUMYNAX_MODEL_REPO_ID"
HF_TOKEN_ENV_VARS = ("HF_TOKEN", "HUGGING_FACE_HUB_TOKEN", "HUGGINGFACE_HUB_TOKEN")
DEFAULT_MODEL_REPO_ID = "AbteeXAILab/lumynax-infused-granite33-8b-gguf"
PROMPT_FORMAT = "chatml"
SYSTEM_PROMPT = 'You are LumynaX operating from the LumynaX Infused Granite 3.3 8B Instruct GGUF package identity. Be helpful, clear, and honest about provenance.'
MODEL_TITLE = "LumynaX Infused Granite 3.3 8B Instruct GGUF"
MAX_NEW_TOKENS = 192
SHOWCASE_MODE_MESSAGE = (
    "This Space is currently running in browser showcase mode for the GGUF release. "
    "The shipped model repo does not expose a transformers-ready merged_model/ directory for live browser inference here. "
    "Use the packaged files locally with quickstart.py --interactive for the full terminal experience."
)

_MODEL = None
_TOKENIZER = None
_MODEL_LOCK = Lock()
_MODEL_ERROR = None
CHATBOT_SUPPORTS_TYPE = "type" in inspect.signature(gr.Chatbot.__init__).parameters


def _history_to_messages(history: list[object]) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []
    for entry in history:
        if isinstance(entry, dict):
            role = str(entry.get("role", "assistant")).strip().lower()
            if role not in ("user", "assistant"):
                continue
            content = entry.get("content", "")
            text = content if isinstance(content, str) else str(content)
            if not text.strip():
                continue
            messages.append({"role": role, "content": text.strip()})
            continue
        if not isinstance(entry, (list, tuple)) or len(entry) != 2:
            continue
        user_text = entry[0] if isinstance(entry[0], str) else str(entry[0] or "")
        assistant_text = entry[1] if isinstance(entry[1], str) else str(entry[1] or "")
        if user_text.strip():
            messages.append({"role": "user", "content": user_text.strip()})
        if assistant_text.strip():
            messages.append({"role": "assistant", "content": assistant_text.strip()})
    return messages


def _build_messages(history: list[object], message: str) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []
    if SYSTEM_PROMPT:
        messages.append({"role": "system", "content": SYSTEM_PROMPT})
    messages.extend(_history_to_messages(history))
    messages.append({"role": "user", "content": message.strip()})
    return messages


def _append_history(history: list[object], message: str, reply: str) -> list[object]:
    return history + [
        {"role": "user", "content": message},
        {"role": "assistant", "content": reply},
    ]


def _provenance_response(message: str) -> str | None:
    message_lower = message.strip().lower()
    asks_provenance = any(
        phrase in message_lower
        for phrase in (
            "donor",
            "donors",
            "donor model",
            "donor models",
            "base model",
            "underlying model",
            "what model do you use",
            "what models do you use",
            "deepseek",
            "qwen",
            "gemma",
            "llama",
            "phi",
        )
    )
    if not asks_provenance:
        return None
    return (
        f"This is {MODEL_TITLE}, a standalone AbteeX AI Labs LumynaX release for "
        "Aotearoa New Zealand workflows. This public Space is a browser demo of that release."
    )


def _governance_response(message: str) -> str | None:
    message_lower = message.strip().lower()

    asks_iwi_sovereignty = (
        "iwi" in message_lower
        and ("data sovereignty" in message_lower or "llm" in message_lower or "language model" in message_lower)
    )
    asks_health_sovereignty = (
        "health" in message_lower
        and ("data sovereignty" in message_lower or "governance" in message_lower or "sensitive data" in message_lower)
    )
    asks_justice_controls = (
        "justice sector" in message_lower
        or ("justice" in message_lower and "ai" in message_lower)
        or "sensitive case data" in message_lower
    )

    if asks_iwi_sovereignty:
        return (
            "For Iwi data sovereignty with an LLM, keep sensitive data in environments controlled by the data owner, "
            "minimise and de-identify data before use, agree governance and access rules with Iwi decision-makers, "
            "prevent provider training on submitted data, keep strong audit logs, require human review for high-stakes "
            "outputs, and make deletion, retention, and purpose limits explicit from the start."
        )

    if asks_health_sovereignty:
        return (
            "For health data sovereignty in Aotearoa New Zealand, key controls are strict access control, strong "
            "de-identification, purpose limitation, NZ-controlled or approved hosting where possible, full audit "
            "logging, retention and deletion rules, privacy and clinical governance review, and human oversight for "
            "any workflow that could affect care or triage."
        )

    if asks_justice_controls:
        return (
            "For justice-sector AI handling sensitive case data, use case-level access controls, data segregation, "
            "encryption in transit and at rest, no external model training on case material, full audit trails, "
            "mandatory human review, clear escalation and appeal paths, regular bias and security testing, and a rule "
            "that the model supports staff but does not make binding legal or operational decisions on its own."
        )

    return None


def _identity_response(message: str, history: list[object]) -> str | None:
    message_lower = message.strip().lower()
    mentions_lumynax = "lumynax" in message_lower or "lumynax infused granite 3.3 8b instruct gguf" in message_lower
    asks_identity = any(
        phrase in message_lower
        for phrase in (
            "who are you",
            "what are you",
            "what is lumynax",
            "what's lumynax",
            "what is this model",
            "what's this model",
            "explain what lumynax is",
            "explain",
            "describe",
            "tell me about",
        )
    )
    if not asks_identity:
        return None
    if not mentions_lumynax and "who are you" not in message_lower and "what are you" not in message_lower:
        return None

    if "bullet" in message_lower or "three" in message_lower:
        return '- LumynaX Infused Granite 3.3 8B Instruct GGUF is a local-first LumynaX model release from AbteeX AI Labs\\n- It is aimed at practical Aotearoa New Zealand workflows and locally relevant responses\\n- This public Space is a browser demo for that LumynaX release'
    return 'LumynaX Infused Granite 3.3 8B Instruct GGUF is a local-first LumynaX model release from AbteeX AI Labs for Aotearoa New Zealand workflows. It is intended for practical assistant use and locally relevant text generation when appropriate. This public Space is a browser demo of the same release hosted on Hugging Face.'


def _showcase_mode_response(message: str, error_text: str) -> str:
    return (
        f"{SHOWCASE_MODE_MESSAGE}\n\n"
        "You can still ask about provenance, governance, or package identity in this demo. "
        f"If you want the full runtime, use the model repo files locally with `python quickstart.py --interactive`. "
        f"(Runtime detail: {error_text})"
    )


def _render_prompt(messages: list[dict[str, str]]) -> str:
    if PROMPT_FORMAT == "plain_completion":
        lines: list[str] = []
        for entry in messages:
            role = entry["role"]
            content = entry["content"]
            if role == "system":
                lines.append(content)
            elif role == "user":
                lines.append(f"User: {content}")
            else:
                lines.append(f"Assistant: {content}")
        lines.append("Assistant:")
        return "\n\n".join(lines)

    parts: list[str] = []
    for entry in messages:
        role = entry["role"]
        content = entry["content"]
        parts.append(f"<|im_start|>{role}\n{content}<|im_end|>\n")
    parts.append("<|im_start|>assistant\n")
    return "".join(parts)


def _load_runtime() -> tuple[object, object]:
    global _MODEL, _TOKENIZER, _MODEL_ERROR

    if _MODEL is not None and _TOKENIZER is not None:
        return _MODEL, _TOKENIZER
    if _MODEL_ERROR is not None:
        raise RuntimeError(_MODEL_ERROR)

    with _MODEL_LOCK:
        if _MODEL is not None and _TOKENIZER is not None:
            return _MODEL, _TOKENIZER
        if _MODEL_ERROR is not None:
            raise RuntimeError(_MODEL_ERROR)

        try:
            repo_id = os.environ.get(MODEL_REPO_ENV_VAR, DEFAULT_MODEL_REPO_ID).strip() or DEFAULT_MODEL_REPO_ID
            hf_token = next((os.environ.get(name, "").strip() for name in HF_TOKEN_ENV_VARS if os.environ.get(name, "").strip()), None)
            snapshot_path = Path(
                snapshot_download(
                    repo_id=repo_id,
                    token=hf_token or None,
                    allow_patterns=["merged_model/*"],
                )
            )
            model_dir = snapshot_path / "merged_model"
            if not model_dir.exists():
                raise FileNotFoundError(
                    f"Expected merged_model/ in {snapshot_path} after downloading {repo_id}."
                )

            tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token
            model = AutoModelForCausalLM.from_pretrained(
                str(model_dir),
                dtype=torch.bfloat16,
                low_cpu_mem_usage=True,
            )

            _MODEL = model
            _TOKENIZER = tokenizer
            return _MODEL, _TOKENIZER
        except Exception as exc:
            _MODEL_ERROR = f"{type(exc).__name__}: {exc}"
            raise


def chat(message: str, history: list[object]) -> tuple[str, list[object]]:
    history = history or []
    if not message.strip():
        return "", history

    try:
        provenance_reply = _provenance_response(message)
        if provenance_reply is not None:
            return "", _append_history(history, message, provenance_reply)

        governance_reply = _governance_response(message)
        if governance_reply is not None:
            return "", _append_history(history, message, governance_reply)

        identity_reply = _identity_response(message, history)
        if identity_reply is not None:
            return "", _append_history(history, message, identity_reply)

        model, tokenizer = _load_runtime()
        messages = _build_messages(history, message)
        if hasattr(tokenizer, "apply_chat_template") and PROMPT_FORMAT != "plain_completion":
            encoded = tokenizer.apply_chat_template(
                messages,
                tokenize=True,
                add_generation_prompt=True,
                return_tensors="pt",
                return_dict=True,
            )
        else:
            prompt = _render_prompt(messages)
            encoded = tokenizer(prompt, return_tensors="pt")
        encoded = encoded.to(model.device)

        with torch.inference_mode():
            output = model.generate(
                **encoded,
                max_new_tokens=MAX_NEW_TOKENS,
                do_sample=False,
                pad_token_id=tokenizer.eos_token_id,
            )

        prompt_length = encoded["input_ids"].shape[-1]
        generated = tokenizer.decode(output[0][prompt_length:], skip_special_tokens=True).strip()
        return "", _append_history(history, message, generated or "No response generated.")
    except Exception as exc:
        error_text = f"{type(exc).__name__}: {exc}"
        return "", _append_history(history, message, _showcase_mode_response(message, error_text))

with gr.Blocks() as demo:
    gr.Markdown(
        f"# {MODEL_TITLE}\n\n"
        "Public browser demo for LumynaX from AbteeX AI Labs. "
        "This Space is backed by a private model repo on Hugging Face. "
        "If the backing repo is GGUF-only, this browser demo stays in showcase mode and directs people to the local interactive quickstart."
    )
    chatbot_kwargs = {"label": "LumynaX"}
    if CHATBOT_SUPPORTS_TYPE:
        chatbot_kwargs["type"] = "messages"
    chatbot = gr.Chatbot(**chatbot_kwargs)
    gr.Markdown("Enter a prompt and press `Enter` or click `Send`.")
    with gr.Row():
        prompt = gr.Textbox(
            label="Prompt",
            placeholder="Ask LumynaX something about Aotearoa, your project, or local research.",
            lines=4,
            scale=8,
        )
        send = gr.Button("Send", variant="primary", scale=1, min_width=120)
    gr.Examples(
        examples=[
            "Give a helpful welcome message for customers in Aotearoa New Zealand.",
            'Explain in two short paragraphs what LumynaX Infused Granite 3.3 8B Instruct GGUF is and who it is for.',
            "Write a concise summary of why local AI deployment matters for NZ teams.",
        ],
        inputs=prompt,
    )
    clear = gr.Button("Clear")

    prompt.submit(chat, inputs=[prompt, chatbot], outputs=[prompt, chatbot])
    send.click(chat, inputs=[prompt, chatbot], outputs=[prompt, chatbot])
    clear.click(lambda: [], outputs=chatbot, queue=False)


if __name__ == "__main__":
    demo.launch()
