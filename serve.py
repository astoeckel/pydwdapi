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

import sys

# Fetch the logger
import logging
logger = logging.getLogger("pydwdapi")

if __name__ == '__main__':
    if len(sys.argv) != 4:
        sys.stderr.write(
            "Usage: ./serve.py <DWD FTP USER> <DWD FTP PASSWORD> <PORT>\n")
        sys.exit(1)

    # Setup logging
    logging.basicConfig(
        stream=sys.stderr,
        level=logging.INFO,
        format='%(filename)s:%(lineno)s %(levelname)s:%(message)s')

    # Create the API instance
    import pydwdapi
    import pydwdapi.server
    api = pydwdapi.PyDWDApi(sys.argv[1], sys.argv[2])

    # Start the server
    logger.info("Starting HTTP server...")
    httpd = pydwdapi.server.create_server(api, int(sys.argv[3]))

    # Handle the requests until CTRL+C is pressed
    logger.info("Listening on port " + sys.argv[3])
    try:
        while True:
            httpd.handle_request()
    except KeyboardInterrupt:
        logger.info("Stopping server...")
        pass
    logger.info("Done.")

