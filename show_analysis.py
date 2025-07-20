import requests
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

TWELVELABS_API_KEY = os.getenv('TWELVELABS_API_KEY')

def show_detailed_analysis(prompt):
    """Show detailed analysis results from TwelveLabs API based on prompt"""
    if not TWELVELABS_API_KEY:
        print("❌ No API key available")
        return False
    
    print("🔍 Getting detailed analysis from TwelveLabs...")
    
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
    
    # Step 2: Get existing videos
    try:
        videos_res = requests.get(f"https://api.twelvelabs.io/v1.3/indexes/{index_id}/videos", 
                                headers={"x-api-key": TWELVELABS_API_KEY})
        videos_res.raise_for_status()
        videos_data = videos_res.json()
        existing_videos = videos_data['data']
        
        if not existing_videos:
            print("❌ No videos found in index")
            return False
            
        # Use the first video for analysis
        test_video = existing_videos[0]
        video_id = test_video['_id']
        filename = test_video['system_metadata']['filename']
        duration = test_video['system_metadata']['duration']
        print(f"📹 Analyzing video: {filename}")
        print(f"⏱️  Duration: {duration:.2f} seconds")
        
    except Exception as e:
        print(f"❌ Failed to get videos: {e}")
        return False
    
    # Use the prompt passed as an argument
    queries = [prompt]

    for query in queries:
        print(f"\n🔍 Query: '{query}'")
        print("=" * 50)
        
        try:
            search_payload = {
                "index_id": (None, index_id),
                "query_text": (None, query),
                "search_options": (None, "visual")
            }
            search_res = requests.post("https://api.twelvelabs.io/v1.3/search", 
                                     files=search_payload, 
                                     headers={"x-api-key": TWELVELABS_API_KEY})
            search_res.raise_for_status()
            search_data = search_res.json()
            
            results = search_data.get('data', [])
            print(f"📊 Found {len(results)} relevant segments:")
            
            for i, result in enumerate(results[:5]):  # Show top 5 results
                score = result.get('score', 'N/A')
                start_time = result.get('start', 'N/A')
                end_time = result.get('end', 'N/A')
                confidence = result.get('confidence', 'N/A')
                video_id_result = result.get('video_id', 'N/A')
                
                print(f"   {i+1}. Score: {score:.2f}, Time: {start_time:.1f}s - {end_time:.1f}s, Confidence: {confidence}")
                
                # Show thumbnail URL if available
                if 'thumbnail_url' in result:
                    print(f"      📷 Thumbnail: {result['thumbnail_url'][:80]}...")
                
        except Exception as e:
            print(f"❌ Search failed: {e}")
    
    print(f"\n🎉 Analysis complete for video: {filename}")
    return result

if __name__ == "__main__":
    # Example usage - pass your prompt here
    test_prompt = "Find inappropriate content"
    show_detailed_analysis(test_prompt)
