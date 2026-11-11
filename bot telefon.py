# Telefon (Termux) uchun yengil versiya: faqat requests va yt-dlp kerak.
import os, re, time, glob, tempfile, threading
import requests, yt_dlp

TOKEN = os.environ.get("BOT_TOKEN") or input("BOT_TOKEN: ").strip()
API = f"https://api.telegram.org/bot{TOKEN}"
MAX_MB = 49
URL_RE = re.compile(r"https?://\S+")
OK = ("instagram.com", "tiktok.com")
sem = threading.Semaphore(2)
last = {}


def send(chat, text):
    return requests.post(f"{API}/sendMessage", data={"chat_id": chat, "text": text}, timeout=30).json()


def download(url, folder):
    opts = {"outtmpl": os.path.join(folder, "%(id)s.%(ext)s"),
            "format": f"best[ext=mp4][filesize<{MAX_MB}M]/best[ext=mp4]/best",
            "quiet": True, "noplaylist": True, "socket_timeout": 20, "retries": 3}
    if os.path.exists("cookies.txt"):
        opts["cookiefile"] = "cookies.txt"
    with yt_dlp.YoutubeDL(opts) as y:
        y.download([url])
    return glob.glob(os.path.join(folder, "*"))[0]


def work(chat, url):
    with sem:
        try:
            send(chat, "Yuklanmoqda...")
            with tempfile.TemporaryDirectory() as tmp:
                p = download(url, tmp)
                if os.path.getsize(p) > MAX_MB * 1024 * 1024:
                    send(chat, "Video juda katta (50 MB dan oshiq).")
                    return
                with open(p, "rb") as f:
                    requests.post(f"{API}/sendVideo", data={"chat_id": chat}, files={"video": f}, timeout=300)
            print("OK", url)
        except Exception as e:
            print("xato:", e)
            send(chat, "Videoni yuklab bo'lmadi. Havola ochiq ekanini tekshiring.")


def main():
    print("bot ishga tushdi")
    offset = 0
    while True:
        try:
            r = requests.get(f"{API}/getUpdates", params={"offset": offset, "timeout": 30}, timeout=40).json()
            for u in r.get("result", []):
                offset = u["update_id"] + 1
                m = u.get("message") or {}
                text, chat = m.get("text", ""), m.get("chat", {}).get("id")
                if not chat:
                    continue
                if text.startswith("/start"):
                    send(chat, "Salom! Instagram yoki TikTok havolasini yuboring.")
                    continue
                f = URL_RE.search(text)
                if not f or not any(h in f.group(0) for h in OK):
                    send(chat, "Instagram yoki TikTok havolasini yuboring.")
                    continue
                if time.time() - last.get(chat, 0) < 5:
                    send(chat, "Biroz kuting.")
                    continue
                last[chat] = time.time()
                threading.Thread(target=work, args=(chat, f.group(0)), daemon=True).start()
        except Exception as e:
            print("aloqa xatosi:", e)
            time.sleep(5)


main()
