import streamlit as st
import sys
import os
import ollama
from datetime import datetime

# Fix import path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import from orchestrator
from core.orchestrator import (
    run_pipeline, 
    calculate_detailed_environmental_risk, 
    get_risk_recommendation, 
    PipelineCache
)

# Initialize Ollama client
ollama_client = ollama.Client(host='http://127.0.0.1:11434')

# Model configuration
CHAT_MODEL = "gemma3:4b"

# ================================
# PRELOAD MODELS
# ================================
@st.cache_resource
def init_models():
    """Initialize and cache all models"""
    try:
        PipelineCache.get_ed_predictor()
        return True
    except Exception as e:
        st.error(f"Failed to load model: {e}")
        return False

models_loaded = init_models()

# ================================
# PAGE CONFIG
# ================================
st.set_page_config(
    page_title="AI Fitness Advisor",
    page_icon="🏃",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ================================
# CUSTOM CSS
# ================================
st.markdown("""
    <style>
    .main-title {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-color: transparent;
        background-clip: text;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .subtitle {
        text-align: center;
        color: #666;
        margin-bottom: 2rem;
    }
    .card {
        background: white;
        padding: 1.5rem;
        border-radius: 1rem;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        margin-bottom: 1.5rem;
        border: 1px solid #e0e0e0;
    }
    .card-title {
        font-size: 1.2rem;
        font-weight: 600;
        margin-bottom: 1rem;
        color: #2c3e50;
        border-left: 4px solid #667eea;
        padding-left: 0.75rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 0.75rem;
        text-align: center;
        margin-bottom: 1rem;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
    }
    .metric-label {
        font-size: 0.85rem;
        opacity: 0.9;
    }
    .risk-safe {
        background: #d4edda;
        color: #155724;
        padding: 0.75rem;
        border-radius: 0.5rem;
        text-align: center;
        font-weight: 600;
        margin: 0.5rem 0;
    }
    .risk-moderate {
        background: #fff3cd;
        color: #856404;
        padding: 0.75rem;
        border-radius: 0.5rem;
        text-align: center;
        font-weight: 600;
        margin: 0.5rem 0;
    }
    .risk-high {
        background: #f8d7da;
        color: #721c24;
        padding: 0.75rem;
        border-radius: 0.5rem;
        text-align: center;
        font-weight: 600;
        margin: 0.5rem 0;
    }
    .risk-danger {
        background: #dc3545;
        color: white;
        padding: 0.75rem;
        border-radius: 0.5rem;
        text-align: center;
        font-weight: 600;
        margin: 0.5rem 0;
    }
    .chat-container {
        max-height: 500px;
        overflow-y: auto;
        padding: 1rem;
        background: #f8f9fa;
        border-radius: 1rem;
        margin-bottom: 1rem;
    }
    .user-message {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 0.75rem 1rem;
        border-radius: 1rem;
        margin: 0.5rem 0;
        margin-left: 20%;
        text-align: right;
    }
    .assistant-message {
        background: white;
        color: #2c3e50;
        padding: 0.75rem 1rem;
        border-radius: 1rem;
        margin: 0.5rem 0;
        margin-right: 20%;
        border: 1px solid #e0e0e0;
    }
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 0.5rem 1rem;
        font-weight: 600;
        border-radius: 0.5rem;
        transition: transform 0.2s;
        width: 100%;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(102,126,234,0.4);
    }
    .custom-divider {
        margin: 2rem 0;
        border-top: 2px solid #e0e0e0;
    }
    .footer {
        text-align: center;
        color: #999;
        font-size: 0.8rem;
        margin-top: 2rem;
    }
    .model-badge {
        background: #28a745;
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 1rem;
        font-size: 0.8rem;
        display: inline-block;
    }
    </style>
""", unsafe_allow_html=True)

# ================================
# HEADER
# ================================
st.markdown('<div class="main-title">🏃 AI Fitness & Health Advisor</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Smart exercise recommendations based on your environment and health data</div>', unsafe_allow_html=True)

if not models_loaded:
    st.error("⚠️ Models failed to load. Please check your data files.")
    st.stop()

st.markdown(f'<div style="text-align: center; margin-bottom: 1rem;"><span class="model-badge">🤖 Using model: {CHAT_MODEL}</span></div>', unsafe_allow_html=True)

# ================================
# TABS
# ================================
tab1, tab2 = st.tabs(["🏃 Activity Analysis", "🌡️ Detailed Environmental Risk"])

# ================================
# TAB 1: Activity Analysis (NOW USING ML MODEL FOR RISK)
# ================================
with tab1:
    left_col, right_col = st.columns([1, 1], gap="large")
    
    with left_col:
        with st.container():
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown('<div class="card-title">📋 Personal Information</div>', unsafe_allow_html=True)
            
            col_a, col_b = st.columns(2)
            with col_a:
                age = st.number_input("Age", min_value=10, max_value=100, value=30, step=1, key="age")
                fitness = st.selectbox("Fitness Level", ["Low", "Medium", "High"], key="fitness")
                health = st.selectbox("Health Condition", ["Healthy", "Asthma", "Heart Condition"], key="health")
            
            with col_b:
                activity = st.selectbox("Activity Type", ["Low Cardio", "High Cardio", "Strength"], key="activity")
                duration = st.number_input("Duration (minutes)", min_value=5, max_value=120, value=30, step=5, key="duration")
                tod = st.selectbox("Time of Day", ["Morning", "Afternoon", "Evening", "Night"], key="tod")
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        with st.container():
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown('<div class="card-title">🌍 Environmental Conditions</div>', unsafe_allow_html=True)
            
            st.markdown("**Weather Conditions**")
            col_c, col_d = st.columns(2)
            with col_c:
                temp = st.slider("Temperature (°C)", -10, 45, 22, key="temp_tab1")
                humid = st.slider("Humidity (%)", 0, 100, 45, key="humid_tab1")
                wind = st.slider("Wind (kph)", 0, 100, 10, key="wind_tab1")
                uv = st.slider("UV Index", 0, 15, 3, key="uv_tab1")
            
            with col_d:
                st.markdown("**Air Quality**")
                pm25 = st.number_input("PM2.5", 0.0, 500.0, 25.0, key="pm25_tab1")
                pm10 = st.number_input("PM10", 0.0, 500.0, 45.0, key="pm10_tab1")
                o3 = st.number_input("O3", 0.0, 300.0, 40.0, key="o3_tab1")
                no2 = st.number_input("NO2", 0.0, 300.0, 10.0, key="no2_tab1")
                so2 = st.number_input("SO2", 0.0, 300.0, 5.0, key="so2_tab1")
                co = st.number_input("CO", 0.0, 5000.0, 200.0, key="co_tab1")
            
            sensitive = st.checkbox("Sensitive (Asthma/Elderly)", key="sensitive_tab1")
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        run_button = st.button("🚀 Analyze My Activity", use_container_width=True, key="analyze_btn")
    
    with right_col:
        if run_button:
            with st.spinner("Analyzing environmental risk..."):
                # Prepare data for ML model
                weather_data = {"temp": temp, "humid": humid, "wind": wind, "uv": uv}
                air_data = {"pm25": pm25, "pm10": pm10, "co": co, "o3": o3, "no2": no2, "so2": so2}
                
                # Get ML risk score
                ml_result = calculate_detailed_environmental_risk(weather_data, air_data)
                risk_score = ml_result["FINAL_SCORE"]
                risk_status = ml_result["STATUS"]
                risk_range = ml_result["RANGE"]
                risk_bias = ml_result["BIAS"]
                
                # Adjust for sensitive individuals
                if sensitive:
                    risk_score = min(100, risk_score + 15)
                    if risk_score >= 80:
                        risk_status = "EXTREME DANGER"
                    elif risk_score >= 65:
                        risk_status = "HIGH RISK"
                    elif risk_score >= 45:
                        risk_status = "MODERATE RISK"
                
                # Create user data for pipeline (with ML risk score as ED)
                user_data = {
                    "Age": age,
                    "HealthCondition": health,
                    "FitnessLevel": fitness,
                    "ActivityType": activity,
                    "DurationMins": duration,
                    "TimeOfDay": tod,
                    "ED": risk_score,  # Use ML score as ED!
                    "sensitive": sensitive
                }
                
                # Create detector output
                detector_output = {
                    "label": "Safe" if risk_score < 45 else "Unsafe",
                    "confidence": 0.85 if risk_score < 45 else 0.90,
                    "reasons": [
                        f"Environmental risk score: {risk_score:.1f}/100",
                        f"Status: {risk_status}",
                        f"Temperature: {temp}°C",
                        f"PM2.5: {pm25}"
                    ]
                }
                
                # Get LLM recommendation
                from transformer.recommender import generate_recommendation
                final_recommendation = generate_recommendation(user_data, detector_output)
            
            # Store for chat
            st.session_state['last_analysis'] = {
                "ED": risk_score,
                "detector": detector_output,
                "final_recommendation": final_recommendation
            }
            
            # Display Risk Score Card
            if risk_score < 30:
                risk_class = "risk-safe"
                risk_icon = "✅"
            elif risk_score < 45:
                risk_class = "risk-safe"
                risk_icon = "ℹ️"
            elif risk_score < 65:
                risk_class = "risk-moderate"
                risk_icon = "⚠️"
            elif risk_score < 80:
                risk_class = "risk-high"
                risk_icon = "⚠️⚠️"
            else:
                risk_class = "risk-danger"
                risk_icon = "🚫"
            
            st.markdown(f'''
            <div class="metric-card">
                <div class="metric-value">{risk_score:.1f}</div>
                <div class="metric-label">Environmental Risk Score (0-100)</div>
            </div>
            <div class="{risk_class}">
                {risk_icon} {risk_status} {risk_icon}<br>
                <small>Risk Range: {risk_range} | Bias: {risk_bias}</small>
            </div>
            ''', unsafe_allow_html=True)
            
            # Safety Assessment
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown('<div class="card-title">⚠️ Safety Assessment</div>', unsafe_allow_html=True)
            
            if risk_score < 30:
                st.success("✅ **LOW RISK** - Environmental conditions are safe for exercise.")
            elif risk_score < 45:
                st.info("ℹ️ **LOW-MODERATE RISK** - Exercise with basic precautions.")
            elif risk_score < 65:
                st.warning("⚠️ **MODERATE RISK** - Limit outdoor exercise duration.")
            elif risk_score < 80:
                st.error("⚠️⚠️ **HIGH RISK** - Avoid outdoor exercise. Consider indoor alternatives.")
            else:
                st.error("🚫 **EXTREME DANGER** - DO NOT exercise outdoors.")
            
            st.markdown(f"""
            **Key Risk Factors:**
            - Temperature: {temp}°C
            - Humidity: {humid}%
            - PM2.5: {pm25} μg/m³
            - UV Index: {uv}
            """)
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Recommendations
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown('<div class="card-title">📋 Recommendations</div>', unsafe_allow_html=True)
            
            recommendations = []
            if risk_score < 30:
                recommendations.append("✅ Safe to exercise outdoors")
                recommendations.append("💧 Stay hydrated")
            elif risk_score < 45:
                recommendations.append("⚠️ Reduce exercise intensity by 25%")
                recommendations.append("💧 Take more frequent breaks")
            elif risk_score < 65:
                recommendations.append("⚠️ Limit outdoor exercise to 15-20 minutes")
                recommendations.append("🏠 Consider indoor alternatives")
                recommendations.append("😷 Wear a mask if exercising outdoors")
            elif risk_score < 80:
                recommendations.append("❌ Avoid outdoor exercise")
                recommendations.append("🏋️ Switch to indoor workouts")
                recommendations.append("💨 Use air purifier if exercising indoors")
            else:
                recommendations.append("🚫 DO NOT exercise outdoors")
                recommendations.append("🏠 Stay indoors with windows closed")
                recommendations.append("💨 Use HEPA air purifier")
            
            if sensitive:
                recommendations.append("🩺 Extra caution needed due to sensitivity")
                if risk_score > 30:
                    recommendations.append("🏠 Recommended to exercise indoors only")
            
            if health == "Asthma" and risk_score > 30:
                recommendations.append("💊 Keep rescue inhaler accessible")
                recommendations.append("🏠 Consider indoor exercise only")
            
            for rec in recommendations:
                st.markdown(f"• {rec}")
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # AI Coach Advice
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown('<div class="card-title">🤖 AI Coach Advice</div>', unsafe_allow_html=True)
            st.info(final_recommendation)
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Show ML details
            with st.expander("📊 Detailed Environmental Analysis"):
                st.json(ml_result)
            
        else:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown('<div class="card-title">📊 Ready for Analysis</div>', unsafe_allow_html=True)
            st.info("👈 Enter your information and click **Analyze My Activity**")
            
            st.markdown("### 🌡️ This analysis uses:")
            st.markdown("""
            - **Machine Learning model** trained on environmental data
            - **Real-time risk assessment** based on:
              - Weather (temperature, humidity, wind, UV)
              - Air quality (PM2.5, PM10, CO, O3, NO2, SO2)
              - User health factors
            - **Personalized recommendations** from AI coach
            """)
            st.markdown('</div>', unsafe_allow_html=True)

# ================================
# TAB 2: Detailed Environmental Risk (Standalone calculator)
# ================================
with tab2:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">🌡️ Detailed Environmental Risk Calculator</div>', unsafe_allow_html=True)
    
    st.markdown("""
    This calculator uses the same ML model as the Activity Analysis tab.
    Enter your local conditions to get a detailed risk assessment.
    """)
    
    col_weather, col_air = st.columns(2)
    
    with col_weather:
        st.markdown("**☁️ Weather Conditions**")
        temp2 = st.number_input("Temperature (°C)", -50.0, 60.0, 22.0, key="temp2")
        humid2 = st.slider("Humidity (%)", 0, 100, 45, key="humid2")
        wind2 = st.slider("Wind (kph)", 0, 100, 10, key="wind2")
        uv2 = st.slider("UV Index", 0, 15, 3, key="uv2")
    
    with col_air:
        st.markdown("**🌫️ Air Quality**")
        pm25_2 = st.number_input("PM2.5", 0.0, 500.0, 25.0, key="pm25_2")
        pm10_2 = st.number_input("PM10", 0.0, 500.0, 45.0, key="pm10_2")
        o3_2 = st.number_input("O3", 0.0, 300.0, 40.0, key="o3_2")
        no2_2 = st.number_input("NO2", 0.0, 300.0, 10.0, key="no2_2")
        so2_2 = st.number_input("SO2", 0.0, 300.0, 5.0, key="so2_2")
        co_2 = st.number_input("CO", 0.0, 5000.0, 200.0, key="co_2")
    
    sensitive2 = st.checkbox("Sensitive (Asthma/Elderly)", key="sensitive2")
    
    if st.button("🌡️ Calculate Risk Score", use_container_width=True, key="calc_btn"):
        with st.spinner("Calculating..."):
            weather_data = {"temp": temp2, "humid": humid2, "wind": wind2, "uv": uv2}
            air_data = {"pm25": pm25_2, "pm10": pm10_2, "co": co_2, "o3": o3_2, "no2": no2_2, "so2": so2_2}
            
            result = calculate_detailed_environmental_risk(weather_data, air_data)
            score = result["FINAL_SCORE"]
            
            if sensitive2:
                score = min(100, score + 15)
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Risk Score", f"{score:.1f}", delta=f"Bias {result.get('BIAS', 0)}")
            col2.markdown(f"### {result['STATUS']}")
            col3.write(f"**Range:** {result.get('RANGE', 'N/A')}")
            
            st.progress(int(min(score, 100)))
            
            recommendation, severity = get_risk_recommendation(score)
            if severity == "danger":
                st.error(recommendation)
            elif severity in ["high", "moderate"]:
                st.warning(recommendation)
            else:
                st.success(recommendation)
            
            with st.expander("📊 Detailed Breakdown"):
                st.json(result)
    
    st.markdown('</div>', unsafe_allow_html=True)

# ================================
# CHAT SECTION
# ================================
st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)

col_title, col_status = st.columns([3, 1])
with col_title:
    st.markdown("### 💬 Ask Your AI Fitness Coach")
with col_status:
    st.caption(f"🤖 Powered by {CHAT_MODEL}")

if 'chat_messages' not in st.session_state:
    st.session_state.chat_messages = []

with st.container():
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    if not st.session_state.chat_messages:
        st.markdown('<div class="assistant-message">👋 Hi! Ask me about your risk assessment, exercise safety, or health concerns!</div>', unsafe_allow_html=True)
    for msg in st.session_state.chat_messages:
        if msg["role"] == "user":
            st.markdown(f'<div class="user-message">👤 {msg["content"]}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="assistant-message">🤖 {msg["content"]}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

col_input, col_send = st.columns([5, 1])
with col_input:
    user_question = st.text_input("Ask a question...", key="chat_input", label_visibility="collapsed")
with col_send:
    send_button = st.button("📤 Send", use_container_width=True)

if st.button("🗑️ Clear Chat", use_container_width=True):
    st.session_state.chat_messages = []
    st.rerun()

if send_button and user_question:
    st.session_state.chat_messages.append({"role": "user", "content": user_question})
    
    context = ""
    if 'last_analysis' in st.session_state:
        last = st.session_state.last_analysis
        context = f"""
        User's Environmental Risk Score: {last.get('ED', 'N/A')}/100
        Safety Status: {last.get('detector', {}).get('label', 'N/A')}
        """
    
    with st.spinner("Thinking..."):
        try:
            prompt = f"""You are a fitness and health advisor. 
            The user's environmental risk score is {context}. 
            Question: {user_question}
            Provide practical, safety-focused advice."""
            
            response = ollama_client.generate(
                model=CHAT_MODEL,
                prompt=prompt,
                options={'temperature': 0.7, 'max_tokens': 500}
            )
            assistant_response = response['response'].strip()
        except Exception as e:
            assistant_response = f"Error: {str(e)}"
    
    st.session_state.chat_messages.append({"role": "assistant", "content": assistant_response})
    st.rerun()

st.markdown('<div class="footer">⚠️ For informational purposes only. Consult a healthcare professional.</div>', unsafe_allow_html=True)