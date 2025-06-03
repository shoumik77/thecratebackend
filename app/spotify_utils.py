# spotify_utils.py - Enhanced version to work with the new system
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize Spotify client
client_credentials_manager = SpotifyClientCredentials(
    client_id=os.getenv('SPOTIFY_CLIENT_ID'),
    client_secret=os.getenv('SPOTIFY_CLIENT_SECRET')
)
sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

def search_track(title="", artist="", limit=1):
    """
    Enhanced search function that handles both specific track searches and general queries
    """
    try:
        if title and artist:
            # Specific track and artist search
            query = f'track:"{title}" artist:"{artist}"'
        elif artist and not title:
            # Artist-only search (for general queries)
            query = f'artist:"{artist}"'
        elif title and not artist:
            # Title-only search
            query = f'track:"{title}"'
        else:
            # Neither provided
            return None
        
        print(f"   Spotify query: {query}")
        results = sp.search(q=query, type='track', limit=limit)
        
        if results['tracks']['items']:
            track = results['tracks']['items'][0]
            return format_track_data(track)
        else:
            return None
            
    except Exception as e:
        print(f"   Spotify search error: {e}")
        return None

def search_tracks_general(query, limit=20):
    """
    General search function for AI-generated queries
    """
    try:
        print(f"   General Spotify search: {query}")
        results = sp.search(q=query, type='track', limit=limit)
        
        tracks = []
        for track in results['tracks']['items']:
            formatted_track = format_track_data(track)
            if formatted_track:
                tracks.append(formatted_track)
        
        return tracks
        
    except Exception as e:
        print(f"   General search error: {e}")
        return []

def search_by_artist(artist_name, limit=20):
    """
    Search for tracks by a specific artist
    """
    try:
        query = f'artist:"{artist_name}"'
        results = sp.search(q=query, type='track', limit=limit)
        
        tracks = []
        for track in results['tracks']['items']:
            formatted_track = format_track_data(track)
            if formatted_track:
                tracks.append(formatted_track)
        
        return tracks
        
    except Exception as e:
        print(f"   Artist search error: {e}")
        return []

def search_by_genre(genre, limit=20):
    """
    Search for tracks by genre
    """
    try:
        query = f'genre:"{genre}"'
        results = sp.search(q=query, type='track', limit=limit)
        
        tracks = []
        for track in results['tracks']['items']:
            formatted_track = format_track_data(track)
            if formatted_track:
                tracks.append(formatted_track)
        
        return tracks
        
    except Exception as e:
        print(f"   Genre search error: {e}")
        return []

def format_track_data(track):
    """
    Format Spotify track data into consistent structure
    """
    try:
        # Get the largest image
        image_url = None
        if track['album']['images']:
            image_url = track['album']['images'][0]['url']
        
        # Get artist names
        artists = [artist['name'] for artist in track['artists']]
        primary_artist = artists[0] if artists else 'Unknown Artist'
        
        # Get genres (might be empty)
        genres = []
        if 'genres' in track['album'] and track['album']['genres']:
            genres = track['album']['genres']
        
        formatted_track = {
            'id': track['id'],
            'title': track['name'],
            'artist': primary_artist,
            'artists': artists,  # All artists
            'album': track['album']['name'],
            'release_date': track['album']['release_date'],
            'popularity': track['popularity'],
            'explicit': track['explicit'],
            'duration_ms': track['duration_ms'],
            'preview_url': track['preview_url'],
            'external_urls': track['external_urls'],
            'image': image_url,
            'genres': genres,
            'uri': track['uri'],
            'track_number': track['track_number'],
            'disc_number': track['disc_number']
        }
        
        return formatted_track
        
    except Exception as e:
        print(f"   Track formatting error: {e}")
        return None

def get_track_features(track_id):
    """
    Get audio features for a track (tempo, energy, etc.)
    """
    try:
        features = sp.audio_features([track_id])
        if features and features[0]:
            return {
                'energy': features[0]['energy'],
                'valence': features[0]['valence'],
                'tempo': features[0]['tempo'],
                'danceability': features[0]['danceability'],
                'acousticness': features[0]['acousticness'],
                'instrumentalness': features[0]['instrumentalness'],
                'key': features[0]['key'],
                'mode': features[0]['mode'],
                'time_signature': features[0]['time_signature']
            }
        return None
        
    except Exception as e:
        print(f"   Audio features error: {e}")
        return None

def get_artist_info(artist_id):
    """
    Get detailed artist information
    """
    try:
        artist = sp.artist(artist_id)
        return {
            'name': artist['name'],
            'genres': artist['genres'],
            'popularity': artist['popularity'],
            'followers': artist['followers']['total'],
            'external_urls': artist['external_urls'],
            'images': artist['images']
        }
        
    except Exception as e:
        print(f"   Artist info error: {e}")
        return None

def get_recommendations_by_seed(seed_artists=None, seed_tracks=None, seed_genres=None, limit=20, **kwargs):
    """
    Get Spotify's built-in recommendations
    """
    try:
        recommendations = sp.recommendations(
            seed_artists=seed_artists,
            seed_tracks=seed_tracks, 
            seed_genres=seed_genres,
            limit=limit,
            **kwargs  # Additional audio feature parameters
        )
        
        tracks = []
        for track in recommendations['tracks']:
            formatted_track = format_track_data(track)
            if formatted_track:
                tracks.append(formatted_track)
        
        return tracks
        
    except Exception as e:
        print(f"   Recommendations error: {e}")
        return []

# Enhanced search function for the new AI system
def search_tracks_enhanced(query, limit=20):
    """
    Enhanced search that tries multiple approaches for better results
    """
    all_tracks = []
    
    # Try general search first
    tracks = search_tracks_general(query, limit)
    all_tracks.extend(tracks)
    
    # If query contains "artist:" or "track:" prefixes, handle specially
    if 'artist:' in query.lower():
        artist_name = query.lower().split('artist:')[1].strip().strip('"')
        artist_tracks = search_by_artist(artist_name, limit//2)
        all_tracks.extend(artist_tracks)
    
    if 'genre:' in query.lower():
        genre_name = query.lower().split('genre:')[1].strip().strip('"')
        genre_tracks = search_by_genre(genre_name, limit//2)
        all_tracks.extend(genre_tracks)
    
    # Remove duplicates by track ID
    seen_ids = set()
    unique_tracks = []
    for track in all_tracks:
        if track['id'] not in seen_ids:
            seen_ids.add(track['id'])
            unique_tracks.append(track)
    
    return unique_tracks[:limit]

# Update your existing search_track function to work with new system
def search_track_legacy(title, artist):
    """
    Keep your original function for backward compatibility
    """
    return search_track(title, artist, limit=1)