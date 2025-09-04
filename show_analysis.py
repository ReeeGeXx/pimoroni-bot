import requests
import json
import time
from requests.exceptions import HTTPError
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


TWELVELABS_API_KEY = os.getenv('TWELVELABS_API_KEY')
def get_default_index():
    url = "https://api.twelvelabs.io/v1.3/indexes"
    headers = {"x-api-key": TWELVELABS_API_KEY}
    res = requests.get(url, headers=headers)
    res.raise_for_status()
    index_id = res.json()["data"][0]["_id"]
    return index_id


def wait_for_video_ready(index_id, video_id, timeout=500, interval=5):
    url = f"https://api.twelvelabs.io/v1.3/indexes/{index_id}/videos/{video_id}"
    headers = {"x-api-key": TWELVELABS_API_KEY}

    waited = 0
    while waited < timeout:
        res = requests.get(url, headers=headers)
        res.raise_for_status()
        data = res.json().get("data", {})
        status = data.get("status")
        if status == "ready":
            return data
        elif status == "failed":
            raise RuntimeError(f"Video {video_id} failed to process: {data}")

        time.sleep(interval)
        waited += interval

    raise TimeoutError(f"Video {video_id} not ready after {timeout}s")


def upload_video_to_twelvelabs(video_path: str, index_id: str):
    url = "https://api.twelvelabs.io/v1.3/tasks"
    headers = {"x-api-key": TWELVELABS_API_KEY}

    with open(video_path, "rb") as f:
        files = {
            "index_id": (None, index_id),
            "video_file": (video_path, f, "video/mp4"),
        }
        res = requests.post(url, files=files, headers=headers)
        res.raise_for_status()
        return res.json()


def twelvelabs_search(index_id, video_id, query, max_retries=3):
    payload = {
        "index_id": (None, str(index_id)),
        "video_id": (None, str(video_id)),
        "query_text": (None, str(query)),
        "search_options": (None, "visual"),
    }
    headers = {"x-api-key": TWELVELABS_API_KEY}
    backoff = 1
    print (payload)
    for attempt in range(1, max_retries + 1):
        try:
            res = requests.post(
                "https://api.twelvelabs.io/v1.3/search", files=payload, headers=headers
            )
            res.raise_for_status()
            return res.json().get("data", [])
        except HTTPError as e:
            if res.status_code == 429 and attempt < max_retries:
                retry_after = int(res.headers.get("Retry-After", backoff))
                time.sleep(retry_after)
                backoff *= 2
            else:
                raise
    raise RuntimeError(f"TwelveLabs search failed after {max_retries} attempts")


def show_detailed_analysis(prompt, video_path):
    """Upload video, wait until ready, then run search"""
    if not TWELVELABS_API_KEY:
        raise RuntimeError("No API key available")

    index_id = get_default_index()

    # Upload video
    uploadRes = upload_video_to_twelvelabs(video_path, index_id)
    video_id = uploadRes.get("video_id")
    if not video_id:
        raise RuntimeError(f"Upload response missing video_id: {uploadRes}")

    # Wait until video is ready
    video_data = wait_for_video_ready(index_id, video_id)
    print(f" UPLOADED: {video_data.get('system_metadata', {}).get('filename')}")

    # Run search
    results_data = twelvelabs_search(index_id, video_id, prompt)

    # Format results
    segments = []
    for result in results_data:
        segments.append(
            {
                "score": result.get("score"),
                "start_time": result.get("start"),
                "end_time": result.get("end"),
                "confidence": result.get("confidence"),
                "thumbnail_url": result.get("thumbnail_url"),
            }
        )
    return segments
