#!/usr/bin/env python3
"""
YouTube Viral Shorts AI Agent — 9:16 VERTICAL FORMAT (Shorts / Reels / TikTok)
Tezkor o'sadigan vertikal qisqa videolar generatsiyasi.
"""

import argparse
import asyncio
import json
import math
import os
import random
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional

import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
PIXABAY_API_KEY = os.environ.get("PIXABAY_API_KEY", "")

LANGUAGE_CONFIG: Dict[str, Dict] = {
    "uz": {
        "name": "Uzbek (Latin script, O'zbek tili)",
        "yt_code": "uz",
        "default_voice": "uz-UZ-SardorNeural",
        "voices": ["uz-UZ-SardorNeural", "uz-UZ-MadinaNeural"],
        "hashtags": "#shorts #qiziqarli #faktlar #uzbekistan #top #trend",
    },
    "en": {
        "name": "English",
        "yt_code": "en",
        "default_voice": "en-US-ChristopherNeural",
        "voices": ["en-US-ChristopherNeural", "en-US-GuyNeural", "en-US-AriaNeural"],
        "hashtags": "#shorts #facts #viral #interesting #didyouknow #fyp",
    },
    "ru": {
        "name": "Russian (Русский язык)",
        "yt_code": "ru",
        "default_voice": "ru-RU-DmitryNeural",
        "voices": ["ru-RU-DmitryNeural", "ru-RU-SvetlanaNeural"],
        "hashtags": "#shorts #факты #топ #интересно #шортс #наука",
    },
    "tr": {
        "name": "Turkish (Türkçe)",
        "yt_code": "tr",
        "default_voice": "tr-TR-AhmetNeural",
        "voices": ["tr-TR-AhmetNeural", "tr-TR-EmelNeural"],
        "hashtags": "#shorts #bilgi #ilginç #fyp #trend #türkiye",
    },
}

SHORTS_TOPICS = [
    "3 mind-bending optical illusions and how your brain gets fooled",
    "the terrifying sound of Saturn's rings recorded by NASA",
    "what happens to your body when you stop eating sugar for 14 days",
    "the deepest artificial hole ever drilled into planet Earth",
    "the smartest animal alive that you never knew about",
    "why astronaut spacesuits cost over 12 million dollars",
    "unsolved ancient mysteries that modern science cannot explain",
    "the psychology trick to instantly read anyone in 5 seconds",
    "what would happen if the Earth stopped spinning for just 1 second",
    "the richest person who ever lived in human history",
]

OUTPUT_DIR = Path("output_videos")
TARGET_W, TARGET_H = 1080, 1920
GEMINI_MODEL_CHAIN = ["gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-flash-latest", "gemini-flash-lite-latest", "gemini-3.8-flash"]


import sys

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


def generate_shorts_script(topic: Optional[str] = None, lang: str = "uz") -> Dict:
    from google import genai
    from google.genai import types

    if not topic:
        topic = random.choice(SHORTS_TOPICS)

    lang_info = LANGUAGE_CONFIG.get(lang, LANGUAGE_CONFIG["uz"])
    lang_name = lang_info["name"]
    hashtags = lang_info["hashtags"]

    try:
        client = genai.Client(api_key=GEMINI_API_KEY, http_options=types.HttpOptions(timeout=45000))
    except Exception:
        client = genai.Client(api_key=GEMINI_API_KEY)

    prompt = f"""
    You are an expert scriptwriter for viral YouTube Shorts, TikTok, and Instagram Reels (9:16).
    Topic: {topic}
    Language: {lang_name}
    Target duration: 35 to 50 seconds (around 80-110 words maximum). Fast-paced, explosive hook.

    Format requirements:
    1. First sentence must be an irresistible psychological HOOK (grab attention in first 2 seconds).
    2. Quick, shocking facts or story delivery.
    3. Ending with a thought-provoking question or call to action.
    4. Provide 8 to 10 visual 2-word English search queries for Pixabay clips.

    Return strictly valid JSON:
    {{
      "title": "Shocking title in {lang_name} #shorts (max 60 chars)",
      "description": "Shorts description in {lang_name} with {hashtags}",
      "tags": ["shorts", "viral", "facts"],
      "narration": "Full spoken script in {lang_name}...",
      "search_queries": ["neon brain", "galaxy spiral", "shocking human", "deep ocean", "earth rotate"]
    }}
    """

    log(f"[1/5] YouTube Shorts ssenariysi yozilmoqda (Til: {lang_name} | Mavzu: {topic})...")
    for model_name in GEMINI_MODEL_CHAIN:
        for attempt in range(1, 3):
            try:
                response = client.models.generate_content(
                    model=model_name, contents=prompt,
                    config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.85),
                )
                data = json.loads(_clean_json_text(response.text))
                if data.get("narration"):
                    log(f"  [+] Shorts ssenariysi tayyor ({model_name}).")
                    return data
            except Exception as exc:
                log(f"  [!] {model_name} xatosi: {exc}")
                time.sleep(2)

    raise RuntimeError("Gemini'dan Shorts ssenariysi olinmadi.")


def get_media_duration(file_path: Path) -> float:
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(file_path)]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(result.stdout.strip())


async def generate_voiceover_and_srt(narration: str, audio_path: Path, srt_path: Path, voice: str) -> None:
    import edge_tts
    log(f"[2/5] Tezkor diktor ovozi yaratilmoqda (Ovoz: {voice})...")
    
    for attempt in range(1, 4):
        try:
            communicate = edge_tts.Communicate(narration, voice, rate="+7%")
            submaker = edge_tts.SubMaker()
            with open(audio_path, "wb") as f:
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        f.write(chunk["data"])
                    elif chunk["type"] == "WordBoundary":
                        try: submaker.feed(chunk)
                        except Exception: pass
            if audio_path.exists() and audio_path.stat().st_size > 0:
                break
        except Exception:
            if attempt == 3: raise
            await asyncio.sleep(1.0)

    # Shorts uchun maxsus 3-4 so'zlik ixcham subtitr yasaymiz
    words = narration.split()
    audio_dur = get_media_duration(audio_path)
    chunk_size = 4
    chunks = [" ".join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]
    total_chars = sum(len(c) for c in chunks) or 1

    def fmt_time(sec: float) -> str:
        hrs, mins, secs = int(sec // 3600), int((sec % 3600) // 60), int(sec % 60)
        ms = int((sec - int(sec)) * 1000)
        return f"{hrs:02d}:{mins:02d}:{secs:02d},{ms:03d}"

    srt_lines = []
    curr_t = 0.0
    for idx, chunk in enumerate(chunks, start=1):
        dur = audio_dur * (len(chunk) / total_chars)
        end_t = min(audio_dur, curr_t + dur)
        srt_lines.append(f"{idx}\n{fmt_time(curr_t)} --> {fmt_time(end_t)}\n{chunk.upper()}\n")
        curr_t = end_t

    with open(srt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(srt_lines))


def mix_shorts_audio(voice_path: Path, mixed_audio_path: Path) -> Path:
    log("[3/5] Ritmik fon musiqasi ulanmoqda...")
    duration = get_media_duration(voice_path)
    # Shorts uchun dinamik bas va ritm
    expr = "0.20*sin(2*PI*130*t)+0.15*sin(2*PI*195*t)+0.12*sin(2*PI*260*t)+0.08*sin(2*PI*390*t)"
    cmd = [
        "ffmpeg", "-y", "-i", str(voice_path), "-f", "lavfi", "-i", f"aevalsrc='{expr}':s=44100:d={duration:.2f}",
        "-filter_complex",
        f"[0:a]volume=1.05[v];[1:a]volume=0.08,afade=t=in:st=0:d=1.0,afade=t=out:st={max(0.0, duration - 1.5):.2f}:d=1.5[bg];"
        f"[v][bg]amix=inputs=2:duration=first[out]",
        "-map", "[out]", "-c:a", "aac", "-b:a", "192k", str(mixed_audio_path),
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    return mixed_audio_path


def download_shorts_clips(queries: List[str], download_dir: Path) -> List[Path]:
    log("[4/5] 9:16 Vertikal format uchun Pixabay kadrlari yuklanmoqda...")
    downloaded = []
    seen_ids = set()

    for q in queries:
        if len(downloaded) >= 12:
            break
        url = f"https://pixabay.com/api/videos/?key={PIXABAY_API_KEY}&q={requests.utils.quote(q)}&per_page=10&safesearch=true"
        try:
            resp = requests.get(url, timeout=15)
            if resp.status_code != 200: continue
            hits = resp.json().get("hits", [])
        except Exception:
            continue

        for v in hits:
            vid_id = v.get("id")
            if vid_id in seen_ids: continue
            variants = v.get("videos", {})
            best = variants.get("medium") or variants.get("large") or variants.get("small")
            if not best or not best.get("url"): continue

            clip_p = download_dir / f"short_clip_{len(downloaded):02d}.mp4"
            try:
                with requests.get(best["url"], stream=True, timeout=25) as r:
                    r.raise_for_status()
                    with open(clip_p, "wb") as f:
                        for chunk in r.iter_content(8192): f.write(chunk)
                seen_ids.add(vid_id)
                downloaded.append(clip_p)
                log(f"  [+] Kadr olindi: {q}")
                break
            except Exception:
                continue

    if not downloaded:
        raise RuntimeError("Pixabay'dan Shorts uchun video topilmadi.")
    return downloaded


def assemble_shorts_video(clips: List[Path], audio_path: Path, srt_path: Path, out_path: Path, clip_dur: float = 3.2) -> Path:
    log("[5/5] 9:16 Vertikal video montaj qilinmoqda...")
    audio_dur = get_media_duration(audio_path)
    work_dir = out_path.parent

    norm_clips = []
    # 9:16 vertikal formatga markazdan qirqib moslashtirish (scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920)
    for i, c in enumerate(clips):
        norm = work_dir / f"vnorm_{i:02d}.mp4"
        vf = f"scale={TARGET_W}:{TARGET_H}:force_original_aspect_ratio=increase,crop={TARGET_W}:{TARGET_H},fps=30,format=yuv420p"
        cmd = ["ffmpeg", "-y", "-stream_loop", "-1", "-i", str(c), "-t", f"{clip_dur:.2f}", "-vf", vf, "-an", "-c:v", "libx264", "-preset", "fast", str(norm)]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        norm_clips.append(norm)

    needed = math.ceil(audio_dur / clip_dur) + 1
    seq = (norm_clips * (needed // len(norm_clips) + 1))[:needed]
    concat_txt = work_dir / "shorts_concat.txt"
    with open(concat_txt, "w", encoding="utf-8") as f:
        for nc in seq: f.write(f"file '{nc.name}'\n")

    # Shorts uchun jozibali sariq-oq neon subtitr stili (ekran o'rtasida)
    sub_style = "FontName=Arial,FontSize=32,PrimaryColour=&H0000FFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=3,Shadow=2,Alignment=2,MarginV=420"
    vf_val = f"subtitles={srt_path.name}:force_style='{sub_style}'"

    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_txt.name, "-i", audio_path.name,
        "-t", f"{audio_dur:.2f}", "-vf", vf_val, "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-c:a", "aac", "-b:a", "192k", "-shortest", out_path.name
    ]
    subprocess.run(cmd, check=True, cwd=str(work_dir))
    log(f"  [+] Tayyor YouTube Shorts: {out_path}")
    return out_path


def run_shorts_pipeline(
    topic: Optional[str] = None,
    lang: str = "uz",
    voice: Optional[str] = None,
    upload: bool = True,
    privacy: str = "public",
    token_file: str = "token_shorts.json",
) -> None:
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    work_dir = OUTPUT_DIR / f"shorts_{lang}_{timestamp}"
    work_dir.mkdir(parents=True, exist_ok=True)

    lang_cfg = LANGUAGE_CONFIG.get(lang, LANGUAGE_CONFIG["uz"])
    sel_voice = voice or lang_cfg["default_voice"]

    metadata = generate_shorts_script(topic=topic, lang=lang)
    with open(work_dir / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    log(f"  Sarlavha: {metadata['title']}")

    raw_voice = work_dir / "voice.mp3"
    srt_p = work_dir / "subtitles.srt"
    asyncio.run(generate_voiceover_and_srt(metadata["narration"], raw_voice, srt_p, sel_voice))

    mixed_a = work_dir / "voice_mixed.m4a"
    mix_shorts_audio(raw_voice, mixed_a)

    clips = download_shorts_clips(metadata["search_queries"], work_dir)

    final_shorts = work_dir / f"shorts_{lang}_{timestamp}.mp4"
    assemble_shorts_video(clips, mixed_a, srt_p, final_shorts)

    if upload:
        import channel_manager
        tf, login_hint = channel_manager.resolve_account_info(token_file or "youtubekanal0004@gmail.com")
        channel_manager.upload_video_to_youtube(
            video_path=final_shorts,
            metadata=metadata,
            token_file=tf,
            login_hint=login_hint,
            lang=lang,
            privacy_status=privacy,
            category_id="24", # Entertainment
        )
    else:
        log(f"  [i] Yuklash o'tkazib yuborildi (--no-upload). Tayyor Shorts: {final_shorts}")


def main():
    import channel_manager
    parser = argparse.ArgumentParser(description="YouTube Shorts 9:16 AI Agent")
    parser.add_argument("--lang", choices=list(LANGUAGE_CONFIG.keys()), default="uz")
    parser.add_argument("--topic", type=str, default=None)
    parser.add_argument("--voice", type=str, default=None)
    parser.add_argument("--privacy", choices=["public", "unlisted", "private"], default="public")
    parser.add_argument("--gmail", type=str, default=None, help="Yuklanadigan Gmail manzili")
    parser.add_argument("--token-file", type=str, default=None)
    parser.add_argument("--no-upload", action="store_true")
    args = parser.parse_args()

    chosen_token, _ = None, None
    if not args.no_upload:
        if args.gmail or args.token_file:
            chosen_token, _ = channel_manager.resolve_account_info(args.gmail or args.token_file, default_email="youtubekanal0004@gmail.com")
        else:
            chosen_token, _ = channel_manager.prompt_account_selection_cli(default_email="youtubekanal0004@gmail.com")

    run_shorts_pipeline(
        topic=args.topic,
        lang=args.lang,
        voice=args.voice,
        upload=not args.no_upload,
        privacy=args.privacy,
        token_file=chosen_token,
    )



if __name__ == "__main__":
    main()
