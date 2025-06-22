#!/usr/bin/env python3

import os
import psutil
import sys
import time
import requests
import subprocess
import base64
import urllib.parse

from dotenv import load_dotenv
load_dotenv()
oauth_token = os.getenv("SPOTIFY_OAUTH_TOKEN")
refresh_token = os.getenv("SPOTIFY_REFRESH_TOKEN")

fzfcmd=["fzf, --layout=reverse-list, --border=rounded, --border-label='Fuzzy Spotify'"]

SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_BASE = "https://api.spotify.com/v1"
LAST_FM_API_BASE = "https://ws.audioscrobbler.com/2.0/"

def open_initial_menu():
    #open fzf menu
    options=[
        "Play",
        "Pause",
        "Shuffle",
        "Skip",
        "Previous",
        "View Queue",
    "Full Playlist",
    "Similar Tracks",
        "Get Recommendations",
    "Play Artist",
    "Single Song",
        "Quit"
    ]
    result = subprocess.run(["fzf", "--layout=reverse-list", "--border=rounded", "--border-label='Fuzzy Spotify'"], input=" \n".join(options), text=True, capture_output=True)

    if result.returncode == 130:
        print("Exiting...")
        sys.exit(0)
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
    if selected=="View Queue":
        return "view_queue"
    if selected=="Similar Tracks":
        return "similar_tracks"
    if selected=="Get Recommendations":
        return "get_recommendations"
    if selected=="Play Artist":
        return "play_artist"
    if selected=="Single Song":
        return "single_song_playlist"
    if selected=="Quit":
        sys.exit(0)
def get_env_var(var):
    return os.environ.get(var)

    #curl -X POST "https://accounts.spotify.com/api/token" \
    #     -H "Content-Type: application/x-www-form-urlencoded" \
    #     -d "grant_type=client_credentials&client_id={ID}&client_secret={SECRET}"

def update_env_variable(key, value, env_path=".env"):
    lines = []
    found = False
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                if line.strip().startswith(f"{key}="):
                    lines.append(f"{key}={value}\n")
                    found = True
                else:
                    lines.append(line)
    if not found:
        lines.append(f"{key}={value}\n")
    with open(env_path, "w") as f:
        f.writelines(lines)

def auth_code_me_path():

    client_id=get_env_var("SPOTIFY_CLIENT_ID")
    redirect_uri = "http://127.0.0.1:3000"
    state="ThisShitStupid"
    scope= "user-read-private user-read-email user-modify-playback-state user-read-currently-playing user-read-playback-state"

    url=f"https://accounts.spotify.com/authorize?response_type=code&client_id={client_id}&scope={scope}&redirect_uri={redirect_uri}&state={state}"
    response = requests.post(url)
    print("Please open the following URL in your browser to authorize the application:")
    print(url)
    return response.url
def get_me_path_authcode():
    #Get code from .return file first line
    returnfile=open(".return", "r")
    #the value I want is in the first line
    code = returnfile.readline().strip()
    redirect_uri = "http://127.0.0.1:3000"
    grant_type = "authorization_code"
    url = f"https://accounts.spotify.com/api/token?grant_type={grant_type}&code={code}&redirect_uri={redirect_uri}"
    base64_auth = base64.b64encode(f"{get_env_var('SPOTIFY_CLIENT_ID')}:{get_env_var('SPOTIFY_SECRET_ID')}".encode('utf-8'))
    headers = {"Content-Type": "application/x-www-form-urlencoded","Accept":"application/json","Authorization": "Basic " + base64_auth.decode('utf-8')}
    response = requests.post(url, headers=headers)
    #print("Response from Spotify API:")
    #print(response.json())
    return response.json().get("access_token", None)



def get_refresh_token():
  
    refresh_token = get_env_var("SPOTIFY_REFRESH_TOKEN")
    url = "https://accounts.spotify.com/api/token"
    payload = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": get_env_var("SPOTIFY_CLIENT_ID"),
    }
    authbase64 = base64.b64encode(f"{get_env_var('SPOTIFY_CLIENT_ID')}:{get_env_var('SPOTIFY_SECRET_ID')}".encode('utf-8'))
    headers = {"Content-Type": "application/x-www-form-urlencoded", "Authorization": "Basic " + authbase64.decode('utf-8')}
    response = requests.post(url, headers=headers, data=payload)
    if response.status_code == 200:
        #print(response.json())
        data = response.json()
        new_access_token = data.get("access_token")
        new_refresh_token = data.get("refresh_token")
        if not new_refresh_token:
            new_refresh_token = refresh_token
        if new_access_token:
            update_env_variable("SPOTIFY_OAUTH_TOKEN", new_access_token)
            update_env_variable("SPOTIFY_REFRESH_TOKEN", new_refresh_token)
            load_dotenv(override=True)  # Reload the environment variables


def create_similiar_lastfm_command(artist, track):
    #create a last.fm command to get similar tracks
    #https://www.last.fm/api/show/track.getSimilar
    api_key = get_env_var("LASTFM_API")
    if not api_key:
        print("LASTFM_API environment variable not set.")
        sys.exit(1)
    return f"{LAST_FM_API_BASE}?method=track.getSimilar&autocorrect=1&artist={artist}&track={track}&api_key={api_key}&format=json"

def add_to_queue(options, token):
    track_uris = []
    for name, artist, uri in options:
        #create spotify query
        #Example: track:Doxy%20artist:Miles%20Davis
        query = f"track:{name} artist:{artist}"
        track = search_spotify(query, token,"tracks" )
        if track:
            track_uris.append(track[0])
    print(f"Adding {len(track_uris)} tracks to playback queue.")
    for uri in track_uris:
        add_to_playback_queue(uri, token)


def search_spotify(query, token, search_type):
    headers = {"Authorization": f"Bearer {token}"}
    if search_type not in ["tracks", "artists", "albums"]:
        sys.exit(f"Invalid search type: {search_type}. Must be one of 'tracks', 'artists', or 'albums'.")
    query_type=""
    if search_type == "tracks":
        query_type = "track"
    elif search_type == "artists":
        query_type = "artist"
    elif search_type == "albums":
        query_type = "album"

    params = {"q": query, "type": query_type, "limit": 20}
    resp = requests.get(f"{SPOTIFY_API_BASE}/search", headers=headers, params=params)
    resp.raise_for_status()
    tracks = resp.json()[search_type]["items"]
    if tracks:
        return [(t["uri"]) for t in tracks]
    else:
        print(f"No tracks found for query: {query}")
        return None

def add_to_playback_queue(uri, token):
    load_dotenv(override=True)  # Reload the environment variables
    authtoken = os.getenv("SPOTIFY_OAUTH_TOKEN")

    #Add a track to the spotify playback queue
    headers = {"Authorization": f"Bearer {authtoken}"}
    resp = requests.post(f"{SPOTIFY_API_BASE}/me/player/queue?uri="+str(uri), headers=headers)
    if resp.status_code == 204:
        print(f"Track {uri} added to playback queue.")
    elif resp.status_code == 401:
        print(resp.text)
        print("Token expired, refreshing token...")
        _=get_refresh_token()
        print("Token refreshed successfully.")

        add_to_playback_queue(uri, token)
    elif resp.status_code==404:
        print(f"Playback device not found. Please ensure a Spotify client is active and try again.")
        sys.exit(1)
    else:
        print(f"Failed to add track {uri} to playback queue. Status code: {resp.status_code}")
        print(resp.text)
def view_queue(token):
    load_dotenv(override=True)  # Reload the environment variables
    authtoken = os.getenv("SPOTIFY_OAUTH_TOKEN")

    #Add a track to the spotify playback queue
    headers = {"Authorization": f"Bearer {authtoken}"}
    resp = requests.get(f"{SPOTIFY_API_BASE}/me/player/queue", headers=headers)
    if resp.status_code == 200:
        queue = resp.json()
        if not queue["queue"]:
            print("Playback queue is empty.")
            sys.exit(0)
        print("Current playback queue:")

        queue_dict = {}
        
        for item in queue["queue"]:
            name = item["name"]
            artist = item["artists"][0]["name"]
            uri = item["uri"]
            

            queue_dict[f"{name} - {artist}"] = uri
            #Get the selected track URI
            
        result = subprocess.run(["fzf", "--layout=reverse-list", "--border=rounded", "--border-label='Fuzzy Spotify'"], input="\n".join(queue_dict.keys()), text=True, capture_output=True)
        if result.returncode == 130:
            print("Exiting...")
            sys.exit(0)
        if result.returncode != 0:
            return None
        sel = result.stdout.strip()
        print(f"Selected track: {sel}")
        sel_uri = queue_dict.get(sel)


        if sel_uri:
            id=ensure_spotifyd_dbus()
            dest=build_dbus_string(id)
            play_uri(sel_uri, dest)

    elif resp.status_code == 401:
        print(resp.text)
        print("Token expired, refreshing token...")
        _=get_refresh_token()
        print("Token refreshed successfully.")

        view_queue(token)
    elif resp.status_code==404:
        print(f"Playback device not found. Please ensure a Spotify client is active and try again.")
        sys.exit(1)
      
    else:
        print(f"Failed to retrieve playback queue. Status code: {resp.status_code}")
        print(resp.text)
        sys.exit(1)


def ensure_spotifyd_running():
    #check if spotifyd is running, start it if not
    id=None
    name = "spotifyd"
    for proc in psutil.process_iter(['pid', 'name']):
        if proc.info['name'] == name:
            print(f"Found spotifyd with PID: {proc.info['pid']}")
            id = proc.info['pid']
    if id is None:
        print("Starting spotifyd...")
        subprocess.Popen("/home/baum/.local/bin/spotifyd", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1)
        #make id return the pid of spotifyd
        for proc in psutil.process_iter(['pid', 'name']):
            #print(proc.info['name'])
            if proc.info['name'] == name:
                print(f"Found spotifyd with PID: {proc.info['pid']}")
                id = proc.info['pid']
    return id
def full_restart_spotifyd():
    id=ensure_spotifyd_running()
    if id is not None:
        print(f"Killing spotifyd with PID: {id}")
        os.kill(id, 9)
        time.sleep(1)
    #start spotifyd again
    subprocess.Popen("/home/baum/.local/bin/spotifyd", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)
    new_id=ensure_spotifyd_running()
    
    dest = f"rs.spotifyd.instance{new_id}"
    activate_cmd = f"dbus-send --print-reply --dest={dest} /rs/spotifyd/Controls rs.spotifyd.Controls.TransferPlayback"

    _=subprocess.run(activate_cmd, shell=True,capture_output=True)
    return new_id


def ensure_spotifyd_dbus():
    spotify_id=ensure_spotifyd_running()
    print("Spotifyd PID: ", spotify_id)

    dest = f"org.mpris.MediaPlayer2.spotifyd.instance{spotify_id}"
    check_cmd = f"dbus-send --print-reply --dest={dest} /org/mpris/MediaPlayer2 org.freedesktop.DBus.Introspectable.Introspect"

    #print(f"Checking D-Bus service with command: \n{check_cmd}")
    
    result = subprocess.run(check_cmd, shell=True, text=True, capture_output=True)
    #print(f"Result of D-Bus introspection: \n{result.stdout}")
    if result.returncode != 0:
        
        dest = f"rs.spotifyd.instance{spotify_id}"
        activate_cmd = f"dbus-send --print-reply --dest={dest} /rs/spotifyd/Controls rs.spotifyd.Controls.TransferPlayback"
        #print(f"Activating D-Bus service with command: \n{activate_cmd}")
        run=subprocess.run(activate_cmd, shell=True,capture_output=True)
        print(f"Result of D-Bus activation: \n{run.stdout}")
        
    return spotify_id


def build_dbus_string(pid):
    return f"org.mpris.MediaPlayer2.spotifyd.instance"+str(pid)


def play_uri(uri,dest):
    
    exec=f"dbus-send --print-reply --dest="+dest+" /org/mpris/MediaPlayer2 org.mpris.MediaPlayer2.Player.OpenUri string:"+str(uri)
    #print(exec)
    run= subprocess.run(exec, shell=True, text=True, capture_output=True)
    #print(run.returncode)
    if run.returncode != 0: 
        #Restart spotifyd
        print("Restarting spotifyd...")
        newid=full_restart_spotifyd()
        dest= build_dbus_string(newid)
        _=play_uri(uri, dest)
        #try again


    return 0


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
    if result.returncode == 130:
        print("Exiting...")
        sys.exit(0)
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
    if result.returncode == 130:
        print("Exiting...")
        sys.exit(0)
    if result.returncode != 0:
        return None
    selected = result.stdout.strip()
    for name, artist, uri in options:
        if f"{name} - {artist}" == selected:
            return uri
def fzf_select_song_name(options):
    input_str = "\n".join([f"{name} - {artist}" for name, artist,uri in options])
    result = subprocess.run(["fzf", "--layout=reverse-list", "--border=rounded", "--border-label='Fuzzy Spotify'"], input=input_str, text=True, capture_output=True)
    if result.returncode == 130:
        print("Exiting...")
        sys.exit(0)
    if result.returncode != 0:
        return None
    selected = result.stdout.strip()
    for name, artist, uri in options:
        if f"{name} - {artist}" == selected:
            return {uri}


    return None
def fzf_select_playlist(options):
    input_str = "\n".join([f"{name}" for name, id in options])
    result = subprocess.run(["fzf", "--layout=reverse-list", "--border=rounded", "--border-label='Fuzzy Spotify'"], input=input_str, text=True, capture_output=True)
    if result.returncode == 130:
        print("Exiting...")
        sys.exit(0)
    if result.returncode != 0:
        return None
    selected = result.stdout.strip()
    print(f"Selected playlist: {selected}")
    for name, id in options:
        if f"{name}" == selected:

            return id
    return None


def play_playlist(playlist_id, token):
    tracks = query_playlists(token, playlist_id)
    
    options = [(t["track"]["name"], t["track"]["artists"][0]["name"], t["track"]["uri"]) for t in tracks["items"]]

    uri = fzf_select_song_name(options)
    if uri:
        #strip out {}
        uri = str(uri).replace("{","").replace("}","").replace("'","")
        #id=ensure_spotifyd_running()
        #print(str(id))
        id=ensure_spotifyd_dbus()
        dest=build_dbus_string(id)
        play_uri(uri, dest)
        return 0
def build_rec_query(seed_tuple):
    #build a query for spotify recommendations
    #Example: seed_artists=artist1,artist2&seed_genres=genre1,genre2&seed_tracks=track1,track2
    query_parts = []
    artiststr=""
    genrestr=""
    trackstr=""
    final_str=""
    for seed_type, seed_value in seed_tuple:
        if seed_type=="artist":
            if artiststr:
                artiststr += ","
            artiststr += seed_value
        if seed_type=="genre":
            if genrestr:
                genrestr += ","
            genrestr += seed_value
        if seed_type=="track":
            if trackstr:
                trackstr += ","
            trackstr += seed_value
    if artiststr:
        final_str += f"artists={artiststr}"
    if genrestr:
        if final_str:
            final_str += "&"
        final_str += f"genres={genrestr}"
    if trackstr:
        if final_str:
            final_str += "&"
        final_str += f"tracks={trackstr}"
    encoded_query = urllib.parse.quote(final_str)
    return encoded_query

def query_recommendations(token, query):
    load_dotenv(override=True)  # Reload the environment variables
    authtoken = os.getenv("SPOTIFY_OAUTH_TOKEN")
    headers = {"Authorization": f"Bearer {authtoken}"}

    url= f"{SPOTIFY_API_BASE}/search?q={query}&type=track"
    #url="https://api.spotify.com/v1/recommendations?seed_artists=4NHQUGzhtTLFvgF5SZesLK&seed_genres=classical%2Ccountry&seed_tracks=0c6xIDDpzE81m2q797ordA"
    resp = requests.get(url, headers=headers)
    #resp.raise_for_status()
    if resp.status_code == 401:
        print(resp.text)
        print("Token expired, refreshing token...")
        _=get_refresh_token()
        load_dotenv(override=True)  # Reload the environment variables
        authtoken = os.getenv("SPOTIFY_OAUTH_TOKEN")
        headers = {"Authorization": f"Bearer {authtoken}"}
        print("Token refreshed successfully.")
        resp = requests.get(url, headers=headers)
    return resp.json()




def play_song(token,playlist_id):
    print("playlist_id:"+str(playlist_id))
    tracks = query_playlists(token, playlist_id)
    print(tracks)

    
    options = [(t["track"]["name"], t["track"]["artists"][0]["name"], t["track"]["uri"]) for t in tracks["items"]]

    uri = fzf_select_song(options)
    if uri:

        #id=ensure_spotifyd_running()
        #print(str(id))
        id=ensure_spotifyd_dbus()
        dest=build_dbus_string(id)
        play_uri(uri, dest)

def play_pause(method):
    #id=ensure_spotifyd_running()
    #print(str(id))
    id=ensure_spotifyd_dbus()

    exec_command = f"dbus-send --print-reply --dest=org.mpris.MediaPlayer2.spotifyd.instance{str(id)} /org/mpris/MediaPlayer2 org.mpris.MediaPlayer2.Player.{method}"
    _= subprocess.run(exec_command, shell=True, text=True, capture_output=True)


def main():
    command=open_initial_menu()

    token = get_spotify_auth()

    if command=="similar_tracks":
        artist_name = input("Enter artist name: ")
        track_name = input("Enter track name: ")

        lastfm_command = create_similiar_lastfm_command(artist_name, track_name)
        response = requests.get(lastfm_command)
        if response.status_code != 200:
            print("Failed to fetch similar tracks from Last.fm")
            sys.exit(1)
        if not response.json().get("similartracks"):
            print("No similar tracks found for the given artist and track.")
            print ("Artist:", artist_name)
            print ("Track:", track_name)
            print(response.json())
            sys.exit(0)
        similar_tracks = response.json()["similartracks"]["track"]
        options = [(track["name"], track["artist"]["name"], track["url"]) for track in similar_tracks]
        print("Building playback queue...")
        query = f"track:{track_name} artist:{artist_name}"
        track = search_spotify(query, token,"tracks")
        if track:
            _=play_uri(track[0], build_dbus_string(ensure_spotifyd_dbus()))
        else:
            print("No track found for query:", query)

        _=add_to_queue(options, token)
        
    elif command == "get_recommendations":
        building=True

        seed_options=["artist", "genre", "track"]
        options_tuple=[]
        while building:
            command = input("Enter seed type (artist, genre, track) or 'done' to finish: ").strip().lower()
            if command == "done":
                building = False
            else:
                if command not in seed_options:
                    print(f"Invalid seed type. Choose from {seed_options}.")
                    continue
                seed_value = input(f"Enter {command} name: ").strip()
                options_tuple.append((command, seed_value))
        if not options_tuple:
            print("No seeds provided. Exiting.")
            sys.exit(0)


        query=build_rec_query(options_tuple)

        recommendations = query_recommendations(token, query)

        if recommendations["tracks"]:
                
            id=ensure_spotifyd_dbus()
            dest=build_dbus_string(id)
            
            print("Adding recommendations to playback queue...")
            for track in recommendations["tracks"]["items"]:
                name = track["name"]
                artist = track["artists"][0]["name"]
                query = f"track:{name} artist:{artist}"
                track = search_spotify(query, token,"tracks")
                if track:
                    add_to_playback_queue(track[0], token)
            print("Recommendations added to playback queue.")
            
    elif command == "view_queue":
        _= view_queue(token)

    elif command == "single_song_playlist":
        artist_name = input("Enter artist name: ")
        track_name = input("Enter track name: ")
        query = f"track:{track_name} artist:{artist_name}"
        track = search_spotify(query, token,"tracks")
        if track:
            _=play_uri(track[0], build_dbus_string(ensure_spotifyd_dbus()))
        else:
            print("No track found for query:", query)

        
    elif command == "play_artist":
        artist_name = input("Enter artist name: ")
       # playlists = get_artist_search(token, str(artist_name))
        query = f"artist:{artist_name}"

        tracks = search_spotify(query, token,"artists")
        if tracks:
            _=play_uri(tracks[0], build_dbus_string(ensure_spotifyd_dbus()))
        

        #options = [(playlist["name"], playlist["uri"]) for playlist in playlists["artists"]["items"]]

        #uri=fzf_select_artist(options)
        ##pid=ensure_spotifyd_running()
        ##print(str(pid))
        #pid=ensure_spotifyd_dbus()
        #dest=build_dbus_string(pid)
        #play_uri(uri, dest)


        #id=fzf_select_playlist(options)
    elif command == "play_playlist":
        playlists = get_my_playlists(token)
        options = [(playlist["name"], playlist["uri"]) for playlist in playlists["items"]]
        uri=fzf_select_playlist(options)

        #id=ensure_spotifyd_running()

        #print(str(id))
        id=ensure_spotifyd_dbus()
        dest=build_dbus_string(id)
        play_uri(uri, dest)


    elif command == "play":
        _= play_pause("Play")

    elif command == "pause":
        _= play_pause("Pause")
    elif command == "shuffle":
        _= play_pause("Shuffle")
    elif command == "next":
        _= play_pause("Next")
    elif command == "previous":
        _= play_pause("Previous")
    elif command == "search":
        query = " ".join(sys.argv[2:])
        tracks = search_tracks(query, token)
        uri = fzf_select_song(tracks)
        if uri:
            #id =ensure_spotifyd_running()
            #print(str(id))
            id=ensure_spotifyd_dbus()
            dest=build_dbus_string(id)
            play_uri(uri, dest)
    else:
        print("Unknown command:", command)

    sys.exit(0)


if __name__ == "__main__":
    main()
    #_=auth_code_me_path()
    #print(get_me_path_authcode())
