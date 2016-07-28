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
            "Usage: ./render.py <DWD FTP USER> <DWD FTP PASSWORD> <MODALITY>\n")
        sys.exit(1)

    logging.basicConfig(
        stream=sys.stderr,
        level=logging.DEBUG,
        format='%(filename)s:%(lineno)s %(levelname)s:%(message)s')

    # Map extents -- min_lat, max_lat, min_lon, max_lon
    extents = [47.0, 55.1, 5.8, 15.1]

    # Create the API and plot the map
    import pydwdapi
    api = pydwdapi.PyDWDApi(sys.argv[1], sys.argv[2])
    api.update()
    api.render_map(sys.argv[3],
                   extents,
                   resolution=256).savefig(sys.argv[3] + ".pdf",
                                           format='pdf',
                                           bbox_inches='tight')

