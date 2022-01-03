#!/usr/bin/env python3
import typing
import os.path as osp
import subprocess as spc
import sys
import re
import io
import os
import webbrowser
import urllib.parse
import xdg.BaseDirectory
import contextlib
import argparse


def record(path: str):
    spc.run([
        "rec", "-C", "-4.0", path, "silence", "1", "0t", "0%", "1", "3t", "0%"
    ],
            check=True)


def safe_filepath(path: str) -> str:
    path = "".join(c for c in path if c.isalnum() or c in " ._-+*()&'!#/"
                   ).rstrip()  # remove potentially illegal characters
    dirs, name_ext = os.path.split(path)
    name_ext = name_ext.encode('utf-8')[:255].decode(
        'utf-8')  # truncate to 255 bytes
    name, extension = os.path.splitext(name_ext)

    # truncate to 4096 characters
    path = os.path.join(dirs, name)[:4096 - len(extension)]
    path += extension

    return path


def song_path(artist_title: str, music_dir: str) -> str:
    return safe_filepath(os.path.join(music_dir, f'{artist_title}.mp3'))


def try_record(path: str, keyboard_interrupt_handler: typing.Callable):
    try:
        record(path)
    except KeyboardInterrupt:
        keyboard_interrupt_handler()


def to_artist_title(line: str) -> str:
    line = re.sub(r'^–', '', line)
    line = re.sub(r' \(\d+\)', ' ', line)
    line = re.sub(r'\*', r'', line)
    line = re.sub(r'–', ' - ', line)
    line = re.sub(r' \(File.*?\).*', '', line)
    line = re.sub(r'^A', ' ', line)
    line = re.sub(r'^ ', '', line)
    line = re.sub(r' +', ' ', line)
    return line


def handle_keyboard_interrupt(artist_title: str, music_dir: str,
                              queue_file: typing.TextIO,
                              lib_file: typing.TextIO, lib: typing.Set[str]):
    os.remove(song_path(artist_title, music_dir))
    options = [
        "Pop the previous song", "Place the song in the front of the queue",
        "Place the song in the back of the queue", "Quit", "Skip"
    ]
    print()
    print("Pick tasks (e.g. 24):")
    print(format_options(options))
    while True:
        response = input("Choose: ")
        if not valid_selection(response, options):
            print("Invalid response. Try again.")
        else:
            break
    input("Stop any currently-playing audio, then press Enter.")
    for c in response:
        if c == "1":
            artist_title = pop_file_line(lib_file)
            lib.remove(artist_title)
        elif c == "2":
            queue_file.write(artist_title + '\n')
        elif c == "3":
            prepend_file(queue_file, artist_title + '\n')
        elif c == "4":
            sys.exit()
        elif c == "5":
            lib.add(artist_title)
            lib_file.write(artist_title + '\n')

def format_options(options: typing.List[str]) -> str:
    return '\n'.join("{}. {}".format(options.index(option) + 1, option)
                     for option in options)


def valid_selection(ints_str: str, options: typing.List[str]):
    try:
        return ints_str != '' and all(
            int(i) in range(1,
                            len(options) + 1) for i in ints_str)
    except ValueError:
        return False


def is_song(string: str) -> bool:
    credit_types = r"Lyrics|Vocals|Written|Additional|Uncredited|Remix|Producer|Featuring|Engineer|Conductor|Programmed|Drums|Guest|Appearance"
    credit = r"(, )?({credit_types})([- ]?By)?".format(**locals())
    credits = r"({credit})+".format(**locals())
    final_regex = r".*{credits}( \[{credits}\])? – .*".format(**locals())
    return not (re.match(final_regex, string) or string.startswith("	")
                or not re.match(r".*[–-].*", string))


def pop_file_line(file: typing.TextIO) -> str:
    file.seek(0, os.SEEK_END)
    character = ''
    character = read_file_char_backwards(file)
    while character == '\n':
        character = read_file_char_backwards(file)
    line = ''
    while character != '\n':
        line += character
        try:
            character = read_file_char_backwards(file)
        except OutOfBounds:
            break
    if character == '\n':
        file.seek(file.tell() + 1, os.SEEK_SET)
    file.truncate()
    return line[::-1]


def web_search(terms: str, search_engine: str = "duckduckgo"):
    if search_engine == "duckduckgo":
        webbrowser.open("https://duckduckgo.com/?q={}".format(
            urllib.parse.quote(terms, safe="")))
    else:
        raise NotImplementedError


def save_data_file_path(file_name: str, APP_NAME: str) -> str:
    path = os.path.join(xdg.BaseDirectory.save_data_path(APP_NAME), file_name)
    open(path, "a").close()
    return path


def prepend_file(file: typing.TextIO, new_data: str):
    file.seek(0, os.SEEK_SET)
    old_data = file.read()
    file.seek(0, os.SEEK_SET)
    file.write(new_data)
    file.write(old_data)


class OutOfBounds(Exception):
    pass


def read_file_char_backwards(file: typing.TextIO) -> str:
    position = file.tell() - 1
    if position < 0:
        raise OutOfBounds
    file.seek(position, os.SEEK_SET)
    while position >= 0:
        try:
            data = file.read(1)
            break
        except UnicodeDecodeError:
            position -= 1
    file.seek(position, os.SEEK_SET)
    return data


def main(music_dir: str):
    app_name = "SongRipper"
    library_path = save_data_file_path("library", app_name)
    queue_path = save_data_file_path("queue", app_name)
    with open(library_path, "r+") as lib_file, open(queue_path,
                                                    "r+") as queue_file:
        lib = set(i.strip() for i in lib_file if i != '\n')
        while True:
            try:
                line = pop_file_line(queue_file)
            except OutOfBounds:
                print("Queue is empty.")
                break
            song = to_artist_title(line)
            if song not in lib and is_song(line):
                web_search('"{}"'.format(song))
                try:
                    record(song_path(song, music_dir))
                    lib.add(song)
                    lib_file.write(song + '\n')
                except KeyboardInterrupt:
                    handle_keyboard_interrupt(song, music_dir, queue_file,
                                              lib_file, lib)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('music_directory')
    args = parser.parse_args()
    main(args.music_directory)
