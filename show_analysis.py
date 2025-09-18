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
import json


def analyze_clip(video_id: str, start: float, end: float):
    url = "https://api.twelvelabs.io/v1.3/analyze"
    headers = {
        "x-api-key": TWELVELABS_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "video_id": video_id,
        "prompt": (
            f"Describe what sensitive information is present within the timeframe {start:.2f} and {end:.2f} seconds. "
            f"Sensitive information may include addresses, license plates, credit cards, ID, etc. Keep it relatively short and straight to the point, but descriptive"
        ),
        "stream": True,  
    }
    res = requests.post(url, json=payload, headers=headers, stream=True)
    res.raise_for_status()

    text_parts = []
    for line in res.iter_lines(decode_unicode=True):
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue

        if event.get("event_type") == "text_generation":
            text_parts.append(event.get("text", ""))

        if event.get("event_type") == "stream_end":
            break 

    return "".join(text_parts).strip()


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
        "search_options": (None, "visual"),
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
    detailed_results = []
    for clip in results:
        start, end = clip["start"], clip["end"]
        analysis = analyze_clip(video_id, start, end)
        clip["analysis"] = analysis
        detailed_results.append(clip)
        print(f"\n⏱ {start:.2f}-{end:.2f}s")
        print(json.dumps(analysis, indent=2))

    return detailed_results
