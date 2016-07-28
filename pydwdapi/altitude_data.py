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

import numpy as np
import scipy.interpolate

class AltitudeData:
    """
    Simple class for reading and querying altitude data.
    """

    def __init__(self):
        self.meta = {
            "ncols": 0,
            "nrows": 0,
            "xllcorner": 0.0,
            "yllcorner": 0.0,
            "cellsize": 0.0
        }
        self.data = np.array(())
        self.xs = np.array(())
        self.ys = np.array(())

    def in_bounds(self, lat, lon):
        return (lat >= self.ys[0]) and (lat <= self.ys[-1]) and (
            lon >= self.xs[0]) and (lon <= self.xs[-1])

    def read(self, f):
        """
        Reads the altitude data from an ArcGIS ASCII Grid file. Such a file can
        be obtained from http://maps.ngdc.noaa.gov/viewers/wcs-client/
        """
        in_header = True
        i = 0
        for s in f.readlines():
            s = s.decode("ascii")
            if in_header:
                if s[0].isalpha():
                    key, value = map(lambda x: x.strip().lower(), s[:-1].split(
                        " ", 1))
                    if key in self.meta:
                        self.meta[key] = type(self.meta[key])(value)
                else:
                    in_header = False
                    self.data = np.zeros((self.meta["nrows"], self.meta[
                        "ncols"]))
            elif i < self.meta["nrows"]:
                row = list(map(float, filter(None, s[:-1].split(" "))))
                if len(row) == self.meta["ncols"]:
                    self.data[i] = row
                else:
                    raise Exception("Invalid row length")
                i = i + 1
            else:
                raise Exception("Invalid row count")

        # Flip the data -- origin is in the lower-left corner
        self.data = np.flipud(self.data)

        # Create the grid meta information
        ncols = self.meta["ncols"]
        nrows = self.meta["nrows"]
        xmin = self.meta["xllcorner"]
        ymin = self.meta["yllcorner"]
        xmax = xmin + self.meta["cellsize"] * (ncols - 1)
        ymax = ymin + self.meta["cellsize"] * (nrows - 1)
        self.xs = np.linspace(xmin, xmax, ncols)
        self.ys = np.linspace(ymin, ymax, nrows)

    def query(self, lats, lons):
        """
        Returns the altitude data for the given points stored in lats and lons.
        lats and lons must have the same shape and may for example be created by
        a call to numpy.meshgrid().
        """
        from numbers import Number

        if isinstance(lats, Number):
            lats = [lats]
        if isinstance(lons, Number):
            lons = [lons]
        return scipy.interpolate.interpn(
            (self.ys, self.xs), self.data, (lats, lons))

