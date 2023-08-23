#!/usr/bin/env python3

import os
import argparse
import unicodedata
import json
import mutagen
import mutagen.id3

class MaloneyRenamer:
    '''
    rename maloney files...
    '''

    path = './'
    verbose = False
    episode_data = []
    mid3v2 = ''

    def __init__(self, verbose=False, episode_json_file=''):
        # Change to script location
        path = os.path.split(os.path.realpath(__file__))[0]
        self.path = path
        self.mid3v2 = path + '/mid3v2.py'
        self.verbose = verbose
        if not episode_json_file:
            episode_json_file = path + '/episode-data.json'
        if os.path.isfile(episode_json_file):
            with open(episode_json_file, mode='r', encoding="utf-8") as file:
                json_string = file.read()
                json_string = unicodedata.normalize('NFKD', json_string).encode('utf-8','ignore')
                self.episode_data = json.loads(json_string)

    def log(self, message):
        if self.verbose:
            print(message)

    def system_command(self, command):
        self.log(command)
        os.system(command)

    def process_file(self, filename):
        if not os.path.isfile(filename):
            return

        path = os.path.dirname(filename)
        base = os.path.basename(filename)
        ext = os.path.splitext(base)[1]
        stem = os.path.splitext(base)[0]

        if not ext == '.mp3':
            print("Can only rename .mp3: {}".format(filename))
            return

        stem = unicodedata.normalize('NFKD', stem).encode('utf-8','ignore').decode('utf-8')
        episode_info = None
        if episode_info is None:
            episode_info = next((item for item in self.episode_data if "uid" in item and item["uid"] == stem), None)
        if episode_info is None:
            episode_info = next((item for item in self.episode_data if item["episode"] == stem), None)
        if episode_info is None:
            episode_info = next((item for item in self.episode_data if item["title"] == stem), None)
        if episode_info is None:
            try:
                id3 = mutagen.id3.ID3(filename, translate=False)
            except Exception as err:
                print(str(err))
            else:
                for frame in id3.values():
                    if frame.FrameID == 'TRCK':
                        stem = str(+frame).zfill(3)
                        episode_info = next((item for item in self.episode_data if item["episode"] == stem), None)

        if not episode_info is None:
            date = episode_info["date"]
            number = episode_info["episode"]
            lead = ''
            if "lead" in episode_info:
                lead = episode_info["lead"]
            title = episode_info["title"]
            mp3_name = "Philip Maloney - {} - {} ({}).mp3".format(number, title, date)

            if path:
                new_filename = "{}/{}".format(path, mp3_name)
            else:
                new_filename = mp3_name
            os.rename(filename, new_filename)

            self.log("  Adding ID3 Tags...")
            options = []
            options += [ '--delete-frames', '"COMM"' ]
            options += [ '-A', '"Philip Maloney"' ]
            options += [ '-a', '"Roger Graf"' ]
            options += [ '-g', '"Book"' ]
            options += [ '--TLAN', '"deu"' ]
            options += [ '-y', '"{}"'.format(date) ]
            options += [ '-t', '"{} ({})"'.format(title, date) ]
            options += [ '-T', '"{}"'.format(number) ]
            if lead:
                options += [ '-c', '"{}:{}:{}"'.format("", lead, "deu") ]

            self.system_command('"{}" {} "{}"'.format(self.mid3v2, ' '.join(options), new_filename))
        else:
            print("Could not find info for: {}".format(stem))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description = 'Options for renamer script')
    parser.add_argument('-j', '--json-data', dest='json', help='Use episode info from json file.', default='')
    parser.add_argument('-v', '--verbose', action='store_true', dest='verbose', help='Enable verbose.')
    parser.add_argument('files', nargs='*')
    args = parser.parse_args()

    renamer = MaloneyRenamer(verbose=args.verbose, episode_json_file = args.json)
    for mp3file in args.files:
        renamer.process_file(filename=mp3file)
