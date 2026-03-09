import streamlit as st
import os, base64, io, uuid
import requests # NEW: Required for the Weather Agent
from datetime import datetime
from openai import OpenAI
import speech_recognition as sr
from gtts import gTTS
from azure.cosmos import CosmosClient
from PIL import Image

# --- 1. PAGE CONFIG & STATE MANAGEMENT ---
st.set_page_config(page_title="KrishivanX Agent", page_icon="🚜", layout="centered")

if 'current_page' not in st.session_state:
    st.session_state.current_page = "landing"

# --- 2. UI STYLING ---
st.markdown("""
    <style>
    .block-container { padding-top: 1.5rem; }
    header {visibility: hidden;}
    .hero-box {
        background: linear-gradient(135deg, #76b900 0%, #ffcc00 100%);
        padding: 40px 20px; border-radius: 20px; text-align: center;
        box-shadow: 0 8px 16px rgba(0,0,0,0.2); margin-bottom: 30px;
    }
    .hero-title { color: #111; font-size: 3.5rem; font-weight: 900; margin-bottom: 0px; line-height: 1.1; }
    .hero-subtitle { color: #222; font-size: 1.3rem; font-weight: 600; margin-top: 10px; }
    .feature-card { background-color: rgba(120, 120, 120, 0.1); padding: 20px; border-radius: 15px; text-align: center; border-bottom: 4px solid #76b900; height: 100%; }
    
    .stButton>button[kind="primary"] { background-color: #111 !important; color: #fff !important; border-radius: 30px; padding: 10px 30px; font-size: 1.2rem; }
    </style>
""", unsafe_allow_html=True)

# --- 3. LANGUAGES ---
LANGUAGES = {
    "English": "en", "Hindi (UP/MP/Bihar)": "hi", "Marathi (Maharashtra)": "mr", "Bengali (West Bengal)": "bn", 
    "Telugu (AP/Telangana)": "te", "Tamil (Tamil Nadu)": "ta", "Gujarati (Gujarat)": "gu", "Punjabi (Punjab)": "pa", 
    "Malayalam (Kerala)": "ml", "Kannada (Karnataka)": "kn", "Odia (Odisha)": "or", "Assamese (Assam)": "as", 
    "Maithili (Bihar)": "mai", "Santali (Jharkhand)": "sat", "Kashmiri (J&K)": "ks", "Nepali (Sikkim)": "ne", 
    "Konkani (Goa)": "kok", "Sindhi": "sd", "Dogri (J&K)": "doi", "Manipuri (Manipur)": "mni", 
    "Bodo (Assam)": "brx", "Urdu": "ur", "Bhojpuri (Bihar/UP)": "hi", "Haryanvi (Haryana)": "hi", "Rajasthani (Rajasthan)": "hi"
}

# --- 4. BACKEND SETUP ---
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN") or st.secrets.get("GITHUB_TOKEN", "")
COSMOS_URI = os.environ.get("COSMOS_URI") or st.secrets.get("COSMOS_URI", "")
COSMOS_KEY = os.environ.get("COSMOS_KEY") or st.secrets.get("COSMOS_KEY", "")

client = OpenAI(base_url="https://models.inference.ai.azure.com", api_key=GITHUB_TOKEN)

container = None
if COSMOS_URI and COSMOS_KEY:
    try:
        cosmos_client = CosmosClient(COSMOS_URI, credential=COSMOS_KEY)
        database = cosmos_client.get_database_client("KrishivanData")
        container = database.get_container_client("ChatHistory")
    except: pass

# --- 4.5 NEW: AGENT DATABASES (Locations & Policies) ---
LOCATION_DB = {
    "Uttar Pradesh": {
        "Kanpur": {"lat": 26.4499, "lon": 80.3319},
        "Lucknow": {"lat": 26.8467, "lon": 80.9462},
        "Varanasi": {"lat": 25.3176, "lon": 82.9739}
    },
    "Punjab": {
        "Ludhiana": {"lat": 30.9010, "lon": 75.8573},
        "Amritsar": {"lat": 31.6340, "lon": 74.8723}
    },
    "Maharashtra": {
        "Pune": {"lat": 18.5204, "lon": 73.8567},
        "Nagpur": {"lat": 21.1458, "lon": 79.0882}
    }
}

POLICY_DB = {
    "Uttar Pradesh": "UP Krishi Yantra Yojana: 50% subsidy on tractors and threshers. Free solar pump scheme active for 2026.",
    "Punjab": "Crop Diversification Scheme: Financial incentives of ₹7,000/acre for shifting from paddy to alternative crops. 80% subsidy on micro-irrigation.",
    "Maharashtra": "Maha-DBT Scheme: Subsidies available for drip irrigation systems and polyhouses. Special drought-relief funds active."
}

# --- 5. CORE FUNCTIONS & AGENT TOOLS ---
def compress_and_encode_image(uploaded_file):
    img = Image.open(uploaded_file)
    img.thumbnail((500, 500)) 
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=80)
    return base64.b64encode(buf.getvalue()).decode('utf-8')

def save_to_db(query, response, itype, img_b64=None):
    if container:
        item = {"id": str(uuid.uuid4()), "userId": "farmer_001", "type": itype, "query": query, "response": response, "image": img_b64, "timestamp": datetime.utcnow().isoformat()}
        try: container.create_item(body=item)
        except: pass

def clear_database():
    if container:
        try:
            items = list(container.query_items("SELECT c.id, c.userId FROM c WHERE c.userId='farmer_001'", enable_cross_partition_query=True))
            for item in items:
                container.delete_item(item=item['id'], partition_key=item['userId'])
        except Exception as e: pass

def text_to_speech(text, lang):
    try:
        tts = gTTS(text=text, lang=lang)
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        return fp.getvalue()
    except: return None

# NEW: Tool for the Agent to fetch live data
@st.cache_data(ttl=600) # Cache for 10 mins so we don't spam the API
def get_advanced_weather(lat, lon):
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m&timezone=auto"
    try:
        response = requests.get(url)
        data = response.json()
        current = data['current']
        return (f"Temperature: {current['temperature_2m']}°C, "
                f"Humidity (Moisture): {current['relative_humidity_2m']}%, "
                f"Rainfall: {current['precipitation']}mm, "
                f"Wind Speed: {current['wind_speed_10m']}km/h")
    except Exception as e:
        return "Live weather data temporarily unavailable."


# --- 6. ROUTING LOGIC ---

# ROUTE A: LANDING PAGE
if st.session_state.current_page == "landing":
    
    st.write("<br>", unsafe_allow_html=True) 
    
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown('<div style="text-align:center;">', unsafe_allow_html=True)
        
        try:
            st.image("Tractor.PNG", width=250) 
        except:
            st.image("https://cdn-icons-png.flaticon.com/512/2153/2153106.png", width=150)
            
        st.markdown('<h1 style="font-size: 3.5rem; font-weight: 900; margin-top: 10px; margin-bottom: 30px;">Welcome to KrishivanX</h1>', unsafe_allow_html=True)
        
        st.markdown("""
            <style>
            div[data-testid="stButton"] > button {
                background-color: #76b900 !important; color: white !important; border-radius: 30px !important;
                padding: 10px 30px !important; font-size: 1.2rem !important; font-weight: bold !important; border: none !important;
            }
            div[data-testid="stButton"] > button:hover { background-color: #8adb00 !important; color: white !important; }
            </style>
        """, unsafe_allow_html=True)
        
        if st.button("Get started", use_container_width=True):
            st.session_state.current_page = "app"
            st.rerun()

    st.write("<br>", unsafe_allow_html=True)
    st.write("<br>", unsafe_allow_html=True)
    f1, f2, f3 = st.columns(3)
    with f1: st.markdown('<div class="feature-card"><h3>📷</h3><b>Visual Scan</b><br><small>Detect crop diseases instantly.</small></div>', unsafe_allow_html=True)
    with f2: st.markdown('<div class="feature-card"><h3>🎙️</h3><b>Voice AI Agent</b><br><small>Ask questions in your local language.</small></div>', unsafe_allow_html=True)
    with f3: st.markdown('<div class="feature-card"><h3>🗄️</h3><b>Cloud DB</b><br><small>Securely save your farm history.</small></div>', unsafe_allow_html=True)
            
    st.markdown('</div>', unsafe_allow_html=True)

# ROUTE B: MAIN APPLICATION
elif st.session_state.current_page == "app":
    
    # --- TOP NAVIGATION BAR ---
    nav1, nav2, nav3, nav4 = st.columns([2.5, 1, 1, 1.5])
    with nav1: st.markdown("### 🌿 KrishivanX Agent")
    with nav2:
        if st.button("🏠 Home", use_container_width=True):
            st.session_state.current_page = "landing"
            st.rerun()
    with nav3:
        if st.button("🔄 Restart", use_container_width=True):
            with st.spinner("Erasing cloud records..."):
                clear_database()
            st.session_state.clear()
            st.session_state.current_page = "landing"
            st.rerun()
    with nav4:
        sel_lang = st.selectbox("Language", list(LANGUAGES.keys()), label_visibility="collapsed")
        l_code = LANGUAGES[sel_lang]
        
    st.write("---")

    # --- NEW: GLOBAL FARM CONTEXT (For Agent) ---
    st.markdown("##### 📍 Local Farm Context")
    ctx1, ctx2, ctx3 = st.columns(3)
    with ctx1: state = st.selectbox("State", options=list(LOCATION_DB.keys()))
    with ctx2: city = st.selectbox("City/District", options=list(LOCATION_DB[state].keys()))
    with ctx3: crop = st.text_input("Target Crop", value="Wheat")

    # The Agent autonomously fetches this data in the background
    coords = LOCATION_DB[state][city]
    live_weather = get_advanced_weather(coords['lat'], coords['lon'])
    state_policy = POLICY_DB.get(state, "No specific state policies listed.")

    # Show the judges what the agent is seeing
    with st.expander("📡 See what the AI Agent knows about your farm right now"):
        st.info(f"**Live Weather ({city}):** {live_weather}\n\n**Active Policies ({state}):** {state_policy}")

    st.write("---")

    # --- MAIN TABS ---
    tab1, tab2, tab3 = st.tabs(["📷 Crop Scanner", "🎙️ Agent Advisory", "🗄️ My Records"])

    # TAB 1: VISION 
    with tab1:
        up_img = st.file_uploader("Upload a clear photo of the infected leaf", type=["jpg", "png", "jpeg"])
        if up_img and st.button("Run Agent Diagnostics"):
            with st.spinner("Analyzing cell structure & cross-referencing local conditions..."):
                b64_compressed = compress_and_encode_image(up_img)
                
                # NEW: Context Injected Prompt
                sys_prompt = f"""You are KrishiVanX, a highly advanced agricultural AI agent advising a farmer. 
                Analyze the image and provide a highly detailed 100 to 150-word report in {sel_lang}.
                
                [LIVE AGENT CONTEXT]
                - Location: {city}, {state}
                - Target Crop: {crop}
                - Current Live Weather: {live_weather}
                - Active State Subsidies/Policies: {state_policy}
                
                Strictly use this markdown format:
                **Disease:** [Name of the disease]
                **Weather Impact:** [Explain if current temp/humidity is making it worse]
                **Organic/Home Remedy:** [Detailed steps for basic organic treatment]
                **Chemical Remedy:** [Specific chemical names and dosage]
                **Govt Scheme:** [Reference the Active State Policy provided above if relevant, or general scheme]
                **Documents Needed:** [2-3 required documents]
                """
                
                try:
                    resp = client.chat.completions.create(
                        model="gpt-4o",
                        messages=[{"role": "system", "content": sys_prompt},
                                  {"role": "user", "content": [{"type": "text", "text": "Diagnose this thoroughly considering my weather:"}, 
                                                               {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_compressed}"}}]}]
                    )
                    ans = resp.choices[0].message.content
                    st.success("Comprehensive Agent Diagnosis Complete")
                    st.markdown(ans)
                    
                    audio_bytes = text_to_speech(ans, l_code)
                    if audio_bytes: st.audio(audio_bytes, format="audio/mp3")
                    
                    save_to_db("Detailed Visual Diagnosis", ans, "Scanner", b64_compressed)
                except Exception as e: st.error(f"Diagnosis failed. Check API key. Error: {e}")

    # TAB 2: VOICE ASSISTANT
    with tab2:
        aud = st.audio_input("Tap to ask about your crop, weather, or government schemes")
        
        if aud and st.button("Consult AI Agent"):
            with st.spinner("Transcribing and synthesizing live data..."):
                r = sr.Recognizer()
                try:
                    with sr.AudioFile(io.BytesIO(aud.getvalue())) as src:
                        q = r.recognize_google(r.record(src), language=l_code)
                    
                    st.info(f"You asked: {q}")
                    
                    # NEW: Context Injected Prompt
                    sys_prompt = f"""You are KrishiVanX, a highly advanced agricultural AI agent advising a farmer. 
                    Analyze the user's query and provide a detailed 100 to 150-word action plan in {sel_lang}.
                    
                    [LIVE AGENT CONTEXT]
                    - Location: {city}, {state}
                    - Target Crop: {crop}
                    - Current Live Weather: {live_weather}
                    - Active State Subsidies/Policies: {state_policy}
                    
                    Strictly use this markdown format:
                    **Core Problem:** [Identify the issue/need]
                    **Immediate Action:** [Provide advice based SPECIFICALLY on the provided Live Weather]
                    **Relevant Govt Scheme:** [Use the provided State Policies if applicable]
                    **Where to Go & Who to Meet:** [Specify the exact local office]
                    **Documents Required:** [List 3-4 essential documents]
                    """
                    
                    resp = client.chat.completions.create(
                        model="gpt-4o",
                        messages=[{"role": "system", "content": sys_prompt}, {"role": "user", "content": q}]
                    )
                    ans = resp.choices[0].message.content
                    st.markdown(ans)
                    
                    audio_bytes = text_to_speech(ans, l_code)
                    if audio_bytes: st.audio(audio_bytes, format="audio/mp3")
                    
                    save_to_db(q, ans, "Audio", None)
                except sr.UnknownValueError: st.error("Could not understand the audio. Please try again.")

    # TAB 3: HISTORY 
    with tab3:
        if st.button("Sync Cloud Records"):
            if container:
                try:
                    items = list(container.query_items("SELECT * FROM c WHERE c.userId='farmer_001' ORDER BY c.timestamp DESC", enable_cross_partition_query=True))
                    if not items: st.info("No records found.")
                    
                    for it in items:
                        with st.container(border=True): 
                            st.caption(f"**Type:** {it['type']} | **Date:** {it['timestamp'][:10]}")
                            st.markdown(f"**Q:** {it['query']}")
                            
                            if it.get("image"):
                                img_col, text_col = st.columns([1, 2.5])
                                with img_col:
                                    st.image(base64.b64decode(it["image"]), use_container_width=True)
                                with text_col:
                                    st.markdown(f"**A:**\n{it['response']}")
                            else:
                                st.markdown(f"**A:**\n{it['response']}")
                                
                except Exception as e: st.error(f"Failed to fetch records: {e}")

            else: st.warning("Database connection is missing.")
