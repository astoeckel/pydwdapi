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
import logging
logger = logging.getLogger("pydwdapi")


def download_newest(session, path, matcher, since=None):
    """
    Downloads either the newest files from a directory on an FTP server or the
    newest files since the given Unix timestamp. Returns an array of triples,
    with each triple containing the file modification date as UNIX timestamp,
    the file name and the binary content of the file. Oldest files are returned
    first, newest last.

    session: ftplib.FTP
        Instance of ftplib.FTP which is already loggeded into an FTP server.
    path: array
        Path from which the data should be downloaded.
    matcher: function
        Function which will be called with a filename. Should return True if the
        file is consistent with some naming scheme and considered for being
        downloaded, False otherwise.
    since: None or number
        If none, only the newest file from the directory which matches will be
        downloaded. Otherwise all files which are newer than the given Unix
        timestamp will be downloaded.
    """

    def parse_ftp_timestamp(s):
        """
        Converts a UTC FTP timestamp to Unix time.
        """
        from datetime import datetime, tzinfo, timedelta
        from time import mktime
        from calendar import timegm

        class UTC(tzinfo):
            def utcoffset(self, dt):
                return timedelta(0)

            def tzname(self, dt):
                return "UTC"

            def dst(self, dt):
                return timedelta(0)

        t = datetime.strptime(s, "%Y%m%d%H%M%S")
        t.replace(tzinfo=UTC())
        return timegm(t.timetuple())

    # Log the query
    logger.info("Querying FTP path " + path)

    # Fetch matching files from the directory
    files = []
    for e in session.mlsd(path):
        fn = e[0]
        ts = parse_ftp_timestamp(e[1]["modify"])
        if matcher(fn):
            files.append((ts, fn))
    files.sort()

    # Either select the newest file or the files which are older than "since"
    if (since is None) and (len(files) > 0):
        files = [files[-1]]
    else:
        files = list(filter(lambda x: x[0] > since, files))

    # Download the files in binary mode and append both date and content to the
    # result.
    res = []
    for entry in files:
        logger.info("Downloading " + path + entry[1] + " via FTP")
        buf = bytearray()
        session.retrbinary("RETR " + path + entry[1], buf.extend)
        res.append((entry[0], entry[1], buf))
    return res

################################################################################
# MAIN PROGRAM
################################################################################

if __name__ == '__main__':
    import sys
    import re

    if len(sys.argv) != 6 and len(sys.argv) != 7:
        sys.stderr.write(
            "Usage: ./ftp_util.py <FTP SERVER> <FTP USER> <FTP PASSWORD> <PATH> <REGEX> [<SINCE>]\n")
        sys.exit(1)

    with ftplib.FTP() as f:
        f.connect(sys.argv[1])
        f.login(sys.argv[2], sys.argv[3])
        since = None if len(sys.argv) == 6 else float(sys.argv[6])
        res = download_newest(f, sys.argv[4], re.compile(sys.argv[5]).match,
                              since)
    for e in res:
        print(e[0], e[1], len(e[2]))
        with open(e[1], "wb") as f:
            f.write(e[2])

