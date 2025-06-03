from flask import Blueprint, request, jsonify
from .gpt_utils import get_ai_powered_recommendations, get_sample_suggestions, clear_cache
from .spotify_utils import search_track, search_tracks_enhanced
import re

main = Blueprint('main', __name__)

@main.route('/', methods=['GET'])
def index():
    return jsonify({"message": "Flask backend is running!"})

@main.route('/recommend', methods=['POST'])
def recommend():
    """Enhanced recommendation endpoint with refresh support"""
    print("POST /recommend called")
    data = request.json
    print("Request JSON:", data)

    prompt = data.get("prompt")
    era = data.get("era", "vintage")
    refresh_seed = data.get("refresh_seed")  # New: refresh functionality
    
    if not prompt:
        return jsonify({"error": "Prompt required"}), 400

    try:
        # Check if we should use enhanced AI or legacy mode
        use_enhanced = True  # Set to False to use legacy mode
        
        if use_enhanced:
            # Enhanced AI mode
            full_prompt = f"{prompt.strip()} in a {era} style"
            
            print(f"🎵 Enhanced AI analyzing prompt: {full_prompt}")
            print("🔍 Step 1-2: Enhanced AI analysis and query generation...")
            
            # Get AI-powered recommendations
            try:
                analysis, search_queries, used_seed = get_ai_powered_recommendations(
                    prompt=full_prompt,
                    refresh_seed=refresh_seed
                )
            except Exception as e:
                print(f"Error getting enhanced AI recommendations: {e}")
                # Fall back to legacy mode
                return recommend_legacy_internal(prompt, era)
            
            # Execute searches using the new queries
            all_tracks = []
            search_count = 0
            
            for query in search_queries[:8]:  # Limit for performance
                try:
                    print(f"   🔍 Searching: {query}")
                    
                    # Try enhanced search first
                    if hasattr(search_tracks_enhanced, '__call__'):
                        tracks = search_tracks_enhanced(query, limit=10)
                        if tracks:
                            all_tracks.extend(tracks)
                            search_count += 1
                            continue
                    
                    # Fallback to individual track search
                    # Parse if the query has artist and title format
                    artist_title_match = re.match(r'^[""](.+?)[""]\s+by\s+(.+)$', query.strip())
                    if artist_title_match:
                        title = artist_title_match.group(1).strip()
                        artist = artist_title_match.group(2).strip()
                        track_data = search_track(title, artist)
                        if track_data:
                            all_tracks.append(track_data)
                    elif 'artist:' in query.lower():
                        # Artist search
                        artist = query.lower().replace('artist:', '').strip().strip('"')
                        track_data = search_track("", artist)
                        if track_data:
                            all_tracks.append(track_data)
                    else:
                        # General search
                        track_data = search_track("", query)
                        if track_data:
                            all_tracks.append(track_data)
                    
                    search_count += 1
                    
                    # Stop if we have enough tracks
                    if not refresh_seed and len(all_tracks) >= 20:
                        break
                    elif refresh_seed and len(all_tracks) >= 30:
                        break
                        
                except Exception as e:
                    print(f"   ❌ Search failed for '{query}': {e}")
                    continue
            
            print(f"   📊 Found {len(all_tracks)} total tracks from {search_count} searches")
            
            if not all_tracks:
                print("No tracks found, falling back to legacy mode...")
                return recommend_legacy_internal(prompt, era)
            
            print(f"   ✅ Returning {len(all_tracks)} tracks")
            
            return jsonify({
                'tracks': all_tracks,
                'total_found': len(all_tracks),
                'queries_used': search_queries[:search_count],
                'refresh_seed': used_seed,
                'analysis': {
                    'style_description': analysis.get('style_description', ''),
                    'approach': analysis.get('analysis_approach', 'default'),
                    'pioneer_artists': analysis.get('pioneer_artists', [])[:3],
                    'contemporary_artists': analysis.get('contemporary_artists', [])[:3],
                },
                'is_refresh': bool(refresh_seed),
                'era': era,
                'mode': 'enhanced'
            })
        
        else:
            # Legacy mode
            return recommend_legacy_internal(prompt, era)
        
    except Exception as e:
        print(f"❌ Recommendation error: {e}")
        print("Falling back to legacy mode...")
        return recommend_legacy_internal(prompt, era)

def recommend_legacy_internal(prompt, era):
    """Internal function for legacy recommendation logic"""
    try:
        full_prompt = f"{prompt.strip()} in a {era} style"
        raw_response = get_sample_suggestions(full_prompt)
        print("Raw GPT response:", raw_response)

        lines = raw_response.strip().split("\n")
        track_list = []

        for line in lines:
            match = re.match(r'^\d+\.\s*[""](.+?)[""]\s+by\s+(.+)$', line.strip())
            if match:
                title = match.group(1).strip()
                artist = match.group(2).strip()
                print(f"Parsed title: {title}, artist: {artist}")
                track_data = search_track(title, artist)
                if track_data:
                    track_list.append(track_data)
            else:
                print(f"Skipped line: {line}")

        return jsonify({
            'tracks': track_list,
            'mode': 'legacy',
            'era': era
        })
        
    except Exception as e:
        print(f"❌ Legacy mode error: {e}")
        return jsonify({
            'error': 'Search failed. Please try again.',
            'details': str(e)
        }), 500

@main.route('/recommend-legacy', methods=['POST'])
def recommend_legacy():
    """Keep your original recommendation logic as backup"""
    print("POST /recommend-legacy called")
    data = request.json
    print("Request JSON:", data)

    prompt = data.get("prompt")
    era = data.get("era", "vintage")

    if not prompt:
        return jsonify({"error": "Prompt required"}), 400

    return recommend_legacy_internal(prompt, era)

@main.route('/refresh', methods=['POST'])
def refresh_recommendations():
    """Dedicated refresh endpoint"""
    data = request.json
    
    prompt = data.get("prompt")
    era = data.get("era", "vintage")
    
    if not prompt:
        return jsonify({"error": "Prompt required"}), 400
    
    # Generate new refresh seed
    import time
    refresh_seed = int(time.time() * 1000)  # Millisecond timestamp
    
    # Call the main recommend function with refresh
    data['refresh_seed'] = refresh_seed
    
    # Temporarily modify request data
    original_json = request.json
    request.json = data
    
    result = recommend()
    
    # Restore original request data
    request.json = original_json
    
    return result

@main.route('/clear-cache', methods=['POST'])
def clear_recommendation_cache():
    """Clear the search results cache"""
    try:
        clear_cache()
        return jsonify({'message': 'Cache cleared successfully'})
    except Exception as e:
        return jsonify({
            'error': 'Failed to clear cache', 
            'details': str(e)
        }), 500

@main.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'music-recommendation-api',
        'features': [
            'basic-recommendations',
            'refresh-functionality', 
            'cache-management',
            'legacy-fallback'
        ]
    })

@main.route('/test-ai', methods=['POST'])
def test_ai():
    """Test endpoint for AI functionality"""
    data = request.json
    prompt = data.get("prompt", "90s boom bap drums")
    
    try:
        analysis, queries, seed = get_ai_powered_recommendations(prompt)
        return jsonify({
            'prompt': prompt,
            'analysis': analysis,
            'queries': queries,
            'seed': seed,
            'status': 'success'
        })
    except Exception as e:
        return jsonify({
            'prompt': prompt,
            'error': str(e),
            'status': 'error'
        }), 500