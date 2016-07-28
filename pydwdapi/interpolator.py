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

import math
import numpy as np
import scipy.interpolate
import time

# Weight of the altitude dimension for the individual modalities
MODALITY_ALTITUDE_WEIGHT = {
    "temperature": 100.0,
    "humidity": 100.0,
    "precipitation": 10.0,
    "pressure": 0.0,
    "wind_speed": 50.0,
    "wind_speed_max": 50.0,
    "wind_direction": 10.0
}

# Number of dimensions used when interpolating a modality
MODALITY_DIMENSIONS = {"wind_direction": 2}

MODALITY_NO_CLAMP = set("wind_direction")


def haversine(lat1, lon1, lat2, lon2):
    """
    Geodesic distance between two latitude/longitude pairs.
    """
    dLat = lat2 - lat1
    dLon = lon2 - lon1
    a = (np.sin(dLat * 0.5)**2) + (np.cos(lat1) * np.cos(lat2) * np.sin(
        dLon * 0.5)**2)
    return 2.0 * np.arctan2(np.sqrt(a),
                            np.sqrt(1.0 - a)) * 6371.0  # Distance in km


class Norm:
    """
    The norm class is used to calculate geodesic, altitude-weight adjusted
    distances between locations.
    """

    def __init__(self, altitude_weight):
        self.altitude_weight = altitude_weight

    def __call__(self, x1, x2):
        # Fetch the required dimension vectors
        lats1 = np.radians(x1[0, :, :])
        lats2 = np.radians(x2[0, :, :])
        lons1 = np.radians(x1[1, :, :])
        lons2 = np.radians(x2[1, :, :])
        alts1 = x1[2, :, :]
        alts2 = x2[2, :, :]

        # Calculate the distances
        d_ground = haversine(lats1, lons1, lats2, lons2)
        d_alt = (alts1 - alts2) / 1000.0 * self.altitude_weight
        return np.sqrt(d_ground**2 + d_alt**2)


class Interpolator:
    """
    The interpolator class is responsible for sampling the weather data at
    locations between the actual weather stations. Upon construction, it
    calculates a set of radial basis functions which represent the weather
    values as a mixture model. The class then allows to sample at arbitrary
    locations (latitude, longitude, altitude) from the function.
    """

    def __init__(self, observations, stations, modality=""):
        """
        Constructor of the Interpolator, creates the radial basis functions from
        which the "interpolate" method will sample.

        observations : map
            Map from station_id to tuples (value, timestamp, source_id), only
            the value is accessed
        stations : Stations object
            Instance of the Stations class, used to translate station ids to
            coordinates via stations.coords.
        modality : str
            Modality of the underlying values -- some modalities require special
            treatment, such as the wind_direction, which is split into a x- and
            y-component which are treated independently.
        """

        # Fetch the minimum/maximum value
        self.min_value = min(map(lambda x: x[0], observations.values()))
        self.max_value = max(map(lambda x: x[0], observations.values()))

        # Fetch the number of dimensions necessary to represent the value
        dims = (MODALITY_DIMENSIONS[modality]
                if modality in MODALITY_DIMENSIONS else 1)

        # Write the observations into a NumPy array containg the value and
        # the latitude/longitude/altitude, if necessary expand the values
        # into multiple dimensions
        self.modality = modality
        self.tbl = np.zeros((len(observations), 3 + dims))
        i = 0
        for station_id, station_data in observations.items():
            if not station_id in stations.coords:
                continue
            lat, lon, alt = stations.coords[station_id]
            value = self._split_value(station_data[0])
            self.tbl[i] = (lat, lon, alt) + value
            i = i + 1
        if i == 0:
            raise Exception("No valid stations found!")
        self.tbl = self.tbl[0:i]

        # Read the altitude weight factor for this modality
        altitude_weight = (MODALITY_ALTITUDE_WEIGHT[modality]
                           if modality in MODALITY_ALTITUDE_WEIGHT else 1.0)

        # Calculate the radial basis functions for each dimension
        self.rbfis = []
        for dim in range(dims):
            obs_lats = self.tbl[:, 0]
            obs_lons = self.tbl[:, 1]
            obs_alts = self.tbl[:, 2]
            obs_values = self.tbl[:, 3 + dim]
            self.rbfis.append(
                scipy.interpolate.Rbf(obs_lats,
                                      obs_lons,
                                      obs_alts,
                                      obs_values,
                                      function="linear",
                                      norm=Norm(altitude_weight)))

    def _split_value(self, v):
        """
        Splits the given value into multiple dimensions -- for example, wind
        direction is split into an x- and y-dimension, weather status codes are
        split into multiple dimensions for rain, snow, sand, wind, clouds, fog,
        etc.
        """
        if self.modality == "wind_direction":
            return (math.cos(np.radians(v)), math.sin(np.radians(v)))
        else:
            return (v, )

    def _join_values(self, vs):
        if self.modality == "wind_direction":
            return np.arctan2(vs[1], vs[0]) * 180.0 / math.pi + 180.0
        else:
            return vs[0]

    def interpolate(self, lats, lons, alts):
        """
        Returns interpolated data for the given observation modality and an
        array of latitudes, longitudes and altitudes.
        """

        # Perform the actual interpolation for each value dimension
        vs = []
        for rbfi in self.rbfis:
            vs.append(rbfi(lats, lons, alts))

        # Join the dimensions into a single value
        res = self._join_values(vs)

        # Clamp the values to the naturally occuring values
        if not self.modality in MODALITY_NO_CLAMP:
            res = np.maximum(np.minimum(res, self.max_value), self.min_value)
        return res

