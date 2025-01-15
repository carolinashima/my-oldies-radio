from enum import unique
import streamlit as st
import os
import sqlite3
from urllib.parse import quote
import musicbrainzngs
import random
from bs4 import BeautifulSoup
from urllib.request import urlopen

st.set_page_config(layout='wide', initial_sidebar_state='expanded',page_title="My oldies radio",
    page_icon="📻")
    
st.sidebar.header(':radio: My oldies radio')

st.sidebar.markdown('''
---
Made by Carolina L. Shimabukuro

⭐⭐⭐

''')

# page content and description
st.title("""
My oldies radio :radio:
""")

st.subheader("""
What do I want to listen to next?
""")

st.write("""
    If I'm awake and not socialising, I'm probably listening to music. Usually
    I have a list somewhere with new stuff to check out, but as a deeply nostalgic
    person I also enjoy revisiting my old favourites.

    This little app was built to inspire me and help me rediscover music I have
    collected until mid-2015.
    """
)

st.subheader("Caveats")
st.write("""
    You can check how I built the database in this notebook,
    but have in mind that the original file where I stored this information was made
    by hand, i.e. I sat down and typed Album - Artist (Year) so there are typos
    and inconsistencies.

    Moreover, I got most of the data with the [MusicBrainz API](https://musicbrainz.org/doc/MusicBrainz_API)
    via the [musicbrainzngs](https://python-musicbrainzngs.readthedocs.io/en/v0.7.1/)
    library and some other info with the [Discogs API](https://www.discogs.com/developers).
    Both depend on manual contributions
    by users, so data on each artist and album is not always complete or accurate.
""")

# divider line
st.divider()

# I'm getting tracklists from musicbrainz by scraping
def scrape_tracklist(mb_album_id):
    """
    Scrape album tracklists from MusicBrainz. There is a way to do this neatly with
    the API, but it requires a disc ID which not all releases have, so I found it
    easier to just use the MusicBrainz ID to get the URL on the website.
    """
    mb_url = 'https://musicbrainz.org/release/' + mb_album_id
    html = urlopen(mb_url).read()
    soupified = BeautifulSoup(html, 'html.parser')
    tracks = soupified.find_all(attrs={"class": "title wrap-anywhere"})
    tracklist = []
    for track in tracks:
        trackname = track.find("bdi").get_text().strip()
        tracklist.append(trackname)
    return tracklist

# connect to database
conn = sqlite3.connect('music_library.db')
cursor = conn.cursor()

# display some basic numbers: artists, albums, genres
col1, col2, col3 = st.columns(3)
# number of artists
cursor.execute("SELECT DISTINCT artist_name FROM artists")
all_artists = [row[0] for row in cursor.fetchall()]
col1.metric("Unique artists", len(all_artists))
# number of albums
cursor.execute("SELECT * FROM albums")
all_albums = [row[0] for row in cursor.fetchall()]
col2.metric("Total albums", len(all_albums))
# unique genres
cursor.execute("SELECT DISTINCT genre FROM artists WHERE genre IS NOT NULL")
genres = [row[0] for row in cursor.fetchall()]
col3.metric("Unique genres", len(genres))

# choose how to filter the database
filter = st.selectbox("Filter selection", ["Genre", "All artists", "Year", "Country", "Get me a random playlist!"])
if filter == "Genre":
    selected_genre = st.selectbox("Select a genre ('not available' means untagged):", genres)
    cursor.execute("SELECT artist_name, lastfm_url FROM artists WHERE genre = ?", (selected_genre,))
    artists = cursor.fetchall()
    st.write(f"Artists in genre '{selected_genre}':")
    for artist_name, lastfm_url in artists:
        encoded_url = quote(lastfm_url, safe='')
        st.write(f"- [{artist_name}]({encoded_url})")
elif filter == "All artists":
    cursor.execute("SELECT artist_name FROM artists")
    artists = [row[0] for row in cursor.fetchall()]
    selected_artist = st.selectbox("Select an artist:", artists, placeholder="Teenage Fanclub")
    cursor.execute("SELECT album_name, label, year FROM albums WHERE artist_name = ?", (selected_artist,))
    artist_albums = cursor.fetchall()
    for album in artist_albums:
        st.write(f"- {album[0]} ({album[2]}, {album[1]})")
elif filter == "Year":
    cursor.execute("SELECT DISTINCT year FROM albums ORDER BY year")
    unique_years = cursor.fetchall()
    year_list = []
    for row in unique_years:
        year_list.append(row[0])
    year = st.selectbox("Enter year (0 means no year in db)", year_list, index=10)
    cursor.execute("SELECT album_name, year, artist_name FROM albums where year = ?", (year,))
    year_albums = cursor.fetchall()
    for album in year_albums:
        st.write(f"{album[2]} - {album[0]}")
elif filter == "Country":
    cursor.execute("SELECT DISTINCT country FROM artists ORDER BY country")
    all_countries = cursor.fetchall()
    country_list = [country[0] for country in all_countries]
    selected_country = st.selectbox("Select a country", country_list)
    cursor.execute("SELECT artist_name, lastfm_url FROM artists WHERE country = ?", (selected_country,))
    country_artists = cursor.fetchall()
    for artist_name, lastfm_url in country_artists:
        encoded_url = quote(lastfm_url, safe='')
        st.write(f"- [{artist_name}]({encoded_url})")
elif filter == "Get me a random playlist!":
    st.write("This generates a playlist of random artists and tracks.")
    min_val = 5
    max_val = 50
    n_options = list(range(min_val, max_val))
    n_tracks = st.selectbox("How many different tracks/artists do you want?", n_options, index=7) # default 12 tracks
    # get random n artists
    artists_query = f"SELECT artist_name FROM artists ORDER BY RANDOM() LIMIT {n_tracks}"
    cursor.execute(artists_query)
    random_artists = cursor.fetchall()
    for idx, artist in enumerate(random_artists):
        albums_query = "SELECT album_name, mb_album_id, year FROM albums WHERE artist_name = ? AND mb_album_id IS NOT NULL"
        cursor.execute(albums_query, (artist))
        artist_albums = cursor.fetchall()
        random_album = random.randint(0, len(artist_albums)-1) # gets idx
        selected_album = artist_albums[random_album]
        mb_album_id = selected_album[1]
        tracklist = scrape_tracklist(mb_album_id)
        random_track_idx = random.randint(0, len(tracklist)-1)
        track_name = tracklist[random_track_idx]
        st.write(f"{idx+1}. {artist[0]} - {track_name} (from album {selected_album[0]}, {selected_album[2]})")

