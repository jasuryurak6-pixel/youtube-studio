#!/usr/bin/env python3
"""
YouTube AI Studio — Multi-Account & Gmail Channel Manager
Barcha agentlar uchun Gmail hisoblarini boshqarish va to'g'ri kanalga yuklash.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

CLIENT_SECRETS_FILE = "client_secrets.json"
YOUTUBE_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
]

# Foydalanuvchi belgilagan maxsus Gmail kanallari
TARGET_ACCOUNTS = {
    "jasuryurak6@gmail.com": {
        "email": "jasuryurak6@gmail.com",
        "label": "📖 2D Animatsion Hikoyalar (jasuryurak6@gmail.com)",
        "token_file": "token_jasuryurak6.json",
        "default_script": "story_animation_agent.py",
        "category_id": "1",  # Film & Animation
    },
    "youtubekanal0004@gmail.com": {
        "email": "youtubekanal0004@gmail.com",
        "label": "🌌 Kosmik & Dunyo Faktlari (youtubekanal0004@gmail.com)",
        "token_file": "token_youtubekanal0004.json",
        "default_script": "youtube_facts_agent.py",
        "category_id": "28",  # Science & Technology
    },
}


def resolve_client_secrets() -> str:
    candidates = [
        CLIENT_SECRETS_FILE,
        "client_secrets.json.json",
        str(Path(__file__).parent / CLIENT_SECRETS_FILE),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    raise FileNotFoundError(f"'{CLIENT_SECRETS_FILE}' topilmadi! Google Cloud Console dan yuklab oling.")


def resolve_account_info(target: Optional[str] = None, default_email: str = "jasuryurak6@gmail.com") -> Tuple[str, str]:
    """
    Gmail yoki token faylini tekshirib, (token_file, login_hint) juftligini qaytaradi.
    """
    if not target:
        target = default_email

    target_str = str(target).strip()
    
    # Agar ro'yxatdagi Gmail bo'lsa
    if target_str in TARGET_ACCOUNTS:
        cfg = TARGET_ACCOUNTS[target_str]
        return cfg["token_file"], cfg["email"]

    # Agar token fayli ko'rsatilgan bo'lsa
    if target_str.endswith(".json"):
        for email, cfg in TARGET_ACCOUNTS.items():
            if cfg["token_file"] == target_str:
                return target_str, email
        return target_str, ""

    # Agar qisman mos kelsa
    for email, cfg in TARGET_ACCOUNTS.items():
        if target_str in email or email in target_str:
            return cfg["token_file"], cfg["email"]

    # Boshqa maxsus Gmail bo'lsa
    if "@" in target_str:
        clean_name = target_str.replace("@", "_").replace(".", "_")
        return f"token_{clean_name}.json", target_str

    cfg = TARGET_ACCOUNTS.get(default_email, list(TARGET_ACCOUNTS.values())[0])
    return cfg["token_file"], cfg["email"]


def get_credentials(token_file: str, login_hint: Optional[str] = None, interactive: bool = False):
    """
    Berilgan token faylidan YouTube Credentials qaytaradi.
    Agar token bo'lmasa yoki eskirgan bo'lsa, login_hint (Gmail) orqali brauzerda qayta kiradi.
    """
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    creds = None
    if os.path.exists(token_file):
        try:
            creds = Credentials.from_authorized_user_file(token_file)
        except Exception:
            creds = None

    if not creds or not creds.valid:
        if creds and creds.refresh_token:
            try:
                creds.refresh(Request())
                with open(token_file, "w", encoding="utf-8") as f:
                    f.write(creds.to_json())
            except Exception:
                if not interactive:
                    return None
                creds = None

        if not creds and interactive:
            secrets_path = resolve_client_secrets()
            flow = InstalledAppFlow.from_client_secrets_file(secrets_path, YOUTUBE_SCOPES)
            
            flow_kwargs = {"port": 0, "prompt": "select_account"}
            if login_hint:
                flow_kwargs["login_hint"] = login_hint
                print(f"\n[🔑 GOOGLE LOGIN] Iltimos, ochilgan brauzerda '{login_hint}' hisobini tanlang!", flush=True)
            else:
                print("\n[🔑 GOOGLE LOGIN] Iltimos, brauzerda kerakli YouTube Gmail hisobini tanlang!", flush=True)

            creds = flow.run_local_server(**flow_kwargs)
            with open(token_file, "w", encoding="utf-8") as f:
                f.write(creds.to_json())
            print(f"[+] Token saqlandi: {token_file}\n", flush=True)

    return creds


def is_account_active(token_file: str) -> bool:
    """Token mavjudligi va ishchi holatini tekshiradi."""
    try:
        creds = get_credentials(token_file, interactive=False)
        return bool(creds and creds.valid)
    except Exception:
        return False


def list_channel_profiles() -> List[Dict]:
    """Foydalanuvchi kanallari va mavjud tokenlar ro'yxatini qaytaradi."""
    profiles = []
    
    # 1. Asosiy maqsadli Gmail kanallari
    for email, cfg in TARGET_ACCOUNTS.items():
        tf = cfg["token_file"]
        active = is_account_active(tf)
        profiles.append({
            "email": email,
            "token_file": tf,
            "label": cfg["label"],
            "description": cfg["label"],
            "exists": os.path.exists(tf),
            "active": active,
            "is_target": True,
        })

    # 2. Boshqa mavjud tokenlar
    for f in os.listdir("."):
        if f.startswith("token_") and f.endswith(".json"):
            if not any(p["token_file"] == f for p in profiles):
                active = is_account_active(f)
                profiles.append({
                    "email": f,
                    "token_file": f,
                    "label": f"Maxsus Token ({f})",
                    "description": f"Fayl: {f}",
                    "exists": True,
                    "active": active,
                    "is_target": False,
                })

    return profiles


def prompt_account_selection_cli(default_email: str) -> Tuple[str, str]:
    """
    Terminal orqali ishga tushirilganda foydalanuvchidan qaysi Gmail kanalga yuklashni so'raydi.
    """
    if not sys.stdin.isatty():
        # Avtomat rejimda (masalan subprocess orqali chaqirilganda) defaultni oladi
        return resolve_account_info(default_email)

    print("\n=======================================================", flush=True)
    print("📺 Qaysi YouTube kanalga (Gmail) yuklamoqchisiz?", flush=True)
    print("=======================================================", flush=True)
    
    items = list(TARGET_ACCOUNTS.items())
    for idx, (em, cfg) in enumerate(items, 1):
        status = "🟢 [Faol]" if is_account_active(cfg["token_file"]) else "⚪ [Login talab qilinadi]"
        is_def = " (Tavsiya)" if em == default_email else ""
        print(f" [{idx}] {cfg['label']} {status}{is_def}", flush=True)
    print(f" [{len(items) + 1}] Boshqa maxsus Gmail hisob", flush=True)
    print("-------------------------------------------------------", flush=True)

    choice = input(f"Tanlovingizni kiriting [1-{len(items) + 1}] (Standart: {default_email}): ").strip()
    
    if choice == "1":
        em = items[0][0]
        return TARGET_ACCOUNTS[em]["token_file"], em
    elif choice == "2" and len(items) >= 2:
        em = items[1][0]
        return TARGET_ACCOUNTS[em]["token_file"], em
    elif choice == str(len(items) + 1):
        custom_mail = input("Gmail manzilingizni kiriting: ").strip()
        if custom_mail:
            return resolve_account_info(custom_mail)

    return resolve_account_info(default_email)


def upload_video_to_youtube(
    video_path: Path,
    metadata: Dict,
    token_file: str = "token_facts.json",
    login_hint: Optional[str] = None,
    lang: str = "uz",
    privacy_status: str = "public",
    category_id: str = "28",
    progress_callback=None,
) -> str:
    """Videoni YouTube'ga yuklaydi va toza havola qaytaradi."""
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    creds = get_credentials(token_file, login_hint=login_hint, interactive=True)
    if not creds:
        raise RuntimeError(f"YouTube uchun ruxsat olinmadi ({token_file})")

    youtube = build("youtube", "v3", credentials=creds)

    body = {
        "snippet": {
            "title": str(metadata.get("title", video_path.stem))[:100],
            "description": str(metadata.get("description", "")),
            "tags": metadata.get("tags", ["viral", "video"]),
            "categoryId": category_id,
            "defaultLanguage": lang,
            "defaultAudioLanguage": lang,
        },
        "status": {
            "privacyStatus": privacy_status,
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True, mimetype="video/mp4")
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            pct = int(status.progress() * 100)
            if progress_callback:
                progress_callback(pct)
            print(f"  Yuklanmoqda: {pct}%", flush=True)

    video_id = response.get("id")
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    print(f"  [MUVAFFAQIYATLI] Video YouTube'ga joylandi: {video_url}", flush=True)
    return video_url
