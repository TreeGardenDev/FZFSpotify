#!/bin/bash

#Intent - Handler to give options in fzfspotify.py and run the selected option as a python script with the arguments passed to it.

options=(
    "Full Playlist"
    "Context Playlist"
    "Play Artist"
    "Single Song"
)

# Get the selected option from fzf
fzf_output=$(printf '%s\n' "${options[@]}" | fzf --height 40% --reverse --inline-info --header "Select an option:")

real_output=""
search_query=""
if [ "$fzf_output" == "Context Playlist" ]; then
    real_output="context_playlist"
elif [ "$fzf_output" == "Single Song" ]; then
    real_output="single_song_playlist"
elif [ "$fzf_output" == "Full Playlist" ]; then
    real_output="play_playlist"
elif [ "$fzf_output" == "Play Artist" ]; then
    real_output="play_artist"
    search_query=$(echo -n "" && read artist_name && echo "$artist_name")
else
    echo "Invalid selection"
    exit 1
fi
final_query=$real_output
if [ "$real_output" == "play_artist" ]; then
    final_query=$real_output" '"$search_query"'"
fi


python ~/git/fzfspot/fzfspotify.py $final_query



