# backend/gpt_utils.py - Fixed version with proper error handling
from openai import OpenAI
import json
import os
from dotenv import load_dotenv
import random
import time
import re

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(
    api_key=os.getenv('OPENAI_API_KEY')
)

# Store previous results to ensure different outputs
previous_results_cache = {}

def clean_json_response(response_text):
    """Clean and extract JSON from OpenAI response"""
    try:
        # Remove any markdown code blocks
        cleaned = re.sub(r'```json\s*', '', response_text)
        cleaned = re.sub(r'```\s*$', '', cleaned)
        
        # Find JSON object in the response
        json_match = re.search(r'\{.*\}', cleaned, re.DOTALL)
        if json_match:
            return json_match.group(0)
        
        return cleaned.strip()
    except Exception as e:
        print(f"Error cleaning JSON: {e}")
        return response_text

def get_prompt_analysis(prompt, refresh_seed=None):
    """Analyze the user's prompt to understand their intent with focus on artist discovery"""
    
    # Create variation in analysis based on refresh
    analysis_variations = [
        "You are a music historian focusing on the PIONEERS and FOUNDERS of this sound.",
        "You are a contemporary music curator focused on MODERN ARTISTS and CURRENT SCENES.",
        "You are an underground music expert focused on OBSCURE and LESSER-KNOWN artists.",
        "You are a music anthropologist studying the CULTURAL and REGIONAL aspects of this sound.",
        "You are a record collector focused on VINTAGE and CLASSIC representations of this style."
    ]
    
    # Use refresh seed to get different analysis approaches
    if refresh_seed is not None:
        random.seed(refresh_seed)
        analysis_approach = random.choice(analysis_variations)
        random.seed()  # Reset seed
    else:
        analysis_approach = analysis_variations[0]  # Default approach
    
    analysis_prompt = f"""
    {analysis_approach}
    
    User Request: "{prompt}"
    
    Analyze this request and return ONLY a valid JSON object (no extra text, no markdown):
    
    {{
        "style_description": "detailed description of the musical style",
        "pioneer_artists": ["3-5 founding/defining artists"],
        "contemporary_artists": ["3-5 current artists in this style"],
        "classic_tracks": ["3-5 essential songs that define this sound"],
        "key_albums": ["2-3 landmark albums"],
        "related_styles": ["connected genres/subgenres"],
        "instruments": ["key instruments/sounds"],
        "era": "primary time period",
        "mood_keywords": ["emotional descriptors"],
        "avoid_terms": ["words to avoid in searches"],
        "analysis_approach": "{analysis_approach.split('.')[0]}"
    }}
    
    Return ONLY the JSON object, nothing else.
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": f"{analysis_approach} You MUST respond with ONLY valid JSON, no additional text or markdown."},
                {"role": "user", "content": analysis_prompt}
            ],
            max_tokens=600,
            temperature=0.7 if refresh_seed else 0.3
        )
        
        response_text = response.choices[0].message.content.strip()
        print(f"Raw analysis response: {response_text[:200]}...")
        
        # Clean and parse JSON
        cleaned_json = clean_json_response(response_text)
        analysis = json.loads(cleaned_json)
        return analysis
        
    except json.JSONDecodeError as e:
        print(f"JSON decode error in analysis: {e}")
        print(f"Response was: {response_text}")
        # Return structured fallback
        return create_fallback_analysis(prompt, analysis_approach)
    except Exception as e:
        print(f"Error in prompt analysis: {e}")
        return create_fallback_analysis(prompt, analysis_approach)

def create_fallback_analysis(prompt, approach="default"):
    """Create a fallback analysis when AI fails"""
    # Basic keyword analysis
    prompt_lower = prompt.lower()
    
    # Detect genre from prompt
    genre_keywords = {
        'boom bap': {'genre': 'hip hop', 'era': '90s', 'pioneers': ['DJ Premier', 'Pete Rock', 'Large Professor']},
        'jazz': {'genre': 'jazz', 'era': '50s-70s', 'pioneers': ['Miles Davis', 'John Coltrane', 'Bill Evans']},
        'lo-fi': {'genre': 'lo-fi', 'era': '2010s', 'pioneers': ['Nujabes', 'J Dilla', 'Madlib']},
        'trap': {'genre': 'trap', 'era': '2010s', 'pioneers': ['Metro Boomin', 'Southside', 'Lex Luger']},
        'house': {'genre': 'house', 'era': '80s-90s', 'pioneers': ['Frankie Knuckles', 'Larry Heard', 'Marshall Jefferson']},
        'soul': {'genre': 'soul', 'era': '60s-70s', 'pioneers': ['James Brown', 'Marvin Gaye', 'Aretha Franklin']},
        'funk': {'genre': 'funk', 'era': '70s', 'pioneers': ['James Brown', 'Parliament-Funkadelic', 'Sly Stone']}
    }
    
    detected_info = None
    for keyword, info in genre_keywords.items():
        if keyword in prompt_lower:
            detected_info = info
            break
    
    if not detected_info:
        detected_info = {'genre': 'various', 'era': 'various', 'pioneers': ['Various Artists']}
    
    return {
        "style_description": f"{detected_info['genre']} style music from the {detected_info['era']} era",
        "pioneer_artists": detected_info['pioneers'],
        "contemporary_artists": ["Modern Artist 1", "Modern Artist 2"],
        "classic_tracks": [f"Classic {detected_info['genre']} track"],
        "key_albums": [f"Essential {detected_info['genre']} album"],
        "related_styles": [detected_info['genre']],
        "instruments": ["drums", "bass", "samples"],
        "era": detected_info['era'],
        "mood_keywords": ["rhythmic", "groovy"],
        "avoid_terms": [prompt.split()[0]] if prompt else [],
        "analysis_approach": approach
    }

def generate_artist_focused_queries(prompt, analysis, refresh_seed=None):
    """Generate search queries focused on specific artists and works"""
    
    # Get artists and info from analysis
    pioneer_artists = analysis.get('pioneer_artists', [])
    contemporary_artists = analysis.get('contemporary_artists', [])
    related_styles = analysis.get('related_styles', [])
    era = analysis.get('era', '')
    
    queries = []
    
    # Add artist searches
    for artist in pioneer_artists[:3]:
        if artist and artist != "Various Artists":
            queries.append(f'artist:"{artist}"')
    
    for artist in contemporary_artists[:2]:
        if artist and artist != "Modern Artist 1" and artist != "Modern Artist 2":
            queries.append(f'artist:"{artist}"')
    
    # Add style searches
    for style in related_styles[:2]:
        if style:
            queries.append(f'{style}')
            if era:
                queries.append(f'{era} {style}')
    
    # Add era-based searches
    if era and era != 'various':
        queries.append(f'{era} music')
        queries.append(f'{era} instrumental')
    
    # Add prompt variations
    queries.append(prompt)
    if 'drums' in prompt.lower():
        queries.append(prompt.replace('drums', 'beats'))
        queries.append(prompt.replace('drums', 'percussion'))
    
    # Remove empty queries and duplicates
    queries = [q.strip() for q in queries if q and q.strip()]
    queries = list(dict.fromkeys(queries))  # Remove duplicates while preserving order
    
    return queries[:10]

def generate_discovery_queries(analysis, refresh_seed=None):
    """Generate additional discovery queries"""
    
    discovery_queries = []
    
    # Add instrumental versions
    for style in analysis.get('related_styles', [])[:2]:
        if style:
            discovery_queries.append(f'{style} instrumental')
            discovery_queries.append(f'{style} samples')
    
    # Add era-specific discoveries
    era = analysis.get('era', '')
    if era and era != 'various':
        discovery_queries.append(f'vintage {era}')
        discovery_queries.append(f'{era} classics')
    
    return discovery_queries[:5]

def get_ai_powered_recommendations(prompt, refresh_seed=None):
    """Enhanced AI-powered recommendation engine with refresh functionality"""
    
    # Generate refresh seed if not provided
    if refresh_seed is None:
        refresh_seed = int(time.time())
    
    print("🔍 Analyzing musical context...")
    if refresh_seed:
        print("🔄 Using refresh mode for completely different results...")
    
    analysis = get_prompt_analysis(prompt, refresh_seed)
    
    print(f"   Approach: {analysis.get('analysis_approach', 'default')}")
    print(f"   Style: {analysis.get('style_description', '')[:60]}...")
    print(f"   Pioneer Artists: {', '.join(analysis.get('pioneer_artists', [])[:3])}")
    print(f"   Contemporary: {', '.join(analysis.get('contemporary_artists', [])[:3])}")
    
    print("🎯 Generating artist-focused search queries...")
    main_queries = generate_artist_focused_queries(prompt, analysis, refresh_seed)
    
    print("🔎 Adding discovery queries for hidden gems...")
    discovery_queries = generate_discovery_queries(analysis, refresh_seed)
    
    # Combine queries
    all_queries = main_queries + discovery_queries
    if refresh_seed:
        random.seed(refresh_seed)
        random.shuffle(all_queries)
        random.seed()
    
    print(f"   Generated {len(all_queries)} diverse search strategies")
    
    return analysis, all_queries, refresh_seed

def clear_cache():
    """Clear the previous results cache"""
    global previous_results_cache
    previous_results_cache.clear()
    print("🗑️ Results cache cleared")

# Keep the old function for backward compatibility
def get_sample_suggestions(prompt):
    """Legacy function for backward compatibility"""
    try:
        analysis, queries, _ = get_ai_powered_recommendations(prompt)
        
        # Format as old-style response
        response_lines = []
        for i, query in enumerate(queries[:5], 1):
            # Try to format as "Track" by Artist
            if 'artist:' in query:
                artist = query.replace('artist:', '').strip('"')
                response_lines.append(f'{i}. "Sample Track {i}" by {artist}')
            else:
                response_lines.append(f'{i}. "Sample Track {i}" by {query}')
        
        return '\n'.join(response_lines)
        
    except Exception as e:
        print(f"Error in legacy function: {e}")
        return f'1. "Sample Track" by Various Artists\n2. "Sample Track 2" by Various Artists'

# Test function
def ai_filter_and_rank_tracks(tracks, original_prompt, analysis, refresh_seed=None):
    """Enhanced filtering and ranking with refresh support"""
    
    if not tracks:
        return []
    
    print(f"🎵 Filtering and ranking {len(tracks)} tracks...")
    
    # Remove duplicates by track ID
    seen_ids = set()
    unique_tracks = []
    for track in tracks:
        track_id = track.get('id')
        if track_id and track_id not in seen_ids:
            seen_ids.add(track_id)
            unique_tracks.append(track)
        elif not track_id:
            # If no ID, add anyway but check by title+artist
            track_key = f"{track.get('title', '')}-{track.get('artist', '')}"
            if track_key not in seen_ids:
                seen_ids.add(track_key)
                unique_tracks.append(track)
    
    print(f"   After deduplication: {len(unique_tracks)} unique tracks")
    
    # Simple ranking: prefer tracks that match analysis criteria
    def rank_track(track):
        score = 0
        
        # Check if artist matches pioneers or contemporary
        artist = track.get('artist', '').lower()
        pioneer_artists = [a.lower() for a in analysis.get('pioneer_artists', [])]
        contemporary_artists = [a.lower() for a in analysis.get('contemporary_artists', [])]
        
        if any(pioneer in artist for pioneer in pioneer_artists):
            score += 50
        elif any(contemporary in artist for contemporary in contemporary_artists):
            score += 30
        
        # Check if title contains relevant keywords
        title = track.get('title', '').lower()
        mood_keywords = analysis.get('mood_keywords', [])
        for keyword in mood_keywords:
            if keyword.lower() in title:
                score += 10
        
        # Prefer older tracks for vintage eras
        era = analysis.get('era', '')
        if era and track.get('release_date'):
            try:
                track_year = int(track['release_date'][:4])
                if '90s' in era and 1990 <= track_year <= 1999:
                    score += 25
                elif '80s' in era and 1980 <= track_year <= 1989:
                    score += 25
                elif '70s' in era and 1970 <= track_year <= 1979:
                    score += 25
            except:
                pass
        
        # Add some randomness for refresh
        if refresh_seed:
            random.seed(refresh_seed + hash(track.get('id', track.get('title', ''))))
            score += random.randint(0, 20)
            random.seed()
        
        return score
    
    # Sort by ranking score
    ranked_tracks = sorted(unique_tracks, key=rank_track, reverse=True)
    
    print(f"   Ranked and returning top {min(len(ranked_tracks), 20)} tracks")
    return ranked_tracks[:20]

def ai_rank_tracks_improved(tracks, prompt, analysis, refresh_seed=None):
    """Improved ranking system - alias for ai_filter_and_rank_tracks"""
    return ai_filter_and_rank_tracks(tracks, prompt, analysis, refresh_seed)

def diversify_tracks(tracks, refresh_seed=None):
    """Ensure track diversity by artist and avoid repetition"""
    
    if refresh_seed is not None:
        random.seed(refresh_seed)
        tracks = tracks.copy()
        random.shuffle(tracks)
        random.seed()
    
    seen_artists = set()
    diversified = []
    remaining = []
    
    # First pass: one track per artist
    for track in tracks:
        artist = track.get('artist', '').lower()
        if artist not in seen_artists:
            diversified.append(track)
            seen_artists.add(artist)
        else:
            remaining.append(track)
    
    # Second pass: add remaining tracks if we need more
    for track in remaining:
        if len(diversified) >= 20:
            break
        diversified.append(track)
    
    return diversified

def analyze_sample_potential(track_data, target_analysis):
    """Analyze how good a specific track would be for sampling"""
    
    # Extract track characteristics
    release_year = track_data.get('release_date', '')[:4] if track_data.get('release_date') else 'unknown'
    popularity = track_data.get('popularity', 0)
    explicit = track_data.get('explicit', False)
    
    score = 0
    reasons = []
    
    # Era matching with more flexibility
    target_eras = target_analysis.get('era_periods', [target_analysis.get('era', '')])
    if target_eras and release_year != 'unknown':
        for era in target_eras:
            if any(decade in era for decade in ['60s', '70s', '80s', '90s']) and release_year != 'unknown':
                era_decade = ''.join(filter(str.isdigit, era))[:2]
                if era_decade and era_decade in release_year:
                    score += 25
                    reasons.append(f"Perfect era match ({release_year})")
                    break
    
    # Popularity scoring (more nuanced)
    if popularity < 20:
        score += 25
        reasons.append("Rare gem (excellent for sampling)")
    elif popularity < 40:
        score += 15
        reasons.append("Obscure track (great for sampling)")
    elif popularity < 65:
        score += 5
        reasons.append("Moderately known")
    
    # Explicit tracks bonus
    if explicit:
        score += 10
        reasons.append("Explicit version available")
    
    # Vintage bonus
    if release_year != 'unknown' and int(release_year) < 1990:
        score += 15
        reasons.append("Vintage recording")
    
    return {
        'score': score,
        'reasons': reasons,
        'sample_grade': 'S' if score >= 60 else 'A' if score >= 40 else 'B' if score >= 25 else 'C'
    }

def test_fixed_system():
    """Test the fixed system"""
    
    test_prompts = [
        "90s boom bap drums",
        "lo-fi jazz piano",
        "dark ambient"
    ]
    
    print("🧪 Testing Fixed AI System...")
    
    for prompt in test_prompts:
        print(f"\n🔍 Testing: '{prompt}'")
        try:
            analysis, queries, seed = get_ai_powered_recommendations(prompt)
            print(f"   ✅ Success - got {len(queries)} queries")
            print(f"   First query: {queries[0] if queries else 'None'}")
            
            # Test ranking with dummy tracks
            dummy_tracks = [
                {'id': '1', 'title': 'Test Track 1', 'artist': 'Test Artist', 'release_date': '1995-01-01'},
                {'id': '2', 'title': 'Test Track 2', 'artist': 'Another Artist', 'release_date': '2000-01-01'}
            ]
            ranked = ai_filter_and_rank_tracks(dummy_tracks, prompt, analysis)
            print(f"   Ranking test: {len(ranked)} tracks ranked")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")

if __name__ == "__main__":
    test_fixed_system()