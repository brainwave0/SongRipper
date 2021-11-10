#!/usr/bin/env python3
import typing as tp
import os.path as osp
import subprocess as spc
import sys
import re

def record(artist_title: str, music_dir: str):
    spc.run([
        "rec", "-C", "-4.0",
        song_path(artist_title, music_dir), "silence", "1", "3t", "0%", "1",
        "3t", "0%"
    ],
        check=True)


def song_path(artist_title: str, music_dir: str) -> str:
    return osp.join(music_dir,
                    "{}.mp3".format(safe_filename(artist_title)))


def cleanup(song: str, music_dir: str):
    os.remove(song_path(song, music_dir))


def try_record(song: str, music_dir: str,
               keyboard_interrupt_handler: tp.Callable):
    while True:
        try:
            record(song, music_dir)
            break
        except KeyboardInterrupt:
            keyboard_interrupt_handler()
            break


def to_artist_title(line: str) -> str:
    line = re.sub(r'^–', '', line)
    line = re.sub(r' \(\d+\)', ' ', line)
    line = re.sub(r'–?	', ' - ', line)
    line = re.sub(r'\*(,? )', '\1', line)
    line = re.sub(r'–', '-', line)
    line = re.sub(r' \(File.*?\).*', '', line)
    line = re.sub(r'', ' ', line)
    line = re.sub(r'^ ', '', line)
    return line


def handle_keyboard_interrupt(song: str, queue_file: io.IOBase,
                              lib_file: io.IOBase):
    cleanup(song)
    options = [
        "Go back to the previous song",
        "Place the song in the front of the queue",
        "Place the song in the back of the queue",
        "Start over",
        "Quit",
        "Skip"
    ]
    print("Pick tasks (e.g. 24):")
    for option in options:
        print("{}. {}".format(options.index(option), option))
    while True:
        response = input("Choose: ")
        if any(int(i) not in range(1, len(options) + 1) for i in response):
            print("Invalid response. Try again.")
        else:
            break
    input("Stop any currently-playing audio, then press Enter.")
    for c in response:
        if c == "1":
            song = pop_last(lib_file)
        elif c == "2":
            queue_file.write(song + '\n')
        elif c == "3":
            prepend(queue_file, song + '\n')
        elif c == "4":
            raise RuntimeError
        elif c == "5":
            sys.exit()
        elif c == "6":
            pass


def is_song(string: str) -> bool:
    credit_types = r"Lyrics|Vocals|Written|Additional|Uncredited|Remix|Producer|Featuring|Engineer"
    credit = r"(, )?({credit_types})([- ]?By)?".format(**locals())
    credits = r"({credit})+".format(**locals())
    final_regex = r".*{credits}( \[{credits}\])? – .*".format(**locals())
    return not (re.match(final_regex, string) or string.startswith("	")
                or not re.match(r".*[–-].*", string))


def main(music_dir: str):
    app_name = "SongRipper"
    library_path = save_data_file_path("library", app_name)
    queue_path = save_data_file_path("queue", app_name)
    with open(library_path, "r+") as lib_file, open(queue_path,
                                                    "r+") as queue_file:
        lib = set(i.strip() for i in lib_file if i != '\n')
        while True:
            line = pop_last(queue_file)
            song = to_artist_title(line)
            if not song:
                print("Queue is empty.")
                break
            if song not in lib and is_song(line):
                web_search('"{}"'.format(song))
                try:
                    try_record(
                        song, lambda: handle_keyboard_interrupt(
                            song, queue_file, lib_file))
                except RuntimeError:
                    continue
                lib.add(song)
                lib_file.write(song + '\n')
