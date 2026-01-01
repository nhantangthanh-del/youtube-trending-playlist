import os
import re
import time
import requests
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

# ================= CONFIG =================
CLIENT_ID = os.environ["YT_CLIENT_ID"]
CLIENT_SECRET = os.environ["YT_CLIENT_SECRET"]
REFRESH_TOKEN = os.environ["YT_REFRESH_TOKEN"]

PLAYLIST_ID = "PLBJ12BPnlyEhG-6JBuzkBQLdfDcyKfR1m"

CHART_URL = "https://charts.youtube.com/charts/TrendingVideos/vn/RightNow"
KWORB_URL = "https://kworb.net/youtube/trending/vn.html"

TARGET_COUNT = 30
TIMEOUT = 15

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
}

# ================= SCRAPE =================
def get_trending_ids():
    """
    Chỉ trả về danh sách khi đủ 30 video
    Không đủ → raise → KHÔNG update
    """
    try:
        res = requests.get(CHART_URL, headers=HEADERS, timeout=TIMEOUT)
        res.raise_for_status()

        ids = re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', res.text)

        uniq = []
        for v in ids:
            if v not in uniq:
                uniq.append(v)
            if len(uniq) == TARGET_COUNT:
                break

        if len(uniq) != TARGET_COUNT:
            raise RuntimeError(f"Charts chỉ có {len(uniq)} video")

        print("✅ Lấy đủ 30 video từ YouTube Charts")
        return uniq

    except Exception as e:
        print("⚠️ Charts lỗi:", e)

    # fallback
    kw = requests.get(KWORB_URL, headers=HEADERS, timeout=TIMEOUT)
    ids = re.findall(r'watch\?v=([a-zA-Z0-9_-]{11})', kw.text)[:TARGET_COUNT]

    if len(ids) != TARGET_COUNT:
        raise RuntimeError("Kworb cũng không đủ 30 video")

    print("⚠️ Dùng fallback Kworb")
    return ids


# ================= YOUTUBE =================
def get_youtube_service():
    creds = Credentials(
        None,
        refresh_token=REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET
    )
    return build("youtube", "v3", credentials=creds)


def clear_playlist(youtube):
    req = youtube.playlistItems().list(
        part="id",
        playlistId=PLAYLIST_ID,
        maxResults=50
    )
    while req:
        res = req.execute()
        for it in res.get("items", []):
            youtube.playlistItems().delete(id=it["id"]).execute()
            time.sleep(0.2)
        req = youtube.playlistItems().list_next(req, res)


def add_videos(youtube, ids):
    for idx, vid in enumerate(ids):
        youtube.playlistItems().insert(
            part="snippet",
            body={
                "snippet": {
                    "playlistId": PLAYLIST_ID,
                    "position": idx,
                    "resourceId": {
                        "kind": "youtube#video",
                        "videoId": vid
                    }
                }
            }
        ).execute()
        time.sleep(0.2)


# ================= MAIN =================
def main():
    print("🚀 START UPDATE TRENDING PLAYLIST")

    # 1️⃣ LẤY DATA TRƯỚC – FAIL THÌ DỪNG
    ids = get_trending_ids()
    print("🎵 Video #1:", f"https://www.youtube.com/watch?v={ids[0]}")

    # 2️⃣ KẾT NỐI API
    yt = get_youtube_service()

    # 3️⃣ UPDATE (xoá rồi thêm)
    clear_playlist(yt)
    add_videos(yt, ids)

    print("🎉 UPDATE THÀNH CÔNG – PLAYLIST AN TOÀN")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("🔥 FAILED – PLAYLIST KHÔNG BỊ ĐỘNG TỚI")
        print(e)
        raise
