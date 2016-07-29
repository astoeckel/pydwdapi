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

import argparse
import sys

# Fetch the logger
import logging
logger = logging.getLogger("pydwdapi")

if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description='Renders a map with interpolated weather data')
    parser.add_argument('--user',
                        dest='user',
                        type=str,
                        help='DWD FTP Username')
    parser.add_argument('--password',
                        dest='password',
                        type=str,
                        help='DWD FTP Password')
    parser.add_argument('--modality',
                        dest='modality',
                        required=True,
                        type=str,
                        help='Modality to plot.')
    parser.add_argument('--bare',
                        dest='bare',
                        action="store_true",
                        default=False,
                        help='If set, does not plot any descriptive overlay')
    parser.add_argument('--resolution',
                        dest='resolution',
                        type=int,
                        default=256,
                        help='Map resolution in pixels')
    parser.add_argument('--format',
                        dest='format',
                        type=str,
                        default="pdf",
                        help='Output format')
    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        stream=sys.stderr,
        level=logging.DEBUG,
        format='%(filename)s:%(lineno)s %(levelname)s:%(message)s')

    # Map extents -- min_lat, max_lat, min_lon, max_lon
    extents = [47.0, 55.1, 5.8, 15.1]

    # Create the API and plot the map
    import pydwdapi
    api = pydwdapi.PyDWDApi(args.user, args.password)
    api.update()
    api.render_map(args.modality,
                   extents,
                   resolution=args.resolution,
                   bare=args.bare).savefig(
                       args.modality + "." + args.format,
                       format=args.format,
                       bbox_inches='tight',
                       pad_inches=(0.0 if args.bare else 0.1))

