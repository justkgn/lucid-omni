import streamlit as st
from groq import Groq
import json
import os
import urllib.parse
import random
import time
import datetime
import requests

# --- 1. KULLANICI KİMLİĞİ VE DOSYA YÖNETİMİ ---
# Her tarayıcı/kullanıcı için benzersiz bir ID oluşturur
if "user_id" not in st.session_state:
    # Kullanıcıyı cihazından tanımak için rastgele bir ID atıyoruz
    st.session_state.user_id = f"User_{random.randint(10000, 99999)}"

# Kullanıcıya özel klasör yolu
USER_CHATS_DIR = f"chats/{st.session_state.user_id}"
if not os.path.exists(USER_CHATS_DIR):
    os.makedirs(USER_CHATS_DIR)

LOG_VISITORS = "ziyaretciler.json"

def ziyaretci_kaydet():
    try:
        response = requests.get('http://ip-api.com/json/', timeout=5)
        data = response.json()
        yeni_kayit = {
            "user_id": st.session_state.user_id, # Kimin hangi IP ile geldiğini eşleştirir
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

ziyaretci_kaydet()

# --- 2. SOHBET FONKSİYONLARI (KULLANICIYA ÖZEL) ---
def sohbeti_kaydet(chat_id, messages):
    with open(f"{USER_CHATS_DIR}/{chat_id}.json", "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=4)

def sohbetleri_listele():
    # Sadece aktif kullanıcının klasöründeki dosyaları getirir
    return sorted([f.replace(".json", "") for f in os.listdir(USER_CHATS_DIR) if f.endswith(".json")], reverse=True)

# --- 3. API VE ARAYÜZ ---
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    client = Groq(api_key="GROQ_API_KEY")

st.set_page_config(page_title="Lucid Omni v8", page_icon="🚀", layout="wide")

# --- 4. YAN PANEL ---
with st.sidebar:
    st.title("🤖 Lucid Omni")
    st.caption(f"Senin Kimliğin: {st.session_state.user_id}")
    
    if st.button("➕ Yeni Sohbet Başlat", use_container_width=True):
        st.session_state.current_chat = f"Sohbet_{int(time.time())}"
        st.session_state.messages = []
        sohbeti_kaydet(st.session_state.current_chat, [])
        st.rerun()

    st.divider()
    st.subheader("📂 Senin Sohbetlerin")
    my_chats = sohbetleri_listele()
    for c in my_chats:
        col_c, col_d = st.columns([0.8, 0.2])
        if col_c.button(f"💬 {c[:12]}", key=f"s_{c}", use_container_width=True):
            st.session_state.current_chat = c
            with open(f"{USER_CHATS_DIR}/{c}.json", "r", encoding="utf-8") as f:
                st.session_state.messages = json.load(f)
            st.rerun()
        if col_d.button("🗑️", key=f"d_{c}"):
            os.remove(f"{USER_CHATS_DIR}/{c}.json")
            st.rerun()

    st.divider()
    with st.expander("🔐 Admin Paneli"):
        if st.text_input("Şifre", type="password") == "Lucid2026":
            if st.button("📊 Tüm Kullanıcıları Gör"):
                if os.path.exists(LOG_VISITORS):
                    st.table(json.load(open(LOG_VISITORS)))
            
            st.write("📂 Sunucu Klasör Yapısı:")
            # Admin olarak hangi kullanıcı klasörleri olduğunu görebilirsin
            st.write(os.listdir("chats"))

# --- 5. ANA PANEL (SOHBET AKIŞI) ---
if "current_chat" not in st.session_state:
    st.session_state.current_chat = "Sohbet_Baslangic"
    if not os.path.exists(f"{USER_CHATS_DIR}/Sohbet_Baslangic.json"):
        sohbeti_kaydet("Sohbet_Baslangic", [])

if "messages" not in st.session_state:
    with open(f"{USER_CHATS_DIR}/{st.session_state.current_chat}.json", "r", encoding="utf-8") as f:
        st.session_state.messages = json.load(f)

# (Sohbet arayüzü ve diğer sekmeler v7 ile aynı şekilde devam eder...)
# Not: tab1, tab2 vb. kısımları v7'den buraya aynen kopyalayabilirsin.
