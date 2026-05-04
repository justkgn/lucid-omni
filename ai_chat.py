import streamlit as st
from groq import Groq
import json
import os
import urllib.parse
import random
import warnings
import time
import datetime
import requests
from pypdf import PdfReader
import pandas as pd
from youtube_transcript_api import YouTubeTranscriptApi
from fpdf import FPDF

# Gereksiz uyarıları kapat
warnings.filterwarnings("ignore")

# --- 1. DOSYA VE LOG YÖNETİMİ ---
CHATS_DIR = "chats"
LOG_VISITORS = "ziyaretciler.json"

for folder in [CHATS_DIR]:
    if not os.path.exists(folder):
        os.makedirs(folder)

def ziyaretci_kaydet():
    try:
        # IP ve Konum bilgisini dış servisten alıyoruz
        response = requests.get('http://ip-api.com/json/', timeout=5)
        data = response.json()
        
        yeni_kayit = {
            "ip": data.get("query", "Bilinmiyor"),
            "sehir": data.get("city", "Bilinmiyor"),
            "ulke": data.get("country", "Bilinmiyor"),
            "isp": data.get("isp", "Bilinmiyor"),
            "zaman": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        visits = []
        if os.path.exists(LOG_VISITORS):
            with open(LOG_VISITORS, "r", encoding="utf-8") as f:
                try:
                    visits = json.load(f)
                except: visits = []
        
        # Son kaydı kontrol et (Aynı IP üst üste binmesin)
        if not visits or visits[-1]["ip"] != yeni_kayit["ip"]:
            visits.append(yeni_kayit)
            with open(LOG_VISITORS, "w", encoding="utf-8") as f:
                json.dump(visits, f, ensure_ascii=False, indent=4)
    except:
        pass

def sohbeti_kaydet(chat_id, messages):
    with open(f"{CHATS_DIR}/{chat_id}.json", "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=4)

def sohbetleri_listele():
    return sorted([f.replace(".json", "") for f in os.listdir(CHATS_DIR) if f.endswith(".json")], reverse=True)

# Uygulama başladığında ziyaretçiyi logla
ziyaretci_kaydet()

# --- 2. YARDIMCI ARAÇLAR ---
def gorsel_olustur(prompt):
    seed = random.randint(1, 999999)
    safe_prompt = urllib.parse.quote(prompt)
    return f"https://image.pollinations.ai/prompt/{safe_prompt}?seed={seed}&width=1024&height=1024&model=flux&nologo=true"

def youtube_ozetle(url):
    try:
        v_id = url.split("v=")[1].split("&")[0]
        transcript = YouTubeTranscriptApi.get_transcript(v_id, languages=['tr', 'en'])
        return " ".join([i['text'] for i in transcript])[:5000]
    except: return "Hata: Altyazı çekilemedi."

# --- 3. API BAĞLANTISI ---
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
# --- 4. ARAYÜZ TASARIMI ---
st.set_page_config(page_title="Lucid Omni v7", page_icon="🚀", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    [data-testid="stSidebar"] { background-color: #161b22; }
    .stChatInput { border-radius: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- 5. SESSION STATE ---
if "current_chat" not in st.session_state: st.session_state.current_chat = "Sohbet_Varsayilan"
if "messages" not in st.session_state: 
    path = f"{CHATS_DIR}/{st.session_state.current_chat}.json"
    st.session_state.messages = json.load(open(path, "r")) if os.path.exists(path) else []

# --- 6. YAN PANEL (ADMİN & KONTROL) ---
with st.sidebar:
    st.title("🤖 Lucid Omni")
    
    if st.button("➕ Yeni Sohbet", use_container_width=True):
        st.session_state.current_chat = f"Sohbet_{int(time.time())}"
        st.session_state.messages = []
        sohbeti_kaydet(st.session_state.current_chat, [])
        st.rerun()

    st.divider()
    st.subheader("📂 Sohbet Geçmişi")
    for c in sohbetleri_listele():
        col_c, col_d = st.columns([0.8, 0.2])
        if col_c.button(f"💬 {c[:12]}", key=f"s_{c}", use_container_width=True):
            st.session_state.current_chat = c
            st.session_state.messages = json.load(open(f"{CHATS_DIR}/{c}.json", "r"))
            st.rerun()
        if col_d.button("🗑️", key=f"d_{c}"):
            os.remove(f"{CHATS_DIR}/{c}.json")
            st.rerun()

    st.divider()
    with st.expander("🔐 Admin Paneli"):
        passw = st.text_input("Şifre", type="password")
        if passw == "Lucid2026":
            st.success("Giriş Başarılı")
            if st.button("📊 IP Loglarını Göster"):
                if os.path.exists(LOG_VISITORS):
                    df_log = pd.read_json(LOG_VISITORS)
                    st.dataframe(df_log)
                else: st.info("Kayıt yok.")
            if st.button("🧹 Logları Temizle"):
                if os.path.exists(LOG_VISITORS): os.remove(LOG_VISITORS)
                st.rerun()

# --- 7. ANA PANEL ---
tab1, tab2, tab3, tab4 = st.tabs(["💬 Sohbet", "🖼️ Vision", "🎥 YouTube", "🛠️ Stüdyo"])

with tab1:
    st.subheader(f"Şu anki Sohbet: {st.session_state.current_chat}")
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.markdown(m["content"])
    
    if prompt := st.chat_input("Mesajınızı yazın..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        with st.chat_message("assistant"):
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile", 
                messages=[{"role": "system", "content": "Sen Lucid'sin."}] + st.session_state.messages
            ).choices[0].message.content
            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
            sohbeti_kaydet(st.session_state.current_chat, st.session_state.messages)

with tab2:
    st.header("👁️ Görsel Analiz")
    img_file = st.file_uploader("Resim yükle", type=["png", "jpg", "jpeg"])
    if img_file: st.image(img_file, caption="Analiz edilecek resim")

with tab3:
    st.header("🎥 YouTube Özetleyici")
    yt_url = st.text_input("YouTube Link:")
    if st.button("Özet Çıkar"):
        with st.spinner("İşleniyor..."):
            st.write(youtube_ozetle(yt_url))

with tab4:
    st.header("🛠️ Tasarım Atölyesi")
    c1, c2 = st.columns(2)
    with c1:
        txt = st.text_input("Resim Çiz:")
        if st.button("Çiz"): st.image(gorsel_olustur(txt))
    with c2:
        code = st.text_area("HTML Kod:", "<h1>Merhaba!</h1>")
        st.components.v1.html(code, height=300)