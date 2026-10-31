#!/usr/bin/env python3
"""
🎬 YouTube AI Studio — Master Web Control Dashboard
Barcha video turlarini (Faktlar, 2D Animatsiya, Shorts, Motivatsiya)
bitta zamonaviy veb studiyadan yaratish va YouTube kanallariga yuklash.
"""

import glob
import json
import os
import subprocess
import sys
import time
from pathlib import Path
import streamlit as st

import channel_manager
import topics_database

st.set_page_config(
    page_title="YouTube AI Studio",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Zamonaviy premium Dark UI dizayni
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    
    .stApp {
        background: radial-gradient(circle at 10% 20%, #0d111a 0%, #07090e 100%);
        color: #e2e8f0;
    }
    
    .studio-header {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.9) 100%);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 18px;
        padding: 24px 32px;
        margin-bottom: 24px;
        box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.5);
    }
    
    .studio-title {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(135deg, #ff4b4b 0%, #ff8a00 50%, #e11d48 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 6px;
    }
    
    .studio-desc {
        color: #94a3b8;
        font-size: 1.05rem;
    }
    
    .status-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        background: rgba(34, 197, 94, 0.15);
        color: #4ade80;
        border: 1px solid rgba(74, 222, 128, 0.3);
        margin-right: 8px;
    }
    
    .card-box {
        background: rgba(30, 41, 59, 0.4);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 14px;
        padding: 18px 22px;
        margin-bottom: 16px;
    }
    
    .terminal-box {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.82rem;
        background: #05070a !important;
        border: 1px solid #1e293b !important;
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)

# Sarlavha
st.markdown("""
<div class="studio-header">
    <div class="studio-title">🎬 YouTube AI Studio Pro</div>
    <div class="studio-desc">Sun'iy intellekt yordamida to'liq avtomatik video generatsiya va YouTube kanallariga yuklash tizimi</div>
    <div style="margin-top: 14px;">
        <span class="status-badge">⚡ Gemini AI 2026</span>
        <span class="status-badge">🔊 Edge-TTS HD</span>
        <span class="status-badge">🎞️ Pixabay API</span>
        <span class="status-badge">🔴 YouTube OAuth v3</span>
    </div>
</div>
""", unsafe_allow_html=True)

tab_create, tab_gallery, tab_channels, tab_diagnostics = st.tabs([
    "🚀 Video Generator",
    "📺 Video Galereyasi & Pleyer",
    "🔴 YouTube Kanallari",
    "⚙️ Tizim & Diagnostika",
])

# =====================================================================
# TAB 1: VIDEO GENERATOR
# =====================================================================
with tab_create:
    col_left, col_right = st.columns([1.1, 0.9])

    with col_left:
        st.markdown("### 1. Video Yo'nalishi va Format")
        genre = st.radio(
            "Video yo'nalishini tanlang:",
            (
                "🌌 Kosmik & Dunyo Faktlari (16:9 Hujjatli film)",
                "📖 2D Animatsion Hikoyalar (Day One uslubi - 16:9)",
                "⚡ Viral YouTube Shorts (9:16 Vertikal - Shorts & Reels)",
                "🏛️ Falsafa va Kuchli Motivatsiya (Stoisizm & Intizom)",
            ),
            index=0,
        )

        st.markdown("### 2. Til va Ovoz")
        c_lang, c_voice = st.columns(2)
        with c_lang:
            lang = st.selectbox(
                "Video tili:",
                ["uz", "en", "ru", "tr"],
                format_func=lambda x: {
                    "uz": "🇺🇿 O'zbek tili (uz)",
                    "en": "🇬🇧 Ingliz tili (en)",
                    "ru": "🇷🇺 Rus tili (ru)",
                    "tr": "🇹🇷 Turk tili (tr)",
                }[x],
            )

        with c_voice:
            voice_options = {
                "uz": ["uz-UZ-SardorNeural (Erkak)", "uz-UZ-MadinaNeural (Ayol)"],
                "en": ["en-US-ChristopherNeural (Chuqur/Erkak)", "en-US-GuyNeural (Energetik)", "en-US-AriaNeural (Ayol)"],
                "ru": ["ru-RU-DmitryNeural (Erkak)", "ru-RU-SvetlanaNeural (Ayol)"],
                "tr": ["tr-TR-AhmetNeural (Erkak)", "tr-TR-EmelNeural (Ayol)"],
            }
            selected_voice_label = st.selectbox("Diktor ovozi:", voice_options[lang])
            voice_code = selected_voice_label.split(" ")[0]

        # Janr identifikatori va mos sozlamalar
        if "2D Animatsion" in genre:
            genre_id = "story"
            default_acc_idx = 0  # jasuryurak6@gmail.com
        elif "Shorts" in genre:
            genre_id = "shorts"
            default_acc_idx = 1  # youtubekanal0004@gmail.com
        elif "Motivatsiya" in genre:
            genre_id = "motivation"
            default_acc_idx = 0  # jasuryurak6@gmail.com
        else:
            genre_id = "facts"
            default_acc_idx = 1  # youtubekanal0004@gmail.com

        st.markdown("### 3. Mavzu (Topic)")
        
        # Tanlangan janr va til uchun alohida 120+ saralangan toza mavzular
        genre_topics = topics_database.get_topics_for_genre(genre_id, lang=lang)
        state_topic_key = f"custom_topic_{genre_id}"

        # Boshlang'ich qiymatni o'rnatish
        if state_topic_key not in st.session_state or not str(st.session_state[state_topic_key]).strip():
            st.session_state[state_topic_key] = genre_topics[0]

        col_t1, col_t2 = st.columns([0.60, 0.40])
        with col_t2:
            if st.button("🎲 Tasodifiy Mavzu", use_container_width=True, key=f"rnd_btn_{genre_id}"):
                import random
                st.session_state[state_topic_key] = random.choice(genre_topics)
                st.rerun()
        with col_t1:
            st.caption(f"📚 Ushbu yo'nalish uchun **{len(genre_topics)} ta** saralangan toza mavzular mavjud")

        with st.expander(f"📋 100+ mavzular katalogidan tanlash ({len(genre_topics)} ta)", expanded=False):
            catalog_options = ["-- Ro'yxatdan mavzu tanlang --"] + genre_topics
            current_val = st.session_state.get(state_topic_key, "")
            sel_idx = catalog_options.index(current_val) if current_val in catalog_options else 0

            def on_catalog_select():
                picked = st.session_state.get(f"catalog_select_{genre_id}")
                if picked and picked != "-- Ro'yxatdan mavzu tanlang --":
                    st.session_state[state_topic_key] = picked

            st.selectbox(
                "Katalogdan tanlang (matn maydoniga tushadi):",
                catalog_options,
                index=sel_idx,
                key=f"catalog_select_{genre_id}",
                on_change=on_catalog_select,
            )

        topic = st.text_area(
            "Maxsus mavzu kiriting (yoki yuqoridagi tugmani bosing):",
            key=state_topic_key,
            height=85,
            help="O'zingiz xohlagan maxsus mavzuni yozing yoki yuqoridagi '🎲 Tasodifiy Mavzu' tugmasi yoxud 100+ katalogdan tanlang.",
        )


    with col_right:
        st.markdown("### 4. YouTube Kanal (Gmail Hisobi)")

        account_choices = [
            "jasuryurak6@gmail.com",
            "youtubekanal0004@gmail.com",
            "Boshqa Gmail hisobi",
        ]

        def format_acc(acc):
            if acc == "jasuryurak6@gmail.com":
                return "📖 jasuryurak6@gmail.com (2D Animatsion Hikoyalar kanali)"
            elif acc == "youtubekanal0004@gmail.com":
                return "🌌 youtubekanal0004@gmail.com (Kosmik & Dunyo Faktlari kanali)"
            return "➕ Boshqa maxsus Gmail hisobi"

        selected_acc_choice = st.selectbox(
            "Qaysi Gmail dagi YouTube kanalga yuklansin?",
            account_choices,
            index=default_acc_idx,
            format_func=format_acc,
            help="Videoni qaysi Gmail hisobingizdagi YouTube kanalga yuklashni tanlang",
        )

        if selected_acc_choice == "Boshqa Gmail hisobi":
            custom_gmail_input = st.text_input("Gmail manzilingizni kiriting:", placeholder="masalan: kanalim@gmail.com")
            target_gmail_to_use = custom_gmail_input.strip() if custom_gmail_input.strip() else "jasuryurak6@gmail.com"
        else:
            target_gmail_to_use = selected_acc_choice

        target_token, _ = channel_manager.resolve_account_info(target_gmail_to_use)
        is_active = channel_manager.is_account_active(target_token)

        if is_active:
            st.markdown(f'<div style="padding: 8px 14px; border-radius: 8px; background: rgba(34,197,94,0.15); border: 1px solid rgba(74,222,128,0.3); color: #4ade80; margin-bottom: 12px;">🟢 <b>{target_gmail_to_use}</b> hisobiga yuklashga 100% tayyor!</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div style="padding: 8px 14px; border-radius: 8px; background: rgba(234,179,8,0.15); border: 1px solid rgba(250,204,21,0.3); color: #facc15; margin-bottom: 12px;">⚪ <b>{target_gmail_to_use}</b> uchun hali Google ruxsati berilmagan.</div>', unsafe_allow_html=True)
            if st.button(f"🔑 {target_gmail_to_use} bilan tizimga kirish"):
                with st.spinner(f"Brauzerda {target_gmail_to_use} tanlanishi kutilmoqda..."):
                    creds = channel_manager.get_credentials(target_token, login_hint=target_gmail_to_use, interactive=True)
                    if creds and creds.valid:
                        st.success("🎉 Ruxsat muvaffaqiyatli olindi!")
                        st.rerun()

        c_priv, c_clip = st.columns(2)
        with c_priv:
            privacy = st.selectbox(
                "Maxfiylik darajasi:",
                ["public", "unlisted", "private"],
                format_func=lambda x: {"public": "🟢 Hammaga ochiq", "unlisted": "🟡 Faqat havola", "private": "🔒 Yopiq"}[x],
            )
        with c_clip:
            no_upload = st.checkbox("💾 Faqat diskka saqlash (YouTube'ga yuklamasdan)", value=False)

        force_login = st.checkbox("🔄 Ushbu Gmail uchun qaytadan Google login qilish")

        if "2D Animatsion" in genre:
            story_orientation = st.radio("Animatsiya formati:", ["16:9 Gorizontal (Keng video)", "9:16 Vertikal (YouTube Shorts)"], index=0)
        elif "Shorts" in genre:
            shorts_engine = st.radio("Shorts uslubi:", ["📖 2D Animatsion Hikoyalar (Day One uslubi)", "⚡ Dinamik Stock Footage (Pixabay)"], index=0)
        elif "Motivatsiya" in genre:
            moti_orientation = st.radio("Motivatsiya formati:", ["16:9 Gorizontal (Keng)", "9:16 Vertikal (Shorts)"], index=0)

        st.write("---")
        run_btn = st.button("🚀 Videoni Yaratish va Kanalga Yuklash", type="primary", use_container_width=True)

    # Ishga tushirish qismi
    if run_btn:
        st.write("---")
        status_bar = st.progress(0, text="Tayyorgarlik ko'rilmoqda...")
        log_box = st.empty()

        # Skript va formatni aniqlaymiz
        is_vertical = False
        if "2D Animatsion" in genre:
            script_name = "story_animation_agent.py"
            if "9:16" in story_orientation:
                is_vertical = True
        elif "Shorts" in genre:
            if "2D Animatsiya" in shorts_engine:
                script_name = "story_animation_agent.py"
                is_vertical = True
            else:
                script_name = "shorts_generator.py"
        elif "Motivatsiya" in genre:
            script_name = "motivation_agent.py"
            if "9:16" in moti_orientation:
                is_vertical = True
        else:
            script_name = "youtube_facts_agent.py"

        # Force login
        if force_login and os.path.exists(target_token):
            try:
                os.remove(target_token)
                st.warning(f"'{target_token}' o'chirildi. Yangi ruxsat talab qilinadi.")
            except Exception as e:
                st.error(f"Fayl o'chirish xatosi: {e}")

        cmd = [
            sys.executable, script_name,
            "--lang", lang,
            "--voice", voice_code,
            "--privacy", privacy,
            "--gmail", target_gmail_to_use,
            "--token-file", target_token,
        ]
        if topic.strip():
            cmd.extend(["--topic", topic.strip()])
        if no_upload:
            cmd.append("--no-upload")
        if is_vertical:
            cmd.append("--vertical")


        full_logs = ""
        start_time = time.time()

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                encoding="utf-8",
                errors="replace",
            )

            for line in iter(process.stdout.readline, ""):
                full_logs += line
                log_box.code(full_logs[-1600:], language="bash")
                
                if "[1/" in line:
                    status_bar.progress(20, text="⏳ 1-bosqich: Ssenariy yozilmoqda...")
                elif "[2/" in line:
                    status_bar.progress(40, text="⏳ 2-bosqich: Diktor ovozi sintez qilinmoqda...")
                elif "[3/" in line:
                    status_bar.progress(60, text="⏳ 3-bosqich: Musiqa va fon birlashtirilmoqda...")
                elif "[4/" in line:
                    status_bar.progress(75, text="⏳ 4-bosqich: Kadrlar tayyorlanmoqda...")
                elif "[5/" in line:
                    status_bar.progress(90, text="⏳ 5-bosqich: FFmpeg montaj qilinmoqda...")
                elif "[6/" in line or "YouTube kanalga yuklanmoqda" in line:
                    status_bar.progress(95, text="⏳ 6-bosqich: YouTube kanalga yuklanmoqda...")

            process.stdout.close()
            ret_code = process.wait()
            elapsed = int(time.time() - start_time)

            if ret_code == 0:
                status_bar.progress(100, text="🎉 Muvaffaqiyatli yakunlandi!")
                st.success(f"Video tayyor bo'ldi! Vaqt: {elapsed // 60}m {elapsed % 60}s")
                for line in full_logs.splitlines():
                    if "youtube.com/watch" in line:
                        st.balloons()
                        url_part = line.split("youtube.com/watch")[1].strip().replace(")", "").replace("]", "")
                        clean_yt = f"https://www.youtube.com/watch{url_part}"
                        st.markdown(f"### 👉 [Videoni YouTube'da Ko'rish]({clean_yt})")
            else:
                status_bar.progress(100, text="❌ Xatolik yuz berdi")
                st.error("Jarayon xatolik bilan tugadi. Yuqoridagi loglarni ko'ring.")

        except Exception as exc:
            st.error(f"Xatolik: {exc}")


# =====================================================================
# TAB 2: VIDEO GALEREYA VA PLEYER
# =====================================================================
with tab_gallery:
    st.markdown("### 📺 Barcha Yaratilgan Videolar")
    video_dirs = sorted(glob.glob("output_videos/*"), key=os.path.getmtime, reverse=True)
    
    valid_videos = []
    for vd in video_dirs:
        mp4_files = glob.glob(f"{vd}/*.mp4")
        # Final / asosiy videoni topamiz
        main_mp4 = [m for m in mp4_files if "final_" in m or "shorts_" in m or "motivation_" in m]
        if main_mp4:
            meta_path = Path(vd) / "metadata.json"
            meta = {}
            if meta_path.exists():
                try:
                    meta = json.loads(meta_path.read_text(encoding="utf-8"))
                except Exception:
                    pass
            valid_videos.append({
                "dir": vd,
                "video_file": main_mp4[0],
                "title": meta.get("title", Path(main_mp4[0]).stem),
                "desc": meta.get("description", ""),
                "time": time.ctime(os.path.getmtime(main_mp4[0])),
                "size_mb": round(os.path.getsize(main_mp4[0]) / (1024 * 1024), 1),
                "metadata": meta,
            })

    if not valid_videos:
        st.info("Hozircha saqlangan videolar yo'q. 'Video Generator' bo'limidan birinchi videoni yarating!")
    else:
        v_col1, v_col2 = st.columns([0.65, 0.35])
        
        with v_col2:
            st.markdown(f"**Jami videolar:** {len(valid_videos)} ta")
            selected_idx = st.selectbox(
                "Tomosha qilish uchun tanlang:",
                range(len(valid_videos)),
                format_func=lambda i: f"[{valid_videos[i]['size_mb']}MB] {valid_videos[i]['title'][:40]}",
            )
            cur = valid_videos[selected_idx]
            st.write(f"📅 **Yaratilgan vaqt:** {cur['time']}")
            st.write(f"💾 **Fayl hajmi:** {cur['size_mb']} MB")
            st.write(f"📂 **Fayl yo'li:** `{cur['video_file']}`")
            if cur['desc']:
                st.caption(f"📝 {cur['desc']}")

            # Yuklab olish tugmasi
            with open(cur['video_file'], "rb") as f:
                st.download_button(
                    label="📥 Videoni Yuklab Olish (MP4)",
                    data=f,
                    file_name=Path(cur['video_file']).name,
                    mime="video/mp4",
                    use_container_width=True,
                )

            st.write("---")
            st.markdown("#### 🚀 Ushbu Videoni YouTube'ga Yuklash")
            gal_acc_choices = ["jasuryurak6@gmail.com", "youtubekanal0004@gmail.com"]
            target_up_gmail = st.selectbox(
                "Qaysi Gmail dagi kanalga yuklansin?",
                gal_acc_choices,
                format_func=lambda x: "📖 jasuryurak6@gmail.com (2D Hikoyalar)" if "jasur" in x else "🌌 youtubekanal0004@gmail.com (Faktlar)",
                key="gal_gmail_choice",
            )
            up_privacy = st.selectbox("Maxfiylik darajasi:", ["public", "unlisted", "private"], key="gal_priv")
            
            if st.button("🔴 YouTube'ga Yuklashni Boshlash", type="primary", use_container_width=True):
                target_up_token, _ = channel_manager.resolve_account_info(target_up_gmail)
                with st.spinner(f"YouTube'ga yuklanmoqda ({target_up_gmail})..."):
                    try:
                        yt_link = channel_manager.upload_video_to_youtube(
                            video_path=Path(cur['video_file']),
                            metadata=cur['metadata'] or {"title": cur['title']},
                            token_file=target_up_token,
                            login_hint=target_up_gmail,
                            privacy_status=up_privacy,
                        )
                        st.success(f"Video yuklandi: [Ko'rish]({yt_link})")
                        st.balloons()
                    except Exception as e:
                        st.error(f"Yuklashda xato: {e}")

        with v_col1:
            st.markdown(f"#### 🎬 {cur['title']}")
            st.video(cur['video_file'])


# =====================================================================
# TAB 3: YOUTUBE KANALLAR
# =====================================================================
with tab_channels:
    st.markdown("### 🔴 YouTube Kanallari (Gmail Hisoblari)")
    st.write("Siz ko'rsatgan 2 ta asosiy Gmail hisobi va ularning ulanish holati:")

    for email, cfg in channel_manager.TARGET_ACCOUNTS.items():
        is_act = channel_manager.is_account_active(cfg["token_file"])
        with st.container():
            st.markdown(f"""
            <div class="card-box">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <span style="font-size: 1.18rem; font-weight: 700;">{cfg['label']}</span>
                        <div style="color: #94a3b8; font-size: 0.88rem; margin-top: 4px;">
                            Gmail: <code>{email}</code> | Token fayli: <code>{cfg['token_file']}</code> | Birlamchi: <b>{cfg['default_script']}</b>
                        </div>
                    </div>
                    <div>
                        {'<span class="status-badge" style="background: rgba(34,197,94,0.2); color: #4ade80;">🟢 Ulanish Faol</span>' if is_act else '<span class="status-badge" style="background: rgba(239,68,68,0.2); color: #f87171;">⚪ Ruxsat berilmagan</span>'}
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            col_btn1, col_btn2 = st.columns([0.5, 0.5])
            with col_btn1:
                btn_label = f"🔄 {email} ruxsatini yangilash" if is_act else f"🔑 {email} bilan kirish"
                if st.button(btn_label, key=f"btn_auth_{email}"):
                    with st.spinner(f"Brauzerda {email} tanlanishi kutilmoqda..."):
                        try:
                            creds = channel_manager.get_credentials(cfg["token_file"], login_hint=email, interactive=True)
                            if creds and creds.valid:
                                st.success(f"🎉 {email} muvaffaqiyatli saqlandi!")
                                st.rerun()
                        except Exception as e:
                            st.error(f"Xatolik: {e}")
            with col_btn2:
                if is_act and st.button(f"🗑️ {email} ruxsatini o'chirish", key=f"btn_del_{email}"):
                    try:
                        if os.path.exists(cfg["token_file"]):
                            os.remove(cfg["token_file"])
                        st.warning(f"{email} tokeni o'chirildi.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Xatolik: {e}")

    st.write("---")
    st.markdown("### ➕ Boshqa Yangi Gmail Hisobini Ulash")
    custom_new_mail = st.text_input("Yangi Gmail manzilini kiriting:", placeholder="masalan: yangikanal@gmail.com", key="new_custom_mail")
    if st.button("🔑 Yangi Gmail Ruxsatini Olish (Brauzer ochiladi)", type="primary"):
        if not custom_new_mail.strip():
            st.error("Iltimos, Gmail manzilini kiriting!")
        else:
            tf, login_hint = channel_manager.resolve_account_info(custom_new_mail.strip())
            with st.spinner(f"Brauzerda {login_hint} tanlanishi kutilmoqda..."):
                try:
                    creds = channel_manager.get_credentials(tf, login_hint=login_hint, interactive=True)
                    if creds and creds.valid:
                        st.success(f"🎉 {login_hint} ruxsati muvaffaqiyatli saqlandi ({tf})!")
                        st.rerun()
                except Exception as e:
                    st.error(f"Xatolik: {e}")



# =====================================================================
# TAB 4: TIZIM & DIAGNOSTIKA
# =====================================================================
with tab_diagnostics:
    st.markdown("### ⚙️ Tizim va API Diagnostikasi")
    
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        st.markdown("#### 🔑 Kalitlar va Muhit")
        from dotenv import load_dotenv
        load_dotenv()
        
        gem_key = os.environ.get("GEMINI_API_KEY", "")
        pix_key = os.environ.get("PIXABAY_API_KEY", "")
        
        st.write(f"• **GEMINI_API_KEY:** `{'*'*20 + gem_key[-6:] if gem_key else '❌ Kiritilmagan'}`")
        st.write(f"• **PIXABAY_API_KEY:** `{'*'*15 + pix_key[-6:] if pix_key else '❌ Kiritilmagan'}`")
        st.write(f"• **client_secrets.json:** `{'✅ Mavjud' if os.path.exists('client_secrets.json') else '❌ Topilmadi'}`")

    with col_d2:
        st.markdown("#### 🧪 Jonli API Sinovlari")
        if st.button("🔍 Barcha API larni Tekshirish", use_container_width=True):
            # 1. Gemini
            with st.spinner("Gemini API tekshirilmoqda..."):
                try:
                    from google import genai
                    c = genai.Client(api_key=gem_key)
                    t0 = time.time()
                    res = c.models.generate_content(model="gemini-3.5-flash-lite", contents="ping")
                    latency = int((time.time() - t0) * 1000)
                    st.success(f"✅ Gemini API: Aloqa a'lo ({latency}ms | gemini-3.5-flash-lite)")
                except Exception as e:
                    st.error(f"❌ Gemini API xatosi: {e}")

            # 2. Pixabay
            with st.spinner("Pixabay API tekshirilmoqda..."):
                try:
                    import requests
                    r = requests.get(f"https://pixabay.com/api/videos/?key={pix_key}&q=stars&per_page=3", timeout=10)
                    if r.status_code == 200:
                        st.success("✅ Pixabay API: Kalit to'g'ri, video qidirish ishlayapti")
                    else:
                        st.error(f"❌ Pixabay API kodi: {r.status_code}")
                except Exception as e:
                    st.error(f"❌ Pixabay xatosi: {e}")

            # 3. FFmpeg
            with st.spinner("FFmpeg tekshirilmoqda..."):
                try:
                    ver = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, check=True)
                    first_line = ver.stdout.splitlines()[0]
                    st.success(f"✅ FFmpeg: O'rnatilgan ({first_line[:40]})")
                except Exception as e:
                    st.error(f"❌ FFmpeg xatosi: {e}")