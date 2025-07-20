#!/usr/bin/env python3

import requests
import time
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

TWELVELABS_API_KEY = os.getenv('TWELVELABS_API_KEY')

def test_video_analysis():
    """Test video analysis with existing videos in TwelveLabs API"""
    if not TWELVELABS_API_KEY:
        print("❌ No API key available")
        return False
    
    print("🔑 API Key found")
    
    # Step 1: Get the default index
    try:
        print("📋 Getting default index...")
        indexes_res = requests.get("https://api.twelvelabs.io/v1.3/indexes", 
                                 headers={"x-api-key": TWELVELABS_API_KEY})
        indexes_res.raise_for_status()
        indexes_data = indexes_res.json()
        index_id = indexes_data['data'][0]['_id']
        print(f"✅ Using index: {index_id}")
    except Exception as e:
        print(f"❌ Failed to get index: {e}")
        return False
    
    # Step 2: Get existing videos
    try:
        print("🎥 Getting existing videos...")
        videos_res = requests.get(f"https://api.twelvelabs.io/v1.3/indexes/{index_id}/videos", 
                                headers={"x-api-key": TWELVELABS_API_KEY})
        videos_res.raise_for_status()
        videos_data = videos_res.json()
        existing_videos = videos_data['data']
        print(f"✅ Found {len(existing_videos)} existing videos")
        
        if not existing_videos:
            print("❌ No videos found in index")
            return False
            
        # Use the first video for testing
        test_video = existing_videos[0]
        video_id = test_video['_id']
        filename = test_video['system_metadata']['filename']
        print(f"📹 Using video: {filename} (ID: {video_id})")
        
    except Exception as e:
        print(f"❌ Failed to get videos: {e}")
        return False
    
    # Step 3: Test search/analysis on existing video
    try:
        print("🔍 Testing search analysis...")
        search_payload = {
            "index_id": (None, index_id),
            "query_text": (None, "Find cars and people"),
            "search_options": (None, "visual")
        }
        search_res = requests.post("https://api.twelvelabs.io/v1.3/search", 
                                 files=search_payload, 
                                 headers={"x-api-key": TWELVELABS_API_KEY})
        search_res.raise_for_status()
        search_data = search_res.json()
        print(f"✅ Search successful, found {len(search_data.get('data', []))} results")
        
        # Print some results
        for i, result in enumerate(search_data.get('data', [])[:3]):
            print(f"   Result {i+1}: Score {result.get('score', 'N/A')}, Time {result.get('start', 'N/A')}-{result.get('end', 'N/A')}s")
        
    except Exception as e:
        print(f"❌ Search failed: {e}")
        return False
    
    print("🎉 Video analysis test completed successfully!")
    return True

if __name__ == "__main__":
    test_video_analysis() 