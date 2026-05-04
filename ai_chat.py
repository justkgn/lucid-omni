import streamlit as st
from groq import Groq
import json
import os
import urllib.parse
import random
import time
import datetime
import requests
from youtube_transcript_api import YouTubeTranscriptApi

# --- 1. KULLANICI KİMLİĞİ VE DOSYA SİSTEMİ ---
if "user_id" not in st.session_state:
    st.session_state.user_id = f"User_{random.randint(10000, 99999)}"

# Klasörleri oluştur
CHATS_BASE_DIR = "chats"
USER_CHATS_DIR = f"{CHATS_BASE_DIR}/{st.session_state.user_id}"
LOG_VISITORS = "ziyaretciler.json"

for path in [CHATS_BASE_DIR, USER_CHATS_DIR]:
    if not os.path.exists(path):
        os.makedirs(path)

# --- 2. LOGLAMA VE YARDIMCI FONKSİYONLAR ---
def ziyaretci_kaydet():
    try:
        response = requests.get('http://ip-api.com/json/', timeout=5)
        data = response.json()
        yeni_kayit = {
            "user_id": st.session_state.user_id,
            "ip": data.get("query", "Bilinmiyor"),
            "konum": f"{data.get('city')}, {data.get('country')}",
            "zaman": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        visits = []
        if os.path.exists(LOG_VISITORS):
            with open(LOG_VISITORS, "r", encoding="utf-8") as f:
                try: visits = json.load(f)
                except: visits = []
        visits.append(yeni_kayit)
        with open(LOG_VISITORS, "w", encoding="utf-8") as f:
            json.dump(visits, f, ensure_ascii=False, indent=4)
    except: pass

def sohbeti_kaydet(chat_id, messages):
    with open(f"{USER_CHATS_DIR}/{chat_id}.json", "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=4)

def sohbetleri_listele():
    return sorted([f.replace(".json", "") for f in os.listdir(USER_CHATS_DIR) if f.endswith(".json")], reverse=True)

# Uygulama açılışında bir kez logla
if "logged" not in st.session_state:
    ziyaretci_kaydet()
    st.session_state.logged = True

# --- 3. API BAĞLANTISI ---
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    client = Groq(api_key="BURAYA_GROQ_ANAHTARINI_YAZ")

# --- 4. ARAYÜZ AYARLARI ---
st.set_page_config(page_title="Lucid Omni", page_icon="🚀", layout="wide")

# --- 5. SESSION STATE BAŞLATMA ---
if "current_chat" not in st.session_state:
    st.session_state.current_chat = "Sohbet_Basla"

if "messages" not in st.session_state:
    path = f"{USER_CHATS_DIR}/{st.session_state.current_chat}.json"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            st.session_state.messages = json.load(f)
    else:
        st.session_state.messages = []

# --- 6. YAN PANEL (SIDEBAR) ---
with st.sidebar:
    st.title("🤖 Lucid Omni")
    st.caption(f"Senin Kimliğin: {st.session_state.user_id}")
    
    if st.button("➕ Yeni Sohbet Başlat", use_container_width=True):
        new_id = f"Sohbet_{random.randint(10000, 99999)}"
        st.session_state.current_chat = new_id
        st.session_state.messages = []
        sohbeti_kaydet(new_id, [])
        st.rerun()

    st.divider()
    st.subheader("📂 Senin Sohbetlerin")
    for c in sohbetleri_listele():
        col_chat, col_del = st.columns([0.8, 0.2])
        if col_chat.button(f"💬 {c[:12]}", key=f"btn_{c}", use_container_width=True):
            st.session_state.current_chat = c
            with open(f"{USER_CHATS_DIR}/{c}.json", "r", encoding="utf-8") as f:
                st.session_state.messages = json.load(f)
            st.rerun()
        if col_del.button("🗑️", key=f"del_{c}"):
            os.remove(f"{USER_CHATS_DIR}/{c}.json")
            st.rerun()

    st.divider()
    with st.expander("🔐 Admin Paneli"):
        if st.text_input("Şifre", type="password") == "Lucid2026":
            if st.button("📊 Ziyaretçileri Gör"):
                if os.path.exists(LOG_VISITORS):
                    st.table(json.load(open(LOG_VISITORS)))
            st.write("Klasörler:", os.listdir(CHATS_BASE_DIR))

# --- 7. ANA PANEL ---
st.title(f"🚀 Lucid Omni - {st.session_state.current_chat}")

tab_chat, tab_vision, tab_yt, tab_studio = st.tabs(["💬 Sohbet", "👁️ Vision", "🎥 YouTube", "🛠️ Stüdyo"])

with tab_chat:
    # Mesajları göster
    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])
    
    # Giriş alanı
    if prompt := st.chat_input("Lucid'e bir şey sor..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            res = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "system", "content": "Sen Lucid'sin."}] + st.session_state.messages
            )
            response = res.choices[0].message.content
            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
            sohbeti_kaydet(st.session_state.current_chat, st.session_state.messages)

with tab_vision:
    st.info("Bu sekme çok yakında görsel analiz için aktif olacak.")

with tab_yt:
    yt_url = st.text_input("Video URL:")
    if st.button("Analiz Et"):
        st.warning("YouTube altyazı servisi şu an meşgul, lütfen sonra tekrar deneyin.")

with tab_studio:
    st.subheader("HTML Önizleme")
    code = st.text_area("Kodunu yaz:", "<h1>Merhaba</h1>")
    st.components.v1.html(code, height=300)
