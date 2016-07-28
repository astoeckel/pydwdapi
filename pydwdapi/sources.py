#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#   Simple REST HTTP Weather Server using DWD weather data for Germany
#   Copyright (C) 2016 Andreas Stöckel
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

import ftplib
import time
import re
import xml.etree.ElementTree

from . import ftp_util
from . import html_dwd_observation_parser

# Fetch the logger
import logging
logger = logging.getLogger("pydwdapi")

# FTP server URL
DWD_SERVER = "ftp-outgoing2.dwd.de"

# Minimum timeout which has to pass after a source is querried again
MIN_BACKOFF = 60.0

# Maximum timeout which has to pass after a source is querried again
MAX_BACKOFF = 600.0


class Sources:
    """
    Class responsible for keeping the data stored in the data-base up to date
    by downloading the raw data from the corresponding servers.
    """

    def __init__(self, config_file):
        self.sources = {}
        self.backoff = {}

        tree = xml.etree.ElementTree.parse(config_file)
        for source in tree.getroot():
            if source.tag == "source":
                self.sources[int(source.attrib["id"])] = {
                    "type": source.find("type").text,
                    "path": source.find("path").text,
                    "matcher": source.find("matcher").text,
                    "timeout": float(source.find("timeout").text)
                }

    def update(self, ftp_user, ftp_password, stations, database):
        # Lazily connect to the server
        connected = {"value": False}

        def connect(f):
            if not connected["value"]:
                logger.info("Connecting to ftp://" + ftp_user + "@" +
                            DWD_SERVER + "/")
                f.connect(DWD_SERVER)
                f.login(ftp_user, ftp_password)
            connected["value"] = True

        has_changes = False
        with ftplib.FTP() as f:
            # Iterate over all sources an check whether a source needs to be
            # updated
            now = time.time()
            for source_id, source in self.sources.items():
                source_time = database.get_source_time(source_id)
                timeout = source["timeout"]
                if now - source_time > timeout:
                    # Make sure we are connected to the server and download the
                    # newest files
                    connect(f)
                    res = ftp_util.download_newest(
                        f, source["path"], re.compile(source["matcher"]).match)
                    if (len(res) == 0):
                        logger.warn("Failed to download data from " + source[
                            "path"])

                    # Check whether the data was actually updated
                    modified, filename, data = res[0]
                    if modified > source_time:
                        # Parse the data and store the results in the database
                        try:
                            parsed = html_dwd_observation_parser.parse(
                                str(data, "latin-1"), stations)
                            for modality, elems in parsed.items():
                                logger.debug("Writing " + str(len(
                                    elems)) + " value(s) for modality " +
                                             modality + " from source " +
                                             source["path"])
                                for station_id, value in elems:
                                    database.store_observation(
                                        modified, value, modality, station_id,
                                        source_id)
                                    has_changes = True
                            database.set_source_time(source_id, modified)
                            self.backoff[source_id] = 0  # Reset the backoff
                            continue
                        except Exception:
                            logger.exception(
                                "Exception while parsing the observation data")

                    # There was no update -- try again in a few minutes with
                    # exponential backoff (min 1-10 minute wait time)
                    if not source_id in self.backoff:
                        self.backoff[source_id] = 0.0
                    self.backoff[source_id] = min(MAX_BACKOFF, max(
                        MIN_BACKOFF, self.backoff[source_id] * 1.5))
                    database.set_source_time(
                        source_id, now - timeout + self.backoff[source_id])
                    logger.debug("No update for " + source["path"] +
                                 ", trying again in " + str(
                                     int(self.backoff[source_id])) + "s")
                else:
                    logger.debug("Source " + source["path"] +
                                 " is up to date, next update in " + str(
                                     int(timeout - now + source_time)) + "s")
        return has_changes

################################################################################
# MAIN PROGRAM
################################################################################

if __name__ == '__main__':
    import sys
    import json
    from database import Database
    from stations import Stations

    logging.basicConfig(
        stream=sys.stderr,
        level=logging.DEBUG,
        format='%(filename)s:%(lineno)s %(levelname)s:%(message)s')

    if len(sys.argv) != 6:
        sys.stderr.write(
            "Usage: ./sources.py <SOURCES XML FILE> <STATIONS XML FILE> <DATABASE FILE> <FTP USER> <FTP PASSWORD>\n")
        sys.exit(1)

    # Create all necessary objects
    sources = Sources(sys.argv[1])
    stations = Stations(sys.argv[2])
    with Database(sys.argv[3]) as database:
        # Perform a full database update
        sources.update(sys.argv[4], sys.argv[5], stations, database)

