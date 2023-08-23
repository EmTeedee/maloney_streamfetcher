Maloney Streamfetcher
=====================

This script is a fork of tschinz' maloney fetcher: https://github.com/tschinz/maloney_streamfetcher. All credits to him!

dirtbit added Python 2.7 support, some other improvements and updated for a new SRF homepage: https://github.com/dirtbit/maloney_streamfetcher

Update to Python 3, fixes for new SRF homepage, persistent metadata and tool to rename files from other sources by EmTeedee.

This Python script lets you download the latest Philip Maloney Episodes from the [SRF Website](https://www.srf.ch/audio/maloney).


Requirements
---
* ``Python 3``
  * ``pycurl``
  * ``mutagen``

On a Debian based Linux:
```bash
sudo apt-get install python3 python3-pycurl python3-mutagen
```

Features
---
* Lets you download all current episodes as MP3
* Lets you download the last 500 episodes as MP3
* Lets you download an episode with a known UID as MP3
* Creates ID3 tags for the episode
* Checks for duplicated episodes

Usage
---

```bash
./maloney_streamfetcher.py -h

Usage: maloney_streamfetcher.py [options]

Options:
  -h, --help            show this help message and exit
  -a, --all             Download all 500 last Maloney episodes. Does not work
                        for the newest one or two, use -l instead.
  -l, --latest          Download the last 10 Maloney episodes, works also for
                        the newest ones ;-).
  -o OUTDIR, --outdir=OUTDIR
                        Specify directory to store episodes to.
  -u UID, --uid=UID     Download a single episode by providing SRF stream UID.
  -j JSON, --json-data JSON
                        Use episode info from json file.
  -w, --write-json      Store json data.
  -v, --verbose         Enable verbose.
```

* Execute script
```bash
./maloney_streamfetcher.py -l -o /location/to/musicfiles
```

* Use Cronjob for automatically execute the script every Monday at 24:00.
```bash
crontab -e
```
```bash
0 * * * 1 /location/to/maloney_streamfetcher.py -l -o /location/to/musicfiles
```

![Maloney Philip](http://www.srfcdn.ch/radio/modules/dynimages/624/drs-3/maloney/2012/142280.maloney1.jpg)


Version Log
---
- `v1.3, Python 3`
  * REMOVE: RTMP support
  * CHG: persistent metadata
  * CHG: SRD homepage update
  * CHG: filename format
  * ADD: rename utility

- `v1.2, only for Python 2.7`
  * ADD: if possible try to avoid RTMP, download mp3 via HTTPS instead
  * CHG: updated broken ID3 data source --> fixed URL, using JSON now
  * CHG: SRF forces to use https --> using certifi in curl

- `v1.1`
  * ADD: Using Optparse
  * ADD: replace mid3v2 with mid3v2.py
  * CHG: Merged `maloney_streamfetcher.py` and `maloney_streamfetcher_all.py`
- `v1.0`
  * Initial Release

Thanks
---
  * All credits to tschinz! (https://github.com/tschinz/maloney_streamfetcher)
  * This work was inspired by [Stream Fetcher](https://www.ruinelli.ch/philip-maloney-stream-fetcher) of Ruinelli, a big thanks to him.
  * Thanks for `v1.1` extension to @dirtbit

Licensing
---
This document is under the [CC BY-NC-ND 3-0 License, Attribution-NonCommercial-NoDerivs 3.0 Unported](http://creativecommons.org/licenses/by-nc-nd/3.0/). Use this script at your own risc!

The Philip Maloney streams are copyright by [Roger Graf](www.rogergraf.ch). The streams are provided by [SRF](www.srf.ch/audio/maloney). It is against the law to distribute the generated mp3 files!
