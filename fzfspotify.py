#!/bin/python

import os
import sys
import time
import requests
import subprocess

SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_BASE = "https://api.spotify.com/v1"

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
    


def fzf_select_song(options):
    input_str = "\n".join([f"{name} - {artist}" for name, artist,uri in options])
    result = subprocess.run(["fzf"], input=input_str, text=True, capture_output=True)
    if result.returncode != 0:
        return None
    selected = result.stdout.strip()
    #print(selected)
    for name, artist, uri in options:
        if f"{name} - {artist}" == selected:
            #print(f"Selected: {uri}")
            return uri
def fzf_select_song_name(options):
    input_str = "\n".join([f"{name} - {artist}" for name, artist,uri in options])
    result = subprocess.run(["fzf"], input=input_str, text=True, capture_output=True)
    if result.returncode != 0:
        return None
    selected = result.stdout.strip()
    #print(selected)
    for name, artist, uri in options:
        if f"{name} - {artist}" == selected:
            #print(f"Selected: {uri}")
            return {name}


    return None
def fzf_select_playlist(options):
    input_str = "\n".join([f"{name}" for name, id in options])
    result = subprocess.run(["fzf"], input=input_str, text=True, capture_output=True)
    if result.returncode != 0:
        return None
    selected = result.stdout.strip()
    #print(selected)
    for name, id in options:
        if f"{name}" == selected:
            print(f"Selected: {id}")
            #strip out {' and '}

            return id
    #print(f"Selected: {selected}") 
                
            

    return None

def play_track(uri, token):
    #use spotifY_player to play the track
    exec_command = f"spotify_player playback start track --id \"{uri}\""
    
    result = subprocess.run(exec_command, shell=True, text=True, capture_output=True)
    #print(str(result))
    
    #print(response)
    return 0
def play_context(uri, token):
    #use spotifY_player to play the track
    exec_command = f"spotify_player playback start context --name \"{uri}\" playlist"
    
    result = subprocess.run(exec_command, shell=True, text=True, capture_output=True)
    print(str(result))

    #print(str(result))
    
    #print(response)
    return 0

def play_playlist(playlist_id, token):
    #tracks = query_playlists(token, playlist_id)
    #print(str(tracks))
    tracks = query_playlists(token, playlist_id)
    
    options = [(t["track"]["name"], t["track"]["artists"][0]["name"], t["track"]["id"]) for t in tracks["items"]]
    #get just [track name]
    #Get ID from song 

    uri = fzf_select_song_name(options)
    #print(uri)
    if uri:
        play_context(uri, token)
        return 0
    

def play_song(token,playlist_id):
    tracks = query_playlists(token, playlist_id)
    
    options = [(t["track"]["name"], t["track"]["artists"][0]["name"], t["track"]["id"]) for t in tracks["items"]]
    #get just [track name]
    #Get ID from song 

    uri = fzf_select_song(options)
    #print(uri)
    if uri:
        play_track(uri, token)
def get_all_id_in_playlist(token,playlist_id):
    tracks = query_playlists(token, playlist_id)
    
    idarray= []
    #options = [(t["track"]["name"], t["track"]["artists"][0]["name"], t["track"]["id"]) for t in tracks["items"]]
    #get just [track name]
    #Get ID from song 
    #for t in tracks["items"]:
    #    idarray.append(t["track"]["id"])
    #    print(t["track"]["id"])

    #print(uri)
    play_playlist(playlist_id, token)


def main():
    if len(sys.argv) < 2:
        print("Usage: spotify_cli.py search <query>")
        sys.exit(1)
    command = sys.argv[1]
    token = get_spotify_auth()
    if command=="myplaylists":
        playlists = get_my_playlists(token)
        options = [(playlist["name"], playlist["id"]) for playlist in playlists["items"]]
        

        id=fzf_select_playlist(options)
        
        playlist=play_playlist(id, token)
        
        #if id:
        #    play_song(token,id)

        return playlist

    elif command == "playlist":
        if len(sys.argv) < 3:
            print("Usage: spotify_cli.py playlist <playlist_id>")
            sys.exit(1)
        playlist_id = sys.argv[2]
        play_song(token,playlist_id)
    elif command == "search":
        query = " ".join(sys.argv[2:])
        tracks = search_tracks(query, token)
        uri = fzf_select_song(tracks)
        if uri:
            play_track(uri, token)
    else:
        print("Unknown command:", command)

if __name__ == "__main__":
    main()
