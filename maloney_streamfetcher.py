#!/usr/bin/env python3
#-------------------------------------------------------------------------------
# Import modules
#
import io
import os
import shutil
import argparse
import unicodedata
import json
from urllib.request import urlopen
import pycurl
import certifi

#-------------------------------------------------------------------------------
# Class Maloney Download
#
class MaloneyDownload:
  '''
  Downloads Maloney Episodes
  '''
  verbose = False
  episode_data = []

  def __init__(self, verbose=False, episode_json_file=''):
    # Change to script location
    path,file=os.path.split(os.path.realpath(__file__))
    os.chdir(path)
    self.path = path
    self.verbose = verbose
    if os.path.isfile(episode_json_file):
        with open(episode_json_file, mode='r') as f:
            json_string = f.read()
            json_string = unicodedata.normalize('NFKD', json_string).encode('utf-8','ignore')
            self.episode_data = json.loads(json_string)

  def fetch_latest(self, outdir = None, uid = None):
    self.process_maloney_episodes(1, outdir=outdir, uid=uid)

  def fetch_all(self, outdir = None, uid = None):
    for i in range(1,20): # each page shows 10 items per page, iterate through pages
      if (self.process_maloney_episodes(i, outdir=outdir, uid=uid) > 0) and uid: # if uid is set and download worked -> exit
        return

  def process_maloney_episodes(self, page_number=1, outdir=None, uid=None):
    # Constants
    path_to_mid3v2   = self.path
    mid3v2   = path_to_mid3v2 + "/mid3v2.py"

    temp_directory   = "./temp"
    #json_url = "https://il.srgssr.ch/integrationlayer/2.0/srf/mediaComposition/audio/"
    #json_url = "https://il.srgssr.ch/integrationlayer/2.0/mediaComposition/byUrn/urn:srf:audio:"
    json_url = "https://il.srf.ch/integrationlayer/2.0/mediaComposition/byUrn/"

    episode_list_url = "https://www.srf.ch/aron/api/audio/shows/A00361/latestEpisodes?page=" + str(page_number)

    # Get user constants
    if outdir is None:
      out_dir = "."
    elif os.path.isdir(outdir):
      out_dir = outdir
    else:
      self.log("Given output directory doesn't exist")
      return None

    # Get page content and id's
    if uid is None:
      urns = self.get_list_urns(episode_list_url)
    else:
      urns = [ 'urn:srf:audio:' + uid]

    # Read JSON Data
    json_data = self.get_jsondata(json_url, urns)

    # Download Files
    self.log("Get Episodes")
    # Create tmp directory
    if not os.path.exists(temp_directory):
      os.makedirs(temp_directory)
    cnt = 0
    idx = []
    for episode in json_data:

      if episode["number"]:
          mp3_name = "Philip Maloney - {} - {} ({}).mp3".format(episode["number"], episode["title"], episode["date"])
      else:
          mp3_name = "Philip Maloney - {} - {} ({}).mp3".format("xxx", episode["title"], episode["date"])
      filename = out_dir + "/" + mp3_name

      if os.path.isfile(filename):
        self.log("  Episode \"{} ({})\" already exists in the output folder {}".format(episode["title"], episode["date"], filename))
        self.log("    Skipping Episode ...")
      else:
        # Download via HTTPS
        self.log("  HTTPS download...")
        self.log(episode['httpsurl'])
        try:
          mp3file = urlopen(episode['httpsurl'])
          with open(filename,'wb') as output:
            output.write(mp3file.read())
        except Exception as err:
          print("Could not download episode {}: {}".format(mp3_name, str(err)))
          continue

        idx.append(cnt)

        self.log("  Adding ID3 Tags...")
        options = []
        options += [ '--delete-frames', '"COMM"' ]
        options += [ '-A', '"Philip Maloney"' ]
        options += [ '-a', '"Roger Graf"' ]
        options += [ '-g', '"Book"' ]
        options += [ '--TLAN', '"deu"' ]
        options += [ '-y', '"{}"'.format(episode["date"]) ]
        options += [ '-t', '"{} ({})"'.format(episode["title"], episode["date"]) ]
        if episode["number"]:
          options += [ '-T', '"{}"'.format(episode["number"]) ]
        if episode["lead"]:
          options += [ '-c', '"{}:{}:{}"'.format("", episode["lead"], "deu") ]

        self.system_command('"{}" {} "{}"'.format(mid3v2, ' '.join(options), filename))

      cnt = cnt + 1

    # Deleting tmp directory
    shutil.rmtree(temp_directory)

    print("------------------------------------------------------")
    if page_number:
        print(" Finished downloading {} Episodes from page {} ({} episodes on page)".format(len(idx), page_number, len(urns)))
    else:
        print(" Finished downloading {} Episodes".format(len(idx)))
    for id in idx:
      print("  * {} ({})".format(json_data[id]["title"], json_data[id]["date"]))
    print("------------------------------------------------------")
    return cnt

  def curl_page(self, url):
    buffer = io.BytesIO()
    c = pycurl.Curl()
    c.setopt(c.WRITEFUNCTION, buffer.write)
    c.setopt(c.URL, url)
    c.setopt(c.WRITEDATA, buffer)
    c.setopt(pycurl.CAINFO, certifi.where())
    c.perform()
    c.close()
    return buffer.getvalue().decode("utf-8")

  def get_jsondata(self, jsonurl, urns):
    json_data = []
    for urn in urns:
      url = jsonurl + urn + ".json"
      page = self.curl_page(url)
      (title, lead, httpsurl, year, date, number) = self.parse_json(page, urn)
      json_data.append({"title": title, "lead": lead, "httpsurl":httpsurl, "year":year, "date":date, "number":number})
    return json_data

  def parse_json(self, json_string, uid):
    json_string = unicodedata.normalize('NFKD', json_string).encode('utf-8','ignore') # we're not interested in any non-unicode data
    jsonobj = json.loads(json_string)

    title = jsonobj['chapterList'][0]['title']
    lead = jsonobj['chapterList'][0].get('lead', '')
    publishedDate = jsonobj['episode']['publishedDate']

    httpsurl = ''
    for x in range(0, len(jsonobj['chapterList'][0]['resourceList'])):
      if 'HTTPS' in jsonobj['chapterList'][0]['resourceList'][x]['protocol']:
        httpsurl = jsonobj['chapterList'][0]['resourceList'][x]['url']

    year = jsonobj['chapterList'][0]['date'][:4]
    date = jsonobj['chapterList'][0]['date'][:10]
    number = ""

    episode_info = next((item for item in self.episode_data if item["title"] == title), None)
    if episode_info is None:
        episode_info = next((item for item in self.episode_data if "alternative_titles" in item and title in item["alternative_titles"]), None)
    if episode_info:
        episode_info["lead"] = lead
        episode_info["uid"] = uid
        date = episode_info["date"]
        number = episode_info["episode"]
    elif self.episode_data:
        print("Could not find episode information for: {}".format(title))

    self.log("   Episode Info")
    self.log("      * Title    : {} Date:{}".format(title, publishedDate, year))
    self.log("      * HTTPS Url: {}".format(httpsurl))
    self.log("      * Lead     : {}".format(lead))

    return (title, lead, httpsurl, year, date, number)

  def get_list_urns(self, url):
    json_string = self.curl_page(url)
    json_string = unicodedata.normalize('NFKD', json_string).encode('utf-8','ignore')
    jsonobj = json.loads(json_string)
    urns = []
    for episode in jsonobj:
        urns.append(episode.get('assetUrn'))
    return urns

  def system_command(self, command):
    self.log(command)
    os.system(command)

  def log(self, message):
    if self.verbose:
      print(message)

#-------------------------------------------------------------------------------
# Execute
#
if __name__ == "__main__":

  parser = argparse.ArgumentParser(description = 'Options for maloney_streamfetcher script')
  parser.add_argument('-a', '--all', action='store_false', dest='latest', help='Download all 500 last Maloney episodes. Does not work for the newest one or two, use -l instead.')
  parser.add_argument('-l', '--latest', action='store_true', dest="latest", help='Download the last 10 Maloney episodes, works also for the newest ones ;-).')
  parser.add_argument('-o', '--outdir', dest='outdir', help='Specify directory to store episodes to.')
  parser.add_argument('-u', '--uid', dest='uid', help='Download a single episode by providing SRF stream UID.')
  parser.add_argument('-j', '--json-data', dest='json', help='Use episode info from json file.')
  parser.add_argument('-w', '--write-json', action='store_true', dest="json_write", help='Store json data.')
  parser.add_argument('-v', '--verbose', action='store_true', dest='verbose', help='Enable verbose.')
  args = parser.parse_args()

  latest = args.latest

  maloney_downloader = MaloneyDownload(verbose=args.verbose, episode_json_file = args.json)

  if args.uid:
    maloney_downloader.process_maloney_episodes(None, args.outdir, uid=args.uid)
  elif latest:
    maloney_downloader.fetch_latest(outdir = args.outdir, uid=args.uid)
  else: # default setting
    maloney_downloader.fetch_all(outdir = args.outdir, uid=args.uid)

  if args.json_write:
    if os.path.isfile(args.json):
        with open(args.json, mode='w') as f:
            json = json.dumps(maloney_downloader.episode_data)
            f.write(json)
