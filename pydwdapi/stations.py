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

import xml.etree.ElementTree


class Stations:
    """
    Class responsible for mapping station IDs to coordinates and station names
    and station names to IDs. Reads the station configuration from the
    stations.xml file.
    """

    def __init__(self, config_file):
        self.ids = {}
        self.names = {}
        self.coords = {}

        tree = xml.etree.ElementTree.parse(config_file)
        for child in tree.getroot():
            if child.tag == "station":
                # Read the attributes
                sname = child.attrib["name"]
                sid = int(child.attrib["id"])

                # Store the mapping from id to possible names
                if sid in self.ids:
                    self.ids[sid].append(sname)
                else:
                    self.ids[sid] = [sname]

                # Store a mapping from the name to the id
                if sname in self.names:
                    raise Exception("Duplicate name \"" + sname + "\"")
                self.names[sname] = sid

                # Store a mapping from the id to the coordinates -- coordinates
                # must not be present
                if ("lat" in child.attrib) and ("lon" in child.attrib) and (
                        "alt" in child.attrib):
                    slat = float(child.attrib["lat"])
                    slon = float(child.attrib["lon"])
                    salt = float(child.attrib["alt"])
                    self.coords[sid] = (slat, slon, salt)

        # Make sure each id has one coordinate pair
        for sid in self.ids.keys():
            if not sid in self.coords:
                raise Exception("No coordinates specified for station " + str(
                    sid))

    def name_and_location_list(self):
        """
        Returns a list containing the name and location of each station. The
        shortes available name is returned.
        """
        res = []
        for sid in self.ids.keys():
            sname = sorted(self.ids[sid], key=lambda x: len(x))[0]
            slat, slon, salt = self.coords[sid]
            res.append((sname, slat, slon, salt))
        return res

################################################################################
# MAIN PROGRAM
################################################################################

if __name__ == '__main__':
    import sys
    import json

    if len(sys.argv) != 2:
        sys.stderr.write("Usage: ./stations.py <STATIONS XML FILE>\n")
        sys.exit(1)

    stations = Stations(sys.argv[1])
    json.dump(
        {
            "ids": stations.ids,
            "names": stations.names,
            "coords": stations.coords
        },
        sys.stdout,
        sort_keys=True,
        indent=4)

