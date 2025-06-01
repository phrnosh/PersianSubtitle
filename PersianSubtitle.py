import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
from pydub import AudioSegment
import whisper
import re
from difflib import SequenceMatcher
from duckduckgo_search import DDGS
import requests
from bs4 import BeautifulSoup
import moviepy.editor as mp

# تنظیم مسیر FFMPEG
AudioSegment.converter = "C:/Users/Farnoosh/Downloads/ffmpeg-7.1.1-essentials_build/ffmpeg-7.1.1-essentials_build/bin/ffmpeg.exe"
os.environ["FFMPEG_BINARY"] = AudioSegment.converter

DOWNLOAD_PATH = os.path.join(os.path.expanduser("~"), "Downloads")

def clean_text(text):
    return re.sub(r'[^\w\sآ-ی]', '', text).strip()

def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()

def get_lyrics_duckduckgo(song_name, artist):
    query = f"متن آهنگ {song_name} {artist}"
    with DDGS() as ddg:
        results = ddg.text(query, region='ir', safesearch='Off', max_results=5)
        for r in results:
            url = r.get("href") or r.get("url")
            if not url:
                continue
            try:
                html = requests.get(url, timeout=5).text
                soup = BeautifulSoup(html, "html.parser")
                paragraphs = [p.text.strip() for p in soup.find_all("p") if len(p.text.strip()) > 100]
                if paragraphs:
                    return "\n".join(paragraphs[:5])
            except:
                continue
    return None

def parse_srt(path):
    with open(path, encoding='utf-8') as f:
        blocks = f.read().strip().split("\n\n")
        return [(b.split("\n")[0], b.split("\n")[1], " ".join(b.split("\n")[2:])) for b in blocks if len(b.split("\n")) >= 3]

def align_and_fix_srt(srt_path, correct_lyrics, output_path):
    srt_blocks = parse_srt(srt_path)
    correct_lines = [clean_text(line) for line in correct_lyrics.split('\n') if line.strip()]
    fixed_blocks, used = [], set()
    for idx, timecode, srt_text in srt_blocks:
        srt_clean = clean_text(srt_text)
        best_match, best_score, best_idx = srt_text, 0, -1
        for i, ref in enumerate(correct_lines):
            if i in used:
                continue
            score = similar(srt_clean, ref)
            if score > best_score:
                best_score, best_match, best_idx = score, ref, i
        if best_score > 0.5:
            used.add(best_idx)
            fixed_blocks.append(f"{idx}\n{timecode}\n{best_match}")
        else:
            fixed_blocks.append(f"{idx}\n{timecode}\n{srt_text}")
    with open(output_path, 'w', encoding='utf-8') as out:
        out.write("\n\n".join(fixed_blocks))

def convert_to_mp4(audio_path, cover_path, output_path, progress_bar):
    audio_clip = mp.AudioFileClip(audio_path)
    image_clip = mp.ImageClip(cover_path).set_duration(audio_clip.duration).set_audio(audio_clip)
    image_clip.write_videofile(output_path, fps=1, logger='bar', verbose=False)

def browse_audio():
    audio_file = filedialog.askopenfilename(filetypes=[("MP3 files", "*.mp3")])
    if audio_file:
        audio_filename.set(audio_file)

def browse_cover():
    cover_file = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg;*.png")])
    if cover_file:
        cover_filename.set(cover_file)

def search_and_show():
    song = song_entry.get()
    artist = artist_entry.get()
    if song and artist:
        lyrics = get_lyrics_duckduckgo(song, artist)
        result_text.delete(1.0, tk.END)
        result_text.insert(tk.END, lyrics or "متن ترانه پیدا نشد.")
    else:
        messagebox.showwarning("ورودی اشتباه", "لطفا نام آهنگ و هنرمند را وارد کنید.")

def process_files():
    audio_path = audio_filename.get()
    cover_path = cover_filename.get()
    song, artist = song_entry.get(), artist_entry.get()

    if not all([audio_path, cover_path, song, artist]):
        messagebox.showwarning("ورودی اشتباه", "لطفا تمامی فیلدها را پر کنید.")
        return

    sound = AudioSegment.from_file(audio_path)
    wav_name = os.path.join(DOWNLOAD_PATH, Path(audio_path).stem + ".wav")
    sound.export(wav_name, format="wav")

    model = whisper.load_model("medium")
    result = model.transcribe(wav_name, language="fa", task="transcribe")

    subtitle_path = os.path.join(DOWNLOAD_PATH, Path(audio_path).stem + ".srt")
    with open(subtitle_path, "w", encoding="utf-8") as srt_file:
        for i, segment in enumerate(result['segments']):
            def format_time(sec):
                h, m, s = int(sec // 3600), int((sec % 3600) // 60), int(sec % 60)
                ms = int((sec - int(sec)) * 1000)
                return f"{h:02}:{m:02}:{s:02},{ms:03}"
            srt_file.write(f"{i+1}\n{format_time(segment['start'])} --> {format_time(segment['end'])}\n{segment['text'].strip()}\n\n")

    final_srt = os.path.join(DOWNLOAD_PATH, Path(audio_path).stem + "_1.srt")
    lyrics = get_lyrics_duckduckgo(song, artist)
    align_and_fix_srt(subtitle_path, lyrics, final_srt) if lyrics else os.rename(subtitle_path, final_srt)

    mp4_output = os.path.join(DOWNLOAD_PATH, Path(audio_path).stem + ".mp4")
    convert_to_mp4(wav_name, cover_path, mp4_output, progress)

    messagebox.showinfo("تمام شد", f"فایل‌ها در {DOWNLOAD_PATH} ذخیره شدند:\n{Path(mp4_output).name}\n{Path(final_srt).name}\n{Path(subtitle_path).name}")

# ساخت رابط کاربری
root = tk.Tk()
root.title("تولید زیرنویس و ویدیو")

audio_filename = tk.StringVar()
cover_filename = tk.StringVar()

tk.Label(root, text="نام آهنگ:").pack()
song_entry = tk.Entry(root, width=50)
song_entry.pack()

tk.Label(root, text="نام هنرمند:").pack()
artist_entry = tk.Entry(root, width=50)
artist_entry.pack()

tk.Button(root, text="انتخاب فایل صوتی", command=browse_audio).pack()
tk.Button(root, text="انتخاب کاور آهنگ", command=browse_cover).pack()
tk.Button(root, text="جستجو ترانه", command=search_and_show).pack()
tk.Button(root, text="پردازش و تبدیل", command=process_files).pack()

tk.Label(root, text="نتایج جستجو:").pack()
result_text = tk.Text(root, height=10, width=50)
result_text.pack()

progress = ttk.Progressbar(root, orient="horizontal", mode="indeterminate", length=300)
progress.pack(pady=10)

root.mainloop()