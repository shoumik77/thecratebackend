# backend/app.py - FIXED to work like your original with refresh support
from flask import Flask, request, jsonify, redirect, session
from flask_cors import CORS
import requests
import base64
import secrets
import os
from urllib.parse import urlencode
from dotenv import load_dotenv

# Import enhanced AI functions from gpt_utils - FIXED IMPORTS
from gpt_utils import (
    get_prompt_analysis,
    get_ai_powered_recommendations,
    ai_filter_and_rank_tracks,
    clear_cache
)

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', secrets.token_hex(16))

# Configure CORS to allow credentials and specific origins - UPDATED FOR PORT 3000
CORS(app, 
     origins=[
         "http://localhost:3000", 
         "http://127.0.0.1:3000",
         "https://thecratefrontend.vercel.app/",  # Will update this
         "https://your-custom-domain.com"        # If you have one
     ],
     supports_credentials=True,
     allow_headers=["Content-Type", "Authorization"],
     methods=["GET", "POST", "OPTIONS"])

# API Keys - AI is REQUIRED for core functionality
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Spotify App Credentials
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
SPOTIFY_REDIRECT_URI = os.getenv('SPOTIFY_REDIRECT_URI', 'http://127.0.0.1:5001/auth/callback')

# Spotify API endpoints
SPOTIFY_AUTH_URL = 'https://accounts.spotify.com/authorize'
SPOTIFY_TOKEN_URL = 'https://accounts.spotify.com/api/token'
SPOTIFY_API_BASE = 'https://api.spotify.com/v1'

@app.route('/')
def index():
    """Root endpoint with API info"""
    return jsonify({
        'message': 'TheCrate - AI-Powered Sample Discovery',
        'version': '3.0.0',
        'description': 'Intelligent sample finder using enhanced OpenAI prompts and Spotify',
        'endpoints': {
            '/auth/login': 'GET - Start Spotify OAuth flow',
            '/auth/callback': 'GET - Spotify OAuth callback',
            '/recommend': 'POST - AI-powered sample recommendations with refresh',
            '/analyze-prompt': 'POST - Analyze search prompt with AI',
            '/health': 'GET - Health check',
            '/clear-cache': 'POST - Clear AI cache'
        },
        'status': 'running',
        'ai_enabled': bool(OPENAI_API_KEY),
        'spotify_configured': bool(SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET),
        'frontend_url': 'http://localhost:3000',
        'features': [
            'Enhanced AI prompt engineering',
            'Refresh functionality for different results',
            'Sample archaeology and genre DNA analysis',
            'Producer-level crate digging intelligence',
            'Original source material discovery'
        ]
    })

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'TheCrate AI Backend v3.0',
        'ai_status': 'enabled' if OPENAI_API_KEY else 'missing - REQUIRED',
        'spotify_auth': 'configured' if SPOTIFY_CLIENT_ID else 'missing',
        'frontend_url': 'http://localhost:3000',
        'ai_features': [
            'Genre archaeology',
            'Refresh functionality',
            'Sampling lineage analysis',
            'Producer mindset AI',
            'Source material discovery'
        ]
    })

@app.route('/auth/login')
def spotify_login():
    """Redirect user to Spotify authorization page"""
    if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
        return jsonify({
            'error': 'Spotify credentials not configured',
            'message': 'Please set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET environment variables'
        }), 500
    
    # Generate random state for security
    state = secrets.token_urlsafe(32)
    session['spotify_auth_state'] = state
    
    # Spotify authorization parameters
    params = {
        'client_id': SPOTIFY_CLIENT_ID,
        'response_type': 'code',
        'redirect_uri': SPOTIFY_REDIRECT_URI,
        'state': state,
        'scope': ' '.join([
            'user-read-private',
            'user-read-email', 
            'streaming',
            'user-modify-playback-state',
            'user-read-playback-state',
            'playlist-read-private',
            'playlist-read-collaborative',
            'user-top-read'
        ]),
        'show_dialog': 'true'
    }
    
    auth_url = f"{SPOTIFY_AUTH_URL}?{urlencode(params)}"
    return redirect(auth_url)

@app.route('/auth/callback')
def spotify_callback():
    """Handle Spotify authorization callback"""
    code = request.args.get('code')
    state = request.args.get('state')
    error = request.args.get('error')
    
    # Handle authorization errors - UPDATED TO PORT 3000
    if error:
        frontend_url = f"http://localhost:3000?error={error}"
        return redirect(frontend_url)
    
    # Verify state parameter for security - UPDATED TO PORT 3000
    if not state or state != session.get('spotify_auth_state'):
        frontend_url = "http://localhost:3000?error=invalid_state"
        return redirect(frontend_url)
    
    if not code:
        frontend_url = "http://localhost:3000?error=no_code"
        return redirect(frontend_url)
    
    # Exchange authorization code for access token
    auth_header = base64.b64encode(
        f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}".encode()
    ).decode()
    
    token_data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': SPOTIFY_REDIRECT_URI
    }
    
    token_headers = {
        'Authorization': f'Basic {auth_header}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    try:
        response = requests.post(SPOTIFY_TOKEN_URL, data=token_data, headers=token_headers)
        
        if response.status_code != 200:
            print(f"Token exchange failed: {response.status_code} - {response.text}")
            frontend_url = "http://localhost:3000?error=token_exchange_failed"
            return redirect(frontend_url)
        
        token_info = response.json()
        access_token = token_info['access_token']
        
        session.pop('spotify_auth_state', None)
        
        # Redirect back to frontend with token - UPDATED TO PORT 3000
        frontend_url = f"http://localhost:3000?access_token={access_token}"
        return redirect(frontend_url)
        
    except Exception as e:
        print(f"Error during token exchange: {e}")
        frontend_url = "http://localhost:3000?error=server_error"
        return redirect(frontend_url)

@app.route('/analyze-prompt', methods=['POST'])
def analyze_prompt():
    """Analyze user prompt with enhanced AI to provide insights"""
    if not OPENAI_API_KEY:
        return jsonify({'error': 'AI functionality requires OpenAI API key'}), 500
    
    try:
        data = request.get_json()
        prompt = data.get('prompt', '').strip()
        
        if not prompt:
            return jsonify({'error': 'No prompt provided'}), 400
        
        print(f"🔍 Analyzing prompt: {prompt}")
        analysis = get_prompt_analysis(prompt)
        
        return jsonify({
            'analysis': analysis,
            'prompt': prompt,
            'ai_version': 'Enhanced Sample Discovery v3.0'
        })
        
    except Exception as e:
        print(f"Error analyzing prompt: {e}")
        return jsonify({'error': 'Failed to analyze prompt'}), 500

@app.route('/recommend', methods=['POST'])
def get_recommendations():
    """Get enhanced AI-powered sample recommendations with refresh support"""
    if not OPENAI_API_KEY:
        return jsonify({
            'error': 'AI functionality disabled',
            'message': 'TheCrate requires OpenAI API key for AI-powered sample discovery',
            'setup_url': 'https://platform.openai.com/api-keys'
        }), 500
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
            
        prompt = data.get('prompt', '').strip()
        refresh_seed = data.get('refresh_seed')  # NEW: For refresh functionality
        
        if not prompt:
            return jsonify({'error': 'No prompt provided'}), 400
        
        print(f"🤖 Enhanced AI analyzing prompt: {prompt}")
        if refresh_seed:
            print("🔄 Using refresh mode for different results...")
        
        # Use enhanced AI to get intelligent recommendations
        recommendations = get_ai_powered_recommendations_wrapper(prompt, refresh_seed)
        
        print(f"✨ Enhanced AI found {len(recommendations)} recommendations")
        return jsonify(recommendations)
    
    except Exception as e:
        print(f"Error getting enhanced AI recommendations: {e}")
        return jsonify({'error': f'Failed to get AI recommendations: {str(e)}'}), 500

@app.route('/clear-cache', methods=['POST'])
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

def get_ai_powered_recommendations_wrapper(prompt, refresh_seed=None):
    """Wrapper function that returns recommendations in the format your frontend expects"""
    
    try:
        # Step 1 & 2: Get enhanced AI analysis and search queries using gpt_utils
        print("🔍 Step 1-2: Enhanced AI analysis and query generation...")
        
        # FIXED: Properly handle the 3 return values
        analysis, search_queries, used_seed = get_ai_powered_recommendations(prompt, refresh_seed)
        
        # Step 3: Search Spotify with AI-generated queries
        print("🎵 Step 3: Searching Spotify with enhanced AI queries...")
        all_tracks = []
        successful_searches = 0
        
        for i, query in enumerate(search_queries[:8]):  # Use more queries for better results
            print(f"   Query {i+1}: {query}")
            tracks = search_spotify_tracks(query, limit=10)
            if tracks:
                all_tracks.extend(tracks)
                successful_searches += 1
        
        print(f"   Found {len(all_tracks)} tracks from {successful_searches} successful searches")
        
        if not all_tracks:
            # Return your original format even when no results
            return []
        
        # Step 4: Enhanced AI-powered filtering and ranking
        print("🧠 Step 4: Enhanced AI filtering and ranking results...")
        filtered_tracks = ai_filter_and_rank_tracks(all_tracks, prompt, analysis, refresh_seed)
        
        # IMPORTANT: Return in your original format (array of tracks)
        # But we can add metadata for the refresh functionality if needed
        return filtered_tracks
        
    except Exception as e:
        print(f"Error in AI recommendations wrapper: {e}")
        # Return empty array on error to match your original format
        return []

def search_spotify_tracks(query, limit=10):
    """Search Spotify for tracks using client credentials"""
    try:
        access_token = get_client_credentials_token()
        if not access_token:
            return []
        
        search_url = f"{SPOTIFY_API_BASE}/search"
        search_params = {
            'q': query,
            'type': 'track',
            'limit': limit,
            'market': 'US'
        }
        
        search_headers = {
            'Authorization': f'Bearer {access_token}'
        }
        
        response = requests.get(search_url, params=search_params, headers=search_headers)
        
        if response.status_code != 200:
            print(f"Search failed for '{query}': {response.status_code}")
            return []
        
        search_data = response.json()
        tracks = search_data.get('tracks', {}).get('items', [])
        
        formatted_tracks = []
        for track in tracks:
            formatted_track = format_track_data(track)
            if formatted_track:
                formatted_tracks.append(formatted_track)
        
        return formatted_tracks
        
    except Exception as e:
        print(f"Error searching Spotify for '{query}': {e}")
        return []

def get_client_credentials_token():
    """Get client credentials access token for Spotify API"""
    if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
        return None
    
    auth_header = base64.b64encode(
        f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}".encode()
    ).decode()
    
    token_data = {
        'grant_type': 'client_credentials'
    }
    
    token_headers = {
        'Authorization': f'Basic {auth_header}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    try:
        response = requests.post(SPOTIFY_TOKEN_URL, data=token_data, headers=token_headers)
        
        if response.status_code == 200:
            return response.json()['access_token']
        else:
            print(f"Failed to get client credentials token: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"Error getting client credentials token: {e}")
        return None

def format_track_data(track):
    """Format Spotify track data for frontend with enhanced metadata"""
    try:
        album_images = track.get('album', {}).get('images', [])
        album_cover = album_images[0]['url'] if album_images else ''
        
        # Return in the EXACT format your frontend expects
        return {
            'id': track['id'],
            'title': track['name'],
            'artist': ', '.join([artist['name'] for artist in track['artists']]),
            'album': track['album']['name'],
            'album_cover': album_cover,
            'image': album_cover,  # Add both for compatibility
            'spotify_url': track['external_urls']['spotify'],
            'spotify_uri': track['uri'],
            'external_urls': track['external_urls'],  # For compatibility
            'preview_url': track.get('preview_url'),
            'duration_ms': track['duration_ms'],
            'popularity': track['popularity'],
            'explicit': track['explicit'],
            'release_date': track['album'].get('release_date', ''),
            'genres': track.get('genres', []),
            # Enhanced metadata for sample analysis
            'sample_potential': calculate_sample_score(track),
            'era': extract_era_from_date(track['album'].get('release_date', '')),
            'sample_grade': grade_track_for_sampling(track)
        }
    except Exception as e:
        print(f"Error formatting track data: {e}")
        return None

def calculate_sample_score(track):
    """Calculate how good this track would be for sampling"""
    score = 0
    
    # Lower popularity = more obscure = better for sampling
    popularity = track.get('popularity', 50)
    if popularity < 30:
        score += 30
    elif popularity < 60:
        score += 15
    
    # Older tracks often have better sample material
    release_date = track.get('album', {}).get('release_date', '')
    if release_date:
        year = int(release_date[:4]) if len(release_date) >= 4 else 2020
        if year < 1980:
            score += 25
        elif year < 1990:
            score += 20
        elif year < 2000:
            score += 15
    
    # Explicit tracks might have better breaks
    if track.get('explicit', False):
        score += 10
    
    return min(score, 100)  # Cap at 100

def extract_era_from_date(release_date):
    """Extract era/decade from release date"""
    if not release_date or len(release_date) < 4:
        return "Unknown"
    
    year = int(release_date[:4])
    if year < 1970:
        return "60s"
    elif year < 1980:
        return "70s"
    elif year < 1990:
        return "80s"
    elif year < 2000:
        return "90s"
    elif year < 2010:
        return "2000s"
    elif year < 2020:
        return "2010s"
    else:
        return "2020s"

def grade_track_for_sampling(track):
    """Give a letter grade for sampling potential"""
    score = calculate_sample_score(track)
    
    if score >= 70:
        return "A"
    elif score >= 50:
        return "B"
    elif score >= 30:
        return "C"
    else:
        return "D"

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    print("🤖 TheCrate Enhanced AI-Powered Backend Starting...")
    print(f"📱 Frontend URL: http://localhost:3000")
    print(f"🔙 Backend URL: http://localhost:5001")
    print(f"🔐 Spotify Redirect URI: {SPOTIFY_REDIRECT_URI}")
    print("🧠 AI Features: Enhanced prompt engineering, refresh functionality, genre archaeology, sample lineage analysis")
    
    # Check AI configuration
    if not OPENAI_API_KEY:
        print("\n❌ CRITICAL: OpenAI API key not found!")
        print("   TheCrate v3.0 requires OpenAI API access for enhanced sample discovery")
        print("   Please set OPENAI_API_KEY in your .env file")
        print("   Get your API key at: https://platform.openai.com/api-keys")
        print("\n⚠️  Enhanced AI features will not function without API key!")
    else:
        print("✅ OpenAI API configured - Enhanced AI features enabled")
    
    # Check Spotify configuration
    if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
        print("\n⚠️  WARNING: Spotify credentials not found!")
        print("   Please set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET")
    else:
        print("✅ Spotify credentials configured")
    
    print("\n🚀 Starting enhanced AI-powered sample discovery server...")
    print("🎯 Now with producer-level crate digging intelligence and refresh functionality!")
    
    # Production-ready server start
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=False)