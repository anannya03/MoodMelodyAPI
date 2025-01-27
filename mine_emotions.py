import spotipy
import requests
import pandas as pd
import sqlite3 as sql
import os
from spotipy.oauth2 import SpotifyClientCredentials
from dotenv import load_dotenv

load_dotenv()


# read API key from file
def getAPIKey():
    with open('APIKey.txt', 'r') as APIKeyFile:
        APIKey = APIKeyFile.read()
    return APIKey


# get the top n four chord progressions
def getTopNChordProgressionsDf(n):
    chordProgressionsDf = pd.read_csv('four_chord_progressions.csv')
    topChordProgressionsDf = chordProgressionsDf.sort_values(
        'probability', ascending=False).head(n)
    return topChordProgressionsDf


# get songs that use the top progressions and determine valence
def mineChordProgressionEmotions(baseUri, APIKey, chordProgressions):

    # define endpoint
    songsEndpoint = baseUri + 'trends/songs'

    # add API key as a Bearer token for authorization
    headers = {"Authorization": "Bearer " + APIKey}

    # list to store the valences and energies of the chord progressions
    valences = []
    energies = []

    for chordProgression in chordProgressions:

        # get the songs that use the progression
        response = requests.get(
            songsEndpoint + '?cp=' + chordProgression, headers=headers)
        songs = response.json()

        avgValence, avgEnergy, songCount = 0, 0, 0

        # find the valence and energy for each song from the songs obtained
        if isinstance(songs, list) and all(isinstance(song, dict) for song in songs):
            for song in songs:
                # print(song)
                songName = song['song']
                artist = song['artist']
                valence, energy = fetchTrackFeatures(songName, artist)

                # check if song features are available
                if valence:
                    print('Progression: ', chordProgression, 'Song: ',
                        songName, 'Artist: ', artist, 'Valence: ', valence, 'Energy: ', energy)
                    avgValence += valence
                    avgEnergy += energy
                    songCount += 1
                else:
                    print('Features not available')
        else:
            print("Error: Expected a list of dictionaries but received:", type(songs))

        # compute the average valence and energry
        if songCount > 0:
            avgValence /= songCount
            avgEnergy /= songCount
            print('Average valence for ', chordProgression,
                  ' = ', avgValence)
            print('Average energy for ', chordProgression,
                  ' = ', avgEnergy)
        else:
            print('No valid song features found for progression:', chordProgression)
            avgValence = None
            avgEnergy = None

        # avgValence /= songCount
        # avgEnergy /= songCount
        # print('Average valence for ', chordProgression,
        #       ' = ', avgValence)
        # print('Average energy for ', chordProgression,
        #       ' = ', avgEnergy)
        valences.append(avgValence)
        energies.append(avgEnergy)

    return valences, energies


def writeEmotionDataToDB():

    # get the top chord progressions
    topChordProgressionsDf = getTopNChordProgressionsDf(50)
    topChordProgressions = topChordProgressionsDf['child_path'].to_list()

    # get the emotion data i.e, valence and energies for the top 5 progressions
    valences, energies = mineChordProgressionEmotions(
        baseUri, APIKey, topChordProgressions)

    # add the emotion data to the dataframe
    topChordProgressionsDf['valence'] = valences
    topChordProgressionsDf['energy'] = energies
    print(topChordProgressionsDf)

    # connect to the SQLite3 DB file called CPDB.db
    conn = sql.connect('CPDB.db')

    # write the dataframe to the DB
    try:
        topChordProgressionsDf.to_sql('chord_progressions', conn, index=False, if_exists='replace')
        print('Database updated successfully.')
    except Exception as e:
        print('Error occurred while creating DB: ', e)

    conn.close()


def fetchTrackFeatures(trackName, artist):

    # authorise with credentials stored as environment variables
    spotify = spotipy.Spotify(
        client_credentials_manager=SpotifyClientCredentials(
        client_id=os.getenv('SPOTIPY_CLIENT_ID'),
        client_secret=os.getenv('SPOTIPY_CLIENT_SECRET')
        ))

    # filter results with track and artist names
    results = spotify.search(
        q='track:' + trackName + ' artist:' + artist, type='track', limit=1)

    # if the song is found, determine the valence and energy
    if results['tracks']['items']:

        # find track id
        trackID = results['tracks']['items'][0]['id']

        # get song information for the corresponding track id
        audioFeatures = spotify.audio_features(trackID)[0]
        return audioFeatures['valence'], audioFeatures['energy']
    else:
        return None, None


# main runner
baseUri = 'https://api.hooktheory.com/v1/'
APIKey = getAPIKey()
writeEmotionDataToDB()
