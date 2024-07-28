import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import streamlit as st
import pandas as pd
from sklearn.neighbors import NearestNeighbors
import os
from dotenv import load_dotenv

#Loading environment variables
load_dotenv() 

# Authenticate with Spotify
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=os.environ.get('SPOTIFY_CLIENT_ID'), client_secret=os.environ.get('SPOTIFY_CLIENT_SECRET')))

@st.cache_data
def get_playlist_tracks(playlist_link):
    # Extract the playlist ID from the link
    playlist_id = playlist_link.split("/")[-1].split("?")[0]

    # Fetch playlist tracks
    results = sp.playlist_tracks(playlist_id)
    tracks = results['items']

    # Collect track details
    track_data = []
    for item in tracks:
        track = item['track']
        track_id = track['id']
        
        # Fetch audio features for the track
        audio_features = sp.audio_features(track_id)[0]
        
        track_info = {
            'song': track['name'],
            'artist': track['artists'][0]['name'],
            'year': track['album']['release_date'],
            'popularity': track['popularity'],
            'tempo': audio_features['tempo'] if audio_features else None, 
            'danceability': audio_features['danceability'] if audio_features else None,
            'energy': audio_features['energy'] if audio_features else None
        }
        track_data.append(track_info)

    # Convert to DataFrame
    df = pd.DataFrame(track_data)
    
    return df 

# Prepare data for machine learning
def prepare_data(df):
    # Select relevant features
    features = df[['tempo', 'danceability', 'energy', 'popularity']]
    return features

# Train a machine learning model
def train_model(features):
    # Initialize the model
    model = NearestNeighbors(n_neighbors=10, algorithm='auto')
    
    # Fit the model
    model.fit(features)
    
    return model

# Find similar songs using the trained model
def find_similar_songs_ml(song_title, df, model):
    # Find the input song
    input_song = df[df['song'] == song_title.split(' by ')[0]]
    if input_song.empty:
        st.write("Song not found in dataset.")
        return pd.Series(), pd.DataFrame()
    
    # Extract input song features
    input_features = input_song[['tempo', 'danceability', 'energy', 'popularity']].values
    
    # Find similar songs
    distances, indices = model.kneighbors(input_features)
    
    # Get similar songs
    similar_songs = df.iloc[indices[0]]
    
    return input_song, similar_songs

# Get song suggestions for autocomplete
def get_song_suggestions(df, query):
    suggestions = df[df['song'].str.contains(query, case=False)]['song'].apply(lambda x: f"{x} by {df[df['song'] == x]['artist'].iloc[0]}").tolist()
    return suggestions

# Streamlit app
st.title("DJ Set Creator")

playlist_link = st.text_input("Enter your Spotify playlist link:", "")

if playlist_link:
    df1 = get_playlist_tracks(playlist_link)
    
    # Prepare the data and train the model
    features = prepare_data(df1)
    model = train_model(features)
    
    song_title_input = st.text_input("Enter song title to search:")
    if song_title_input:
        song_suggestions = get_song_suggestions(df1, song_title_input)
        song_title_input = st.selectbox("Select a song:", song_suggestions)

        if not song_suggestions:
            st.write("No matching songs found.")
        else:
            if st.button("Find Similar Songs"):
                input_song, similar_songs = find_similar_songs_ml(song_title_input, df1, model)
                if similar_songs.empty:
                    st.write("No similar songs found.")
                else:
                    st.write(f"### Current Song: {input_song['song'].iloc[0]} by {input_song['artist'].iloc[0]}")
                    st.write("Here are some songs you might like:")
                    similar_songs['year'] = similar_songs['year'].astype(str)
                    st.dataframe(similar_songs[['song', 'artist', 'tempo', 'danceability', 'energy', 'popularity', 'year']])
else:
    st.write("Please enter a valid Spotify playlist link to get started.")
