#!/usr/bin/env python3

import requests
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

TWELVELABS_API_KEY = os.getenv('TWELVELABS_API_KEY')

def test_my_video():
    """Test analysis on your uploaded video"""
    if not TWELVELABS_API_KEY:
        print("❌ No API key available")
        return False
    
    print("🔍 Testing your uploaded video...")
    
    # Step 1: Get the default index
    try:
        indexes_res = requests.get("https://api.twelvelabs.io/v1.3/indexes", 
                                 headers={"x-api-key": TWELVELABS_API_KEY})
        indexes_res.raise_for_status()
        indexes_data = indexes_res.json()
        index_id = indexes_data['data'][0]['_id']
        print(f"📋 Using index: {index_id}")
    except Exception as e:
        print(f"❌ Failed to get index: {e}")
        return False
    
    # Step 2: Get all videos in the index
    try:
        videos_res = requests.get(f"https://api.twelvelabs.io/v1.3/indexes/{index_id}/videos", 
                                headers={"x-api-key": TWELVELABS_API_KEY})
        videos_res.raise_for_status()
        videos_data = videos_res.json()
        existing_videos = videos_data['data']
        
        if not existing_videos:
            print("❌ No videos found in index")
            print("💡 Please upload a video through the TwelveLabs dashboard first:")
            print("   https://app.twelvelabs.io/")
            return False
        
        print(f"📹 Found {len(existing_videos)} videos in your index:")
        for i, video in enumerate(existing_videos):
            filename = video['system_metadata']['filename']
            duration = video['system_metadata']['duration']
            status = video['hls']['status']
            video_id = video['_id']
            print(f"   {i+1}. {filename} ({duration:.1f}s) - ID: {video_id} - Status: {status}")
        
        #Look for specific video
        target_video_id = "687c3709c5994cb471749bc7"  #video ID
        target_video = None
        
        for video in existing_videos:
            if video['_id'] == target_video_id:
                target_video = video
                break
        
        if target_video:
            test_video = target_video
            print(f"\n🎯 Found your video: {test_video['system_metadata']['filename']}")
        else:
            # Use the most recent video if target not found
            test_video = existing_videos[0]
            print(f"\n⚠️  Your video ID not found, using: {test_video['system_metadata']['filename']}")
        
        video_id = test_video['_id']
        filename = test_video['system_metadata']['filename']
        duration = test_video['system_metadata']['duration']
        print(f"🎯 Analyzing: {filename}")
        print(f"⏱️  Duration: {duration:.2f} seconds")
        print(f"🆔 Video ID: {video_id}")
        
    except Exception as e:
        print(f"❌ Failed to get videos: {e}")
        return False
    
    # Step 3: Test with your custom query
    print("\n🔍 Enter your search query (or press Enter for default):")
    custom_query = input("Query: ").strip()
    
    if not custom_query:
        custom_query = "Find cars, people, and license plates"
    
    print(f"\n🔍 Searching for: '{custom_query}'")
    print("=" * 60)
    
    try:
        search_payload = {
            "index_id": (None, index_id),
            "query_text": (None, custom_query),
            "search_options": (None, "visual")
        }
        search_res = requests.post("https://api.twelvelabs.io/v1.3/search", 
                                 files=search_payload, 
                                 headers={"x-api-key": TWELVELABS_API_KEY})
        search_res.raise_for_status()
        search_data = search_res.json()
        
        results = search_data.get('data', [])
        print(f"📊 Found {len(results)} relevant segments:")
        
        if results:
            for i, result in enumerate(results[:10]):  # Show top 10 results
                score = result.get('score', 'N/A')
                start_time = result.get('start', 'N/A')
                end_time = result.get('end', 'N/A')
                confidence = result.get('confidence', 'N/A')
                
                print(f"   {i+1}. Score: {score:.2f}, Time: {start_time:.1f}s - {end_time:.1f}s, Confidence: {confidence}")
                
                # Show thumbnail URL if available
                if 'thumbnail_url' in result:
                    print(f"      📷 Thumbnail: {result['thumbnail_url']}")
        else:
            print("   No relevant segments found for this query.")
        
    except Exception as e:
        print(f"❌ Search failed: {e}")
        return False
    
    print(f"\n🎉 Analysis complete for: {filename}")
    return True

if __name__ == "__main__":
    test_my_video() 