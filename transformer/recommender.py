# transformer/recommender.py
"""
LLM Recommender for Fitness Safety Advisor
Uses fine-tuned Qwen3 model via Ollama.

Key design goals:
- Answers are complete (never cut off mid-sentence).
- Only the answer is returned (no chain-of-thought / reasoning).
- Clean, precise Markdown -- especially real Markdown tables for weekly/monthly plans.
- Deterministic-enough output for a *safety* advisor (low temperature).
"""

import ollama
from typing import Dict, Any, Optional, List
import time
import traceback
import threading
import re

# Initialize Ollama client
client = ollama.Client(host="http://127.0.0.1:11434")

# Use your fine-tuned model
MODEL_NAME = "fitpulse"

# ---------------------------------------------------------------------------
# Generation profiles (centralised so all call sites stay consistent)
# ---------------------------------------------------------------------------
# num_ctx is large enough to hold the RAG context + prompt + full answer.
# num_predict is generous so the model is NEVER cut off mid-answer.
# Low temperature keeps a safety advisor factual and consistent.
# Safe stop tokens only: never include markdown ('---') or the header word
# ('Recommendation:'), which would truncate or empty the output.
# NOTE: On recent Ollama builds, models on the new Go-native "ollamarunner"
# path (this includes Qwen3) accept repeat_penalty / frequency_penalty /
# presence_penalty in the API but silently IGNORE them -- only temperature,
# top_k, top_p and min_p are actually applied by the sampler
# (ollama/ollama#15783). If you're on that path, repeat_penalty below is a
# no-op, which is the likely cause of repetition loops (e.g. a sentence
# template repeating with only a number changing). Verify with
# `ollama show my-fitness-model --modelfile` / your Ollama version, and lean
# on temperature/top_k/top_p/min_p (which do work) plus the post-generation
# repetition guard below as the real safety net either way.
STOP_SAFE = ["<|im_end|>", "<|endoftext|>", "\nUser:", "\nQuestion:", "<|im_start|>"]

# Assistant-prefill text: we make the model START its turn already answering,
# which is the most reliable way to suppress a "thinking out loud" fine-tune
# that emits plain-text reasoning (no <think> tags to strip).
PRIME_REC = "Here's my advice: "
PRIME_TABLE = "|"

OPTS_RECOMMENDATION = {
    "temperature": 0.35,
    "top_p": 0.9,
    "top_k": 40,               # Respected even where repeat_penalty is ignored
    "min_p": 0.05,              # Cuts the long tail that loops tend to live in
    "num_predict": 150,        # Enough for 2-4 sentences, less room to spiral
    "num_ctx": 1536,           # Room for RAG context + answer
    "repeat_penalty": 1.3,     # Kept for engines that honor it; see note above
    "repeat_last_n": 128,
    "stop": STOP_SAFE,
}

OPTS_TABLE = {
    "temperature": 0.2,
    "top_p": 0.9,
    "top_k": 40,
    "min_p": 0.05,
    "num_predict": 600,        # Enough for a 7-day x 5-col table
    "num_ctx": 1536,
    "repeat_penalty": 1.2,
    "repeat_last_n": 128,
    "stop": ["<|im_end|>", "<|endoftext|>", "\nUser:", "\nQuestion:", "<|im_start|>"],
}


class TimeoutError(Exception):
    pass


class OllamaWithTimeout:
    def __init__(self, timeout_seconds=90):
        self.timeout_seconds = timeout_seconds
        self.response = None
        self.error = None

    def _run(self, fn):
        try:
            self.response = fn()
        except Exception as e:  # noqa: BLE001
            self.error = e

    def _call(self, fn):
        thread = threading.Thread(target=self._run, args=(fn,))
        thread.daemon = True
        thread.start()
        thread.join(self.timeout_seconds)
        if thread.is_alive():
            raise TimeoutError(f"Timed out after {self.timeout_seconds}s")
        if self.error:
            raise self.error
        return self.response

    def chat(self, model, messages, options, think=False):
        def _do():
            # Disable Qwen3 "thinking" at the API level when supported.
            # Older ollama-python versions don't accept `think`; fall back.
            try:
                # pyrefly: ignore [unexpected-keyword]
                return client.chat(model=model, messages=messages, options=options, think=think)
            except TypeError:
                return client.chat(model=model, messages=messages, options=options)
        return self._call(_do)

    def generate(self, model, prompt, options, think=False):
        def _do():
            try:
                # pyrefly: ignore [unexpected-keyword]
                return client.generate(model=model, prompt=prompt, options=options, think=think)
            except TypeError:
                return client.generate(model=model, prompt=prompt, options=options)
        return self._call(_do)


# ---------------------------------------------------------------------------
# Output cleaning
# ---------------------------------------------------------------------------
_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_THINK_OPEN_RE = re.compile(r"<think>.*", re.DOTALL | re.IGNORECASE)


def _combine_prime(prime: str, generated: str) -> str:
    """Join the assistant prefill with the model continuation.

    Ollama returns only the newly generated text, so we prepend the prime
    unless the model already repeated it.
    """
    generated = generated or ""
    if generated.lstrip().lower().startswith(prime.strip().lower()):
        return generated.strip()
    return (prime + generated).strip()


def _strip_thinking(text: str) -> str:
    """Remove Qwen3 <think>...</think> reasoning blocks entirely."""
    if not text:
        return text
    text = _THINK_RE.sub("", text)
    # Handle an unclosed <think> (model was cut off inside reasoning)
    text = _THINK_OPEN_RE.sub("", text)
    return text.strip()


_REASON_STARTS = re.compile(
    r"^(okay\b|ok\b|hmm|well,|alright|so,|so i\b|now,|right,|"
    r"let me\b|let's\b|lets\b|"
    r"i need\b|i should\b|i think\b|i'll\b|i will\b|i want\b|i have to\b|"
    r"i must\b|i can\b|i could\b|i might\b|i'm going\b|i'm considering\b|i'd\b|"
    r"the user\b|they want\b|they're\b|they need\b|since the user\b|"
    r"given that\b|considering\b|to approach this\b|my goal\b|the goal\b|"
    r"step by step\b|breaking (this|it) down\b|first, the user\b|for someone\b)",
    re.IGNORECASE,
)


def _sentence_template(sentence: str) -> str:
    """Collapse a sentence to a shape for repetition detection.

    Strips digits and extra whitespace so sentences that only differ by a
    number (the classic 'I want to do it for 40 minutes... 60 minutes...
    90 minutes...' loop) are recognised as the same repeated template even
    though the literal text isn't identical.
    """
    return re.sub(r"\s+", " ", re.sub(r"\d+", "#", sentence.strip().lower()))


def _strip_reasoning_prose(text: str) -> str:
    """
    Truncate at the first sign of mid‑text drift or repetition loop.
    Scans the whole text, not just the start.
    """
    if not text:
        return text

    # 1. Look for reasoning drift markers anywhere in the text.
    # Expanded to include standalone "okay", "so", "now", "well", "alright",
    # and common first-person planning phrases.
    drift_pattern = re.compile(
        r'\b(okay[,.]?\s+|so[,.]?\s+|now[,.]?\s+|well[,.]?\s+|alright[,.]?\s+|'
        r'but\s+wait\s+|wait\s+,\s*|'
        r'i think\s+|i should\s+|i want\s+|i need\s+|let me\s+|'
        r'i\'ll\s+|i\'m going\s+|i would\s+|'
        r'breaking it down\s+|step by step\s+|'
        r'for someone who\s+|given that\s+|the user\s+|they want\s+)',
        re.IGNORECASE
    )
    match = drift_pattern.search(text)
    if match:
        # Truncate at the start of the drifting sentence.
        before = text[:match.start()]
        # Find the last sentence-ending punctuation before the drift.
        last_punct = max(
            before.rfind('.'),
            before.rfind('!'),
            before.rfind('?')
        )
        if last_punct != -1:
            # Keep everything up to and including that punctuation.
            return before[:last_punct+1].strip()
        else:
            # If no punctuation, cut at the drift start.
            return before.strip()

    # 2. Detect repetition loop (template with changing numbers).
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    seen_templates = set()
    kept = []
    for sentence in sentences:
        s = sentence.strip()
        if not s:
            continue
        # Remove digits for template comparison.
        template = re.sub(r'\d+', '#', s)
        # Also collapse numbers like "40" to "#" but we already did.
        if template in seen_templates:
            break  # loop detected, stop here
        seen_templates.add(template)
        kept.append(sentence)

    return ' '.join(kept).strip()


def _clean_response(text: str) -> str:
    """
    Produce a clean, complete answer.

    Conservative on purpose: we ONLY strip reasoning blocks and an optional
    echoed 'Recommendation:' header. We do NOT delete content lines just
    because they start with words like 'First', 'But', 'Finally' -- those are
    legitimate parts of a real recommendation.
    """
    if not text:
        return text

    text = _strip_thinking(text)

    # Drop an echoed header if the model repeated the prompt cue.
    text = re.sub(r"^\s*(here'?s my advice|my recommendation|recommendation|answer|response)\s*:?\s*",
                  "", text, flags=re.IGNORECASE)

    # Remove any leading plain-text reasoning this fine-tune tends to emit.
    text = _strip_reasoning_prose(text)

    # Collapse 3+ blank lines but keep paragraph/list structure.
    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    if not text:
        return "I'd recommend staying active and listening to your body today."

    # Ensure the answer ends on a complete sentence (guards against cutoffs).
    text = _ensure_complete_ending(text)
    return text


def _ensure_complete_ending(text: str) -> str:
    """If the text ends mid-sentence, trim back to the last complete one."""
    stripped = text.rstrip()
    if not stripped:
        return text
    # Tables / lists are fine as-is.
    if "|" in stripped or stripped.endswith((".", "!", "?", ":", ")")):
        return stripped
    # Find the last sentence-ending punctuation and cut there.
    m = list(re.finditer(r"[.!?](\s|$)", stripped))
    if m:
        return stripped[: m[-1].end()].strip()
    # No sentence end at all -> add a period rather than leave it dangling.
    return stripped + "."


def normalize_markdown(text: str) -> str:
    """
    Return clean, standard Markdown (do NOT convert to HTML).
    - Keeps **bold**, *italic*, and tables intact.
    - Normalises bullet markers to '- '.
    """
    if not text:
        return text
    lines = text.split("\n")
    out = []
    for line in lines:
        s = line.rstrip()
        # Normalise bullet markers (•, *, +) to '- ' but leave table rows alone.
        if "|" not in s:
            m = re.match(r"^(\s*)([•*+])\s+(.*)$", s)
            if m:
                s = f"{m.group(1)}- {m.group(3)}"
        out.append(s)
    return "\n".join(out).strip()


# ---------------------------------------------------------------------------
# Markdown table repair / validation
# ---------------------------------------------------------------------------
def _looks_like_table(text: str) -> bool:
    return text.count("|") >= 4 and "\n" in text


def _repair_table(text: str) -> str:
    """
    Ensure a Markdown table has a proper header separator row so it renders.
    Extracts only the table block and inserts the '|---|' row if missing.
    """
    text = _strip_thinking(text).strip()
    lines = [ln.rstrip() for ln in text.split("\n")]
    table_lines = [ln for ln in lines if ln.strip().startswith("|") or ("|" in ln and ln.strip())]
    if not table_lines:
        return text

    # Keep only contiguous table rows.
    rows: List[str] = []
    for ln in lines:
        if "|" in ln:
            rows.append(ln.strip())
        elif rows:
            break  # stop at first non-table line after the table starts

    if len(rows) < 1:
        return text

    # Normalise each row to start/end with '|'.
    def norm(r: str) -> str:
        r = r.strip()
        if not r.startswith("|"):
            r = "| " + r
        if not r.endswith("|"):
            r = r + " |"
        return r

    rows = [norm(r) for r in rows]
    header = rows[0]
    ncols = header.count("|") - 1

    # Is the second row a separator (contains ---)?
    has_sep = len(rows) > 1 and re.match(r"^\|\s*:?-{2,}", rows[1].replace(" ", ""))
    if not has_sep:
        sep = "| " + " | ".join(["---"] * max(ncols, 1)) + " |"
        rows = [header, sep] + rows[1:]

    return "\n".join(rows)


# ---------------------------------------------------------------------------
# Weekly plan (table) generation
# ---------------------------------------------------------------------------
def generate_schedule(user: Dict[str, Any], plan_type: str = "workout") -> str:
    """Generate a weekly plan as a clean Markdown table."""
    age = user.get("Age", "N/A")
    health = user.get("HealthCondition", "N/A")
    fitness = user.get("FitnessLevel", "N/A")

    if plan_type == "workout":
        columns = "Day | Focus | Exercises (Sets x Reps) | Duration"
    else:
        columns = "Day | Breakfast | Lunch | Dinner | Snack"

    system = (
        "You are a fitness and nutrition planner. "
        "Output ONLY a valid GitHub-Flavored Markdown table -- no intro, no notes, "
        "no explanation before or after. Include the header separator row (|---|). "
        "Cover all 7 days (Monday to Sunday). /no_think"
    )
    user_msg = (
        f"Create a weekly {plan_type} plan for a {age}-year-old with {health} "
        f"and {fitness} fitness level.\n"
        f"Use exactly these columns: {columns}.\n"
        f"Return only the Markdown table."
    )

    try:
        wrapper = OllamaWithTimeout(90)
        resp = wrapper.chat(
            MODEL_NAME,
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg},
                # Prefill with "|" so the model starts the table row immediately.
                {"role": "assistant", "content": PRIME_TABLE},
            ],
            OPTS_TABLE,
        )
        raw = _combine_prime(PRIME_TABLE, resp["message"]["content"])
        raw = _strip_thinking(raw)

        if _looks_like_table(raw):
            return _repair_table(raw)
        return "I couldn't generate a proper table. Please try again."
    except Exception as e:  # noqa: BLE001
        print(f"Schedule error: {e}")
        return "I'm having trouble generating a plan right now."


# ---------------------------------------------------------------------------
# Recommendation generation
# ---------------------------------------------------------------------------
def _wants_plan(query: Optional[str]) -> Optional[str]:
    """Return 'diet' / 'workout' if the query asks for a plan, else None."""
    if not query:
        return None
    q = query.lower()
    plan_phrases = ["give me a", "create a", "make a", "generate a", "i need a", "build me a"]
    plan_keywords = ["plan", "schedule", "routine", "workout plan", "meal plan",
                     "diet plan", "weekly", "monthly"]
    if any(p in q for p in plan_phrases) and any(k in q for k in plan_keywords):
        return "diet" if any(w in q for w in ["meal", "diet", "food", "nutrition"]) else "workout"
    return None


def _risk_text(label: str) -> str:
    if label == "Safe":
        return "the conditions are good for exercise"
    if label == "Moderate":
        return "the conditions are okay but take some extra care"
    return "the conditions are not ideal for outdoor exercise"


def generate_recommendation(
    user: Dict[str, Any],
    detector_output: Dict[str, Any],
    query: Optional[str] = None,
) -> str:
    """Give a direct, complete, human-friendly recommendation."""
    plan = _wants_plan(query)
    if plan:
        return generate_schedule(user, plan)

    label = detector_output.get("label", "N/A")
    try:
        age = user.get("Age", "N/A")
        health = user.get("HealthCondition", "N/A")
        fitness = user.get("FitnessLevel", "N/A")
        activity = user.get("ActivityType", "N/A")
        duration = user.get("DurationMins", "N/A")
        time_of_day = user.get("TimeOfDay", "N/A")

        system = (
            "You are a fitness safety coach. "
            "Do not answer too long. "
            "Do NOT think out loud. Do NOT explain your reasoning. "
            "Do NOT use words like 'Okay, ', 'I think', 'maybe', 'okay', or 'let me'. "
            "Start with 'You should' or 'It's best to'. "
            "Do NOT actually write down your reasoning, just give the final advice. "
        )
        user_msg = (
            f"User: {age} years old, {health}, {fitness} fitness.\n"
            f"Planning: {activity} for {duration} minutes in the {time_of_day}.\n"
            f"Risk: {_risk_text(label)}.\n\n"
            f"Give your recommendation."
        )
        if query:
            user_msg += f"\n\nUser's question: {query}"

        print("📝 Calling Ollama...")
        start_time = time.time()

        wrapper = OllamaWithTimeout(timeout_seconds=90)
        response = wrapper.chat(
            MODEL_NAME,
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg},
                # Prefill the assistant turn so the model continues an answer
                # instead of starting to reason.
                {"role": "assistant", "content": PRIME_REC},
            ],
            OPTS_RECOMMENDATION,
        )

        elapsed = time.time() - start_time
        print(f"✅ Ollama responded in {elapsed:.2f}s")

        raw = _combine_prime(PRIME_REC, response["message"]["content"])
        print(f"📝 Raw ({len(raw)} chars): {raw[:160]}...")
        cleaned = _clean_response(raw)
        if cleaned and len(cleaned) > 10:
            formatted = normalize_markdown(cleaned)
            return formatted

        print("⚠️ Response too short, using fallback")
        return _fallback(label)

    except TimeoutError as te:
        print(f"⏰ Timeout: {te}")
        return _fallback(label)
    except Exception as e:  # noqa: BLE001
        print(f"❌ Ollama error: {type(e).__name__}: {e}")
        traceback.print_exc()
        return _fallback(label)


def _fallback(label):
    if label == "Safe":
        return "✅ Great conditions! Enjoy your workout today. Stay hydrated and listen to your body."
    if label == "Moderate":
        return "💡 Moderate risk. Take it a bit easier, use extra breaks, and stay aware of how you feel."
    return "⚠️ Not the best day for outdoor exercise. Consider moving indoors or doing a gentle activity."


# ---------------------------------------------------------------------------
# RAG-augmented recommendation
# ---------------------------------------------------------------------------
def generate_recommendation_with_rag(
    user,
    detector_output,
    query=None,
    rag_context=None,
) -> str:
    """Use RAG context but keep the recommendation simple and complete."""
    plan = _wants_plan(query)
    if plan:
        return generate_schedule(user, plan)

    label = detector_output.get("label", "N/A")
    try:
        if rag_context:
            context = rag_context
        else:
            from rag.query_builder import get_rag_context
            context = get_rag_context(user, detector_output)

        age = user.get("Age", "N/A")
        health = user.get("HealthCondition", "N/A")
        fitness = user.get("FitnessLevel", "N/A")
        activity = user.get("ActivityType", "N/A")

        # Trim context to leave plenty of room in num_ctx for the answer.
        if context and len(context) > 1500:
            context = context[:1500] + "..."

        system = (
            "You are a friendly fitness safety coach talking directly TO the user. "
            "Use the medical context if relevant. Reply with ONLY the final advice "
            "in 2-4 short sentences, in second person (\"you\"). Do NOT think out "
            "loud, do NOT explain your reasoning, do NOT restate the question, do "
            "NOT mention \"the user\". Start immediately with the advice. "
            "Use clean Markdown. /no_think"
        )
        user_msg = (
            f"Medical context:\n{context}\n\n"
            f"User: {age} years old, {health}, {fitness} fitness.\n"
            f"Risk level: {label}.\n"
            f"Activity: {activity}.\n\n"
            f"Give your recommendation."
        )
        if query:
            user_msg += f"\n\nUser's question: {query}"

        print("📝 [RAG] Calling Ollama...")
        wrapper = OllamaWithTimeout(timeout_seconds=90)
        response = wrapper.chat(
            MODEL_NAME,
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg},
                {"role": "assistant", "content": PRIME_REC},
            ],
            OPTS_RECOMMENDATION,
        )

        raw = _combine_prime(PRIME_REC, response["message"]["content"])
        print(f"📝 [RAG] Raw ({len(raw)} chars): {raw[:200]}...")
        cleaned = _clean_response(raw)
        print(f"📝 [RAG] Cleaned ({len(cleaned)} chars): {cleaned[:150]}...")
        if cleaned and len(cleaned) > 10:
            return normalize_markdown(cleaned)
        print("⚠️ [RAG] Cleaned output too short -> falling through to non-RAG path")
        return generate_recommendation(user, detector_output, query)

    except Exception as e:  # noqa: BLE001
        print(f"❌ RAG error: {type(e).__name__}: {e}")
        traceback.print_exc()
        return generate_recommendation(user, detector_output, query)