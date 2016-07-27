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

from .html_table_parser import HTMLTableParser

import logging
logger = logging.getLogger("pydwdapi")

# Map from wind direction names to vectorial wind direction
DWD_DIRECTION_MAP = {
    "N": 360,
    "NO": 45,
    "O": 90,
    "SO": 135,
    "S": 180,
    "SW": 225,
    "W": 270,
    "NW": 315,
}

# Map from table column names to the record keys, including a potential scale
# factor
DWD_KEY_MAP = {
    "STATION": "station",
    "Station": "station",
    "LUFTD.": "pressure",
    "Luftd.": "pressure",
    "Luftdruck": "pressure",
    "TEMP.": "temperature",
    "Temp.": "temperature",
    "U%": "humidity",
    "RR1": "precipitation",
    "RR30": ("precipitation", 2.0),
    "DD": "wind_direction",
    "FF": ("wind_speed", 1.0 / 3.6),
    "FX": ("wind_speed_max", 1.0 / 3.6),
}

def parse(data, stations):
    # Parse the table from the resulting HTML and store the data in a numpy
    # array
    p = HTMLTableParser()
    p.feed(data)
    if (len(p.tables) == 0) or (len(p.tables[0]) == 0):
        return {}
    tbl = p.tables[0]

    # Fetch the table and create the result map

    # Translate the table header (row zero)
    header = []  # Translated header names
    scale = []  # Data scale factor
    for col in tbl[0]:
        if col in DWD_KEY_MAP:
            col = DWD_KEY_MAP[col]
            if type(col) is tuple:
                header.append(col[0])
                scale.append(col[1])
            else:
                header.append(col)
                scale.append(1.0)
        else:
            header.append(None)
            scale.append(None)

    # Parse the actual data
    res = {}
    for row in tbl[1:]:
        station_id = None
        values = {}
        for i, col in enumerate(row):
            if (i >= len(header)) or (header[i] is None):
                continue
            name = header[i]
            value = 0.0
            if name == "station":
                if col in stations.names:
                    station_id = stations.names[col]
                else:
                    logger.warn("Unmatched station \"" + col +"\"")
            elif name == "wind_direction":
                if col in DWD_DIRECTION_MAP:
                    values["wind_direction"] = DWD_DIRECTION_MAP[col]
            else:
                try:
                    values[name] = float(col) * scale[i]
                except Exception:
                    pass
        if not station_id is None:
            for key in values.keys():
                if not key in res:
                    res[key] = []
                res[key].append((station_id, values[key]))
    return res

################################################################################
# MAIN PROGRAM
################################################################################

if __name__ == '__main__':
    from stations import Stations
    import sys
    import json

    logging.basicConfig(
        stream=sys.stderr,
        level=logging.DEBUG,
        format='%(filename)s:%(lineno)s %(levelname)s:%(message)s')

    if len(sys.argv) != 3:
        sys.stderr.write(
            "Usage: ./html_dwd_observation_parser.py <FILE> <STATIONS FILE>\n")
        sys.exit(1)

    stations = Stations(sys.argv[2])
    with open(sys.argv[1]) as f:
        json.dump(parse(f.read(), stations), sys.stdout, indent=4, sort_keys=True)


