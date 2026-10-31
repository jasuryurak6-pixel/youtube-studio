#!/usr/bin/env python3
"""
YouTube 2D Story Animation AI Agent — VARIETY & MULTI-WORLD EDITION
===================================================================
Har bir video vizual, musiqiy va syujet jihatidan takrorlanmas chiqadi:
- 8 xil joylashuv: bedroom, living_room, gym, library, park, street, school, basketball
- 10 xil animatsion harakat: workout, work_desk, sleep_bed, phone_scroll, celebrate va b.
- 5 xil dinamik shkala: MOOD, ENERGY, FOCUS, DISCIPLINE, HEALTH
- 5 xil hikoya strukturasi (Story Arcs) + Takrorlanmas mavzular xotirasi (used_topics.json)
- 4 xil avtomatik sintez qilinadigan fon musiqasi va har videoda yangi rang palitrasi.
"""

import argparse
import asyncio
import json
import math
import os
import random
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# =====================================================================
# SOZLAMALAR (CONFIG)
# =====================================================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY")

LANGUAGE_CONFIG: Dict[str, Dict] = {
    "en": {
        "name": "English",
        "yt_code": "en",
        "voices": [
            "en-US-ChristopherNeural",
            "en-GB-RyanNeural",
            "en-US-GuyNeural",
            "en-US-EricNeural",
        ],
        "hashtags": "#animation #storytime #selfimprovement #motivation #mentalhealth #discipline",
    },
    "uz": {
        "name": "Uzbek (Latin script, O'zbek tili)",
        "yt_code": "uz",
        "voices": [
            "uz-UZ-SardorNeural",
            "uz-UZ-MadinaNeural",
        ],
        "hashtags": "#animatsiya #motivatsiya #psixologiya #hikoya #uzbekistan #intizom",
    },
    "ru": {
        "name": "Russian (Русский язык)",
        "yt_code": "ru",
        "voices": [
            "ru-RU-DmitryNeural",
            "ru-RU-SvetlanaNeural",
        ],
        "hashtags": "#анимация #мотивация #психология #саморазвитие #история",
    },
}

try:
    from topics_database import STORY_ANIMATION_TOPICS
    STORY_TOPICS = STORY_ANIMATION_TOPICS
except ImportError:
    STORY_TOPICS = [
        "It started with just one game — how gaming addiction stole his youth and how he reclaimed it",
        "Just 5 more minutes of scrolling — how short videos destroyed his focus bar until he fought back",
        "The guy who always said 'Tomorrow' — how procrastination quietly ate 5 years of his life",
    ]


STORY_ARCS = [
    "Classic Downfall & Comeback (starts innocent -> habit takes over -> hits rock bottom -> rebuilds step by step)",
    "The Two Paths / Contrast (shows the stark contrast between giving in to instant gratification vs choosing long-term growth)",
    "The Silent Compound Effect (starts in deep struggle/low energy -> discovers ONE tiny daily habit -> fails at first -> slowly transforms life)",
    "The Wake-Up Call (living on autopilot ignoring loved ones -> a sudden emotional realization -> fighting the inner shadow to change before it's too late)",
    "Overcoming the Inner Critic (the Shadow represents self-doubt and fear rather than addiction -> hero learns courage through action)",
]

COLOR_THEMES = [
    {"name": "midnight_blue", "bg": (16, 19, 28), "floor": (11, 13, 19), "accent": (70, 150, 255)},
    {"name": "warm_charcoal", "bg": (24, 20, 19), "floor": (15, 12, 12), "accent": (245, 160, 65)},
    {"name": "deep_emerald",  "bg": (15, 24, 22), "floor": (10, 16, 15), "accent": (65, 215, 155)},
    {"name": "cyber_violet",  "bg": (22, 17, 29), "floor": (14, 11, 19), "accent": (185, 105, 255)},
    {"name": "obsidian_gold", "bg": (18, 18, 20), "floor": (12, 12, 14), "accent": (240, 200, 70)},
]

HERO_SHIRT_COLORS = [
    None,               # Klassik oq minimalistik personaj
    (65, 125, 215),     # Ko'k hoodie
    (215, 75, 75),      # Qizil futbolka
    (75, 170, 115),     # Yashil hoodie
    (225, 165, 55),     # Sariq sviter
    (135, 95, 205),     # Binafsha kiyim
]

OUTPUT_DIR = Path("output_videos")
USED_TOPICS_FILE = Path("used_topics.json")
CLIENT_SECRETS_FILE = "client_secrets.json"
DEFAULT_GMAIL = "jasuryurak6@gmail.com"
TOKEN_FILE = "token_jasuryurak6.json"
YOUTUBE_SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

WIDTH, HEIGHT = 1280, 720
FPS = 24
GEMINI_MODEL_CHAIN = ["gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-flash-latest", "gemini-flash-lite-latest", "gemini-3.8-flash"]


def get_dimensions(vertical: bool = False) -> Tuple[int, int, int]:
    """Qaytaradi: (width, height, floor_y)"""
    if vertical:
        return 720, 1280, 920
    return 1280, 720, 540


if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def log(msg: str) -> None:
    try:
        print(msg, flush=True)
    except Exception:
        try:
            print(msg.encode("ascii", errors="replace").decode("ascii"), flush=True)
        except Exception:
            pass


def pick_unique_topic(custom_topic: Optional[str] = None, lang: str = "en") -> str:
    """Oldin ishlatilgan hikoya mavzularini takrorlamasdan yangisini tanlaydi."""
    if custom_topic and custom_topic.strip():
        return custom_topic.strip()

    used: List[str] = []
    used_file = Path("used_topics_story.json")
    if used_file.exists():
        try:
            used = json.loads(used_file.read_text(encoding="utf-8"))
        except Exception:
            used = []

    try:
        from topics_database import STORY_ANIMATION_TOPICS_UZ, STORY_ANIMATION_TOPICS_EN
        pool = STORY_ANIMATION_TOPICS_UZ if lang.startswith("uz") else STORY_ANIMATION_TOPICS_EN
    except Exception:
        pool = STORY_TOPICS

    available = [t for t in pool if t not in used]
    if available:
        chosen = random.choice(available)
    else:
        chosen = random.choice(pool)

    used.append(chosen)
    try:
        used_file.write_text(json.dumps(used[-100:], indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass
    return chosen


# =====================================================================
# 1-BOSQICH: GEMINI AI ORQALI XILMA-XIL SSENARIY YARATISH
# =====================================================================
def _clean_json_text(raw_text: str) -> str:
    text = raw_text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def generate_story_script(topic: Optional[str] = None, lang: str = "en", vertical: bool = False) -> Dict:
    from google import genai
    from google.genai import types

    chosen_topic = pick_unique_topic(topic, lang=lang)
    chosen_arc = random.choice(STORY_ARCS)

    lang_info = LANGUAGE_CONFIG.get(lang, LANGUAGE_CONFIG["en"])
    lang_name = lang_info["name"]
    hashtags = lang_info["hashtags"]
    if vertical and "#shorts" not in hashtags:
        hashtags += " #shorts #short #animation"

    try:
        client = genai.Client(api_key=GEMINI_API_KEY, http_options=types.HttpOptions(timeout=50000))
    except Exception:
        client = genai.Client(api_key=GEMINI_API_KEY)

    scene_count_rule = "create 6 to 8 punchy high-energy scenes (total duration 35-50s for YouTube Shorts, scene 1 has an intense hook)" if vertical else "create 11 to 13 scenes (1-2 minutes total duration)"

    prompt = f"""
    You are the creative director for a viral 2D minimalist animation channel like "Day One Films".
    Topic: {chosen_topic}
    Story Structure / Arc to follow: {chosen_arc}
    Format: {"9:16 Vertical YouTube Shorts" if vertical else "16:9 Landscape Video"}
    Scene count: {scene_count_rule}
    Language for all text (`title`, `description`, `narration`, `screen_text`, `other_speech`, `hero_speech`, `shadow_speech`): {lang_name}.

    IMPORTANT FOR VARIETY:
    - Do NOT make every scene look the same! Change `setting` and `action` frequently across scenes so the viewer sees different rooms, outdoor places, and activities.
    - Choose the most fitting `stat_name` for this story from: "MOOD", "ENERGY", "FOCUS", "DISCIPLINE", "HEALTH".

    Return strictly valid JSON matching this exact structure:
    {{
      "title": "Viral emotional title in {lang_name} (max 65 chars)",
      "description": "Emotional SEO description in {lang_name} with hashtags ({hashtags})",
      "tags": ["animation", "story", "motivation", "mentalhealth", "discipline", "shorts"],
      "stat_name": "MOOD",
      "scenes": [
        {{
          "setting": "bedroom",
          "action": "phone_scroll",
          "expression": "excited",
          "mood": 85,
          "day_label": "",
          "narration": "Spoken narrator voiceover for this scene (1-2 impactful sentences in {lang_name}).",
          "screen_text": "Short top caption on screen (max 8 words in {lang_name})",
          "other_char": "none",
          "other_speech": "",
          "hero_speech": "",
          "shadow": false,
          "shadow_speech": ""
        }}
      ]
    }}

    Allowed values for scene fields:
    - `setting`: "bedroom" | "living_room" | "gym" | "library" | "park" | "street" | "school" | "basketball"
    - `action`: "walk_in" | "sit_play" | "phone_scroll" | "work_desk" | "workout" | "sleep_bed" | "sit_sad" | "stand" | "shoot_hoop" | "celebrate"
    - `expression`: "happy" | "excited" | "neutral" | "angry" | "sad" | "tired"
    - `other_char`: "none" | "mom" | "brother" | "friend"
    - `mood`: integer from 10 to 100 (represents the percentage of `stat_name`)
    - `day_label`: "" or "DAY 1" or "DAY 3" or "DAY 14" or "DAY 30" or "1 YEAR LATER"
    - `shadow`: true or false (use true in 2-3 key temptation/doubt scenes; provide a short creepy whisper in `shadow_speech`, max 5 words)
    """

    fmt_lbl = "Shorts (9:16)" if vertical else "16:9 Video"
    log(f"[1/5] 2D Ssenariy yaratilmoqda (Format: {fmt_lbl} | Til: {lang_name})...")
    log(f"  [i] Mavzu: {chosen_topic}")
    log(f"  [i] Syujet uslubi: {chosen_arc}")

    last_error = None
    for model_name in GEMINI_MODEL_CHAIN:
        for attempt in range(1, 3):
            try:
                log(f"  -> {model_name} ga so'rov yuborilmoqda (urinish {attempt}/2)...")
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.85,
                    ),
                )
                data = json.loads(_clean_json_text(response.text))
                if not data.get("scenes"):
                    raise ValueError("Sahnalar ro'yxati bo'sh qaytdi")
                log(f"  [+] Ssenariy tayyor: {len(data['scenes'])} ta turli sahna ({model_name}).")
                return data
            except Exception as exc:
                last_error = exc
                log(f"  [!] {model_name} xatosi: {exc}")
                time.sleep(2)

    raise RuntimeError(f"Ssenariy olinmadi: {last_error}")


# =====================================================================
# 2-BOSQICH: HAR BIR SAHNA UCHUN DIKTOR OVOZINI YARATISH (EDGE-TTS)
# =====================================================================
def get_media_duration(file_path: Path) -> float:
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(file_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(result.stdout.strip())


async def _synthesize_scene_voice(text: str, out_path: Path, voice: str) -> None:
    import edge_tts
    last_err = None
    for attempt in range(1, 4):
        try:
            communicate = edge_tts.Communicate(text, voice, rate="-3%")
            with open(out_path, "wb") as f:
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        f.write(chunk["data"])
            if out_path.exists() and out_path.stat().st_size > 0:
                return
        except Exception as exc:
            last_err = exc
            await asyncio.sleep(1.0)
    if not out_path.exists() or out_path.stat().st_size == 0:
        raise RuntimeError(f"Ovoz yaratishda xatolik (urinishlar tugadi): {last_err}")


def generate_all_scene_voices(scenes: List[Dict], work_dir: Path, voice: str) -> List[Tuple[Path, float]]:
    log(f"[2/5] Har bir sahna uchun diktor ovozi yaratilmoqda (Ovoz: {voice})...")
    scene_audios: List[Tuple[Path, float]] = []

    for idx, scene in enumerate(scenes):
        narration = (scene.get("narration") or scene.get("screen_text") or "...").strip()
        audio_file = work_dir / f"scene_voice_{idx:02d}.mp3"
        asyncio.run(_synthesize_scene_voice(narration, audio_file, voice))

        raw_dur = get_media_duration(audio_file) if audio_file.exists() else 4.0
        padded_file = work_dir / f"scene_voice_pad_{idx:02d}.m4a"
        scene_dur = max(4.2, raw_dur + 1.1)

        cmd = [
            "ffmpeg", "-y",
            "-i", str(audio_file),
            "-af", "apad=pad_dur=1.1",
            "-t", f"{scene_dur:.2f}",
            "-c:a", "aac", "-b:a", "192k",
            str(padded_file),
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        scene_audios.append((padded_file, scene_dur))
        log(f"  [+] Sahna {idx + 1}/{len(scenes)} ({scene.get('setting')} / {scene.get('action')}) — {scene_dur:.1f}s")

    return scene_audios


# =====================================================================
# 3-BOSQICH: 8 XIL OLAM VA 10 XIL HARAKATLI 2D ANIMATSIYA DVIGATELI
# =====================================================================
def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        "C:/Windows/Fonts/comicbd.ttf" if bold else "C:/Windows/Fonts/comic.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()


FONT_TITLE = _load_font(33, bold=True)
FONT_BUBBLE = _load_font(21, bold=True)
FONT_MOOD = _load_font(15, bold=True)
FONT_DAY = _load_font(26, bold=True)


def _create_vignette_bg(setting: str, theme: Dict, width: int = 1280, height: int = 720, floor_y: int = 540) -> Image.Image:
    """Tanlangan makon (setting) va rang mavzusi bo'yicha boy detallarga ega fon chizadi (Gorizontal va Vertikal moslashuvchan)."""
    bg_c = theme["bg"]
    fl_c = theme["floor"]
    img = Image.new("RGB", (width, height), bg_c)
    draw = ImageDraw.Draw(img)

    is_vert = (width < height)
    spot_max = 680 if is_vert else 620
    for r in range(spot_max, 40, -30):
        boost = int((spot_max - r) * 0.04)
        c = (min(255, bg_c[0] + boost), min(255, bg_c[1] + boost), min(255, bg_c[2] + boost + 4))
        draw.ellipse([width // 2 - r, height // 2 - r // 2 - 40, width // 2 + r, height // 2 + r // 2 + 120], fill=c)

    draw.line([(0, floor_y), (width, floor_y)], fill=(80, 84, 96), width=3)
    draw.rectangle([0, floor_y + 2, width, height], fill=fl_c)

    if setting == "bedroom":
        if is_vert:
            draw.rectangle([60, 320, 240, 490], fill=(22, 30, 48), outline=(85, 90, 105), width=4)
            draw.ellipse([180, 340, 215, 375], fill=(240, 235, 200))
            draw.rounded_rectangle([30, floor_y - 95, 270, floor_y], radius=10, fill=(55, 45, 40), outline=(25, 20, 18), width=3)
            draw.rounded_rectangle([40, floor_y - 120, 115, floor_y - 90], radius=8, fill=(220, 220, 230))
            draw.rounded_rectangle([105, floor_y - 110, 265, floor_y - 50], radius=10, fill=(75, 95, 145))
            draw.rectangle([460, floor_y - 110, 690, floor_y], fill=(48, 42, 38), outline=(75, 68, 62), width=3)
            draw.rectangle([535, floor_y - 200, 645, floor_y - 125], fill=(25, 30, 40), outline=(140, 145, 155), width=3)
        else:
            draw.rectangle([120, 170, 270, 320], fill=(22, 30, 48), outline=(85, 90, 105), width=4)
            draw.ellipse([220, 190, 245, 215], fill=(240, 235, 200))
            draw.rounded_rectangle([80, 450, 370, floor_y], radius=10, fill=(55, 45, 40), outline=(25, 20, 18), width=3)
            draw.rounded_rectangle([90, 425, 165, 455], radius=8, fill=(220, 220, 230))
            draw.rounded_rectangle([155, 435, 365, 495], radius=10, fill=(75, 95, 145))
            draw.rectangle([820, 430, 1120, floor_y], fill=(48, 42, 38), outline=(75, 68, 62), width=3)
            draw.rectangle([935, 340, 1055, 415], fill=(25, 30, 40), outline=(140, 145, 155), width=3)
            draw.rectangle([985, 415, 1005, 430], fill=(110, 115, 125))

    elif setting == "gym":
        if is_vert:
            draw.rectangle([120, 320, 440, 600], fill=(32, 38, 48), outline=(95, 100, 115), width=5)
            draw.rectangle([480, floor_y - 180, 690, floor_y], fill=(35, 35, 42), outline=(80, 82, 92), width=3)
            for dy in (floor_y - 140, floor_y - 80):
                draw.line([(480, dy), (690, dy)], fill=(90, 95, 105), width=4)
                for dx in range(500, 670, 50):
                    draw.ellipse([dx, dy - 14, dx + 26, dy - 2], fill=(20, 20, 24), outline=(110, 110, 120), width=2)
        else:
            draw.rectangle([160, 170, 560, 430], fill=(32, 38, 48), outline=(95, 100, 115), width=5)
            draw.line([(210, 400), (320, 200)], fill=(65, 75, 90), width=3)
            draw.line([(250, 410), (360, 210)], fill=(65, 75, 90), width=2)
            draw.rectangle([860, 360, 1140, floor_y], fill=(35, 35, 42), outline=(80, 82, 92), width=3)
            for dy in (400, 460):
                draw.line([(860, dy), (1140, dy)], fill=(90, 95, 105), width=4)
                for dx in range(890, 1120, 55):
                    draw.ellipse([dx, dy - 14, dx + 28, dy - 2], fill=(20, 20, 24), outline=(110, 110, 120), width=2)

    elif setting == "library":
        if is_vert:
            draw.rectangle([40, 320, 240, floor_y], fill=(42, 34, 28), outline=(78, 64, 52), width=4)
            for sy in range(380, floor_y, 75):
                draw.line([(40, sy), (240, sy)], fill=(78, 64, 52), width=4)
                for bx in range(50, 225, 24):
                    b_col = [(165, 65, 65), (65, 115, 165), (75, 145, 95), (185, 145, 65)][(bx + sy) % 4]
                    draw.rectangle([bx, sy - 45, bx + 18, sy - 2], fill=b_col)
            draw.rectangle([460, floor_y - 110, 690, floor_y], fill=(55, 44, 34), outline=(85, 70, 55), width=3)
            draw.polygon([(580, floor_y - 190), (630, floor_y - 190), (645, floor_y - 160), (565, floor_y - 160)], fill=(55, 155, 95))
            draw.line([(605, floor_y - 160), (605, floor_y - 110)], fill=(160, 150, 110), width=4)
        else:
            for sx in (110, 340):
                draw.rectangle([sx, 150, sx + 190, floor_y], fill=(42, 34, 28), outline=(78, 64, 52), width=4)
                for sy in range(210, floor_y, 65):
                    draw.line([(sx, sy), (sx + 190, sy)], fill=(78, 64, 52), width=4)
                    for bx in range(sx + 12, sx + 170, 22):
                        b_col = [(165, 65, 65), (65, 115, 165), (75, 145, 95), (185, 145, 65)][(bx + sy) % 4]
                        draw.rectangle([bx, sy - 42, bx + 16, sy - 2], fill=b_col)
            draw.rectangle([760, 430, 1080, floor_y], fill=(55, 44, 34), outline=(85, 70, 55), width=3)
            draw.polygon([(960, 350), (1010, 350), (1025, 380), (945, 380)], fill=(55, 155, 95))
            draw.line([(985, 380), (985, 430)], fill=(160, 150, 110), width=4)

    elif setting == "park":
        if is_vert:
            for tx in (120, 600):
                draw.rectangle([tx - 16, floor_y - 200, tx + 16, floor_y], fill=(58, 42, 30))
                draw.ellipse([tx - 85, floor_y - 360, tx + 85, floor_y - 180], fill=(34, 72, 48), outline=(52, 105, 70), width=3)
                draw.ellipse([tx - 65, floor_y - 410, tx + 65, floor_y - 260], fill=(42, 88, 58))
            draw.rectangle([210, floor_y - 85, 510, floor_y - 65], fill=(95, 68, 45), outline=(30, 22, 15), width=2)
            draw.rectangle([210, floor_y - 120, 510, floor_y - 98], fill=(95, 68, 45), outline=(30, 22, 15), width=2)
            draw.rectangle([240, floor_y - 65, 260, floor_y], fill=(35, 35, 40))
            draw.rectangle([460, floor_y - 65, 480, floor_y], fill=(35, 35, 40))
        else:
            for tx in (150, 410, 1040):
                draw.rectangle([tx - 14, 340, tx + 14, floor_y], fill=(58, 42, 30))
                draw.ellipse([tx - 75, 200, tx + 75, 365], fill=(34, 72, 48), outline=(52, 105, 70), width=3)
                draw.ellipse([tx - 55, 160, tx + 55, 290], fill=(42, 88, 58))
            draw.rectangle([520, 465, 780, 485], fill=(95, 68, 45), outline=(30, 22, 15), width=2)
            draw.rectangle([520, 430, 780, 452], fill=(95, 68, 45), outline=(30, 22, 15), width=2)
            draw.rectangle([550, 485, 568, floor_y], fill=(35, 35, 40))
            draw.rectangle([732, 485, 750, floor_y], fill=(35, 35, 40))

    elif setting == "street":
        if is_vert:
            for bx in range(20, width, 140):
                bh = 280 + (bx * 43) % 180
                draw.rectangle([bx, floor_y - bh, bx + 110, floor_y], fill=(24, 26, 34), outline=(42, 45, 58))
                for wy in range(floor_y - bh + 25, floor_y - 30, 45):
                    for wx in (bx + 20, bx + 65):
                        if (wx + wy) % 3 == 0:
                            draw.rectangle([wx, wy, wx + 20, wy + 24], fill=(215, 185, 95))
            draw.rectangle([540, floor_y - 340, 552, floor_y], fill=(70, 75, 85))
            draw.line([(490, floor_y - 340), (552, floor_y - 340)], fill=(70, 75, 85), width=6)
            draw.polygon([(475, floor_y - 335), (515, floor_y - 335), (630, floor_y), (370, floor_y)], fill=(42, 44, 32))
            draw.ellipse([480, floor_y - 345, 510, floor_y - 325], fill=(255, 235, 150))
        else:
            for bx in range(40, width, 160):
                bh = 200 + (bx * 43) % 160
                draw.rectangle([bx, floor_y - bh, bx + 115, floor_y], fill=(24, 26, 34), outline=(42, 45, 58))
                for wy in range(floor_y - bh + 25, floor_y - 30, 40):
                    for wx in (bx + 20, bx + 65):
                        if (wx + wy) % 3 == 0:
                            draw.rectangle([wx, wy, wx + 22, wy + 24], fill=(215, 185, 95))
            draw.rectangle([880, 180, 892, floor_y], fill=(70, 75, 85))
            draw.line([(830, 180), (892, 180)], fill=(70, 75, 85), width=6)
            draw.polygon([(815, 185), (855, 185), (970, floor_y), (710, floor_y)], fill=(42, 44, 32))
            draw.ellipse([820, 175, 850, 195], fill=(255, 235, 150))

    elif setting == "school":
        if is_vert:
            draw.rectangle([120, 360, 600, 600], fill=(22, 38, 30), outline=(95, 75, 55), width=6)
            draw.text((160, 420), "FOCUS = SUCCESS\n1% BETTER EVERY DAY", fill=(210, 220, 210), font=FONT_BUBBLE)
        else:
            draw.rectangle([720, 170, 1140, 390], fill=(22, 38, 30), outline=(95, 75, 55), width=6)
            draw.text((770, 215), "FOCUS = SUCCESS\n1% BETTER EVERY DAY", fill=(210, 220, 210), font=FONT_BUBBLE)
            draw.rectangle([140, 175, 310, 345], fill=(35, 55, 75), outline=(90, 95, 105), width=5)
            draw.line([(225, 175), (225, 345)], fill=(90, 95, 105), width=4)
            draw.line([(140, 260), (310, 260)], fill=(90, 95, 105), width=4)

    else:
        # living_room
        if is_vert:
            draw.rectangle([220, 380, 500, 580], fill=(20, 26, 42), outline=(85, 90, 100), width=5)
            draw.ellipse([340, 420, 380, 460], fill=(235, 235, 210))
            draw.line([(360, 380), (360, 580)], fill=(85, 90, 100), width=4)
            draw.line([(220, 480), (500, 480)], fill=(85, 90, 100), width=4)
            draw.rounded_rectangle([190, floor_y - 120, 530, floor_y], radius=16, fill=(52, 54, 68), outline=(25, 26, 34), width=4)
        else:
            draw.rectangle([75, 240, 195, floor_y], fill=(38, 32, 28), outline=(75, 65, 55), width=4)
            draw.ellipse([172, 390, 184, 402], fill=(180, 160, 90))
            draw.rectangle([260, 170, 420, 330], fill=(20, 26, 42), outline=(85, 90, 100), width=5)
            draw.ellipse([365, 195, 390, 220], fill=(235, 235, 210))
            draw.line([(340, 170), (340, 330)], fill=(85, 90, 100), width=4)
            draw.line([(260, 250), (420, 250)], fill=(85, 90, 100), width=4)
            draw.rounded_rectangle([470, 415, 790, floor_y], radius=16, fill=(52, 54, 68), outline=(25, 26, 34), width=4)
            draw.rounded_rectangle([930, 475, 1180, floor_y], radius=12, fill=(40, 42, 50), outline=(70, 72, 82), width=3)
            draw.polygon([(1110, 395), (1145, 395), (1138, 475), (1117, 475)], fill=(235, 238, 245))

    return img


def _draw_clock(draw: ImageDraw.ImageDraw, cx: int, cy: int, t: float) -> None:
    r = 30
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(28, 30, 36), outline=(140, 145, 155), width=3)
    ang_m = t * 4.5
    ang_h = t * 0.6
    draw.line([(cx, cy), (cx + int(20 * math.cos(ang_m)), cy + int(20 * math.sin(ang_m)))], fill=(220, 220, 220), width=2)
    draw.line([(cx, cy), (cx + int(13 * math.cos(ang_h)), cy + int(13 * math.sin(ang_h)))], fill=(220, 220, 220), width=3)


def _draw_stat_bar(draw: ImageDraw.ImageDraw, x: int, y: int, val: int, label: str = "MOOD", scale: float = 1.0) -> None:
    w = int(122 * scale)
    h = int(18 * scale)
    left = x - w // 2
    top = y - int(170 * scale)
    draw.text((left + 2, top - int(22 * scale)), label.upper(), fill=(235, 235, 235), font=FONT_MOOD)
    draw.rounded_rectangle([left, top, left + w, top + h], radius=int(5 * scale), fill=(25, 25, 30), outline=(210, 210, 215), width=2)

    segments = 8
    active = max(1, round((val / 100.0) * segments))
    if val >= 65:
        bar_color = (95, 230, 115) if label in ("HEALTH", "DISCIPLINE") else (245, 200, 55)
    elif val >= 35:
        bar_color = (240, 140, 45)
    else:
        bar_color = (230, 55, 55)

    seg_w = (w - 10) // segments
    for i in range(active):
        sx = left + 5 + i * seg_w
        draw.rectangle([sx, top + 4, sx + seg_w - 3, top + h - 4], fill=bar_color)


def _draw_character(
    draw: ImageDraw.ImageDraw,
    x: int,
    floor_y: int,
    t: float,
    body_color: Tuple[int, int, int] = (238, 236, 228),
    shirt_color: Optional[Tuple[int, int, int]] = None,
    expression: str = "neutral",
    action: str = "stand",
    scale: float = 1.0,
    facing: int = 1,
) -> None:
    """10 xil harakatni bajara oladigan 2D personaj."""
    walking = (action == "walk_in")
    sitting = action in ("sit_play", "sit_sad", "work_desk")
    sleeping = (action == "sleep_bed")

    if sleeping:
        # Krovatda yotgan holat
        bx, by = 230, 445
        draw.ellipse([bx - 95, by - 35, bx - 35, by + 25], fill=body_color, outline=(20, 20, 20), width=3)
        draw.line([(bx - 65, by - 12), (bx - 53, by - 12)], fill=(20, 20, 20), width=3)
        if int(t * 2) % 2 == 0:
            draw.text((bx - 40, by - 75), "zZz", fill=(180, 195, 235), font=FONT_BUBBLE)
        return

    bob = int(abs(math.sin(t * 7.0)) * 6) if walking else int(math.sin(t * 3.0) * 2)
    leg_h = int(48 * scale)
    torso_h = int(68 * scale)
    torso_w = int(52 * scale)
    head_r = int(34 * scale)

    base_y = (floor_y - 25 if sitting else floor_y) - bob
    swing = int(math.sin(t * 7.0) * 18 * scale) if walking else 0

    if sitting:
        draw.rounded_rectangle([x - 22, base_y - 22, x - 6, base_y + 24], radius=7, fill=body_color, outline=(20, 20, 20), width=3)
        draw.rounded_rectangle([x + 6, base_y - 22, x + 22, base_y + 24], radius=7, fill=body_color, outline=(20, 20, 20), width=3)
        torso_bottom = base_y - 15
    else:
        draw.line([(x - 12, base_y - leg_h), (x - 12 - swing, floor_y)], fill=(20, 20, 20), width=int(18 * scale))
        draw.line([(x - 12, base_y - leg_h), (x - 12 - swing, floor_y)], fill=body_color, width=int(12 * scale))
        draw.line([(x + 12, base_y - leg_h), (x + 12 + swing, floor_y)], fill=(20, 20, 20), width=int(18 * scale))
        draw.line([(x + 12, base_y - leg_h), (x + 12 + swing, floor_y)], fill=body_color, width=int(12 * scale))
        torso_bottom = base_y - leg_h + 6

    torso_top = torso_bottom - torso_h
    fill_torso = shirt_color if shirt_color else body_color
    draw.rounded_rectangle(
        [x - torso_w // 2, torso_top, x + torso_w // 2, torso_bottom],
        radius=int(20 * scale), fill=fill_torso, outline=(20, 20, 20), width=3,
    )

    head_cy = torso_top - head_r + 10
    draw.ellipse([x - head_r, head_cy - head_r, x + head_r, head_cy + head_r], fill=body_color, outline=(20, 20, 20), width=3)

    # Qo'llar va buyumlar (Action bo'yicha)
    if action == "sit_play":
        draw.line([(x - torso_w // 2, torso_top + 20), (x - 10, torso_bottom - 18)], fill=body_color, width=11)
        draw.line([(x + torso_w // 2, torso_top + 20), (x + 10, torso_bottom - 18)], fill=body_color, width=11)
        draw.rounded_rectangle([x - 16, torso_bottom - 26, x + 16, torso_bottom - 10], radius=6, fill=(220, 225, 240), outline=(20, 20, 20), width=2)
    elif action == "phone_scroll":
        draw.line([(x + torso_w // 2 - 4, torso_top + 20), (x + 34, torso_top + 5)], fill=body_color, width=11)
        # Yorug' ekranli smartfon
        draw.rounded_rectangle([x + 28, torso_top - 16, x + 46, torso_top + 14], radius=4, fill=(40, 180, 255), outline=(20, 20, 20), width=2)
        draw.polygon([(x + 28, torso_top - 10), (x + 8, head_cy - 10), (x + 8, head_cy + 15)], fill=(60, 150, 220))
    elif action == "workout":
        # Shtanga ko'tarish animatsiyasi
        lift = int(math.sin(t * 4.5) * 28)
        bar_y = torso_top - 25 - lift
        draw.line([(x - 24, torso_top + 16), (x - 32, bar_y)], fill=body_color, width=11)
        draw.line([(x + 24, torso_top + 16), (x + 32, bar_y)], fill=body_color, width=11)
        draw.line([(x - 75, bar_y), (x + 75, bar_y)], fill=(160, 165, 175), width=6)
        draw.rounded_rectangle([x - 78, bar_y - 24, x - 60, bar_y + 24], radius=5, fill=(30, 32, 38), outline=(120, 120, 130), width=2)
        draw.rounded_rectangle([x + 60, bar_y - 24, x + 78, bar_y + 24], radius=5, fill=(30, 32, 38), outline=(120, 120, 130), width=2)
    elif action == "celebrate":
        wave = int(math.sin(t * 8.0) * 12)
        draw.line([(x - torso_w // 2, torso_top + 16), (x - 45, torso_top - 35 + wave)], fill=body_color, width=11)
        draw.line([(x + torso_w // 2, torso_top + 16), (x + 45, torso_top - 35 - wave)], fill=body_color, width=11)
    else:
        arm_swing = -swing // 2
        draw.line([(x - torso_w // 2 + 2, torso_top + 16), (x - torso_w // 2 - 6 + arm_swing, torso_bottom - 6)], fill=body_color, width=int(11 * scale))
        draw.line([(x + torso_w // 2 - 2, torso_top + 16), (x + torso_w // 2 + 6 - arm_swing, torso_bottom - 6)], fill=body_color, width=int(11 * scale))

    # Yuz ifodalari
    ex_offset = 6 * facing
    eye_y = head_cy - 4
    lx, rx = x - 11 + ex_offset, x + 11 + ex_offset

    blink = (int(t * 10) % 35 == 0)
    if blink or expression == "tired":
        draw.line([(lx - 5, eye_y), (lx + 5, eye_y)], fill=(20, 20, 20), width=3)
        draw.line([(rx - 5, eye_y), (rx + 5, eye_y)], fill=(20, 20, 20), width=3)
    else:
        draw.ellipse([lx - 4, eye_y - 4, lx + 4, eye_y + 4], fill=(20, 20, 20))
        draw.ellipse([rx - 4, eye_y - 4, rx + 4, eye_y + 4], fill=(20, 20, 20))

    if expression == "angry":
        draw.line([(lx - 7, eye_y - 11), (lx + 5, eye_y - 6)], fill=(20, 20, 20), width=3)
        draw.line([(rx - 5, eye_y - 6), (rx + 7, eye_y - 11)], fill=(20, 20, 20), width=3)
    elif expression in ("sad", "tired"):
        draw.line([(lx - 6, eye_y - 6), (lx + 5, eye_y - 10)], fill=(20, 20, 20), width=2)
        draw.line([(rx - 5, eye_y - 10), (rx + 6, eye_y - 6)], fill=(20, 20, 20), width=2)
    else:
        draw.line([(lx - 6, eye_y - 9), (lx + 5, eye_y - 9)], fill=(20, 20, 20), width=2)
        draw.line([(rx - 5, eye_y - 9), (rx + 6, eye_y - 9)], fill=(20, 20, 20), width=2)

    mouth_y = head_cy + 12
    mx = x + ex_offset
    if expression in ("happy", "excited") or action == "celebrate":
        draw.arc([mx - 10, mouth_y - 6, mx + 10, mouth_y + 8], 0, 180, fill=(20, 20, 20), width=3)
    elif expression in ("sad", "tired", "angry"):
        draw.arc([mx - 9, mouth_y, mx + 9, mouth_y + 10], 180, 360, fill=(20, 20, 20), width=3)
    else:
        draw.line([(mx - 7, mouth_y + 3), (mx + 7, mouth_y + 3)], fill=(20, 20, 20), width=3)


def _draw_shadow_demon(draw: ImageDraw.ImageDraw, x: int, floor_y: int, t: float, speech: str, scale: float = 1.0) -> None:
    sway = int(math.sin(t * 3.0) * 5)
    sx = x + sway
    top_y = floor_y - int(210 * scale)

    for r in range(8, 1, -2):
        draw.rounded_rectangle([sx - int(34 * scale) - r, top_y + int(45 * scale) - r, sx + int(34 * scale) + r, floor_y], radius=int(24 * scale), outline=(120 + r * 10, 20, 25), width=2)
    draw.rounded_rectangle([sx - int(32 * scale), top_y + int(50 * scale), sx + int(32 * scale), floor_y], radius=int(20 * scale), fill=(8, 8, 10), outline=(210, 45, 45), width=2)
    draw.ellipse([sx - int(38 * scale), top_y - int(10 * scale), sx + int(38 * scale), top_y + int(66 * scale)], fill=(8, 8, 10), outline=(210, 45, 45), width=2)

    ey = top_y + int(24 * scale)
    draw.line([(sx - int(18 * scale), ey - 3), (sx - int(6 * scale), ey + 2)], fill=(255, 55, 55), width=4)
    draw.line([(sx + int(6 * scale), ey + 2), (sx + int(18 * scale), ey - 3)], fill=(255, 55, 55), width=4)
    draw.arc([sx - int(14 * scale), ey + 8, sx + int(14 * scale), ey + 24], 15, 165, fill=(235, 50, 50), width=3)

    if speech:
        chars = max(1, int(len(speech) * min(1.0, t / 1.8)))
        draw.text((sx - 110, top_y - 45), speech[:chars], fill=(245, 65, 65), font=FONT_BUBBLE)


def _draw_speech_bubble(draw: ImageDraw.ImageDraw, x: int, y: int, text: str, t: float, start_delay: float = 0.4) -> None:
    if not text or t < start_delay:
        return
    progress = min(1.0, (t - start_delay) / 1.2)
    shown = text[: max(1, int(len(text) * progress))]

    bbox = draw.textbbox((0, 0), shown, font=FONT_BUBBLE)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    bx1 = max(20, min(WIDTH - tw - 40, x - tw // 2 - 14))
    by1 = max(40, y - th - 26)
    draw.rounded_rectangle([bx1, by1, bx1 + tw + 28, by1 + th + 18], radius=12, fill=(15, 16, 20), outline=(95, 100, 115), width=2)
    draw.text((bx1 + 14, by1 + 7), shown, fill=(240, 240, 245), font=FONT_BUBBLE)


def render_scene_video(
    scene: Dict,
    duration: float,
    audio_path: Path,
    out_mp4: Path,
    theme: Dict,
    hero_shirt: Optional[Tuple[int, int, int]],
    stat_name: str,
    vertical: bool = False,
) -> None:
    width, height, floor_y = get_dimensions(vertical)
    scale = 1.35 if vertical else 1.0

    setting = scene.get("setting", "living_room")
    action = scene.get("action", "stand")
    expression = scene.get("expression", "neutral")
    mood = int(scene.get("mood", 75))
    day_label = scene.get("day_label", "")
    screen_text = scene.get("screen_text", "")
    other_char = scene.get("other_char", "none")
    other_speech = scene.get("other_speech", "")
    hero_speech = scene.get("hero_speech", "")
    has_shadow = bool(scene.get("shadow", False))
    shadow_speech = scene.get("shadow_speech", "")

    bg_base = _create_vignette_bg(setting, theme, width=width, height=height, floor_y=floor_y)
    total_frames = max(1, int(duration * FPS))

    cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo", "-vcodec", "rawvideo",
        "-s", f"{width}x{height}", "-pix_fmt", "rgb24", "-r", str(FPS),
        "-i", "-", "-i", str(audio_path),
        "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-shortest",
        str(out_mp4),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    for frame_idx in range(total_frames):
        t = frame_idx / FPS
        frame = bg_base.copy()
        draw = ImageDraw.Draw(frame)

        if not vertical and setting not in ("basketball", "park", "street"):
            _draw_clock(draw, 1160, 140, t)

        center_x = width // 2
        if action == "walk_in":
            start_x = int(center_x * 0.4)
            hx = min(center_x, int(start_x + t * (145 * scale)))
            cur_action = "walk_in" if hx < center_x else "stand"
        elif action == "work_desk":
            hx = int(width * 0.72) if not vertical else int(center_x * 1.1)
            cur_action = "work_desk"
        elif action == "shoot_hoop":
            hx = int(center_x * 0.8)
            cur_action = "shoot_hoop"
            bp = min(1.0, (t % 2.4) / 1.5)
            bx = int(hx + 30 + bp * (width * 0.75 - hx - 30))
            by = int(floor_y - 110 - math.sin(bp * math.pi) * 240 + bp * 40)
            draw.ellipse([bx - 16, by - 16, bx + 16, by + 16], fill=(230, 105, 35), outline=(20, 20, 20), width=3)
        else:
            hx = center_x
            cur_action = action

        if has_shadow:
            _draw_shadow_demon(draw, hx - int(95 * scale), floor_y, t, shadow_speech, scale=scale)

        if other_char and other_char != "none":
            ox = int(center_x * 0.45) if hx >= center_x else int(center_x * 1.4)
            o_scale = 0.72 * scale if other_char == "brother" else 0.95 * scale
            o_shirt = (90, 145, 115) if other_char == "mom" else ((85, 115, 165) if other_char == "friend" else None)
            _draw_character(
                draw, ox, floor_y, t,
                body_color=(225, 205, 190), shirt_color=o_shirt,
                expression="sad" if mood < 50 else "happy",
                action="stand", scale=o_scale, facing=1 if ox < hx else -1,
            )
            if other_speech:
                _draw_speech_bubble(draw, ox, floor_y - int(185 * o_scale), other_speech, t, start_delay=0.3)

        _draw_character(
            draw, hx, floor_y, t,
            shirt_color=hero_shirt,
            expression=expression,
            action=cur_action,
            scale=scale,
            facing=1,
        )
        stat_x = int(width * 0.3) if cur_action == "sleep_bed" else hx
        _draw_stat_bar(draw, stat_x, floor_y - (15 if cur_action in ("sit_play", "sit_sad", "work_desk") else 0), mood, stat_name, scale=scale)

        if hero_speech:
            _draw_speech_bubble(draw, hx + int(40 * scale), floor_y - int(210 * scale), hero_speech, t, start_delay=1.1)

        if screen_text:
            chars = max(1, int(len(screen_text) * min(1.0, t / 1.4)))
            shown_title = screen_text[:chars]
            bbox = draw.textbbox((0, 0), shown_title, font=FONT_TITLE)
            tw = bbox[2] - bbox[0]
            top_y = 120 if vertical else 56
            draw.text(((width - tw) // 2 + 2, top_y + 2), shown_title, fill=(0, 0, 0), font=FONT_TITLE)
            draw.text(((width - tw) // 2, top_y), shown_title, fill=(245, 245, 250), font=FONT_TITLE)

        if day_label:
            day_x = 36 if vertical else 48
            day_y = height - 100 if vertical else height - 68
            draw.text((day_x, day_y), day_label, fill=theme["accent"], font=FONT_DAY)

        try:
            proc.stdin.write(frame.tobytes())
        except Exception:
            break

    proc.stdin.close()
    proc.wait()


# =====================================================================
# 4-BOSQICH: 4 XIL DINAMIK MUSIQA PROFILI BILAN BIRLASHTIRISH
# =====================================================================
MUSIC_PROFILES = {
    "synthwave": "0.22*sin(2*PI*220*t)+0.18*sin(2*PI*261.63*t)+0.16*sin(2*PI*329.63*t)+0.10*sin(2*PI*440*t*(1+0.2*sin(2*PI*2*t)))",
    "melancholic_ambient": "0.24*sin(2*PI*146.83*t)+0.20*sin(2*PI*174.61*t)+0.16*sin(2*PI*220*t)+0.12*sin(2*PI*261.63*t)",
    "dreamy_lofi": "0.22*sin(2*PI*196.00*t)+0.18*sin(2*PI*246.94*t)+0.16*sin(2*PI*293.66*t)+0.14*sin(2*PI*349.23*t)",
    "retro_chiptune": "0.20*sin(2*PI*261.63*t)+0.16*sin(2*PI*329.63*t)+0.14*sin(2*PI*392.00*t)+0.12*sin(2*PI*523.25*t)",
}


def concat_and_add_music(scene_clips: List[Path], final_path: Path) -> Path:
    music_style, expr = random.choice(list(MUSIC_PROFILES.items()))
    log(f"[4/5] Sahnalar birlashtirilmoqda (Musiqa uslubi: {music_style})...")
    work_dir = final_path.parent
    concat_list = work_dir / "scenes_concat.txt"

    with open(concat_list, "w", encoding="utf-8") as f:
        for clip in scene_clips:
            f.write(f"file '{clip.name}'\n")

    merged_raw = work_dir / "merged_scenes.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "scenes_concat.txt", "-c", "copy", merged_raw.name],
        cwd=str(work_dir), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True,
    )

    total_dur = get_media_duration(merged_raw)
    cmd = [
        "ffmpeg", "-y",
        "-i", merged_raw.name,
        "-f", "lavfi",
        "-i", f"aevalsrc='{expr}':s=44100:d={total_dur:.2f}",
        "-filter_complex",
        f"[0:a]volume=1.0[v];[1:a]lowpass=f=850,volume=0.13,afade=t=in:st=0:d=1.5,"
        f"afade=t=out:st={max(0.0, total_dur - 2.5):.2f}:d=2.5[bg];"
        f"[v][bg]amix=inputs=2:duration=first[aout]",
        "-map", "0:v", "-map", "[aout]",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        final_path.name,
    ]
    subprocess.run(cmd, cwd=str(work_dir), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    log(f"  [+] Tayyor 2D Animatsion video saqlandi: {final_path}")
    return final_path


# =====================================================================
# 5-BOSQICH: YOUTUBE KANALGA AVTOMATIK YUKLASH
# =====================================================================
def _resolve_client_secrets() -> str:
    if os.path.exists(CLIENT_SECRETS_FILE):
        return CLIENT_SECRETS_FILE
    if os.path.exists("client_secrets.json.json"):
        return "client_secrets.json.json"
    raise FileNotFoundError(f"'{CLIENT_SECRETS_FILE}' topilmadi!")


def upload_to_youtube(video_path: Path, metadata: Dict, lang: str = "en", privacy_status: str = "public", token_file: Optional[str] = None, gmail: Optional[str] = None) -> str:
    import channel_manager
    tf = token_file or TOKEN_FILE
    target_gmail = gmail or DEFAULT_GMAIL
    log(f"[5/5] YouTube kanalga yuklanmoqda ({video_path.name}) | Gmail: {target_gmail}...")
    return channel_manager.upload_video_to_youtube(
        video_path=video_path,
        metadata=metadata,
        token_file=tf,
        login_hint=target_gmail,
        lang=lang,
        privacy_status=privacy_status,
        category_id="1",  # Film & Animation
    )


# =====================================================================
# ASOSIY PIPELINE
# =====================================================================
def run_story_pipeline(
    topic: Optional[str] = None,
    lang: str = "en",
    voice: Optional[str] = None,
    upload: bool = True,
    privacy: str = "public",
    token_file: Optional[str] = None,
    gmail: Optional[str] = None,
    vertical: bool = False,
) -> None:
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    prefix = "story_shorts" if vertical else "story"
    work_dir = OUTPUT_DIR / f"{prefix}_{lang}_{timestamp}"
    work_dir.mkdir(parents=True, exist_ok=True)

    target_gmail = gmail or DEFAULT_GMAIL
    selected_token = token_file or TOKEN_FILE

    lang_cfg = LANGUAGE_CONFIG.get(lang, LANGUAGE_CONFIG["en"])
    selected_voice = voice or random.choice(lang_cfg["voices"])
    selected_theme = random.choice(COLOR_THEMES)
    selected_shirt = random.choice(HERO_SHIRT_COLORS)

    # 1. Ssenariy
    metadata = generate_story_script(topic=topic, lang=lang, vertical=vertical)
    with open(work_dir / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    stat_name = metadata.get("stat_name", "MOOD")
    log(f"  Sarlavha: {metadata['title']}")
    log(f"  Kanal (Gmail): {target_gmail} | Format: {'9:16 Shorts' if vertical else '16:9 Keng'} | Shkala: {stat_name}")

    scenes = metadata["scenes"]

    # 2. Diktor ovozlari
    scene_audios = generate_all_scene_voices(scenes, work_dir, selected_voice)

    # 3. Har bir sahnani chizish
    log(f"[3/5] 2D Animatsiya sahnalari chizilmoqda ({len(scenes)} ta sahna)...")
    scene_clips: List[Path] = []
    for idx, (scene, (audio_file, dur)) in enumerate(zip(scenes, scene_audios)):
        scene_mp4 = work_dir / f"scene_clip_{idx:02d}.mp4"
        render_scene_video(
            scene, dur, audio_file, scene_mp4,
            theme=selected_theme, hero_shirt=selected_shirt, stat_name=stat_name,
            vertical=vertical,
        )
        scene_clips.append(scene_mp4)
        log(f"  [+] Sahna {idx + 1}/{len(scenes)} chizildi [{scene.get('setting')} | {stat_name}: {scene.get('mood')}%]")

    # 4. Birlashtirish va musiqa
    final_video = work_dir / f"final_{prefix}_{lang}_{timestamp}.mp4"
    concat_and_add_music(scene_clips, final_video)

    # 5. YouTube'ga yuklash
    if upload:
        upload_to_youtube(final_video, metadata, lang=lang, privacy_status=privacy, token_file=selected_token, gmail=target_gmail)
    else:
        log(f"  [i] Yuklash o'tkazib yuborildi (--no-upload). Tayyor fayl: {final_video}")


def main():
    import channel_manager
    parser = argparse.ArgumentParser(description="YouTube 2D Story Animation AI Agent — jasuryurak6@gmail.com Edition")
    parser.add_argument("--lang", choices=list(LANGUAGE_CONFIG.keys()), default="en", help="Til: en, uz, ru")
    parser.add_argument("--topic", type=str, default=None, help="Maxsus hikoya mavzusi")
    parser.add_argument("--voice", type=str, default=None, help="Maxsus diktor ovozi")
    parser.add_argument("--privacy", choices=["public", "unlisted", "private"], default="public")
    parser.add_argument("--gmail", type=str, default=None, help="YouTube yuklanadigan Gmail manzili")
    parser.add_argument("--token-file", type=str, default=None, help="YouTube OAuth token fayli")
    parser.add_argument("--no-upload", action="store_true", help="Faqat videoni yaratish (yuklamasdan)")
    parser.add_argument("--vertical", action="store_true", help="9:16 Vertikal format (YouTube Shorts)")
    args = parser.parse_args()

    chosen_token, chosen_gmail = None, None
    if not args.no_upload:
        if args.gmail or args.token_file:
            chosen_token, chosen_gmail = channel_manager.resolve_account_info(args.gmail or args.token_file, default_email=DEFAULT_GMAIL)
        else:
            chosen_token, chosen_gmail = channel_manager.prompt_account_selection_cli(default_email=DEFAULT_GMAIL)

    user_topic = args.topic
    if not user_topic and sys.stdin.isatty():
        fmt_str = "9:16 YouTube Shorts" if args.vertical else "16:9 Standart Video"
        print("\n=======================================================", flush=True)
        print(f"📖 2D Animatsion Hikoyalar ({fmt_str}) | jasuryurak6@gmail.com", flush=True)
        print("=======================================================", flush=True)
        print("💡 125+ ta saralangan psixologik, intizom va hayotiy mavzular mavjud.", flush=True)
        val = input("Maxsus mavzu kiriting (yoki tasodifiy tanlash uchun Enter bosing): ").strip()
        if val:
            user_topic = val

    run_story_pipeline(
        topic=user_topic,
        lang=args.lang,
        voice=args.voice,
        upload=not args.no_upload,
        privacy=args.privacy,
        token_file=chosen_token,
        gmail=chosen_gmail,
        vertical=args.vertical,
    )


if __name__ == "__main__":
    main()
