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
import time

from numbers import Number

from .altitude_data import AltitudeData
from .database import Database
from .interpolator import Interpolator
from .sources import Sources
from .stations import Stations

# Fetch the logger
import logging
logger = logging.getLogger("pydwdapi")

# Border contour used when plotting the data
# https://www.google.com/fusiontables/data?docid=1zn8cjdD6qlAFI7ALMEnwn89g50weLi1D-bAGSZw
GERMAN_BORDER = [
    [10.979445, 54.380556], [10.818537, 53.890055], [12.526945, 54.474161],
    [12.924166, 54.426943], [12.369722, 54.265001], [13.02389, 54.399721],
    [13.455832, 54.096109], [13.718332, 54.169718], [13.813055, 53.845278],
    [14.275629, 53.699068], [14.149168, 52.86278], [14.640276, 52.572496],
    [14.599443, 51.818605], [15.03639, 51.285555], [14.828333, 50.865831],
    [14.309721, 51.053606], [12.093706, 50.322535], [12.674444, 49.424997],
    [13.833612, 48.773607], [12.758333, 48.123888], [13.016668, 47.470278],
    [12.735556, 47.684168], [11.095556, 47.396112], [10.478056, 47.591944],
    [10.173334, 47.274721], [9.566725, 47.540453], [8.566111, 47.80694],
    [8.576422, 47.591372], [7.697226, 47.543329], [7.58827, 47.584482],
    [7.57889, 48.119722], [8.22608, 48.964418], [6.362169, 49.459391],
    [6.524446, 49.808611], [6.134417, 50.127848], [6.398207, 50.323175],
    [6.011801, 50.757273], [5.864721, 51.046106], [6.222223, 51.46583],
    [5.9625, 51.807779], [6.82889, 51.965555], [7.065557, 52.385828],
    [6.68889, 52.549166], [7.051668, 52.64361], [7.208364, 53.242807],
    [7.015554, 53.414721], [7.295835, 53.685274], [8.008333, 53.710001],
    [8.503054, 53.354166], [8.665556, 53.893885], [9.832499, 53.536386],
    [8.899721, 53.940828], [8.883612, 54.294168], [8.599443, 54.333887],
    [9.016943, 54.498331], [8.580549, 54.86788], [8.281111, 54.746943],
    [8.393332, 55.053057], [8.664545, 54.913095], [9.44536, 54.825403],
    [9.972776, 54.76111], [9.870279, 54.454439], [10.979445, 54.380556]
]

# Map used to define the human readable titles that should be plotted along with
# the map
MODALITY_TITLES = {
    "temperature": "Temperature",
    "humidity": "Humidity",
    "precipitation": "Precipation",
    "pressure": "Pressure",
    "wind_speed": "Wind speed",
    "wind_speed_max": "Wind speed (max. values)",
    "wind_direction": "Wind direction",
    "wind_direction_x": "Wind direction (x-component)",
    "wind_direction_y": "Wind direction (y-component)",
}

MODALITY_UNITS = {
    "temperature": "°C",
    "humidity": "%",
    "precipitation": "mm",
    "pressure": "hPa",
    "wind_speed": "m/s",
    "wind_speed_max": "m/s",
    "wind_direction": "°"
}

# Map used to define the value range used for coloring the maps
MODALITY_VRANGE = {
    "temperature": (-10, 40),
    "humidity": (0, 100),
    "precipitation": (0, 10),
    "pressure": (985, 1035),
    "wind_speed": (0, 40),
    "wind_speed_max": (0, 40),
    "wind_direction": (0, 360),
}

# Map defining the color scheme used when coloring the maps
MODALITY_COLORMAP = {"wind_direction": "hsv"}

class PyDWDApiException(Exception):
    pass


class PyDWDApi:
    """
    Class which provides cached access to the DWD data and interpolation
    facilities.
    """

    def __init__(self,
                 ftp_user="",
                 ftp_password="",
                 database="pydwdapi.db",
                 sources="./data/sources.xml",
                 stations="./data/stations.xml",
                 altitude_data="./data/etopo1_germany.asc.bz2",
                 max_observation_age=(4 * 60 * 60)):
        # Copy all the settings
        self.ftp_user = ftp_user
        self.ftp_password = ftp_password
        self.database_file = database
        self.sources = Sources(sources)
        self.stations = Stations(stations)
        self.altitude_data = AltitudeData()
        self.max_observation_age = max_observation_age

        # Initialize the interpolator cache
        self.interpolators = {}

        # Read the altitude data
        if type(altitude_data) is str and altitude_data:
            logger.info("Loading altitude data from " + altitude_data)
            if altitude_data.endswith(".bz2"):
                import bz2
                with bz2.BZ2File(altitude_data) as f:
                    self.altitude_data.read(f)
            else:
                with open(altitude_data, "rb") as f:
                    self.altitude_data.read(f)


    def update(self):
        if not self.ftp_user or not self.ftp_password:
            logger.warn("No username or password given, will not download new data")
            return
        with Database(self.database_file) as database:
            if self.sources.update(self.ftp_user, self.ftp_password,
                                   self.stations, database):
                self.interpolators = {}

    def _cleanup_caches(self):
        """
        Deletes the least used cached interpolators.
        """

        # Do nothing as long as the cache is not too full (TODO: Increase bound)
        if len(self.interpolators) < 1024:
            return

        # Find the elements with minimal usage and delete them
        min_usage = min(map(lambda x: x[1], self.interpolators.values()))
        del_keys = []
        for key, value in self.interpolators.items():
            if value[1] == min_usage:
                del_keys.append(key)
        for key in del_keys:
            del self.interpolators[key]

    def _update_caches(self, entry):
        """
        Increments the cache usage count for the given entry and decreases it
        for all other entries.
        """

        for key, value in self.interpolators.items():
            if key == entry:
                value[1] = value[1] + 1
            else:
                value[1] = value[1] - 1

    def _since_max_ts_pair(self, ts=None):
        ts = time.time() if ts is None else ts
        since = ts - self.max_observation_age
        return since, ts

    def interpolate_observations(self, modalities, lats, lons, alts, ts=None):
        """
        Returns interpolated data for the given observation modality and an
        array of latitudes, longitudes and altitudes.
        """
        # Converts the incomming data to arrays in case scalar values are given
        if type(modalities) is str:
            modalities = [modalities]
        if isinstance(lats, Number):
            lats = [lats]
        if isinstance(lons, Number):
            lons = [lons]
        if isinstance(alts, Number):
            alts = [alts]

        # Connect to the database, query all observations which fall into the
        # given time-range and track the latest timestamp used in the
        # computation
        res_ts = 0
        with Database(self.database_file) as database:
            res = []
            for modality in modalities:
                # Load the observations for this timestamp from the database
                since, max_ts = self._since_max_ts_pair(ts)
                observations = database.query_observations(modality, since,
                                                           max_ts)
                if (len(observations) == 0):
                    return None, 0.0
                latest_ts = max(map(lambda x: x[1], observations.values()))
                res_ts = max(res_ts, latest_ts)

                # Check whether an interpolator already exists for this
                # timestamp -- if not, create it
                cache_entry = (modality, latest_ts)
                if not cache_entry in self.interpolators:
                    self._cleanup_caches()
                    self.interpolators[cache_entry] = [Interpolator(
                        observations, self.stations, modality), 0]

                # Call the actual interpolation routine
                res.append(self.interpolators[cache_entry][0].interpolate(
                    lats, lons, alts))

                # Perform some cache management -- update the usage counts
                self._update_caches(cache_entry)
        return res, res_ts

    def query_stations(self, station_ids, ts=None):
        """
        Queries the current weather data for the given stations.
        """
        if isinstance(station_ids, Number):
            station_ids = [station_ids]

        res = {}
        with Database(self.database_file) as database:
            since, max_ts = self._since_max_ts_pair(ts)
            for station_id in station_ids:
                since, max_ts = self._since_max_ts_pair(ts)
                observations = database.query_observations_for_station(station_id, since, max_ts)
                for key, value in observations.items():
                    observations[key] = {
                        "value": observations[key][0],
                        "dt": observations[key][1],
                        "src": observations[key][2]
                    }
                if station_id in self.stations.ids:
                    coords = self.stations.coords[station_id]
                res[station_id] = {
                    "meta": {
                        "names":  self.stations.ids[station_id],
                        "lat": coords[0],
                        "lon": coords[1],
                        "alt": coords[2]
                    },
                    "data": observations
                }
        return res

    def query_interpolated(self, lat, lon, alt=None, ts=None):
        """
        Queries the interpolated data for all modalities at a certain location
        and returns a JSON structure containing the interpolated data. If no
        altitude is given, the altitude is loaded from the internal altitude
        data.
        """

        def query_interpolated_key(tar, key, key_tar=None):
            key_tar = key if key_tar is None else key_tar
            try:
                res, res_ts = self.interpolate_observations(key, lat, lon,
                                                           alt)
                if not res is None:
                    tar[key_tar] = round(res[0][0], 2)
                    response["dt"] = max(res_ts, response["dt"])
            except Exception:
                logger.exception("Exception in query_interpolated_key")
                pass

        # Try to find the altitude if none is given
        if alt is None:
            if self.altitude_data.in_bounds(lat, lon):
                alt = round(self.altitude_data.query(lat, lon)[0], 2)
            else:
                raise PyDWDApiException("No altitude data available for the given point, please specify explicitly!")

        # Assemble the response
        response = {
            "coord": {
                "lat": lat,
                "lon": lon,
                "alt": alt
            },
            "main": {},
            "wind": {},
            "dt": 0.0
        }
        query_interpolated_key(response["main"], "temperature", "temp")
        query_interpolated_key(response["main"], "pressure")
        query_interpolated_key(response["main"], "humidity")
        query_interpolated_key(response["main"], "precipitation")
        query_interpolated_key(response["wind"], "wind_speed", "speed")
        query_interpolated_key(response["wind"], "wind_speed_max", "max")
        query_interpolated_key(response["wind"], "wind_direction", "deg")
        return response

    def render_map(self,
                   modality,
                   extents=None,
                   ts=None,
                   resolution=256,
                   altitude=None,
                   bare=False):
        """
        Returns a Matplotlib figure which pictures the given quantity. Mainly
        for debugging purposes.
        """
        import matplotlib
        import matplotlib.pyplot as plt

        # Fetch the minimum/maximum latitude
        station_coords = np.array(list(self.stations.coords.values()))
        if extents is None:
            min_lat = np.min(station_coords[:, 0]) - 0.5
            max_lat = np.max(station_coords[:, 0]) + 0.5
            min_lon = np.min(station_coords[:, 1]) - 0.5
            max_lon = np.max(station_coords[:, 1]) + 0.5
        else:
            min_lat, max_lat, min_lon, max_lon = extents

        lats, lons = np.meshgrid(
            np.linspace(min_lat, max_lat, resolution),
            np.linspace(min_lon, max_lon, resolution))
        if altitude is None:
            alts = np.maximum(self.altitude_data.query(lats, lons), 0)
        else:
            alts = np.tile(altitude, (resolution, resolution))
        lats = np.reshape(lats, (resolution, resolution, 1))
        lons = np.reshape(lons, (resolution, resolution, 1))
        alts = np.reshape(alts, (resolution, resolution, 1))

        # Perform the actual interpolation
        zzs, res_ts = self.interpolate_observations(modality, lats, lons, alts,
                                            ts)
        if zzs is None:
            fig = plt.figure()
            fig.gca().annotate("No data available")
            return fig

        zzs = zzs[0][:, :, 0]

        # Fetch the currect value range for coloring the map
        if modality in MODALITY_VRANGE:
            vmin, vmax = MODALITY_VRANGE[modality]
        else:
            vmin, vmax = (np.min(zzs), np.max(zzs))
        cmap = (MODALITY_COLORMAP[modality] if modality in MODALITY_COLORMAP
                else "jet")

        # Plot the map itself
        fig = plt.figure(figsize=(10, 11.75))
        ax = fig.add_axes([0.0, 0.05, 1.0, 0.95])
        ax.imshow(zzs.T,
                  extent=[min_lon, max_lon, min_lat, max_lat],
                  origin="lower",
                  vmin=vmin,
                  vmax=vmax,
                  cmap=cmap)
        if bare:
            ax.set_axis_off()
            ax.get_xaxis().set_visible(False)
            ax.get_yaxis().set_visible(False)
        else:
            # Plot Germany's outline
            border = np.array(GERMAN_BORDER)
            ax.plot(border[:, 0], border[:, 1], '-', color="#dddddd", linewidth=5)

            # Plot used stations' locations and names
            for name, lat, lon, _, _ in self.stations.name_and_location_list():
                ax.plot(lon, lat, '+', markersize=10, color='k')
                ax.annotate(name,
                            xy=(lon, lat),
                            xytext=(0.2, 0.2),
                            textcoords='offset points')

            ax.set_xlabel("Longitude")
            ax.set_ylabel("Latitude")
            ax.set_title(time.strftime("%Y/%m/%d %H:%M", time.localtime(res_ts)))
            ax.set_xlim(min_lon, max_lon)
            ax.set_ylim(min_lat, max_lat)
            ax.set_aspect((max_lon - min_lon) / (max_lat - min_lat))

            # Plot the colorbar
            title = (MODALITY_TITLES[modality] if modality in MODALITY_TITLES else
                     modality)
            unit = (" [" + MODALITY_UNITS[
                modality] + "]" if modality in MODALITY_UNITS else "")
            ax_cbar = fig.add_axes([0.0, 0.0, 1.0, 0.025])
            cbar = matplotlib.colorbar.ColorbarBase(
                ax_cbar,
                orientation='horizontal',
                norm=matplotlib.colors.Normalize(vmin, vmax),
                cmap=cmap)
            cbar.set_label(title + unit)

        return fig

