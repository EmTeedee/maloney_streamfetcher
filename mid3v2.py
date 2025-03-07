#!/usr/bin/env python3
# Pretend to be /usr/bin/id3v2 from id3lib, sort of.
# Copyright 2005 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.

import sys
import locale
import codecs

from optparse import OptionParser, SUPPRESS_HELP

import mutagen
import mutagen.id3

VERSION = (1, 3)

global verbose
verbose = True


def getpreferredencoding(*args):
    return locale.getpreferredencoding(*args) or "utf-8"


class ID3OptionParser(OptionParser):
    def __init__(self):
        mutagen_version = ".".join(map(str, mutagen.version))
        my_version = ".".join(map(str, VERSION))
        version = "mid3v2 %s\nUses Mutagen %s" % (my_version, mutagen_version)
        self.edits = []
        OptionParser.__init__(
            self, version=version,
            usage="%prog [OPTION] [FILE]...",
            description="Mutagen-based replacement for id3lib's id3v2.")

    def format_help(self, *args, **kwargs):
        text = OptionParser.format_help(self, *args, **kwargs)
        return text + """\
You can set the value for any ID3v2 frame by using '--' and then a frame ID.
For example:
        mid3v2 --TIT3 "Monkey!" file.mp3
would set the "Subtitle/Description" frame to "Monkey!".

Any editing operation will cause the ID3 tag to be upgraded to ID3v2.4.
"""


def split_escape(string, sep, maxsplit=None, escape_char=u"\\"):
    """Like unicode.split but allows for the separator to be escaped"""

    assert len(sep) == 1
    assert len(escape_char) == 1

    if maxsplit is None:
        maxsplit = len(string)

    result = []
    current = u""
    escaped = False
    for char in string:
        if escaped:
            if char != escape_char and char != sep:
                current += escape_char
            current += char
            escaped = False
        else:
            if char == escape_char:
                escaped = True
            elif char == sep and len(result) < maxsplit:
                result.append(current)
                current = u""
            else:
                current += char
    result.append(current)
    return result


def unescape_bytes(string):
    assert isinstance(string, bytes)

    return codecs.escape_decode(string)[0]


def list_frames(option, opt, value, parser):
    items = mutagen.id3.Frames.items()
    for name, frame in sorted(items):
        print("    --%s    %s" % (name, frame.__doc__.split("\n")[0]))
    raise SystemExit


def list_frames_2_2(option, opt, value, parser):
    items = mutagen.id3.Frames_2_2.items()
    items.sort()
    for name, frame in items:
        print("    --%s    %s" % (name, frame.__doc__.split("\n")[0]))
    raise SystemExit


def list_genres(option, opt, value, parser):
    for i, genre in enumerate(mutagen.id3.TCON.GENRES):
        print("%3d: %s" % (i, genre))
    raise SystemExit


def delete_tags(filenames, v1, v2):
    for filename in filenames:
        if verbose:
            print("deleting ID3 tag info in %s" % filename)
        mutagen.id3.delete(filename, v1, v2)


def delete_frames(deletes, filenames):
    frames = deletes.split(",")
    for filename in filenames:
        if verbose:
            print("deleting %s from %s" % (deletes, filename))
        try:
            id3 = mutagen.id3.ID3(filename)
        except mutagen.id3.ID3NoHeaderError:
            if verbose:
                print("No ID3 header found; skipping.")
        except StandardError as err:
            print(str(err))
        else:
            for frame in frames:
                id3.delall(frame)
            id3.save()


def write_files(edits, filenames, escape):
    enc = getpreferredencoding()

    # unescape escape sequences and decode values
    encoded_edits = []
    for frame, value in edits:
        if not value:
            continue

        # strip "--"
        frame = frame[2:]

        value = value.encode(enc, "surrogateescape")

        if escape:
            try:
                value = unescape_bytes(value)
            except ValueError as err:
                print("%s: %s" % (frame, str(err)))
                raise SystemExit(1)

        try:
            value = value.decode(enc)
        except UnicodeDecodeError as err:
            print("%s: %s" % (frame, str(err)))
            raise SystemExit(1)

        encoded_edits.append((frame, value))
    edits = encoded_edits

    # preprocess:
    #   for all [frame,value] pairs in the edits list
    #      gather values for identical frames into a list
    tmp = {}
    for frame, value in edits:
        if frame in tmp:
            tmp[frame].append(value)
        else:
            tmp[frame] = [value]
    # edits is now a dictionary of frame -> [list of values]
    edits = tmp

    # escape also enables escaping of the split separator
    if escape:
        string_split = split_escape
    else:
        string_split = lambda s, *args, **kwargs: s.split(*args, **kwargs)

    for filename in filenames:
        if verbose:
            print("Writing", filename)
        try:
            id3 = mutagen.id3.ID3(filename)
        except mutagen.id3.ID3NoHeaderError:
            if verbose:
                print("No ID3 header found; creating a new tag")
            id3 = mutagen.id3.ID3()
        except StandardError as err:
            print(str(err))
            continue
        for (frame, vlist) in edits.items():
            if frame == "POPM":
                for value in vlist:
                    values = string_split(value, ":")
                    if len(values) == 1:
                        email, rating, count = values[0], 0, 0
                    elif len(values) == 2:
                        email, rating, count = values[0], values[1], 0
                    else:
                        email, rating, count = values

                    frame = mutagen.id3.POPM(
                        email=email, rating=int(rating), count=int(count))
                    id3.add(frame)

            elif frame == "COMM":
                for value in vlist:
                    values = string_split(value, ":")
                    if len(values) == 1:
                        value, desc, lang = values[0], "", "eng"
                    elif len(values) == 2:
                        desc, value, lang = values[0], values[1], "eng"
                    else:
                        value = ":".join(values[1:-1])
                        desc, lang = values[0], values[-1]
                    frame = mutagen.id3.COMM(
                        encoding=3, text=value, lang=lang, desc=desc)
                    id3.add(frame)
            elif frame == "TXXX":
                for value in vlist:
                    values = string_split(value, ":", 1)
                    if len(values) == 1:
                        desc, value = "", values[0]
                    else:
                        desc, value = values[0], values[1]
                    frame = mutagen.id3.TXXX(encoding=3, text=value, desc=desc)
                    id3.add(frame)
            elif issubclass(mutagen.id3.Frames[frame], mutagen.id3.UrlFrame):
                frame = mutagen.id3.Frames[frame](encoding=3, url=vlist)
                id3.add(frame)
            else:
                frame = mutagen.id3.Frames[frame](encoding=3, text=vlist)
                id3.add(frame)
        id3.save(filename)


def list_tags(filenames):
    enc = getpreferredencoding()
    for filename in filenames:
        print("IDv2 tag info for %s:" % filename)
        try:
            id3 = mutagen.id3.ID3(filename, translate=False)
        except StandardError as err:
            print(str(err))
        else:
            print(id3.pprint().encode(enc, "replace"))


def list_tags_raw(filenames):
    for filename in filenames:
        print("Raw IDv2 tag info for %s:" % filename)
        try:
            id3 = mutagen.id3.ID3(filename, translate=False)
        except StandardError as err:
            print(str(err))
        else:
            for frame in id3.values():
                print(repr(frame))


def main(argv):
    parser = ID3OptionParser()
    parser.add_option(
        "-v", "--verbose", action="store_true", dest="verbose", default=False,
        help="be verbose")
    parser.add_option(
        "-q", "--quiet", action="store_false", dest="verbose",
        help="be quiet (the default)")
    parser.add_option(
        "-e", "--escape", action="store_true", default=False,
        help="enable interpretation of backslash escapes")
    parser.add_option(
        "-f", "--list-frames", action="callback", callback=list_frames,
        help="Display all possible frames for ID3v2.3 / ID3v2.4")
    parser.add_option(
        "--list-frames-v2.2", action="callback", callback=list_frames_2_2,
        help="Display all possible frames for ID3v2.2")
    parser.add_option(
        "-L", "--list-genres", action="callback", callback=list_genres,
        help="Lists all ID3v1 genres")
    parser.add_option(
        "-l", "--list", action="store_const", dest="action", const="list",
        help="Lists the tag(s) on the open(s)")
    parser.add_option(
        "--list-raw", action="store_const", dest="action", const="list-raw",
        help="Lists the tag(s) on the open(s) in Python format")
    parser.add_option(
        "-d", "--delete-v2", action="store_const", dest="action",
        const="delete-v2", help="Deletes ID3v2 tags")
    parser.add_option(
        "-s", "--delete-v1", action="store_const", dest="action",
        const="delete-v1", help="Deletes ID3v1 tags")
    parser.add_option(
        "-D", "--delete-all", action="store_const", dest="action",
        const="delete-v1-v2", help="Deletes ID3v1 and ID3v2 tags")
    parser.add_option(
        '--delete-frames', metavar='FID1,FID2,...', action='store',
        dest='deletes', default='', help="Delete the given frames")
    parser.add_option(
        "-C", "--convert", action="store_const", dest="action",
        const="convert",
        help="Convert tags to ID3v2.4 (any editing will do this)")

    parser.add_option(
        "-a", "--artist", metavar='"ARTIST"', action="callback",
        help="Set the artist information", type="string",
        callback=lambda *args: args[3].edits.append(("--TPE1", args[2])))
    parser.add_option(
        "-A", "--album", metavar='"ALBUM"', action="callback",
        help="Set the album title information", type="string",
        callback=lambda *args: args[3].edits.append(("--TALB", args[2])))
    parser.add_option(
        "-t", "--song", metavar='"SONG"', action="callback",
        help="Set the song title information", type="string",
        callback=lambda *args: args[3].edits.append(("--TIT2", args[2])))
    parser.add_option(
        "-c", "--comment", metavar='"DESCRIPTION":"COMMENT":"LANGUAGE"',
        action="callback", help="Set the comment information", type="string",
        callback=lambda *args: args[3].edits.append(("--COMM", args[2])))
    parser.add_option(
        "-g", "--genre", metavar='"GENRE"', action="callback",
        help="Set the genre or genre number", type="string",
        callback=lambda *args: args[3].edits.append(("--TCON", args[2])))
    parser.add_option(
        "-y", "--year", "--date", metavar='YYYY[-MM-DD]', action="callback",
        help="Set the year/date", type="string",
        callback=lambda *args: args[3].edits.append(("--TDRC", args[2])))
    parser.add_option(
        "-T", "--track", metavar='"num/num"', action="callback",
        help="Set the track number/(optional) total tracks", type="string",
        callback=lambda *args: args[3].edits.append(("--TRCK", args[2])))

    for frame in mutagen.id3.Frames:
        if (issubclass(mutagen.id3.Frames[frame], mutagen.id3.TextFrame)
                or issubclass(mutagen.id3.Frames[frame], mutagen.id3.UrlFrame)
                or issubclass(mutagen.id3.Frames[frame], mutagen.id3.POPM)):
            parser.add_option(
                "--" + frame, action="callback", help=SUPPRESS_HELP,
                type='string', metavar="value",  # optparse blows up with this
                callback=lambda *args: args[3].edits.append(args[1:3]))

    (options, args) = parser.parse_args(argv[1:])
    global verbose
    verbose = options.verbose

    if args:
        if parser.edits or options.deletes:
            if options.deletes:
                delete_frames(options.deletes, args)
            if parser.edits:
                write_files(parser.edits, args, options.escape)
        elif options.action in [None, 'list']:
            list_tags(args)
        elif options.action == "list-raw":
            list_tags_raw(args)
        elif options.action == "convert":
            write_files([], args, options.escape)
        elif options.action.startswith("delete"):
            delete_tags(args, "v1" in options.action, "v2" in options.action)
        else:
            parser.print_help()
    else:
        parser.print_help()


if __name__ == "__main__":
    main(sys.argv)

