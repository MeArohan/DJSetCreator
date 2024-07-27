import streamlit as st
import pandas as pd
import json
import streamlit.components.v1 as com
from streamlit_lottie import st_lottie  

# Load and preprocess data
df1 = pd.read_csv('spotify_data.csv')
df1 = df1.drop(columns=['loudness', 'mode', 'speechiness', 'acousticness', 'instrumentalness', 'liveness', 'valence']).reset_index(drop=True)
df1['genre'] = df1['genre'].apply(lambda x: [genre.strip() for genre in x.split(',')]) 

def find_similar_songs(song_title=None, min_tempo=None, max_tempo=None, df=df1, n_recs=10, initial_tempo_tolerance=5, max_tempo_tolerance=100, year_range=(2000, 2020),genres=None):
    df = df.drop_duplicates(subset=['song', 'artist']).reset_index(drop=True)
    filtered_df = df[(df['year'] >= year_range[0]) & (df['year'] <= year_range[1])]

    if genres:
        genres_set = set(genres)
        filtered_df = filtered_df[filtered_df['genre'].apply(lambda g: any(genre in genres_set for genre in g))]
    else:
        genres = list(set([genre for sublist in df['genre'] for genre in sublist]))  # If no genres selected, include all genres

    if song_title:
        input_song = df[df['song'] == song_title.split(' by ')[0]]
        if input_song.empty:
            st.write("Song not found in dataset.")
            return [], pd.DataFrame()
        
        input_song_info = input_song[['song', 'artist', 'tempo', 'genre', 'year']].iloc[0]
        input_song_info['tempo'] = int(input_song_info['tempo'])
        
        input_tempo = input_song.iloc[0]['tempo']

        tempo_tolerance = initial_tempo_tolerance
        similar_songs = pd.DataFrame()
        
        while similar_songs.empty and tempo_tolerance <= max_tempo_tolerance:
            similar_songs = filtered_df[abs(filtered_df['tempo'] - input_tempo) <= tempo_tolerance]
            tempo_tolerance += 10

        if similar_songs.empty:
            st.write("No similar songs found within the maximum tempo tolerance.")
            return [], pd.DataFrame()

        similar_songs = similar_songs[similar_songs['song'] != song_title.split(' by ')[0]].sort_values(by='tempo', ascending=False).head(n_recs)
        
    elif min_tempo is not None and max_tempo is not None:
        similar_songs = filtered_df[(filtered_df['tempo'] >= min_tempo) & (filtered_df['tempo'] <= max_tempo)]
        if similar_songs.empty:
            st.write("No songs found within the specified tempo range.")
            return [], pd.DataFrame()
        
        similar_songs = similar_songs.sort_values(by='tempo', ascending=False).head(n_recs)
        input_song_info = pd.Series({'song': 'Custom Tempo Range', 'artist': '', 'tempo': f'{min_tempo}-{max_tempo}', 'genre': ', '.join(genres), 'year': ''})


    similar_songs['tempo'] = similar_songs['tempo'].astype(int)
    similar_songs['year'] = similar_songs['year'].astype(str)

    return input_song_info, similar_songs[['song', 'artist', 'tempo', 'genre', 'year']]

# Function to get song suggestions for autocomplete
def get_song_suggestions(df, query):
    suggestions = df[df['song'].str.contains(query, case=False)]['song'].apply(lambda x: f"{x} by {df[df['song'] == x]['artist'].iloc[0]}").tolist()
    return suggestions

# Streamlit app
st.title("DJ Set Creator")

option = st.radio(
    "Choose an option:",
    ("Search by Song Title", "Search by BPM Range")
)

genre_set = {'hip hop', 'pop', 'Dance/Electronic', 'latin','R&B','rock','country','metal','classical','blues','jazz','Folk/Acoustic'}

if option == "Search by Song Title":
    song_title_input= ''
    song_suggestions = get_song_suggestions(df1, song_title_input)
    song_title_input = st.selectbox("Select a song:", song_suggestions)

    if not song_suggestions:
            st.write("No matching songs found.")
    else:
            #selected_song = st.selectbox("Select a song:", song_suggestions)
            year_range = st.slider("Select the year range for songs:", 1990, 2020, (2010, 2020))
            selected_genres = st.multiselect('Select Genres', genre_set)
            initial_tempo_tolerance = st.slider('BPM Tolerance (+/-)', min_value=5, max_value=30, value=5)
            
            if st.button("Find Similar Songs"):
                current_song_info, similar_songs = find_similar_songs(song_title=song_title_input, df=df1, n_recs=30, initial_tempo_tolerance=initial_tempo_tolerance, year_range=year_range, genres=selected_genres)
                if similar_songs.empty:
                    st.write("No similar songs found.")
                else:
                    st.write(f"### Current Song: {current_song_info['song']} by {current_song_info['artist']}")
                    st.write(f"Tempo: {current_song_info['tempo']}")
                    st.write(f"Genre: {', '.join(current_song_info['genre'])}")
                    st.write("Here are some songs you might like:")
                    st.dataframe(similar_songs)

elif option == "Search by BPM Range":
    min_tempo = st.slider("Minimum Tempo:", min_value=0, max_value=200, value=60)
    max_tempo = st.slider("Maximum Tempo:", min_value=min_tempo, max_value=200, value=120)
    year_range = st.slider("Select the year range for songs:", 1990, 2020, (2010, 2020))
    selected_genres = st.multiselect('Select Genres', genre_set)
    if st.button("Find Songs within BPM Range"):
        current_song_info, similar_songs = find_similar_songs(min_tempo=min_tempo, max_tempo=max_tempo, df=df1, n_recs=30, year_range=year_range,genres=selected_genres)
        if similar_songs.empty:
            st.write("No songs found within the specified tempo range.")
        else:
            st.write(f"### Searching by BPM Range")
            st.write(f"Tempo: {min_tempo}-{max_tempo}")
            st.write(f"Genre: {', '.join(selected_genres) if selected_genres else 'All'}")

            st.write("Here are some songs you might like:")
            st.dataframe(similar_songs)
