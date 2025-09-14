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
    url = f"https://api.twelvelabs.io/v1.3/indexes/{index_id}/videos/{video_id}"
    headers = {"x-api-key": TWELVELABS_API_KEY}

    waited = 0
    while waited < timeout:
        res = requests.get(url, headers=headers)
        res.raise_for_status()
        data = res.json()
        status = data.get("hls", {}).get("status")
        print(f"Video status: {status}")
        #print(json.dumps(data, indent=2))

        if status == "COMPLETE":
            return data  # return metadata when ready

        time.sleep(interval)
        waited += interval

    raise TimeoutError(f"Video {video_id} not ready after {timeout}s")


def twelvelabs_search(video_id, prompt, timeout=300, interval=5):
    """
    Run a TwelveLabs analysis job on a video and wait for results.
    Returns the completed results list.
    """

    # 1. Kick off analysis request
    data = {
        "video_id": video_id,
        "prompt": prompt,
        "temperature": 0.2
    }
    headers = {"x-api-key": TWELVELABS_API_KEY}

    res = requests.post("https://api.twelvelabs.io/v1.3/analyze", json=data, headers=headers)
    res.raise_for_status()
    job = res.json()

    job_id = job.get("id")
    if not job_id:
        raise RuntimeError(f"No job id returned: {job}")

    print(f"Started analysis job {job_id} for video {video_id}")

    # 2. Poll until COMPLETED or timeout
    waited = 0
    while waited < timeout:
        status_res = requests.get(
            f"https://api.twelvelabs.io/v1.3/analyze/{job_id}",
            headers=headers
        )
        status_res.raise_for_status()
        status_data = status_res.json()

        status = status_data.get("status")
        if status == "COMPLETED":
            print("✅ Analysis completed")
            return status_data.get("results", [])
        elif status == "FAILED":
            raise RuntimeError(f"Analysis failed: {status_data}")
        
        print(f"⏳ Still {status}... waited {waited}s")
        time.sleep(interval)
        waited += interval

    raise TimeoutError(f"Analysis job {job_id} did not finish after {timeout} seconds")


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
    print(results)
    return results
