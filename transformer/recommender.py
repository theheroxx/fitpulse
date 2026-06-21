# transformer/recommender.py
"""
LLM Recommender for Fitness Safety Advisor
Uses fine-tuned Qwen3 model via Ollama
Human-friendly, conversational tone - no technical jargon or ED numbers
"""

import ollama
from typing import Dict, Any
import time
import traceback
import threading
import re

# Initialize Ollama client
client = ollama.Client(host='http://127.0.0.1:11434')

# Use your fine-tuned model
MODEL_NAME = "my-fitness-model"


class TimeoutError(Exception):
    """Custom timeout exception"""
    pass


class OllamaWithTimeout:
    """Wrapper for Ollama with timeout support"""
    
    def __init__(self, timeout_seconds=30):
        self.timeout_seconds = timeout_seconds
        self.response = None
        self.error = None
    
    def _generate(self, model, prompt, options):
        """Internal generate method"""
        try:
            self.response = client.generate(
                model=model,
                prompt=prompt,
                options=options
            )
        except Exception as e:
            self.error = e
    
    def generate(self, model, prompt, options):
        """Generate with timeout"""
        thread = threading.Thread(target=self._generate, args=(model, prompt, options))
        thread.daemon = True
        thread.start()
        thread.join(self.timeout_seconds)
        
        if thread.is_alive():
            raise TimeoutError(f"Ollama request timed out after {self.timeout_seconds} seconds")
        
        if self.error:
            raise self.error
        
        return self.response


def add_markdown_formatting(text: str) -> str:
    """
    Add markdown formatting to plain text LLM response.
    Converts plain text to formatted markdown for better UI display.
    """
    if not text:
        return text
    
    formatted = text
    
    # Bold key terms
    keywords = ['safety', 'risk', 'danger', 'warning', 'caution', 'safe', 'unsafe', 
                'moderate', 'extreme', 'critical', 'important', 'health']
    for keyword in keywords:
        pattern = rf'\b({keyword})\b'
        formatted = re.sub(pattern, r'**\1**', formatted, flags=re.IGNORECASE)
    
    # Format bullet points
    lines = formatted.split('\n')
    formatted_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped and (stripped[0] in ['-', '*', '•']) and len(stripped) > 1:
            formatted_lines.append(f"• {stripped[1:].strip()}")
        else:
            formatted_lines.append(line)
    formatted = '\n'.join(formatted_lines)
    
    # Add emojis based on context (human-friendly)
    if any(word in text.lower() for word in ['danger', 'extreme', 'unsafe', 'avoid', 'dangerous']):
        formatted = "⚠️ " + formatted
    elif any(word in text.lower() for word in ['safe', 'good', 'favorable', 'enjoy']):
        formatted = "✅ " + formatted
    elif any(word in text.lower() for word in ['moderate', 'caution', 'careful']):
        formatted = "💡 " + formatted
    
    # Format numbered lists
    formatted = re.sub(r'(\d+)\.\s+', r'\1. ', formatted)
    
    # Add line breaks for readability (but not too many)
    if len(formatted) > 150:
        formatted = formatted.replace('. ', '.\n\n')
    
    return formatted


def generate_recommendation(user: Dict[str, Any], detector_output: Dict[str, Any]) -> str:
    """
    Generate immediate personalized recommendation using Ollama LLM with timeout.
    Uses fine-tuned Qwen3 model with human-friendly, conversational tone.
    NEVER mentions ED scores or technical jargon.
    """
    
    print("=" * 60)
    print("🤖 GENERATE_RECOMMENDATION - STARTED")
    print(f"   Time: {time.strftime('%H:%M:%S')}")
    print("=" * 60)
    
    try:
        # Extract user data (no ED numbers!)
        age = user.get('Age', 'N/A')
        health = user.get('HealthCondition', 'N/A')
        fitness = user.get('FitnessLevel', 'N/A')
        activity = user.get('ActivityType', 'N/A')
        duration = user.get('DurationMins', 'N/A')
        time_of_day = user.get('TimeOfDay', 'N/A')
        label = detector_output.get('label', 'N/A')
        
        print(f"📊 User Data:")
        print(f"   Age: {age}")
        print(f"   Health: {health}")
        print(f"   Fitness: {fitness}")
        print(f"   Activity: {activity}")
        print(f"   Duration: {duration}")
        print(f"   Time: {time_of_day}")
        print(f"   Risk Label: {label}")
        
        # Human-friendly risk context (no numbers!)
        if label == "Safe":
            risk_context = "The conditions are good for exercise"
            tone = "encouraging and positive"
        elif label == "Moderate":
            risk_context = "The conditions are okay but you should take some extra care"
            tone = "cautious but helpful"
        else:
            risk_context = "The conditions are not great for outdoor exercise today"
            tone = "concerned and advising caution"
        
        print(f"📊 Risk Context: {risk_context}")
        
        # Human-friendly prompt - conversational, warm, clear
        prompt = f"""You are a friendly, approachable fitness advisor. Talk like a helpful friend giving practical advice.

USER PROFILE:
- {age} years old
- Health: {health}
- Fitness level: {fitness}
- Planning: {activity} for {duration} minutes in the {time_of_day}
- What's happening: {risk_context}

Your task: Give a short, warm, practical recommendation (2-3 sentences, max 100 words).

STYLE RULES:
1. Be friendly and conversational - like a caring friend, not a doctor
2. Use simple, everyday language - no technical terms
3. NEVER mention any numbers or scores
4. Give specific, actionable advice
5. Be encouraging but honest

EXAMPLE: "Hey there! The weather looks fine for a nice walk today. Just remember to take a water bottle and listen to your body - if you feel tired, it's okay to slow down. Have a great workout!"

RECOMMENDATION:"""

        print(f"📝 Prompt sent to model")
        print("🤖 Calling Ollama...")
        
        start_time = time.time()
        
        try:
            wrapper = OllamaWithTimeout(timeout_seconds=30)
            response = wrapper.generate(
                model=MODEL_NAME,
                prompt=prompt,
                options={
                    'temperature': 0.8,           # Slightly more creative for friendly tone
                    'num_predict': 200,
                    'num_ctx': 2048,
                    'repeat_penalty': 1.15,
                    'repeat_last_n': 64,
                    'stop': ['\n\n\n', 'User:', 'Question:', '---', 'RECOMMENDATION:']
                }
            )
            
            elapsed = time.time() - start_time
            print(f"✅ Ollama responded in {elapsed:.2f} seconds")
            
            result = response['response'].strip()
            
            # Safety trim
            if len(result) > 800:
                result = result[:800] + "..."
            
            print(f"📝 Response length: {len(result)} characters")
            print(f"📝 Response preview: {result[:150]}...")
            
            if result and len(result) > 10:
                # Add markdown formatting for display
                formatted_result = add_markdown_formatting(result)
                print("✅ Returning formatted recommendation")
                return formatted_result
            
            print("⚠️ Response too short, using fallback")
            return _get_fallback_recommendation(label, activity)
            
        except TimeoutError as te:
            print(f"⏰ {te}")
            return _get_fallback_recommendation(label, activity)
        
    except Exception as e:
        print(f"❌ Ollama error: {type(e).__name__}: {e}")
        traceback.print_exc()
        return _get_fallback_recommendation(label, activity)


def _get_fallback_recommendation(risk_label, activity):
    """Human-friendly fallback when Ollama is unavailable"""
    print("📋 _get_fallback_recommendation called")
    
    if risk_label == "Safe":
        return "✅ **Great conditions for exercise!** 🌤️\n\n• Enjoy your workout today\n• Stay hydrated\n• Listen to your body and have fun!"
    elif risk_label == "Moderate":
        return "💡 **Things are okay, but take it easy**\n\n• Consider taking it a bit easier than usual\n• Take more breaks if you need to\n• Stay aware of how you're feeling"
    else:
        return "⚠️ **Not the best day for outdoor exercise**\n\n• You might want to move your workout indoors today\n• Try a gentle indoor activity instead\n• It's okay to take a rest day too!"


def generate_recommendation_with_rag(user: Dict[str, Any], detector_output: Dict[str, Any]) -> str:
    """
    Version with RAG - uses medical context but still human-friendly and NEVER mentions ED numbers.
    """
    print("🤖 generate_recommendation_with_rag called")
    try:
        from rag.query_builder import get_rag_context, generate_rag_response
        
        # Get RAG context (contains medical info, no ED numbers)
        context = get_rag_context(user, detector_output)
        
        # Build human-friendly query - no numbers!
        user_query = f"""Provide a friendly, practical recommendation for a {user.get('Age')}-year-old with {user.get('HealthCondition')} who wants to do {user.get('ActivityType')}.
        
IMPORTANT RULES:
1. Be friendly and conversational - like a helpful friend
2. Use simple, everyday language
3. NEVER mention any numbers or technical scores
4. Give specific, actionable advice
5. Be warm and encouraging"""
        
        return generate_rag_response(context, user_query)
    except Exception as e:
        print(f"❌ RAG failed: {e}")
        return generate_recommendation(user, detector_output)