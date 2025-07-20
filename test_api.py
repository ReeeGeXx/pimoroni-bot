#!/usr/bin/env python3

import requests
import time
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

TWELVELABS_API_KEY = os.getenv('TWELVELABS_API_KEY')

def test_twelvelabs_api():
    """Test the TwelveLabs API integration"""
    if not TWELVELABS_API_KEY:
        print("❌ No API key available")
        return False
    
    print("🔑 API Key found")
    
    # Test 1: Get indexes
    try:
        print("📋 Testing index retrieval...")
        indexes_res = requests.get("https://api.twelvelabs.io/v1.3/indexes", 
                                 headers={"x-api-key": TWELVELABS_API_KEY})
        indexes_res.raise_for_status()
        indexes_data = indexes_res.json()
        index_id = indexes_data['data'][0]['_id']
        print(f"✅ Index retrieved: {index_id}")
    except Exception as e:
        print(f"❌ Failed to get index: {e}")
        return False
    
    # Test 2: Get videos in the index
    try:
        print("🎥 Testing video retrieval...")
        videos_res = requests.get(f"https://api.twelvelabs.io/v1.3/indexes/{index_id}/videos", 
                                headers={"x-api-key": TWELVELABS_API_KEY})
        videos_res.raise_for_status()
        videos_data = videos_res.json()
        print(f"✅ Found {len(videos_data['data'])} videos in index")
    except Exception as e:
        print(f"❌ Failed to get videos: {e}")
        return False
    
    # Test 3: Test search endpoint
    try:
        print("🔍 Testing search endpoint...")
        search_payload = {
            "index_id": (None, index_id),
            "query_text": (None, "test query"),
            "search_options": (None, "visual")
        }
        search_res = requests.post("https://api.twelvelabs.io/v1.3/search", 
                                 files=search_payload, 
                                 headers={"x-api-key": TWELVELABS_API_KEY})
        search_res.raise_for_status()
        search_data = search_res.json()
        print(f"✅ Search successful, found {len(search_data.get('data', []))} results")
    except Exception as e:
        print(f"❌ Search failed: {e}")
        return False
    
    print("🎉 All API tests passed!")
    return True

if __name__ == "__main__":
    test_twelvelabs_api() 