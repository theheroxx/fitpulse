# transformer/recommender.py
"""
LLM Recommender for Fitness Safety Advisor
Clean, direct, and human-friendly.
"""

import ollama
from typing import Dict, Any, Optional
import time
import traceback
import threading
import re

client = ollama.Client(host='http://127.0.0.1:11434')
MODEL_NAME = "my-fitness-model"


class TimeoutError(Exception):
    pass


class OllamaWithTimeout:
    def __init__(self, timeout_seconds=45):
        self.timeout_seconds = timeout_seconds
        self.response = None
        self.error = None

    def _generate(self, model, prompt, options):
        try:
            self.response = client.generate(model=model, prompt=prompt, options=options)
        except Exception as e:
            self.error = e

    def generate(self, model, prompt, options):
        thread = threading.Thread(target=self._generate, args=(model, prompt, options))
        thread.daemon = True
        thread.start()
        thread.join(self.timeout_seconds)
        if thread.is_alive():
            raise TimeoutError(f"Timed out after {self.timeout_seconds}s")
        if self.error:
            raise self.error
        return self.response


def _clean_response(text: str) -> str:
    """Minimal cleaning: remove image URLs and weird artifacts."""
    if not text:
        return text
    # Remove image markdown and URLs
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
    text = re.sub(r'https?://\S+', '', text)
    # Remove common separator artifacts
    text = re.sub(r'!-!+', '', text)
    # If the response starts with reasoning markers, strip that line
    lines = text.split('\n')
    if lines and re.match(r'^(so,|let me|maybe|i think|i should|hmm|okay)', lines[0].strip(), re.IGNORECASE):
        lines = lines[1:]
    result = '\n'.join(lines).strip()
    if not result:
        return "I'd recommend staying active and listening to your body today."
    # Ensure it ends with punctuation
    if result[-1] not in '.!?':
        result += '.'
    return result


def add_markdown_formatting(text: str) -> str:
    """Light markdown: bold and bullet lists."""
    if not text:
        return text
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    lines = text.split('\n')
    formatted = []
    for line in lines:
        if line.strip().startswith(('-', '*', '•')):
            formatted.append('• ' + line.strip()[1:].strip())
        else:
            formatted.append(line)
    return '\n'.join(formatted)


def generate_schedule(user: Dict[str, Any], plan_type: str = "workout") -> str:
    """Generate a weekly plan (workout or diet) as a markdown table."""
    age = user.get('Age', 'N/A')
    health = user.get('HealthCondition', 'N/A')
    fitness = user.get('FitnessLevel', 'N/A')
    columns = "Day | Focus | Exercises (Sets x Reps) | Duration" if plan_type == "workout" else "Day | Breakfast | Lunch | Dinner | Snack"
    prompt = f"Create a weekly {plan_type} plan for a {age}-year-old with {health} and {fitness} fitness level. Return only a markdown table with columns: {columns}. No extra text."
    try:
        wrapper = OllamaWithTimeout(45)
        resp = wrapper.generate(MODEL_NAME, prompt, {
            'temperature': 0.4,
            'num_predict': 400,
            'num_ctx': 1024,
            'repeat_penalty': 1.1,
            'stop': ['\n\n\n', 'User:', 'Question:']
        })
        result = resp['response'].strip()
        if '|' in result and 'Day' in result:
            return result
        return "I couldn't generate a proper table. Please try again."
    except Exception as e:
        print(f"Schedule error: {e}")
        return "I'm having trouble generating a plan right now."


def generate_recommendation(
    user: Dict[str, Any],
    detector_output: Dict[str, Any],
    query: Optional[str] = None
) -> str:
    """Give a direct, human-friendly recommendation."""
    # Plan request?
    if query:
        q_lower = query.lower()
        plan_phrases = ['give me a', 'create a', 'make a', 'generate a', 'i need a']
        plan_keywords = ['plan', 'schedule', 'routine', 'workout plan', 'meal plan', 'diet plan', 'weekly']
        if any(p in q_lower for p in plan_phrases) and any(k in q_lower for k in plan_keywords):
            return generate_schedule(user, 'diet' if 'meal' in q_lower else 'workout')

    try:
        age = user.get('Age', 'N/A')
        health = user.get('HealthCondition', 'N/A')
        fitness = user.get('FitnessLevel', 'N/A')
        activity = user.get('ActivityType', 'N/A')
        duration = user.get('DurationMins', 'N/A')
        time_of_day = user.get('TimeOfDay', 'N/A')
        label = detector_output.get('label', 'N/A')

        # Simple risk description
        if label == "Safe":
            risk_text = "The conditions are good for exercise."
        elif label == "Moderate":
            risk_text = "The conditions are okay, but take some extra care."
        else:
            risk_text = "The conditions are not ideal for outdoor exercise."

        # Direct prompt (like the old version)
        prompt = f"""
You are a friendly fitness advisor. Give a short, practical recommendation (2-3 sentences) based on the user's situation.

User: {age} years old, {health}, {fitness} fitness.
Planning: {activity} for {duration} minutes in the {time_of_day}.
Risk: {risk_text}

Recommendation:"""
        wrapper = OllamaWithTimeout(45)
        response = wrapper.generate(
            MODEL_NAME,
            prompt,
            {
                'temperature': 0.7,
                'num_predict': 200,
                'num_ctx': 2048,
                'repeat_penalty': 1.15,
                'stop': ['\n\n\n', 'User:', 'Question:', '---', 'Recommendation:']
            }
        )
        raw = response['response'].strip()
        cleaned = _clean_response(raw)
        if len(cleaned) > 800:
            cleaned = cleaned[:800] + "..."
        if cleaned and len(cleaned) > 10:
            return add_markdown_formatting(cleaned)
        return _fallback(label)
    except Exception as e:
        print(f"Error: {e}")
        return _fallback(label)


def _fallback(label):
    if label == "Safe":
        return "✅ Great conditions! Enjoy your workout today. Stay hydrated and listen to your body."
    elif label == "Moderate":
        return "💡 Moderate risk. Take it a bit easier, use extra breaks, and stay aware of how you feel."
    else:
        return "⚠️ Not the best day for outdoor exercise. Consider moving indoors or doing a gentle activity."


def generate_recommendation_with_rag(
    user, 
    detector_output, 
    query=None, 
    rag_context=None
) -> str:
    """Use RAG context but keep the recommendation simple and direct."""
    try:
        if rag_context:
            context = rag_context
        else:
            from rag.query_builder import get_rag_context
            context = get_rag_context(user, detector_output)
        # Plan request?
        if query and any(k in query.lower() for k in ['plan', 'schedule', 'routine']):
            return generate_schedule(user, 'diet' if 'meal' in query.lower() else 'workout')

        age = user.get('Age', 'N/A')
        health = user.get('HealthCondition', 'N/A')
        fitness = user.get('FitnessLevel', 'N/A')
        activity = user.get('ActivityType', 'N/A')
        label = detector_output.get('label', 'N/A')

        # Simple prompt with context
        prompt = f"""
You are a friendly fitness advisor. Use the medical context below if relevant, but keep your answer short and practical (2-3 sentences).

Medical context:
{context[:1000]}

User: {age} years old, {health}, {fitness} fitness.
Risk level: {label}.
Activity: {activity}.

Recommendation:"""
        wrapper = OllamaWithTimeout(45)
        response = wrapper.generate(
            MODEL_NAME,
            prompt,
            {
                'temperature': 0.7,
                'num_predict': 200,
                'num_ctx': 2048,
                'repeat_penalty': 1.15,
                'stop': ['\n\n\n', 'User:', 'Question:', '---', 'Recommendation:']
            }
        )
        cleaned = _clean_response(response['response'].strip())
        return add_markdown_formatting(cleaned)
    except Exception as e:
        print(f"RAG error: {e}")
        return generate_recommendation(user, detector_output, query)