import os
import re
import time
import requests
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

# ================== CONFIG ==================
CLIENT_ID = os.environ["YT_CLIENT_ID"]
CLIENT_SECRET = os.environ["YT_CLIENT_SECRET"]
REFRESH_TOKEN = os.environ["YT_REFRESH_TOKEN"]

# PLAYLIST MỚI (đã cập nhật)
PLAYLIST_ID = "PLBJ12BPnlyEhL8ryH-IqEL0Aeu69MePm6"

CHART_URL = "https://charts.youtube.com/charts/TrendingVideos/vn/RightNow"
KWORB_URL = "https://kworb.net/youtube/trending/vn.html"

TARGET_COUNT = 30
TIMEOUT = 15

# Video rác cố định (Better Love)
GARBAGE_IDS = {
    "37_rIn60nwg"
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://charts.youtube.com/",
}

# ================== SCRAPE ==================
def get_video_ids():
    """
    Logic thực dụng – chắc ăn:
    - Regex videoId đơn giản
    - Loại video rác
    - Deduplicate
    - Không đủ 30 → fallback Kworb
    """
    try:
        res = requests.get(CHART_URL, headers=HEADERS, timeout=TIMEOUT)
        res.raise_for_status()

        raw_ids = re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', res.text)

        final_ids = []
        for vid in raw_ids:
            if vid in GARBAGE_IDS:
                continue
            if vid not in final_ids:
                final_ids.append(vid)
            if len(final_ids) >= TARGET_COUNT:
                break

        if len(final_ids) == TARGET_COUNT:
            print("✅ Lấy đủ 30 video từ YouTube Charts")
            return final_ids

        print(f"⚠️ Charts chỉ có {len(final_ids)} video hợp lệ")

    except Exception as e:
        print("⚠️ Charts lỗi:", e)

    # ===== FALLBACK KWORB =====
    print("🔁 Chuyển sang nguồn dự phòng Kworb")
    res_kw = requests.get(KWORB_URL, headers=HEADERS, timeout=TIMEOUT)
    kw_ids = re.findall(r'watch\?v=([a-zA-Z0-9_-]{11})', res_kw.text)

    final_kw = []
    for vid in kw_ids:
        if vid not in final_kw:
            final_kw.append(vid)
        if len(final_kw) >= TARGET_COUNT:
            break

    return final_kw


# ================== YOUTUBE ==================
def get_youtube_service():
    creds = Credentials(
        token=None,
        refresh_token=REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
    )
    return build("youtube", "v3", credentials=creds)


def clear_playlist(youtube):
    print("🧹 Đang xoá video cũ...")
    req = youtube.playlistItems().list(
        part="id",
        playlistId=PLAYLIST_ID,
        maxResults=50
    )
    total = 0
    while req:
        res = req.execute()
        for it in res.get("items", []):
            youtube.playlistItems().delete(id=it["id"]).execute()
            total += 1
            time.sleep(0.2)
        req = youtube.playlistItems().list_next(req, res)

    print(f"🗑️ Đã xoá {total} video cũ")


def add_videos(youtube, ids):
    print(f"➕ Thêm {len(ids)} video mới...")
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


# ================== MAIN ==================
def main():
    print("🚀 START UPDATE TRENDING PLAYLIST")

    video_ids = get_video_ids()

    if len(video_ids) < TARGET_COUNT:
        print("❌ Không đủ 30 video – DỪNG UPDATE để bảo toàn playlist")
        return

    print("🎵 Video #1:", f"https://www.youtube.com/watch?v={video_ids[0]}")

    youtube = get_youtube_service()

    clear_playlist(youtube)
    add_videos(youtube, video_ids)

    print("🎉 UPDATE PLAYLIST THÀNH CÔNG!")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("🔥 FAILED – PLAYLIST KHÔNG BỊ ĐỘNG TỚI")
        print(e)
        raise
