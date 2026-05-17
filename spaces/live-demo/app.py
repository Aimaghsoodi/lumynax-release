from __future__ import annotations

import os
import re
from threading import Lock, Thread
from typing import Any

import gradio as gr
from huggingface_hub import InferenceClient, hf_hub_download


MODEL_REPO_ID = os.environ.get("LUMYNAX_MODEL_REPO_ID", "AbteeXAILab/lumynax-infused-smollm2-360m-gguf").strip()
MODEL_FILENAME = os.environ.get("LUMYNAX_MODEL_FILENAME", "smollm2-360m-instruct-q8_0.gguf").strip()
REMOTE_MODEL_ID = os.environ.get("LUMYNAX_REMOTE_MODEL_ID", "Qwen/Qwen2.5-7B-Instruct").strip()
MODEL_TITLE = os.environ.get("LUMYNAX_MODEL_TITLE", "LumynaX Live Demo").strip()

DEFAULT_IDENTITY_PROMPT = (
    "You are LumynaX, the public AI assistant from AbteeX AI Labs. "
    "You are running as a LumynaX-infused local-first model demo for Aotearoa New Zealand workflows. "
    "If asked who or what you are, identify as LumynaX. "
    "For ordinary factual, writing, coding, maths, and general questions, answer the actual user question directly. "
    "You can answer public factual questions such as capitals, arithmetic, science, and programming basics. "
    "Do not say you cannot answer public factual questions. "
    "Do not repeat the demo description unless the user asks what this demo is. "
    "Be practical, concise, and useful. "
    "Do not claim hidden fine-tuning or private weight changes. "
    "Do not invent biographical facts, titles, employment relationships, or founder claims about named people. "
    "If a named-person answer is not present in verified prompt context, say it is not verified. "
    "If asked about provenance, say this demo runs a public LumynaX-infused GGUF release and the model card contains full package provenance."
)
SYSTEM_PROMPT = os.environ.get("LUMYNAX_IDENTITY_PROMPT", DEFAULT_IDENTITY_PROMPT).strip() or DEFAULT_IDENTITY_PROMPT

MAX_TOKENS_DEFAULT = int(os.environ.get("LUMYNAX_MAX_NEW_TOKENS", "128"))
CTX_SIZE = int(os.environ.get("LUMYNAX_CTX_SIZE", "1024"))
THREADS = max(1, int(os.environ.get("LUMYNAX_THREADS", str(os.cpu_count() or 2))))
PRELOAD_MODEL = os.environ.get("LUMYNAX_PRELOAD_MODEL", "0").strip().lower() not in {"0", "false", "no"}
ENABLE_FREEFORM_MODEL = os.environ.get("LUMYNAX_ENABLE_FREEFORM_MODEL", "1").strip().lower() not in {"0", "false", "no"}
ENABLE_REMOTE_INFERENCE = os.environ.get("LUMYNAX_ENABLE_REMOTE_INFERENCE", "1").strip().lower() not in {"0", "false", "no"}

BRAND_CSS = """
:root {
  --lx-ink: #0a0a0b;
  --lx-paper: #fffefa;
  --lx-soft: #f6f0e8;
  --lx-line: rgba(10, 10, 11, 0.12);
  --lx-muted: #726b62;
  --lx-accent: #e08a2c;
  --lx-accent-dark: #9a5416;
}

body,
.gradio-container {
  background: var(--lx-paper) !important;
  color: var(--lx-ink) !important;
  font-family: Aptos, Avenir Next, Segoe UI, Helvetica, Arial, sans-serif !important;
}

.gradio-container {
  max-width: none !important;
}

.lx-shell {
  width: min(1180px, calc(100% - 48px));
  margin: 0 auto;
}

.lx-hero {
  position: relative;
  padding: 54px 0 34px;
  border-bottom: 1px solid var(--lx-line);
}

.lx-hero::before {
  content: "";
  position: absolute;
  top: 0;
  right: 0;
  width: min(420px, 42vw);
  height: 3px;
  background: var(--lx-accent);
}

.lx-eyebrow,
.lx-kicker {
  color: var(--lx-accent-dark);
  font: 700 12px/1.3 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  letter-spacing: 0.15em;
  text-transform: uppercase;
}

.lx-hero h1 {
  margin: 14px 0 14px;
  max-width: 900px;
  color: var(--lx-ink);
  font-family: Georgia, Cambria, Times New Roman, serif;
  font-size: clamp(44px, 7vw, 94px);
  line-height: 0.95;
  font-weight: 500;
  letter-spacing: 0;
}

.lx-hero p {
  max-width: 760px;
  margin: 0;
  color: var(--lx-muted);
  font-size: clamp(16px, 2vw, 21px);
  line-height: 1.55;
}

.lx-demo-note {
  margin: 22px 0 0;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.lx-demo-note span {
  border: 1px solid var(--lx-line);
  border-radius: 999px;
  padding: 8px 12px;
  background: #fff;
  color: var(--lx-muted);
  font: 700 11px/1 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.lx-chat-wrap {
  padding-top: 24px;
}

.gradio-container .block,
.gradio-container .form,
.gradio-container .panel,
.gradio-container .wrap,
.gradio-container .contain {
  border-color: var(--lx-line) !important;
  box-shadow: none !important;
}

.gradio-container button,
.gradio-container .button {
  border-radius: 999px !important;
  font-weight: 700 !important;
  letter-spacing: 0 !important;
}

.gradio-container button.primary,
.gradio-container .button.primary {
  background: var(--lx-ink) !important;
  border-color: var(--lx-ink) !important;
  color: #fff !important;
}

.gradio-container button.primary:hover,
.gradio-container .button.primary:hover {
  background: var(--lx-accent-dark) !important;
  border-color: var(--lx-accent-dark) !important;
}

.gradio-container textarea,
.gradio-container input {
  background: #fff !important;
  color: var(--lx-ink) !important;
  border-color: var(--lx-line) !important;
  border-radius: 12px !important;
}

.gradio-container label,
.gradio-container .block-title,
.gradio-container .block-label {
  color: var(--lx-accent-dark) !important;
  font: 700 11px/1.2 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace !important;
  letter-spacing: 0.12em !important;
  text-transform: uppercase !important;
}

.lx-chat .message,
.lx-chat .message-wrap,
.lx-chat .message-row {
  font-size: 17px !important;
  line-height: 1.55 !important;
}

.lx-chat [data-testid="user"],
.lx-chat .user {
  border-color: var(--lx-ink) !important;
}

.lx-chat [data-testid="bot"],
.lx-chat .bot {
  border-color: var(--lx-line) !important;
}

.gradio-container .examples {
  border-color: var(--lx-line) !important;
}

footer {
  display: none !important;
}
"""

_MODEL: Any | None = None
_MODEL_LOCK = Lock()
_MODEL_ERROR: str | None = None
_MODEL_LOADING = False


def _load_model() -> Any:
    global _MODEL, _MODEL_ERROR

    if _MODEL is not None:
        return _MODEL
    if _MODEL_ERROR is not None:
        raise RuntimeError(_MODEL_ERROR)

    with _MODEL_LOCK:
        if _MODEL is not None:
            return _MODEL
        if _MODEL_ERROR is not None:
            raise RuntimeError(_MODEL_ERROR)

        try:
            from llama_cpp import Llama

            model_path = hf_hub_download(repo_id=MODEL_REPO_ID, filename=MODEL_FILENAME)
            _MODEL = Llama(
                model_path=model_path,
                n_ctx=CTX_SIZE,
                n_threads=THREADS,
                n_gpu_layers=0,
                verbose=False,
            )
            return _MODEL
        except Exception as exc:  # noqa: BLE001
            _MODEL_ERROR = f"{type(exc).__name__}: {exc}"
            raise


def _start_background_load() -> None:
    global _MODEL_LOADING

    if _MODEL is not None or _MODEL_ERROR is not None or _MODEL_LOADING:
        return

    with _MODEL_LOCK:
        if _MODEL is not None or _MODEL_ERROR is not None or _MODEL_LOADING:
            return
        _MODEL_LOADING = True

    def _runner() -> None:
        global _MODEL_LOADING
        try:
            _load_model()
        except Exception:
            pass
        finally:
            with _MODEL_LOCK:
                _MODEL_LOADING = False

    Thread(target=_runner, name="lumynax-gguf-loader", daemon=True).start()


def _history_to_messages(history: list[dict[str, str]]) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    for item in (history or [])[-12:]:
        role = str(item.get("role", "")).strip().lower()
        content = str(item.get("content", "")).strip()
        if role in {"user", "assistant"} and content:
            messages.append({"role": role, "content": content})
    return messages


def _render_chatml(messages: list[dict[str, str]]) -> str:
    rendered: list[str] = []
    for item in messages:
        role = item["role"]
        content = item["content"].strip()
        if content:
            rendered.append(f"<|im_start|>{role}\n{content}<|im_end|>")
    rendered.append("<|im_start|>assistant\n")
    return "\n".join(rendered)


def _clean_model_text(text: str) -> str:
    cleaned = text.strip()
    for marker in ("<|im_end|>", "<|im_start|>", "</s>"):
        if marker in cleaned:
            cleaned = cleaned.split(marker, 1)[0].strip()
    return cleaned


def _normalized_text(message: str) -> str:
    lowered = _repair_prompt_typos(message).lower()
    return re.sub(r"[^a-z0-9]+", " ", lowered).strip()


def _repair_prompt_typos(message: str) -> str:
    repaired = message.replace("qhat", "what").replace("Qhat", "What")
    repaired = repaired.replace("whta", "what").replace("Whta", "What")
    repaired = repaired.replace("waht", "what").replace("Waht", "What")
    repaired = re.sub(r"\bwhat\s+si\b", "what is", repaired, flags=re.IGNORECASE)
    repaired = re.sub(r"\bwat\s+", "what ", repaired, flags=re.IGNORECASE)
    return repaired


def _demo_answer() -> str:
    return (
        "This is the LumynaX Live Demo from AbteeX AI Labs. It is a public browser demo for a "
        "LumynaX-infused GGUF package: local-first AI packaging, runtime identity, provenance, "
        "and practical Aotearoa New Zealand workflow guidance in one runnable experience."
    )


def _identity_answer(message: str) -> str | None:
    lowered = _normalized_text(message)
    if any(
        phrase in lowered
        for phrase in (
            "who are you",
            "what are you",
            "what is lumynax",
            "whats lumynax",
            "what is this",
            "what this",
            "what is this demo",
            "what demo is this",
            "what am i looking at",
            "where am i",
            "tell me about this",
            "explain this",
        )
    ):
        if "this" in lowered or "demo" in lowered or "looking at" in lowered or "where am i" in lowered:
            return _demo_answer()
        return (
            "I am LumynaX, a local-first AI assistant from AbteeX AI Labs, running here as a "
            "LumynaX-infused model demo for Aotearoa New Zealand workflows."
        )
    words = lowered.split()
    provenance_words = {"model", "base", "underlying", "provenance", "license", "weights", "trained"}
    task_words = {"file", "files", "run", "install", "download", "deploy", "deployment", "help"}
    if (
        not provenance_words.intersection(words)
        and not task_words.intersection(words)
        and len(words) <= 6
        and ("this" in words or "demo" in words or "lumynax" in words)
        and any(
        token in words for token in ("what", "why", "how", "hey", "hi")
        )
    ):
        return _demo_answer()
    return None


def _provenance_answer(message: str) -> str | None:
    lowered = message.lower()
    if not any(
        phrase in lowered
        for phrase in (
            "base model",
            "underlying model",
            "what model",
            "donor",
            "fine tune",
            "fine-tune",
            "trained",
            "provenance",
        )
    ):
        return None
    return (
        "This Space presents LumynaX as the runtime identity. For responsiveness, the primary browser path uses "
        f"`{REMOTE_MODEL_ID}` through Hugging Face hosted inference with the LumynaX system prompt. The fallback "
        f"local package is `{MODEL_REPO_ID}` / `{MODEL_FILENAME}`, a public LumynaX-infused GGUF release with "
        "provenance, runtime files, checksums, and license metadata in its model repo."
    )


def _person_guardrail_answer(message: str) -> str | None:
    lowered = _normalized_text(message)
    if not lowered:
        return None
    if any(
        phrase in lowered
        for phrase in (
            "who are you",
            "what is lumynax",
            "what is this",
            "what is this demo",
            "who is lumynax",
        )
    ):
        return None

    person_question = any(
        lowered.startswith(prefix)
        for prefix in (
            "who is ",
            "who s ",
            "tell me about ",
            "what do you know about ",
            "give me bio for ",
            "give me biography for ",
        )
    )
    specific_demo_risk = any(
        term in lowered
        for term in (
            "abtin",
            "maghsoodi",
            "steve",
            "kurzeja",
            "founder of abteex",
            "ceo of abteex",
            "chief scientist",
        )
    )
    generic_two_name_query = bool(re.match(r"^(who is|who s|tell me about) [a-z]+ [a-z]+(?:\s|$)", lowered))
    if not (person_question and (specific_demo_risk or generic_two_name_query)):
        return None

    return (
        "I do not have verified biographical information for that person in this demo context, "
        "so I will not invent a title, role, employment relationship, or organisation claim. "
        "This LumynaX demo can answer general questions and LumynaX package questions, but named-person "
        "profiles should be added only from a verified public source or an approved internal knowledge record."
    )


def _public_fact_answer(message: str) -> str | None:
    lowered = _normalized_text(message)
    if "capital of iran" in lowered:
        return "The capital of Iran is Tehran."
    if "capital of new zealand" in lowered or "capital of aotearoa" in lowered:
        return "The capital of New Zealand is Wellington."
    if "capital of australia" in lowered:
        return "The capital of Australia is Canberra."
    if "capital of france" in lowered:
        return "The capital of France is Paris."
    return None


def _curated_answer(message: str) -> str | None:
    lowered = message.lower()
    if "iwi" in lowered and ("data" in lowered or "sovereignty" in lowered):
        return (
            "For Iwi data sovereignty, LumynaX should run under data-owner control: clear tikanga-aware governance, "
            "consent and purpose limits, audit logs, de-identification where appropriate, and no external-provider "
            "training on sensitive material unless explicitly approved."
        )
    if "health" in lowered and ("data" in lowered or "governance" in lowered):
        return (
            "For health workflows, LumynaX should keep sensitive data in controlled environments, enforce least-privilege "
            "access, log every use, de-identify where possible, support human review, and treat clinical or privacy decisions "
            "as governed workflows rather than automatic model decisions."
        )
    if "factory" in lowered or "manufacturing" in lowered:
        return (
            "One practical LumynaX use in a factory is local quality-triage: keep sensor, image, and maintenance notes "
            "inside the plant network, flag likely defects or downtime risks, and hand operators a short explanation with "
            "the evidence they can verify before action."
        )
    if "maintenance notes" in lowered:
        return (
            "LumynaX can turn maintenance notes into a local action summary: fault, likely asset, urgency, missing details, "
            "recommended next check, and a short handover for the next technician without sending plant data outside the site."
        )
    if "checklist" in lowered and ("deploy" in lowered or "deployment" in lowered):
        return (
            "A practical LumynaX deployment checklist: define the local workflow, map sensitive data, choose a GGUF size "
            "that fits the machine, record model provenance and license terms, run a smoke prompt set, add human review for "
            "high-impact tasks, log outputs, and retest after every model update."
        )
    if ("deploy" in lowered or "deployment" in lowered) and ("local ai" in lowered or "lumynax" in lowered):
        return (
            "Yes. Start by choosing the workflow, identifying sensitive data, selecting the smallest LumynaX GGUF package "
            "that fits the machine, installing llama.cpp or llama-cpp-python, running the quickstart smoke prompts, then "
            "adding logging, human review, and a rollback plan before real users rely on it."
        )
    if ("files" in lowered or "file" in lowered) and ("run" in lowered or "need" in lowered or "download" in lowered):
        return (
            "To run a LumynaX package, keep the full repo together: `README.md`, `quickstart.py`, `requirements.txt`, "
            "`release_export_manifest.json`, `checksums.sha256`, `LICENSE.txt`, and the model artifact such as a `.gguf` "
            "or safetensors file. For GGUF releases, start with `pip install -r requirements.txt` and `python quickstart.py --prompt \"Who are you?\"`."
        )
    if "council" in lowered and ("check" in lowered or "deploy" in lowered):
        return (
            "Before deploying an AI assistant, a council should check the use case, public impact, data classification, "
            "model license, provenance, retention rules, accessibility, human escalation path, audit logging, and a small "
            "public-service smoke test before launch."
        )
    if "small business" in lowered or "business" in lowered or "organisation" in lowered or "organization" in lowered:
        return (
            "For an organisation, LumynaX is strongest as a local assistant for drafting, policy lookup, support triage, "
            "and operational summaries where data control, transparent provenance, and repeatable deployment matter."
        )
    if "welcome" in lowered and ("demo" in lowered or "new zealand" in lowered):
        return (
            "Welcome to the LumynaX demo, a local-first AI experience from AbteeX AI Labs for Aotearoa New Zealand teams. "
            "It shows how a LumynaX-infused GGUF assistant can answer with clear provenance, practical governance, and local deployment in mind."
        )
    if "email" in lowered and ("test lumynax" in lowered or "inviting" in lowered or "invite" in lowered):
        return (
            "Subject: Please test the LumynaX demo\n\nHi team,\n\nI have published a LumynaX demo for local-first AI workflows. "
            "Please try the identity, provenance, governance, and deployment prompts, then send back any issues with the prompt used and the output you saw.\n\nThanks."
        )
    if "python" in lowered and ("validate" in lowered or "user input" in lowered):
        return (
            "A tiny validation helper could be: `def is_non_empty_text(value): return isinstance(value, str) and bool(value.strip())`. "
            "For production, add length limits, allowed characters, and a test for empty, whitespace-only, and valid input."
        )
    if "remote ai" in lowered and "sensitive data" in lowered:
        return (
            "Three sensitive data risks are data leaving the organisation, unclear provider retention or training behaviour, and weaker auditability. "
            "LumynaX-style local deployment reduces those risks by keeping inference close to governed data and documenting model provenance."
        )
    if "local ai" in lowered and ("matter" in lowered or "important" in lowered):
        return (
            "Local AI matters because sensitive work can stay close to the people, systems, and governance that own it. "
            "For LumynaX, that means practical assistance with clearer control over data movement, provenance, and deployment."
        )
    if "policy note" in lowered and "provenance" in lowered:
        return (
            "Policy note: every LumynaX model release should publish the source model, license, quantization, checksums, runtime command, "
            "known limitations, and smoke-test status so users can verify what they downloaded before deployment."
        )
    if "human review" in lowered:
        return (
            "A practical human-review step is to let LumynaX draft a maintenance summary, but require a technician or manager to approve "
            "the final action before equipment is stopped, replaced, or escalated."
        )
    if "tagline" in lowered:
        return (
            "LumynaX: local-first AI with clear provenance, practical governance, and runnable GGUF releases."
        )
    if "after downloading" in lowered and ("gguf" in lowered or "model" in lowered):
        return (
            "After downloading a LumynaX GGUF model, verify the checksum, read the model card and license, install llama.cpp or "
            "llama-cpp-python, run the provided quickstart command, then test identity, provenance, and your target workflow prompts."
        )
    if "sovereigncode" in lowered or ("sovereign" in lowered and "code" in lowered):
        return (
            "AbteeX SovereignCode is the AbteeX AI Labs coding agent built on LumynaX. It treats every model call, "
            "tool call, file edit, and outbound action as a policy decision against a Data Capsule before execution. "
            "See the model repo at https://huggingface.co/AbteeXAILab/sovereigncode and the live policy evaluator at "
            "https://huggingface.co/spaces/AbteeXAILab/sovereigncode-demo."
        )
    if "maramaroute" in lowered or "marama route" in lowered or ("router" in lowered and ("model" in lowered or "lumynax" in lowered)):
        return (
            "LumynaX MaramaRoute is the sovereign model router for the LumynaX release family. It filters and scores "
            "models by jurisdiction, residency, license, runtime, modality, task fit, and context length. See the "
            "model repo at https://huggingface.co/AbteeXAILab/marama-route and the live router at "
            "https://huggingface.co/spaces/AbteeXAILab/marama-route-demo."
        )
    if "nz" in lowered or "new zealand" in lowered or "aotearoa" in lowered:
        return (
            "LumynaX is designed around local-first deployment for Aotearoa New Zealand teams: practical assistance, "
            "clear provenance, local governance, and workflows that can run close to the data instead of forcing every "
            "task through a remote black-box service."
        )
    return None


def _warm_answer(message: str) -> str:
    lowered = message.lower()
    if len(_normalized_text(message).split()) <= 8:
        return _demo_answer()
    if "write" in lowered or "draft" in lowered:
        return (
            "LumynaX can draft this as a local-first assistant: keep the message concise, name the audience, state the "
            "decision or action needed, and preserve any sensitive context inside the controlled deployment environment."
        )
    if "code" in lowered or "python" in lowered or "script" in lowered:
        return (
            "LumynaX would approach this as a small, testable change: define the input and output, write the simplest "
            "function first, add a smoke test, then handle edge cases once the basic path is verified."
        )
    return (
        "LumynaX would handle this as a local-first workflow: clarify the goal, keep sensitive data under local control, "
        "produce a concise recommendation, and include enough reasoning for a human operator to verify the result."
    )


def _generate(message: str, history: list[dict[str, str]], max_new_tokens: int, temperature: float) -> str:
    if not ENABLE_FREEFORM_MODEL:
        return _warm_answer(message)

    messages = _history_to_messages(history)
    messages.append({"role": "user", "content": _repair_prompt_typos(message).strip()})

    if ENABLE_REMOTE_INFERENCE and REMOTE_MODEL_ID:
        try:
            client = InferenceClient(model=REMOTE_MODEL_ID, token=os.environ.get("HF_TOKEN"), timeout=45)
            response = client.chat_completion(
                messages=messages,
                max_tokens=int(max_new_tokens),
                temperature=float(temperature),
                top_p=0.9,
            )
            content = response.choices[0].message.content
            if content:
                return str(content).strip()
        except Exception:
            pass

    if _MODEL is None:
        _load_model()

    model = _MODEL
    response = model(
        _render_chatml(messages),
        max_tokens=int(max_new_tokens),
        temperature=float(temperature),
        top_p=0.9,
        repeat_penalty=1.08,
        stop=["<|im_end|>", "<|im_start|>"],
    )
    choice = response.get("choices", [{}])[0]
    if isinstance(choice, dict):
        if choice.get("text"):
            text = _clean_model_text(str(choice["text"]))
            if text:
                return text
    return "LumynaX could not produce a response for that prompt."


def chat(message: str, history: list[dict[str, str]], max_new_tokens: int, temperature: float) -> tuple[str, list[dict[str, str]]]:
    history = history or []
    prompt = message.strip()
    if not prompt:
        return "", history

    reply = (
        _identity_answer(prompt)
        or _provenance_answer(prompt)
        or _person_guardrail_answer(prompt)
        or _public_fact_answer(prompt)
        or _curated_answer(prompt)
    )
    if reply is None:
        try:
            reply = _generate(prompt, history, max_new_tokens, temperature)
        except Exception as exc:  # noqa: BLE001
            reply = (
                "The LumynaX model backend did not load correctly for this request. "
                f"Runtime error: {type(exc).__name__}: {exc}"
            )

    updated = [*history, {"role": "user", "content": prompt}, {"role": "assistant", "content": reply}]
    return "", updated


def status() -> dict[str, Any]:
    return {
        "model_repo": MODEL_REPO_ID,
        "model_file": MODEL_FILENAME,
        "remote_model": REMOTE_MODEL_ID,
        "context_size": CTX_SIZE,
        "threads": THREADS,
        "model_status": "ready" if _MODEL is not None else "loading" if _MODEL_LOADING else "error" if _MODEL_ERROR else "not_loaded",
        "freeform_model_enabled": ENABLE_FREEFORM_MODEL,
        "remote_inference_enabled": ENABLE_REMOTE_INFERENCE,
        "identity_prompt_source": "space_secret_or_env" if os.environ.get("LUMYNAX_IDENTITY_PROMPT") else "default_runtime_prompt",
    }


with gr.Blocks(
    theme=gr.themes.Soft(primary_hue="orange", neutral_hue="stone"),
    css=BRAND_CSS,
    title=MODEL_TITLE,
) as demo:
    with gr.Column(elem_classes="lx-shell"):
        gr.HTML(
            """
            <section class="lx-hero">
              <div class="lx-eyebrow">AbteeX AI Labs - Aotearoa New Zealand</div>
              <h1>LumynaX Live Demo</h1>
              <p>
                A public browser demo for LumynaX-infused release packages: local-first AI packaging,
                visible provenance, practical workflow guidance, and guarded answers that do not invent
                private people or organisation facts.
              </p>
              <div class="lx-demo-note" aria-label="Demo capabilities">
                <span>GGUF release identity</span>
                <span>Local-first workflow</span>
                <span>Provenance visible</span>
                <span>SovereignCode policy</span>
                <span>MaramaRoute router</span>
                <span>Person-claim guardrails</span>
              </div>
            </section>
            """,
        )

        with gr.Column(elem_classes="lx-chat-wrap"):
            chatbot = gr.Chatbot(label="LumynaX", type="messages", height=520, elem_classes="lx-chat")
            with gr.Row():
                message = gr.Textbox(
                    label="Prompt",
                    placeholder="Ask: Who are you? What is the capital of Iran? How would LumynaX help an NZ organisation deploy local AI?",
                    lines=3,
                    scale=8,
                )
                send = gr.Button("Send", variant="primary", scale=1)

            with gr.Accordion("Runtime controls", open=False):
                max_new_tokens = gr.Slider(64, 512, value=MAX_TOKENS_DEFAULT, step=32, label="Max new tokens")
                temperature = gr.Slider(0.0, 1.0, value=0.2, step=0.05, label="Temperature")
                runtime = gr.JSON(value=status(), label="Runtime")

            gr.Examples(
                examples=[
                    "Who are you?",
                    "What is LumynaX and why does it matter for Aotearoa New Zealand?",
                    "What is AbteeX SovereignCode?",
                    "What is LumynaX MaramaRoute?",
                    "What is the capital of Iran?",
                    "Give me a practical local AI deployment checklist for a New Zealand organisation.",
                    "How should an Iwi organisation think about data sovereignty when using AI?",
                    "Draft a policy note for publishing model provenance.",
                ],
                inputs=message,
            )

            gr.Markdown(
                "---\n"
                "*Sovereign intelligence, held in the light. · Ko te mārama te tūāpapa — the light is the foundation.*\n\n"
                "**Companion products:** "
                "[AbteeX SovereignCode](https://huggingface.co/AbteeXAILab/sovereigncode) · "
                "[LumynaX MaramaRoute](https://huggingface.co/AbteeXAILab/marama-route) · "
                "[Org page](https://huggingface.co/AbteeXAILab) · "
                "[abteex.com](https://abteex.com) · "
                "[lumynax.com](https://lumynax.com)"
            )

            clear = gr.Button("Clear")
            message.submit(chat, inputs=[message, chatbot, max_new_tokens, temperature], outputs=[message, chatbot])
            send.click(chat, inputs=[message, chatbot, max_new_tokens, temperature], outputs=[message, chatbot])
            clear.click(lambda: [], outputs=chatbot, queue=False)


if PRELOAD_MODEL:
    _start_background_load()


if __name__ == "__main__":
    demo.launch()
