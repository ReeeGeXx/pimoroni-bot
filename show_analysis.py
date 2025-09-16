import requests
import json
import time
from requests.exceptions import HTTPError
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
TWELVELABS_API_KEY = os.getenv("TWELVELABS_API_KEY")

def get_default_index():
    url = "https://api.twelvelabs.io/v1.3/indexes"
    headers = {"x-api-key": TWELVELABS_API_KEY}
    res = requests.get(url, headers=headers)
    res.raise_for_status()
    return res.json()["data"][0]["_id"]

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

def wait_until_ready(index_id, video_id, timeout=600, interval=10):
    """Poll TwelveLabs until the video is indexed and ready for search"""
    url = f"https://api.twelvelabs.io/v1.3/tasks/{video_id}"
    headers = {"x-api-key": TWELVELABS_API_KEY}

    waited = 0
    while waited < timeout:
        res = requests.get(url, headers=headers)
        res.raise_for_status()
        data = res.json()
        status = data.get("status")
        print(f"Video status: {status}")

        if status == "ready":
            return data  # return metadata when ready

        time.sleep(interval)
        waited += interval

    raise TimeoutError(f"Video {video_id} not ready after {timeout}s")


import requests
def twelvelabs_search(index_id, video_id, query, max_retries=3):
    """
    Run a TwelveLabs search query against an indexed video.
    """
    payload = {
        "index_id": (None, str(index_id)),
        "video_id": (
            None,
            str(video_id),
        ),
        "query_text": (None, "Look for movement"),
        "search_options": (None, "visual,audio,text"),
    }
    headers = {"x-api-key": TWELVELABS_API_KEY}

    backoff = 1
    for attempt in range(1, max_retries + 1):
        try:
            res = requests.post(
                "https://api.twelvelabs.io/v1.3/search",
                files=payload, 
                headers=headers,
            )
            res.raise_for_status()
            results = res.json().get("data", [])

            for clip in results:
                score = clip.get("score")
                start = clip.get("start")
                end = clip.get("end")
                confidence = clip.get("confidence")
                print(f"score={score} start={start} end={end} confidence={confidence}")
            return results

        except HTTPError as e:
            if res.status_code == 429 and attempt < max_retries:
                retry_after = int(res.headers.get("Retry-After", backoff))
                time.sleep(retry_after)
                backoff *= 2
            else:
                print("❌ Search failed:", res.text)
                raise


def show_detailed_analysis(prompt, video_path):
    if not TWELVELABS_API_KEY:
        raise RuntimeError("No API key available")

    index_id = get_default_index()

    # Upload video
    uploadRes = upload_video_to_twelvelabs(video_path, index_id)
    video_id = uploadRes.get("video_id")
    if not video_id:
        raise RuntimeError(f"Upload response missing video_id: {uploadRes}")

    # Wait until the video is fully indexed
    video_meta = wait_until_ready(index_id, video_id)
    print(f"✅ Video ready: {video_meta.get('system_metadata', {}).get('filename')}")

    # Now search
    results = twelvelabs_search(index_id, video_id, prompt)
    import json
    print("\n🔎 Analysis Results:")
    print(json.dumps(results, indent=2))
    return results
