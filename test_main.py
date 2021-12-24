#!/usr/bin/env pytest
from main import *
import threading
from playsound import playsound
import time
import os
import mutagen.mp3
import pytest

artist_title = "foo - bar"
music_dir = "/tmp"
path = f"{music_dir}/{artist_title}.mp3"

@pytest.fixture
def recording():
    global path
    global artist_title
    global music_dir
    threading.Thread(target=record, args=(artist_title, music_dir)).start()
    playsound("sine_tone.wav")
    time.sleep(4)  # wait for silence to be detected, and for the file to be written
    yield path
    try:
        os.remove(path)
    except FileNotFoundError:
        pass

def test_record(recording):
    assert mutagen.mp3.MP3(recording).info.length - 4 < 0.01  # assert that a four-second MP3 file was written

def test_song_path():
    assert song_path(artist_title, "/home/me/my music") == "/home/me/my music/foo - bar.mp3"

def test_cleanup(recording):
    cleanup(artist_title, music_dir)
    assert not os.path.isfile(recording)

