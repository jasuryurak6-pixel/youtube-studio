#!/usr/bin/env python3
"""
YouTube Cosmic & World Facts AI Agent — MULTI-LANGUAGE & DYNAMIC CUTS (16:9)
Barcha xatoliklar to'liq tuzatilgan, toza versiya.
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
from typing import Dict, List, Optional

import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY")
PIXABAY_API_KEY = os.environ.get("PIXABAY_API_KEY", "YOUR_PIXABAY_API_KEY")

LANGUAGE_CONFIG: Dict[str, Dict] = {
    "uz": {
        "name": "Uzbek (Latin script, O'zbek tili)",
        "yt_code": "uz",
        "default_voice": "uz-UZ-SardorNeural",
        "voices": ["uz-UZ-SardorNeural", "uz-UZ-MadinaNeural"],
        "hashtags": "#koinot #faktlar #ilm #fan #uzbekistan #qiziqarli",
    },
    "en": {
        "name": "English",
        "yt_code": "en",
        "default_voice": "en-US-ChristopherNeural",
        "voices": ["en-US-ChristopherNeural", "en-GB-RyanNeural", "en-US-GuyNeural", "en-US-AriaNeural"],
        "hashtags": "#universe #space #facts #science #cosmos",
    },
    "ru": {
        "name": "Russian (Русский язык)",
        "yt_code": "ru",
        "default_voice": "ru-RU-DmitryNeural",
        "voices": ["ru-RU-DmitryNeural", "ru-RU-SvetlanaNeural"],
        "hashtags": "#космос #факты #наука #вселенная",
    },
    "tr": {
        "name": "Turkish (Türkçe)",
        "yt_code": "tr",
        "default_voice": "tr-TR-AhmetNeural",
        "voices": ["tr-TR-AhmetNeural", "tr-TR-EmelNeural"],
        "hashtags": "#evren #uzay #bilim #ilginçbilgiler",
    },
}

try:
    from topics_database import COSMIC_FACTS_TOPICS
    TOPIC_POOL = COSMIC_FACTS_TOPICS
except ImportError:
    TOPIC_POOL = [
        "mind-blowing facts about black holes and neutron stars",
        "mysterious phenomena in the deep ocean and Earth's core",
        "the unbelievable scale of the observable universe and galaxies",
    ]


FALLBACK_QUERIES = [
    "galaxy stars", "deep space", "planet earth", "nebula cosmos",
    "black hole", "night sky stars", "solar system", "astronaut space",
]

OUTPUT_DIR = Path("output_videos")
CLIENT_SECRETS_FILE = "client_secrets.json"
DEFAULT_GMAIL = "youtubekanal0004@gmail.com"
TOKEN_FILE = "token_youtubekanal0004.json"
YOUTUBE_SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

TARGET_W, TARGET_H = 1920, 1080
GEMINI_MODEL_CHAIN = ["gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-flash-latest", "gemini-flash-lite-latest", "gemini-3.8-flash"]


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


def pick_unique_fact_topic(custom_topic: Optional[str] = None, lang: str = "uz") -> str:
    """Oldin ishlatilgan faktlar mavzularini takrorlamasdan yangisini tanlaydi."""
    if custom_topic and custom_topic.strip():
        return custom_topic.strip()

    used: List[str] = []
    used_file = Path("used_topics_facts.json")
    if used_file.exists():
        try:
            used = json.loads(used_file.read_text(encoding="utf-8"))
        except Exception:
            used = []

    try:
        from topics_database import COSMIC_FACTS_TOPICS_UZ, COSMIC_FACTS_TOPICS_EN
        pool = COSMIC_FACTS_TOPICS_UZ if lang.startswith("uz") else COSMIC_FACTS_TOPICS_EN
    except Exception:
        pool = TOPIC_POOL

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


def generate_fact_script(topic: Optional[str] = None, lang: str = "uz") -> Dict:
    from google import genai
    from google.genai import types

    topic = pick_unique_fact_topic(topic, lang=lang)

    lang_info = LANGUAGE_CONFIG.get(lang, LANGUAGE_CONFIG["en"])
    lang_name = lang_info["name"]
    hashtags = lang_info["hashtags"]

    try:
        client = genai.Client(api_key=GEMINI_API_KEY, http_options=types.HttpOptions(timeout=45000))
    except Exception:
        client = genai.Client(api_key=GEMINI_API_KEY)

    prompt = f"""
    You are an expert scriptwriter for a viral YouTube documentary channel about the Universe, Science, and the World.
    Topic: {topic}
    Target Narration & Metadata Language: {lang_name}
    Target length: 3 to 4 minutes (around 400-550 words), engaging documentary style.

    Requirements:
    1. Write `title`, `description`, `tags`, and `narration` strictly in {lang_name}.
    2. Start `narration` with a powerful hook in the first sentence.
    3. Share 100% real, scientifically accurate, awe-inspiring facts.
    4. Provide ONLY raw spoken text in `narration`.
    5. IMPORTANT: Provide 12 to 15 simple, 2-word visual `search_queries` strictly in ENGLISH so Pixabay can easily find videos (e.g., "spiral galaxy", "deep ocean", "planet earth", "supernova stars").

    Return strictly valid JSON with this exact schema:
    {{
      "title": "Catchy SEO title in {lang_name} (max 70 chars)",
      "description": "SEO description in {lang_name} with summary and hashtags ({hashtags})",
      "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
      "narration": "Full spoken script in {lang_name}...",
      "search_queries": ["spiral galaxy", "planet earth", "black hole", "astronaut space"]
    }}
    """

    log(f"[1/6] Ssenariy yaratilmoqda (Til: {lang_name} | Mavzu: {topic})...")

    last_error: Optional[Exception] = None
    for model_name in GEMINI_MODEL_CHAIN:
        for attempt in range(1, 3):
            try:
                log(f"  -> {model_name} ga so'rov yuborilmoqda (urinish {attempt}/2)...")
                response = client.models.generate_content(
                    model=model_name, contents=prompt,
                    config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.75),
                )
                data = json.loads(_clean_json_text(response.text))
                if not data.get("narration"):
                    raise ValueError("Bo'sh ssenariy qaytdi")
                log(f"  [+] Ssenariy tayyor ({model_name} orqali).")
                return data
            except Exception as exc:
                last_error = exc
                log(f"  [!] {model_name} xatosi: {exc}")
                time.sleep(3)

    raise RuntimeError(f"Gemini'dan ssenariy olinmadi. Oxirgi xatolik: {last_error}")


def _build_proportional_srt(narration: str, total_duration: float) -> str:
    words = narration.split()
    if not words or total_duration <= 0:
        return ""
    chunk_size = 7
    chunks = [" ".join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]
    total_chars = sum(len(c) for c in chunks) or 1

    def fmt_time(sec: float) -> str:
        hrs, mins, secs = int(sec // 3600), int((sec % 3600) // 60), int(sec % 60)
        ms = int((sec - int(sec)) * 1000)
        return f"{hrs:02d}:{mins:02d}:{secs:02d},{ms:03d}"

    srt_lines = []
    curr_t = 0.0
    for idx, chunk in enumerate(chunks, start=1):
        dur = total_duration * (len(chunk) / total_chars)
        end_t = min(total_duration, curr_t + dur)
        srt_lines.append(f"{idx}\n{fmt_time(curr_t)} --> {fmt_time(end_t)}\n{chunk}\n")
        curr_t = end_t
    return "\n".join(srt_lines)


async def generate_voiceover_and_srt(narration: str, audio_path: Path, srt_path: Path, voice: str) -> None:
    import edge_tts
    log(f"[2/6] Ovoz va subtitr yaratilmoqda (Ovoz: {voice})...")
    communicate = edge_tts.Communicate(narration, voice, rate="+2%")
    submaker = edge_tts.SubMaker()

    with open(audio_path, "wb") as audio_file:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_file.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                try:
                    submaker.feed(chunk)
                except Exception:
                    pass

    srt_content = ""
    if hasattr(submaker, "get_srt"):
        try:
            srt_content = submaker.get_srt()
        except Exception:
            pass

    if not srt_content.strip() or len(srt_content.splitlines()) > 600:
        audio_dur = get_media_duration(audio_path)
        srt_content = _build_proportional_srt(narration, audio_dur)
        log("  [i] Subtitr audio davomiyligi bo'yicha tekis qatorlarga sinxronlandi.")
    else:
        log("  [i] Subtitr muvaffaqiyatli yaratildi.")

    with open(srt_path, "w", encoding="utf-8") as srt_file:
        srt_file.write(srt_content)


def get_media_duration(file_path: Path) -> float:
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(file_path)]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(result.stdout.strip())


def mix_cosmic_ambient_audio(voice_path: Path, mixed_audio_path: Path, custom_music_path: Optional[Path] = None) -> Path:
    log("[3/6] Kosmik fon musiqasi ovoz bilan birlashtirilmoqda...")
    duration = get_media_duration(voice_path)

    if custom_music_path and custom_music_path.exists():
        cmd = [
            "ffmpeg", "-y", "-i", str(voice_path), "-stream_loop", "-1", "-i", str(custom_music_path),
            "-filter_complex",
            f"[0:a]volume=1.0[v];[1:a]atrim=0:{duration:.2f},volume=0.12,afade=t=out:st={max(0.0, duration - 2.0):.2f}:d=2.0[bg];"
            f"[v][bg]amix=inputs=2:duration=first:dropout_transition=2[out]",
            "-map", "[out]", "-c:a", "aac", "-b:a", "192k", str(mixed_audio_path),
        ]
    else:
        expr = "0.25*sin(2*PI*110*t)+0.20*sin(2*PI*164.81*t)+0.18*sin(2*PI*220*t)+0.15*sin(2*PI*261.63*t)+0.12*sin(2*PI*329.63*t)"
        cmd = [
            "ffmpeg", "-y", "-i", str(voice_path), "-f", "lavfi", "-i", f"aevalsrc='{expr}':s=44100:d={duration:.2f}",
            "-filter_complex",
            f"[0:a]volume=1.0[v];[1:a]lowpass=f=600,volume=0.10,afade=t=in:st=0:d=1.5,afade=t=out:st={max(0.0, duration - 2.0):.2f}:d=2.0[bg];"
            f"[v][bg]amix=inputs=2:duration=first[out]",
            "-map", "[out]", "-c:a", "aac", "-b:a", "192k", str(mixed_audio_path),
        ]

    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    return mixed_audio_path


def download_pixabay_videos(queries: List[str], download_dir: Path, clips_per_query: int = 2) -> List[Path]:
    log("[4/6] Pixabay'dan ko'p kadrli HD fon videolari qidirilmoqda va yuklanmoqda...")
    downloaded_files: List[Path] = []
    seen_video_ids = set()
    clip_counter = 0
    all_queries = list(queries) + [q for q in FALLBACK_QUERIES if q not in queries]

    # Linkni bo'lib yozamiz, toki nusxalaganingizda chat uni buzib qo'ymasin
    prot = "http" + "s://"
    domen = "pixabay" + ".com"
    manzil = prot + domen + "/api/videos/"

    for query in all_queries:
        if len(downloaded_files) >= 24:
            break
            
        safe_query = requests.utils.quote(query)
        url = f"{manzil}?key={PIXABAY_API_KEY}&q={safe_query}&per_page=15&safesearch=true"
        
        try:
            resp = requests.get(url, timeout=20)
            if resp.status_code != 200: continue
            hits = resp.json().get("hits", [])
        except Exception as exc:
            log(f"  [!] Tarmoq xatosi ({query}): {exc}")
            continue

        available_hits = [h for h in hits if h.get("id") not in seen_video_ids]
        if not available_hits: continue

        random.shuffle(available_hits)
        selected_hits = available_hits[:clips_per_query]

        for video_data in selected_hits:
            vid_id = video_data.get("id")
            video_variants = video_data.get("videos", {})
            best_file = video_variants.get("medium") or video_variants.get("large") or video_variants.get("small")
            if not best_file or not best_file.get("url"): continue

            clip_path = download_dir / f"clip_{clip_counter:03d}.mp4"
            try:
                with requests.get(best_file["url"], stream=True, timeout=45) as r:
                    r.raise_for_status()
                    with open(clip_path, "wb") as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            f.write(chunk)
                seen_video_ids.add(vid_id)
                downloaded_files.append(clip_path)
                clip_counter += 1
                log(f"  [+] Yuklandi: {clip_path.name} ({query})")
            except Exception as exc:
                log(f"  [!] Yuklashda xato ({query}): {exc}")

    if not downloaded_files:
        raise RuntimeError("Fon videolari yuklanmadi. PIXABAY_API_KEY ni tekshiring.")
    log(f"  [i] Jami {len(downloaded_files)} ta noyob kadr yuklab olindi.")
    return downloaded_files


def assemble_video(clips: List[Path], audio_path: Path, srt_path: Path, output_path: Path, clip_duration: float = 4.5) -> Path:
    log(f"[5/6] FFmpeg orqali dinamik montaj qilinmoqda (har bir kadr: ~{clip_duration}s)...")
    audio_duration = get_media_duration(audio_path)
    work_dir = output_path.parent

    normalized_clips: List[Path] = []
    for i, clip in enumerate(clips):
        norm_clip = work_dir / f"norm_{i:03d}.mp4"
        vf_filter = f"scale={TARGET_W}:{TARGET_H}:force_original_aspect_ratio=increase,crop={TARGET_W}:{TARGET_H},fps=30,format=yuv420p"
        cmd = [
            "ffmpeg", "-y", "-stream_loop", "-1", "-i", str(clip), "-t", f"{clip_duration:.2f}",
            "-vf", vf_filter, "-an", "-c:v", "libx264", "-preset", "fast", str(norm_clip)
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        normalized_clips.append(norm_clip)

    total_segments_needed = math.ceil(audio_duration / clip_duration) + 1
    sequence: List[Path] = []
    last_clip: Optional[Path] = None

    while len(sequence) < total_segments_needed:
        batch = normalized_clips.copy()
        random.shuffle(batch)
        if last_clip is not None and len(batch) > 1 and batch[0] == last_clip:
            batch[0], batch[-1] = batch[-1], batch[0]
        sequence.extend(batch)
        last_clip = sequence[-1]

    sequence = sequence[:total_segments_needed]
    concat_list = work_dir / "concat_list.txt"
    with open(concat_list, "w", encoding="utf-8") as f:
        for nc in sequence: f.write(f"file '{nc.name}'\n")

    subtitle_style = "FontName=Arial,FontSize=22,PrimaryColour=&H0000FFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=1,Alignment=2,MarginV=50"
    has_valid_srt = srt_path.exists() and srt_path.stat().st_size > 0
    vf_value = f"subtitles={srt_path.name}:force_style='{subtitle_style}'" if has_valid_srt else f"scale={TARGET_W}:{TARGET_H}"

    final_cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "concat_list.txt", "-i", audio_path.name,
        "-t", f"{audio_duration:.2f}", "-vf", vf_value, "-c:v", "libx264", "-preset", "medium", "-crf", "21",
        "-c:a", "aac", "-b:a", "192k", "-shortest", output_path.name,
    ]
    subprocess.run(final_cmd, check=True, cwd=str(work_dir))
    log(f"  [+] Tayyor video saqlandi: {output_path}")
    return output_path


def _resolve_client_secrets() -> str:
    if os.path.exists(CLIENT_SECRETS_FILE): return CLIENT_SECRETS_FILE
    if os.path.exists("client_secrets.json.json"): return "client_secrets.json.json"
    raise FileNotFoundError(f"'{CLIENT_SECRETS_FILE}' topilmadi!")


def upload_to_youtube(video_path: Path, metadata: Dict, lang: str = "uz", privacy_status: str = "public", token_file: Optional[str] = None, gmail: Optional[str] = None) -> str:
    import channel_manager
    tf = token_file or TOKEN_FILE
    target_gmail = gmail or DEFAULT_GMAIL
    log(f"[6/6] YouTube kanalga yuklanmoqda ({video_path.name}) | Gmail: {target_gmail}...")
    return channel_manager.upload_video_to_youtube(
        video_path=video_path,
        metadata=metadata,
        token_file=tf,
        login_hint=target_gmail,
        lang=lang,
        privacy_status=privacy_status,
        category_id="28",  # Science & Technology
    )


def run_agent_pipeline(
    topic: Optional[str] = None,
    lang: str = "uz",
    voice: Optional[str] = None,
    clip_duration: float = 4.5,
    upload: bool = True,
    privacy: str = "public",
    music_file: Optional[str] = None,
    token_file: Optional[str] = None,
    gmail: Optional[str] = None,
) -> None:
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    work_dir = OUTPUT_DIR / f"video_{lang}_{timestamp}"
    work_dir.mkdir(parents=True, exist_ok=True)

    target_gmail = gmail or DEFAULT_GMAIL
    selected_token = token_file or TOKEN_FILE

    lang_cfg = LANGUAGE_CONFIG.get(lang, LANGUAGE_CONFIG["uz"])
    selected_voice = voice or lang_cfg["default_voice"]

    try:
        metadata = generate_fact_script(topic=topic, lang=lang)
        with open(work_dir / "metadata.json", "w", encoding="utf-8") as f: json.dump(metadata, f, indent=2, ensure_ascii=False)
        log(f"  Sarlavha: {metadata['title']}")
        log(f"  Kanal (Gmail): {target_gmail}")

        raw_voice_path = work_dir / "voiceover_raw.mp3"
        srt_path = work_dir / "subtitles.srt"
        asyncio.run(generate_voiceover_and_srt(metadata["narration"], raw_voice_path, srt_path, voice=selected_voice))

        mixed_audio_path = work_dir / "voiceover_mixed.m4a"
        custom_music = Path(music_file) if music_file else None
        mix_cosmic_ambient_audio(raw_voice_path, mixed_audio_path, custom_music)

        clips = download_pixabay_videos(metadata["search_queries"], work_dir, clips_per_query=2)

        final_video_path = work_dir / f"final_{lang}_{timestamp}.mp4"
        assemble_video(clips, mixed_audio_path, srt_path, final_video_path, clip_duration=clip_duration)

        if upload:
            upload_to_youtube(final_video_path, metadata, lang=lang, privacy_status=privacy, token_file=selected_token, gmail=target_gmail)
        else:
            log(f"  [i] Yuklash o'tkazib yuborildi (--no-upload). Tayyor fayl: {final_video_path}")

    except Exception as exc:
        log(f"  [XATOLIK] Pipeline to'xtadi: {exc}")
        log(f"  Ish papkasi: {work_dir.resolve()}")
        raise


def main():
    import channel_manager
    parser = argparse.ArgumentParser(description="YouTube Cosmic & Facts AI Agent — youtubekanal0004@gmail.com")
    parser.add_argument("--lang", choices=list(LANGUAGE_CONFIG.keys()), default="uz")
    parser.add_argument("--topic", type=str, default=None)
    parser.add_argument("--voice", type=str, default=None)
    parser.add_argument("--clip-duration", type=float, default=4.5)
    parser.add_argument("--music", type=str, default=None)
    parser.add_argument("--privacy", choices=["public", "unlisted", "private"], default="public")
    parser.add_argument("--gmail", type=str, default=None, help="YouTube yuklanadigan Gmail manzili")
    parser.add_argument("--token-file", type=str, default=None)
    parser.add_argument("--no-upload", action="store_true")
    parser.add_argument("--schedule", type=str, default=None)
    args = parser.parse_args()

    chosen_token, chosen_gmail = None, None
    if not args.no_upload:
        if args.gmail or args.token_file:
            chosen_token, chosen_gmail = channel_manager.resolve_account_info(args.gmail or args.token_file, default_email=DEFAULT_GMAIL)
        else:
            chosen_token, chosen_gmail = channel_manager.prompt_account_selection_cli(default_email=DEFAULT_GMAIL)

    user_topic = args.topic
    if not user_topic and sys.stdin.isatty() and not args.schedule:
        print("\n=======================================================", flush=True)
        print("🌌 Kosmik va Dunyo Faktlari (youtubekanal0004@gmail.com)", flush=True)
        print("=======================================================", flush=True)
        print("💡 125+ ta saralangan koinot, fan va dunyo sirlari mavzulari mavjud.", flush=True)
        val = input("Maxsus mavzu kiriting (yoki tasodifiy tanlash uchun Enter bosing): ").strip()
        if val:
            user_topic = val

    if args.schedule:
        import schedule
        log(f"[*] Agent har kuni soat {args.schedule} da ({args.lang} tilida | {chosen_gmail}) ishga tushadi...")
        schedule.every().day.at(args.schedule).do(
            run_agent_pipeline,
            topic=user_topic,
            lang=args.lang,
            voice=args.voice,
            clip_duration=args.clip_duration,
            upload=not args.no_upload,
            privacy=args.privacy,
            music_file=args.music,
            token_file=chosen_token,
            gmail=chosen_gmail,
        )
        while True:
            schedule.run_pending()
            time.sleep(30)
    else:
        run_agent_pipeline(
            topic=user_topic,
            lang=args.lang,
            voice=args.voice,
            clip_duration=args.clip_duration,
            upload=not args.no_upload,
            privacy=args.privacy,
            music_file=args.music,
            token_file=chosen_token,
            gmail=chosen_gmail,
        )

if __name__ == "__main__":
    main()
