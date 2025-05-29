#!/usr/bin/env python3

import os
import sys
import time
import requests
import subprocess
spotplayercmd="/home/baum/.cargo/bin/spotify_player"
fzfcmd=["fzf, --layout=reverse-list, --border=rounded, --border-label='Fuzzy Spotify'"]

SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_BASE = "https://api.spotify.com/v1"

def open_initial_menu():
    #open fzf menu
    options=[
        "Play",
        "Pause",
        "Shuffle",
        "Skip",
        "Previous",
    "Full Playlist",
    "Context Playlist",
    "Play Artist",
    "Single Song",
        "Quit"
    ]
    result = subprocess.run(["fzf", "--layout=reverse-list", "--border=rounded", "--border-label='Fuzzy Spotify'"], input=" \n".join(options), text=True, capture_output=True)

    if result.returncode != 0:
        return None
    selected = result.stdout.strip()
    if selected == "Play":
        return "play"
    if selected == "Pause": 
        return "pause"
    if selected == "Shuffle":
        return "shuffle"
    if selected == "Skip":
        return "next"
    if selected =="Previous":
        return "previous"
    if selected=="Full Playlist":
        return "play_playlist"
    if selected=="Context Playlist":
        return "context_playlist"
    if selected=="Play Artist":
        #get artist name from user
        return "play_artist"
    if selected=="Single Song":
        return "single_song_playlist"
    if selected=="Quit":
        sys.exit(0)
#return selected
def ensure_spotifyd_running():
    #check if spotifyd is running, start it if not
    try:
        subprocess.run(["pgrep", "spotifyd"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        print("Starting spotifyd...")
        subprocess.Popen(["spotifyd"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(2)

def get_env_var(var):
    return os.environ.get(var)

    #curl -X POST "https://accounts.spotify.com/api/token" \
    #     -H "Content-Type: application/x-www-form-urlencoded" \
    #     -d "grant_type=client_credentials&client_id={ID}&client_secret={SECRET}"

def get_spotify_auth():
    
    client_id = get_env_var("SPOTIFY_CLIENT_ID")
    client_secret = get_env_var("SPOTIFY_SECRET_ID")
    data = {"grant_type": "client_credentials", "client_id": client_id, "client_secret": client_secret}
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    resp = requests.post(SPOTIFY_TOKEN_URL, headers=headers, data=data)
    resp.raise_for_status()
    token = resp.json()["access_token"]
    return token

def search_tracks(query, token):
    headers = {"Authorization": f"Bearer {token}"}
    params = {"q": query, "type": "track", "limit": 20}
    resp = requests.get(f"{SPOTIFY_API_BASE}/search", headers=headers, params=params)
    resp.raise_for_status()
    tracks = resp.json()["tracks"]["items"]
    return [(t["name"], t["artists"][0]["name"], t["uri"]) for t in tracks]

def get_my_playlists(token):
    username=str(get_env_var("SPOTIFY_USERNAME"))
    url= f"{SPOTIFY_API_BASE}/users/"
    url=url+username+"/playlists"
    headers= {"Authorization": f"Bearer {token}"}
    resp = requests.get(url, headers=headers)
    return resp.json()

def query_playlists(token, playlist_id):
    headers = {"Authorization": f"Bearer {token}"}
    #print(f"playlist_id:"+str(playlist_id))
    resp = requests.get(f"{SPOTIFY_API_BASE}/playlists/"+str(playlist_id)+"/tracks", headers=headers)
    #print(resp.json())
    
    return resp.json()
def get_artist_search(token, artist_id):
    headers = {"Authorization": f"Bearer {token}"}
    #encode artist_id for url

    artist_id = artist_id.replace(" ", "+")
    #print(f"playlist_id:"+str(playlist_id))
    resp = requests.get(f"{SPOTIFY_API_BASE}/search?q="+artist_id+"&type=artist", headers=headers)

    return resp.json()
def fzf_select_artist(options):
    input_str = "\n".join([f"{artist} - {uri}" for  artist,uri in options])
    result = subprocess.run(["fzf"], input=input_str, text=True, capture_output=True)
    if result.returncode != 0:
        return None
    selected = result.stdout.strip()
    #print(selected)
    for artist, uri in options:
        if f"{artist} - {uri}" == selected:
            #print(f"Selected: {uri}")
            return uri


def fzf_select_song(options):
    input_str = "\n".join([f"{name} - {artist}" for name, artist,uri in options])
    result = subprocess.run(["fzf", "--layout=reverse-list", "--border=rounded", "--border-label='Fuzzy Spotify'"], input=input_str, text=True, capture_output=True)
    if result.returncode != 0:
        return None
    selected = result.stdout.strip()
    for name, artist, uri in options:
        if f"{name} - {artist}" == selected:
            return uri
def fzf_select_song_name(options):
    input_str = "\n".join([f"{name} - {artist}" for name, artist,uri in options])
    result = subprocess.run(["fzf", "--layout=reverse-list", "--border=rounded", "--border-label='Fuzzy Spotify'"], input=input_str, text=True, capture_output=True)
    if result.returncode != 0:
        return None
    selected = result.stdout.strip()
    for name, artist, uri in options:
        if f"{name} - {artist}" == selected:
            return {name}


    return None
def fzf_select_playlist(options):
    input_str = "\n".join([f"{name}" for name, id in options])
    result = subprocess.run(["fzf", "--layout=reverse-list", "--border=rounded", "--border-label='Fuzzy Spotify'"], input=input_str, text=True, capture_output=True)
    if result.returncode != 0:
        return None
    selected = result.stdout.strip()
    for name, id in options:
        if f"{name}" == selected:

            return id
                
            

    return None

def play_track(uri):
    #use spotifY_player to play the track
    exec_command = spotplayercmd+" playback start track --id "+str(uri)
    
    _= subprocess.run(exec_command, shell=True, text=True, capture_output=True)
    
    return 0
def play_context(uri):
    #use spotifY_player to play the track
    exec_command = spotplayercmd+" playback start context --name '"+str(uri)+"' playlist"
    
    _= subprocess.run(exec_command, shell=True, text=True, capture_output=True)

    
    return 0
def play_radio_playlist(uri):
    #use spotifY_player to play the track
    exec_command = spotplayercmd+" playback start radio --name '"+str(uri)+"' playlist"

    
    _= subprocess.run(exec_command, shell=True, text=True, capture_output=True)

    return 0

def play_playlist(playlist_id, token):
    tracks = query_playlists(token, playlist_id)
    
    options = [(t["track"]["name"], t["track"]["artists"][0]["name"], t["track"]["id"]) for t in tracks["items"]]

    uri = fzf_select_song_name(options)
    if uri:
        #strip out {}
        uri = str(uri).replace("{","").replace("}","").replace("'","")
        play_context(uri)
        return 0
    
def play_playlist_radio(playlist_id, token):

    exec_command = spotplayercmd+" playback start radio --id "+ playlist_id +" playlist"
    
    _=subprocess.run(exec_command, shell=True, text=True, capture_output=True)
    
    return 0

    
def play_artist(token,id):
    exec_command = spotplayercmd+" playback start radio --id '"+id+"' artist"
    
    _= subprocess.run(exec_command, shell=True, text=True, capture_output=True)
    
    return 0




def play_song(token,playlist_id):
    tracks = query_playlists(token, playlist_id)
    
    options = [(t["track"]["name"], t["track"]["artists"][0]["name"], t["track"]["id"]) for t in tracks["items"]]

    uri = fzf_select_song(options)
    if uri:
        play_track(uri)
def play_pause(method):
    exec_command = spotplayercmd+" playback "+str(method)
    _= subprocess.run(exec_command, shell=True, text=True, capture_output=True)


def main():
    command=open_initial_menu()

    token = get_spotify_auth()

    if command=="context_playlist":
        playlists = get_my_playlists(token)
        options = [(playlist["name"], playlist["id"]) for playlist in playlists["items"]]

        id=fzf_select_playlist(options)
        
        playlist=play_playlist(id, token)
        
        return playlist

    elif command == "single_song_playlist":
        playlists = get_my_playlists(token)
        options = [(playlist["name"], playlist["id"]) for playlist in playlists["items"]]
        id=fzf_select_playlist(options)
        play_song(token,id)

    elif command == "play_artist":
        artist_name = input("Enter artist name: ")
        playlists = get_artist_search(token, str(artist_name))
        

        options = [(playlist["name"], playlist["id"]) for playlist in playlists["artists"]["items"]]

        id=fzf_select_artist(options)

        #id=fzf_select_playlist(options)
        play_artist(token,id)
    elif command == "play_playlist":
        playlists = get_my_playlists(token)
        options = [(playlist["name"], playlist["id"]) for playlist in playlists["items"]]
        id=fzf_select_playlist(options)
        play_playlist_radio(id, token)
    elif command == "play":
        _= play_pause("play")

    elif command == "pause":
        _= play_pause("pause")
    elif command == "shuffle":
        _= play_pause("shuffle")
    elif command == "next":
        _= play_pause("next")
    elif command == "previous":
        _= play_pause("previous")
    elif command == "search":
        query = " ".join(sys.argv[2:])
        tracks = search_tracks(query, token)
        uri = fzf_select_song(tracks)
        if uri:
            play_track(uri)
    else:
        print("Unknown command:", command)


if __name__ == "__main__":
    main()
