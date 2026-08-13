"""
LLM Recommender for Fitness Safety Advisor
Standardized implementation using fine-tuned Qwen3 model via Ollama.
"""

import ollama
from typing import Dict, Any, Optional, List
import time
import traceback
import threading
import re

# Initialize Ollama client
client = ollama.Client(host="http://127.0.0.1:11434")

MODEL_NAME = "fitpulse"

# ---------------------------------------------------------------------------
# Standardized Generation Parameters
# ---------------------------------------------------------------------------
STOP_SAFE = ["<|im_end|>", "<|endoftext|>", "\nUser:", "\nQuestion:", "<|im_start|>"]

OPTS_RECOMMENDATION = {
    "temperature": 0.3,
    "top_p": 0.9,
    "num_predict": 250,
    "num_ctx": 4096,  # Increased context window
    "repeat_penalty": 1.1,
    "stop": STOP_SAFE,
}

OPTS_TABLE = {
    "temperature": 0.1,
    "top_p": 0.9,
    "num_predict": 600,
    "num_ctx": 4096,  # Increased context window
    "repeat_penalty": 1.1,
    "stop": STOP_SAFE,
}


class TimeoutError(Exception):
    pass


class OllamaWithTimeout:
    def __init__(self, timeout_seconds=120):  # Increased from 90 to 120
        self.timeout_seconds = timeout_seconds
        self.response = None
        self.error = None

    def _run(self, fn):
        try:
            self.response = fn()
        except Exception as e:
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
            try:
                # pyrefly: ignore [unexpected-keyword]
                return client.chat(model=model, messages=messages, options=options, think=think)
            except TypeError:
                return client.chat(model=model, messages=messages, options=options)
        return self._call(_do)


# ---------------------------------------------------------------------------
# RAG Context Limiting
# ---------------------------------------------------------------------------
def limit_rag_context(rag_context: str, max_chars: int = 2000) -> str:
    """
    Limit RAG context to prevent LLM timeout.
    Keeps the most relevant information while staying within limits.
    """
    if not rag_context or len(rag_context) <= max_chars:
        return rag_context
    
    # Split into lines
    lines = rag_context.split('\n')
    
    # Extract document references (lines starting with [Reference or [Ref)
    references = []
    other_lines = []
    
    current_ref = None
    
    for line in lines:
        # Detect reference markers
        if re.match(r'^\[(Reference|Ref)\s*\d*\]', line.strip()):
            if current_ref:
                references.append(current_ref)
            current_ref = line.strip()
        elif current_ref is not None:
            # Append to current reference
            if current_ref in references:
                # Find and update
                idx = references.index(current_ref)
                references[idx] = current_ref + " " + line.strip()
            else:
                current_ref = current_ref + " " + line.strip()
        else:
            if line.strip():
                other_lines.append(line.strip())
    
    # Add final reference if exists
    if current_ref and current_ref not in references:
        references.append(current_ref)
    
    # Build limited context
    limited_parts = []
    current_length = 0
    
    # Add header if present
    for line in other_lines[:5]:  # Keep first 5 non-reference lines
        if current_length + len(line) > max_chars * 0.3:
            break
        limited_parts.append(line)
        current_length += len(line)
    
    # Add references (truncate each to 400 chars)
    for ref in references:
        # Truncate individual reference
        if len(ref) > 400:
            # Find sentence boundary
            truncated = ref[:400]
            last_period = truncated.rfind('.')
            if last_period > 200:
                ref = truncated[:last_period + 1] + "..."
            else:
                ref = truncated + "..."
        
        if current_length + len(ref) > max_chars:
            break
        
        limited_parts.append(ref)
        current_length += len(ref)
    
    truncated = '\n\n'.join(limited_parts)
    
    # Add truncation notice
    if len(rag_context) > max_chars:
        truncated += f"\n\n... [truncated from {len(rag_context)} to {max_chars} chars]"
    
    return truncated


# ---------------------------------------------------------------------------
# Lightweight Response Normalization
# ---------------------------------------------------------------------------
def clean_response(text: str) -> str:
    """Basic cleanup to remove thinking tags and excess whitespace."""
    if not text:
        return ""
    # Remove Qwen/DeepSeek style thinking tags
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<think>.*", "", text, flags=re.DOTALL | re.IGNORECASE)
    
    text = text.strip()
    
    # Simple check for abrupt cut-offs
    if text and not text.endswith((".", "!", "?", "|", ")")):
        last_punct = max(text.rfind("."), text.rfind("!"), text.rfind("?"))
        if last_punct != -1:
            text = text[: last_punct + 1]
        else:
            text += "."
            
    return text


# ---------------------------------------------------------------------------
# Weekly Plan Generation
# ---------------------------------------------------------------------------
def generate_schedule(user: Dict[str, Any], plan_type: str = "workout") -> str:
    age = user.get("Age", "N/A")
    health = user.get("HealthCondition", "N/A")
    fitness = user.get("FitnessLevel", "N/A")

    columns = (
        "Day | Focus | Exercises (Sets x Reps) | Duration"
        if plan_type == "workout"
        else "Day | Breakfast | Lunch | Dinner | Snack"
    )

    system_prompt = (
        "You are an expert fitness and nutrition coach.\n"
        "Generate a complete 7-day plan in clean GitHub-Flavored Markdown table format.\n"
        "Output ONLY the markdown table. Do not include intro or concluding text."
    )
    
    user_prompt = (
        f"Create a 7-day {plan_type} schedule for a user with the following profile:\n"
        f"- Age: {age}\n"
        f"- Health Conditions: {health}\n"
        f"- Fitness Level: {fitness}\n\n"
        f"Table Columns to use: {columns}"
    )

    try:
        wrapper = OllamaWithTimeout(120)
        resp = wrapper.chat(
            MODEL_NAME,
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            OPTS_TABLE,
        )
        return clean_response(resp["message"]["content"])
    except Exception as e:
        print(f"Schedule generation error: {e}")
        return "Unable to generate schedule at this time."


# ---------------------------------------------------------------------------
# Recommendation generation (RAG-aware & Direct)
# ---------------------------------------------------------------------------
def generate_recommendation_with_rag(
    user: Dict[str, Any],
    detector_output: Dict[str, Any],
    query: Optional[str] = None,
    rag_context: Optional[str] = None,
    include_history: bool = False,
    chat_history: Optional[List[Dict]] = None,
) -> str:
    """Generate direct, grounded fitness safety advice."""
    
    # Plan Routing
    if query and any(k in query.lower() for k in ["plan", "schedule", "routine", "table"]):
        plan_type = "diet" if any(w in query.lower() for w in ["meal", "diet", "food", "nutrition"]) else "workout"
        return generate_schedule(user, plan_type)

    label = detector_output.get("label", "Safe")
    
    # Fetch Contexts
    if not rag_context:
        try:
            from rag.query_builder import (
                get_rag_context,
                format_context_for_prompt,
            )

            # Get structured RAG result
            rag_result = get_rag_context(
                user_input=user,
                detector_output=detector_output,
                user_query=query or "",
            )

            # Convert retrieved documents into LLM-readable context
            rag_context = format_context_for_prompt(
                rag_result,
                max_docs=3,  # Reduced from 5 to 3
            )
            
            # CRITICAL: Limit context size to prevent timeout
            rag_context = limit_rag_context(rag_context, max_chars=2000)

            # Debug output (reduced verbosity)
            print(f"\n[RAG] Intent: {rag_result.get('intent')}, Error: {rag_result.get('error')}")
            print(f"[RAG] Context length: {len(rag_context or '')} chars")

        except Exception as e:
            print(f"[RAG] Context generation failed: {e}")
            traceback.print_exc()
            rag_context = ""

    history_context = ""
    if include_history and user.get("id"):
        try:
            from database.db import get_user_records
            records = get_user_records(user["id"])
            if records:
                history_lines = [f"- {r.get('record_type')}: {r.get('title')}" for r in records[:3]]
                history_context = "\nRecent History:\n" + "\n".join(history_lines)
        except Exception:
            pass

    # Standardized System Prompt
    system_prompt = (
        "You are a supportive, practical fitness safety coach. "
        "The user's question is the priority — answer it directly and specifically. "
        "Use the medical context and profile as supporting detail, not a substitute for answering the actual question. "
        "Provide 2-4 sentences of direct, practical advice spoken directly to the user ('you'). "
        "Do not output internal reasoning or preambles."
    )

    # Standardized User Prompt — question leads, structured fields support it
    user_prompt = ""
    if query:
        user_prompt += f"User's Question: {query}\n\n"

    user_prompt += f"Medical Context:\n{rag_context or 'None'}\n\n"
    user_prompt += f"User Profile:\n"
    user_prompt += f"- Health Condition: {user.get('HealthCondition', 'None')}\n"
    user_prompt += f"- Fitness Level: {user.get('FitnessLevel', 'Moderate')}\n"
    user_prompt += f"- Planned Activity: {user.get('ActivityType', 'Exercise')} ({user.get('DurationMins', 30)} mins)\n"
    user_prompt += f"- Environmental Risk Level: {label}\n"

    if user.get("bio"):
        user_prompt += f"- Personal Bio: {user.get('bio')}\n"
    if history_context:
        user_prompt += f"{history_context}\n"

    # ─── Recent conversation, flattened as plain text ──────────────────────
    if chat_history:
        history_turns = [
            m for m in chat_history
            if not (m.get("role") == "user" and m.get("content") == query)
        ]
        convo_lines = []
        for msg in history_turns[-4:]:
            role = msg.get("role")
            content = msg.get("content", "")
            if role == "user" and content:
                convo_lines.append(f"User: {content}")
            elif role == "assistant" and content:
                convo_lines.append(f"Assistant: {content}")
        if convo_lines:
            user_prompt += "\nRecent Conversation:\n" + "\n".join(convo_lines) + "\n"

    if query:
        user_prompt += f"\nRemember: directly answer this specific question: {query}\n"

    user_prompt += "\nProvide direct advice now:"

    # Debug output
    print(f"[recommender] Prompt length: {len(user_prompt)} chars")
    print(f"[recommender] RAG context length: {len(rag_context or '')} chars")
    print(f"[recommender] Sending to {MODEL_NAME}...")

    try:
        wrapper = OllamaWithTimeout(timeout_seconds=120)
        response = wrapper.chat(
            MODEL_NAME,
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            OPTS_RECOMMENDATION,
        )

        cleaned = clean_response(response["message"]["content"])
        return cleaned if cleaned else _fallback(label)

    except TimeoutError as e:
        print(f"Timeout error: {e}")
        return _fallback(label)
    except Exception as e:
        print(f"Error generating recommendation: {e}")
        return _fallback(label)


def generate_recommendation(
    user: Dict[str, Any],
    detector_output: Dict[str, Any],
    query: Optional[str] = None,
    include_history: bool = False,
    chat_history: Optional[List[Dict]] = None,
) -> str:
    """Direct alias/wrapper for non-RAG recommendations to keep backward compatibility."""
    return generate_recommendation_with_rag(
        user=user,
        detector_output=detector_output,
        query=query,
        rag_context=None,
        include_history=include_history,
        chat_history=chat_history,
    )


def _fallback(label: str) -> str:
    if label == "Safe":
        return "Conditions look great for your workout! Stay hydrated and listen to your body."
    if label == "Moderate":
        return "Exercise conditions are moderate. Take extra rest breaks and keep your intensity light."
    return "Outdoor conditions are currently unfavorable. Consider moving your workout indoors today."