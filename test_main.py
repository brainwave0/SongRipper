#!/usr/bin/env pytest
from main import *
import threading
from playsound import playsound
import time
import os
import mutagen.mp3
import pytest
import wave
import contextlib
import csv
import signal

dst_path = '/tmp/foo - bar.mp3'


@pytest.mark.parametrize('src_path',
                          ['sine_tone.wav', 'sine_tone_interrupted.wav'])
def test_record(src_path):
    global dst_path
    threading.Thread(target=record, args=(dst_path,)).start()

    # get the duration of the source file
    with contextlib.closing(wave.open(src_path, 'r')) as file:
        frames = file.getnframes()
        rate = file.getframerate()
        duration = frames / float(rate)

    time.sleep(1)  # wait for SoX to start recording
    playsound(src_path)
    time.sleep(
        duration +
        4)  # wait for silence to be detected, and for the file to be written
    try:
        assert mutagen.mp3.MP3(
            dst_path
        ).info.length - duration < 0.01  # assert that a MP3 file was written with the original duration
    finally:
        with contextlib.suppress(FileNotFoundError):
            os.remove(dst_path)


def test_safe_filepath():
    # see if a file can be named using the contents of rand_str.txt
    with open('rand_str.txt', 'r', errors='ignore') as str_file:
        contents = str_file.read()
        path = safe_filepath(''.join(i for i in contents if i != '/'))
        open(path, 'a').close()
        os.remove(path)


def test_song_path():
    assert song_path('foo - bar',
                     "/home/me/my music") == "/home/me/my music/foo - bar.mp3"


def test_to_artist_title():
    with open('artist_titles.csv', 'r') as file:
        reader = csv.reader(file)
        for row in reader:
            if row[1] != 'None':
                assert to_artist_title(row[0]) == row[1]


def test_is_song():
    with open('artist_titles.csv', 'r') as file:
        reader = csv.reader(file)
        for row in reader:
            if row[1] == 'None':
                assert is_song(row[0]) is False
            else:
                assert is_song(row[0]) is True


def test_pop_file_line():
    with contextlib.suppress(FileNotFoundError):
        os.remove('/tmp/test.txt')
    open('/tmp/test.txt', 'x').close()
    with open('/tmp/test.txt', 'r+') as file:
        with pytest.raises(OutOfBounds):
            pop_file_line(file)
        file.seek(0)
        file.write("some text")
        assert pop_file_line(file) == "some text"
        file.seek(0)
        assert file.read() == ""
        file.seek(0)
        file.write("more text\neven more text")
        assert pop_file_line(file) == "even more text"
        file.seek(0)
        assert file.read() == 'more text\n'
        file.write('foo\n')
        assert pop_file_line(file) == 'foo'
    os.remove('/tmp/test.txt')

def test_prepend_file():
    with contextlib.suppress(FileNotFoundError):
        os.remove('/tmp/test.txt')
    open('/tmp/test.txt', 'x').close()
    with open('/tmp/test.txt', 'r+') as file:
        prepend_file(file, 'foo')
        file.seek(0)
        assert file.read() == 'foo'
        prepend_file(file, 'bar')
        file.seek(0)
        assert file.read() == 'barfoo'


def test_read_file_char_backwards():
    with contextlib.suppress(FileNotFoundError):
        os.remove('/tmp/test.txt')
    open('/tmp/test.txt', 'x').close()
    with open('/tmp/test.txt', 'r+') as file:
        with pytest.raises(OutOfBounds):
            read_file_char_backwards(file)
        file.write("foo")
        assert read_file_char_backwards(file) == 'o'

def test_valid_selection():
    assert valid_selection("", ["a", "b", "c"]) is False
    assert valid_selection("1", ["a", "b", "c"]) is True
    assert valid_selection("11", ["a", "b", "c"]) is True
    assert valid_selection("12", ["a", "b", "c"]) is True
    assert valid_selection("124", ["a", "b", "c"]) is False
    assert valid_selection("g", ["a", "b", "c"]) is False

def test_format_options():
    assert format_options(["a", "b", "c"]) == "1. a\n2. b\n3. c"
