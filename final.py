import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import streamlit as st
import pandas as pd
import json
import streamlit.components.v1 as com
from streamlit_lottie import st_lottie  
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
            'album': track['album']['name'],
            'year': track['album']['release_date'],
            'duration (ms)': track['duration_ms'],
            'popularity': track['popularity'],
            'tempo': audio_features['tempo'] if audio_features else None, 
            'danceability': audio_features['danceability'] if audio_features else None
        }
        track_data.append(track_info)

    # Convert to DataFrame
    df = pd.DataFrame(track_data)
    df['year'] = pd.to_datetime(df['year'], errors='coerce', format='%Y-%m-%d').dt.year
    return df 

def find_similar_songs(song_title=None, min_tempo=None, max_tempo=None, df=None, n_recs=10, initial_tempo_tolerance=5, max_tempo_tolerance=100, year_range=(2000, 2020)):
    if df is None:
        return pd.Series(), pd.DataFrame()

    df = df.drop_duplicates(subset=['song', 'artist']).reset_index(drop=True)
    filtered_df = df[(df['year'] >= year_range[0]) & (df['year'] <= year_range[1])]

    if song_title:
        input_song = df[df['song'] == song_title.split(' by ')[0]]
        if input_song.empty:
            st.write("Song not found in dataset.")
            return pd.Series(), pd.DataFrame()
        
        input_song_info = input_song[['song', 'artist', 'tempo', 'year']].iloc[0]
        input_song_info['tempo'] = int(input_song_info['tempo'])
        
        input_tempo = input_song.iloc[0]['tempo']

        tempo_tolerance = initial_tempo_tolerance
        similar_songs = pd.DataFrame()
        
        while similar_songs.empty and tempo_tolerance <= max_tempo_tolerance:
            similar_songs = filtered_df[abs(filtered_df['tempo'] - input_tempo) <= tempo_tolerance]
            tempo_tolerance += 10

        if similar_songs.empty:
            st.write("No similar songs found within the maximum tempo tolerance.")
            return pd.Series(), pd.DataFrame()

        similar_songs = similar_songs[similar_songs['song'] != song_title.split(' by ')[0]].sort_values(by='tempo', ascending=False).head(n_recs)
        
    elif min_tempo is not None and max_tempo is not None:
        similar_songs = filtered_df[(filtered_df['tempo'] >= min_tempo) & (filtered_df['tempo'] <= max_tempo)]
        if similar_songs.empty:
            st.write("No songs found within the specified tempo range.")
            return pd.Series(), pd.DataFrame()
        
        input_song_info = pd.Series({'song': 'Custom Tempo Range', 'artist': '', 'tempo': f'{min_tempo}-{max_tempo}', 'year': ''})

    similar_songs['tempo'] = similar_songs['tempo'].astype(int)
    similar_songs['year'] = similar_songs['year'].astype(str)

    return input_song_info, similar_songs[['song', 'artist', 'tempo', 'year']]

# Function to get song suggestions for autocomplete
def get_song_suggestions(df, query):
    suggestions = df[df['song'].str.contains(query, case=False)]['song'].apply(lambda x: f"{x} by {df[df['song'] == x]['artist'].iloc[0]}").tolist()
    return suggestions

# Streamlit app
st.title("DJ Set Creator")

playlist_link = st.text_input("Enter your Spotify playlist link:", "")

if playlist_link:
    df1 = get_playlist_tracks(playlist_link)
    df1.to_csv('playlist.csv', index=False)
    
    option = st.radio(
        "Choose an option:",
        ("Search by Song Title", "Search by BPM Range")
    )

    if option == "Search by Song Title":
        song_title_input = ''
        song_suggestions = get_song_suggestions(df1, song_title_input)
        song_title_input = st.selectbox("Select a song:", song_suggestions)

        if not song_suggestions:
                st.write("No matching songs found.")
        else:
                year_range = st.slider("Select the year range for songs:", 1990, 2025, (2010, 2025))
                initial_tempo_tolerance = st.slider('BPM Tolerance (+/-)', min_value=5, max_value=40, value=5)
                
                if st.button("Find Similar Songs"):
                    current_song_info, similar_songs = find_similar_songs(song_title=song_title_input, df=df1, n_recs=30, initial_tempo_tolerance=initial_tempo_tolerance, year_range=year_range)
                    if similar_songs.empty:
                        st.write("No similar songs found.")
                    else:
                        st.write(f"### Current Song: {current_song_info['song']} by {current_song_info['artist']}")
                        st.write(f"Tempo: {current_song_info['tempo']}")
                        st.write("Here are some songs you might like:")
                        st.dataframe(similar_songs)

    elif option == "Search by BPM Range":
        min_tempo = st.slider("Minimum Tempo:", min_value=0, max_value=200, value=60)
        max_tempo = st.slider("Maximum Tempo:", min_value=min_tempo, max_value=200, value=120)
        year_range = st.slider("Select the year range for songs:", 1990, 2025, (2010, 2025))
        
        if st.button("Find Songs within BPM Range"):
            current_song_info, similar_songs = find_similar_songs(min_tempo=min_tempo, max_tempo=max_tempo, df=df1, n_recs=30, year_range=year_range)
            if similar_songs.empty:
                st.write("No songs found within the specified tempo range.")
            else:
                st.write(f"### Searching by BPM Range")
                st.write(f"Tempo: {min_tempo}-{max_tempo}")
                st.write("Here are some songs you might like:")
                similar_songs['year'] = similar_songs['year'].astype(str)
                st.dataframe(similar_songs)
else:
    st.write("Please enter a valid Spotify playlist link to get started.")
