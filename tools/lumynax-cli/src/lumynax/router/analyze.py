"""Prompt analyzer — heuristic detection of intent, language, modality, length.

Returns a PromptAnalysis the Router uses to choose filters + score boosts.
Heuristic-only (no LLM call) so it stays fast and self-contained.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


# ---- intent signals ----
CODE_TOKENS = re.compile(
    r"(?:```|^\s*def |^\s*class |^\s*function |^\s*const |^\s*let |^\s*import |"
    r"^\s*from |^\s*#include|^\s*\$ |\bSELECT \b|\bUPDATE \b|\bINSERT \b|"
    r"=>|::|\(\)|->|\{[^}]*\}|\b[A-Za-z_][A-Za-z0-9_]*\([^)]*\))",
    re.IGNORECASE | re.MULTILINE,
)
CODE_LANGS = re.compile(
    r"\b(?:python|javascript|typescript|rust|golang|java|c\+\+|cpp|csharp|swift|kotlin|"
    r"ruby|bash|shell|sql|html|css|react|vue|svelte|node\.js|django|flask|fastapi|"
    r"refactor|debug|stack trace|exception|test case|unit test|regex)\b",
    re.IGNORECASE,
)

MATH_TOKENS = re.compile(
    r"(?:\$.*?\$|\\\(.*?\\\)|\\begin\{|\\frac|\\sum|\\int|\\prod|\\lim|\\sqrt|"
    r"\\theorem|\\lemma|\\proof|\\forall|\\exists|"
    r"\b(?:proof|prove|proves|proven|theorem|lemma|corollary|derivative|integral|"
    r"matrix|matrices|eigenvalue|quadratic|polynomial|equation|factorial|"
    r"limit|inequality|algebra|geometry|calculus)\b)",
    re.IGNORECASE,
)

VISION_TOKENS = re.compile(
    r"(?:!\[.*?\]\(.*?\)|<img\b|data:image/|\.(?:png|jpe?g|gif|webp|bmp|svg)\b|"
    r"\bdescribe (?:this |the )?image\b|\bwhat'?s? in (?:this |the )?(?:image|picture|photo)\b|"
    r"\bocr\b|\bvisual\b|\bdiagram\b|\bchart\b|\bgraph\b|\blook at\b)",
    re.IGNORECASE,
)

AUDIO_TOKENS = re.compile(
    r"(?:\.(?:wav|mp3|ogg|m4a|flac|opus)\b|\baudio\b|\btranscrib|\bspeech\b|"
    r"\bvoice\b|\brecording\b|\bsubtitle\b)",
    re.IGNORECASE,
)

REASONING_TOKENS = re.compile(
    r"\b(?:think step by step|reason carefully|chain of thought|prove that|"
    r"explain why|step-by-step|carefully analyze|breakdown|deduce|infer)\b",
    re.IGNORECASE,
)

TOOL_TOKENS = re.compile(
    r"(?:\bcall (?:a |an |the )?[\w_]*\s*(?:function|tool|api|method|endpoint)\b|"
    r"\binvoke\b|\bexecute\b|\brun (?:a |the )?(?:command|tool|api)\b|"
    r"\bweb search\b|\bsearch the web\b|\bfetch from\b|\bapi call\b|"
    r"\bjson schema\b|\btool_calls\b|\bfunction_call\b)",
    re.IGNORECASE,
)

JSON_TOKENS = re.compile(
    r"(?:return (?:as |in )?json|json schema|valid json|structured output|"
    r"\{[\s\S]*:[\s\S]*\}|response_format)",
    re.IGNORECASE,
)

EMBED_TOKENS = re.compile(
    r"\b(?:embed(?:ding|der)?|vector(?:ize)?|cosine similarity|semantic search|"
    r"rerank(?:er|ing)?|retrieval)\b",
    re.IGNORECASE,
)

TRANSLATE_TOKENS = re.compile(
    r"\b(?:translate|translation)\b\s+(?:to|into|from)\s+\b("
    r"english|maori|māori|samoan|tongan|fijian|chinese|mandarin|japanese|"
    r"korean|spanish|french|german|italian|portuguese|arabic|hindi|russian|dutch|swedish)\b",
    re.IGNORECASE,
)

# ---- Māori / te reo signal ----
TE_REO_TOKENS = re.compile(
    r"\b(?:kia ora|aroha|whanau|whānau|iwi|hapū|hapu|tikanga|kaupapa|wairua|"
    r"mauri|tapu|noa|tangata|aotearoa|tiriti|maori|māori|wh[āa]nau|te reo)\b",
    re.IGNORECASE,
)


@dataclass
class PromptAnalysis:
    """Structured analysis of a prompt's intent / modality / language needs."""
    # Detected intents (boolean signals)
    is_code: bool = False
    is_math: bool = False
    is_reasoning: bool = False
    needs_tools: bool = False
    needs_json: bool = False
    is_embedding_task: bool = False
    is_translation: bool = False
    contains_te_reo: bool = False

    # Modalities the prompt references
    needs_vision: bool = False
    needs_audio: bool = False

    # Length signals
    char_count: int = 0
    estimated_tokens: int = 0
    is_long_context: bool = False  # >32k tokens estimated

    # Detected programming languages (if any)
    code_langs: list[str] = field(default_factory=list)

    # Detected translation target language (if any)
    translate_target: Optional[str] = None

    # Confidence (0-1) — combination of strength of signals
    confidence: float = 0.0

    def task_tags(self) -> list[str]:
        """Convert detected signals into routing tag hints."""
        out = []
        if self.is_code:            out.append("coder")
        if self.is_math:            out.append("math")
        if self.is_reasoning:       out.append("reasoning")
        if self.is_translation:     out.append("translate")
        if self.contains_te_reo:    out.append("te-reo")
        if self.is_embedding_task:  out.append("embedding")
        if self.needs_vision:       out.append("vision")
        if self.needs_audio:        out.append("audio")
        if self.is_long_context:    out.append("long-context")
        return out


def analyze(prompt: str) -> PromptAnalysis:
    """Run all heuristics and return a PromptAnalysis."""
    if not prompt:
        return PromptAnalysis()

    a = PromptAnalysis()
    a.char_count = len(prompt)
    a.estimated_tokens = max(1, len(prompt) // 4)  # ~4 chars/token English
    a.is_long_context = a.estimated_tokens > 32_000

    code_hits = len(CODE_TOKENS.findall(prompt)) + len(CODE_LANGS.findall(prompt))
    a.is_code = code_hits >= 2 or bool(re.search(r"```", prompt))
    if a.is_code:
        a.code_langs = sorted(set(m.lower() for m in CODE_LANGS.findall(prompt)))[:5]

    a.is_math = bool(MATH_TOKENS.search(prompt))
    a.is_reasoning = bool(REASONING_TOKENS.search(prompt)) or a.is_math
    a.needs_tools = bool(TOOL_TOKENS.search(prompt))
    a.needs_json = bool(JSON_TOKENS.search(prompt))
    a.is_embedding_task = bool(EMBED_TOKENS.search(prompt))
    a.needs_vision = bool(VISION_TOKENS.search(prompt))
    a.needs_audio = bool(AUDIO_TOKENS.search(prompt))

    tm = TRANSLATE_TOKENS.search(prompt)
    if tm:
        a.is_translation = True
        a.translate_target = tm.group(1).lower()

    a.contains_te_reo = bool(TE_REO_TOKENS.search(prompt))
    if a.is_translation and a.translate_target in {"maori", "māori"}:
        a.contains_te_reo = True

    # confidence: strength of clearest signal
    signals = [a.is_code, a.is_math, a.is_translation, a.needs_vision,
               a.needs_audio, a.is_embedding_task, a.is_reasoning,
               a.contains_te_reo, a.is_long_context, a.needs_tools, a.needs_json]
    a.confidence = min(1.0, 0.25 * sum(signals))
    return a
