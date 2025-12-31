import os
import requests
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("YOUTUBE_CLIENT_ID")
CLIENT_SECRET = os.getenv("YOUTUBE_CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("YOUTUBE_REFRESH_TOKEN")
PLAYLIST_TITLE = os.getenv("PLAYLIST_TITLE")
PLAYLIST_DESCRIPTION = os.getenv("PLAYLIST_DESCRIPTION")

SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]

def get_authenticated_service():
    creds = Credentials(
        None,
        refresh_token=REFRESH_TOKEN,
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        token_uri="https://oauth2.googleapis.com/token",
        scopes=SCOPES
    )
    return build("youtube", "v3", credentials=creds)

def get_trending_videos():
    url = "https://charts.youtube.com/charts/TrendingVideos/vn/RightNow"
    html = requests.get(url).text
    parts = html.split("videoId")
    ids = []
    for p in parts[1:31]:
        v = p.split('"')[1]
        ids.append(v)
    return ids

def find_playlist(youtube):
    req = youtube.playlists().list(part="id,snippet", mine=True).execute()
    for pl in req.get("items", []):
        if pl["snippet"]["title"] == PLAYLIST_TITLE:
            return pl["id"]
    return None

def create_playlist(youtube):
    body = {
        "snippet": {
            "title": PLAYLIST_TITLE,
            "description": PLAYLIST_DESCRIPTION
        },
        "status": {"privacyStatus": "public"}
    }
    res = youtube.playlists().insert(part="snippet,status", body=body).execute()
    return res["id"]

def clear_playlist(youtube, playlist_id):
    items = youtube.playlistItems().list(
        playlistId=playlist_id, part="id", maxResults=50
    ).execute().get("items", [])
    for it in items:
        youtube.playlistItems().delete(id=it["id"]).execute()

def add_videos_to_playlist(youtube, playlist_id, video_ids):
    for vid in video_ids:
        youtube.playlistItems().insert(
            part="snippet",
            body={
                "snippet": {
                    "playlistId": playlist_id,
                    "resourceId": {"kind": "youtube#video", "videoId": vid}
                }
            }
        ).execute()

if __name__ == "__main__":
    yt = get_authenticated_service()
    vids = get_trending_videos()
    pl_id = find_playlist(yt)
    if not pl_id:
        pl_id = create_playlist(yt)
    clear_playlist(yt, pl_id)
    add_videos_to_playlist(yt, pl_id, vids)
    print("✅ Playlist cập nhật thành công!")
