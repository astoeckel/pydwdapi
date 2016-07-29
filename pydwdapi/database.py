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

import sqlite3

# Table used to store the individual observations from all stations
TABLE_SCHEMA_OBSERVATIONS = """CREATE TABLE observations (
    timestamp real,
    value real,
    modality int,
    station int,
    source int
);"""

# Table use to store the time at which the latest date was downloaded from which
# source
TABLE_SCHEMA_SOURCE_UPDATES = """CREATE TABLE source_updates (
    source int,
    timestamp real,
    PRIMARY KEY(source)
);"""

# Map containing the table names and the corresponding schemas -- used by the
# constructor of the Database class to create non-existing tables
TABLE_SCHEMAS = {
    "observations": TABLE_SCHEMA_OBSERVATIONS,
    "source_updates": TABLE_SCHEMA_SOURCE_UPDATES
}

# Used to update the source time
SQL_SET_SOURCE_TIME = "INSERT OR REPLACE INTO source_updates VALUES (?, ?)"

# Used to get the source time
SQL_GET_SOURCE_TIME = "SELECT timestamp FROM source_updates WHERE source=?"

# SQL used to store observations in the database
SQL_STORE_OBSERVATION = "INSERT INTO observations VALUES (?, ?, ?, ?, ?)"

# SQL used to retrieve the latest observations
SQL_QUERY_OBSERVATIONS = "SELECT value, timestamp, station, source FROM observations WHERE modality = ? AND timestamp > ? AND timestamp <= ? ORDER BY timestamp DESC"

# SQL used to retrieve the latest observations
SQL_QUERY_STATION_OBSERVATIONS = "SELECT value, timestamp, modality, source FROM observations WHERE station = ? AND timestamp > ? AND timestamp <= ? ORDER BY timestamp DESC"

# Map used by the Database class to map between the individual modality names
# and the id which is actually stored in the database
MODALITY_MAP = {
    "temperature": 100,
    "pressure": 200,
    "humidity": 300,
    "wind_speed": 400,
    "wind_speed_max": 500,
    "wind_direction": 600,
    "precipitation": 700
}
MODALITY_ID_MAP = {v: k for k, v in MODALITY_MAP.items()}


class Database:
    """
    The Database class persistently stores all observations read from the DWD
    servers. It provides functions for querying and inserting new data points,
    providing an abstraction layer over the underlying SQL database.
    """

    def __init__(self, filename):
        """
        Connects to the databse file specifed by "filename" and creates tables
        which do not yet exist in the database.
        """

        # Connect to the database
        self.conn = sqlite3.connect(filename)

        # Make sure that all tables exist
        tables = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type=\"table\"").fetchall()
        tables = set(map(lambda x: x[0], tables))
        for table in TABLE_SCHEMAS:
            if not table in tables:
                self.conn.execute(TABLE_SCHEMAS[table])

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.conn.commit()
        self.conn.close()

    def set_source_time(self, source_id, ts):
        """
        Sets the last source update time to the given timestamp.

        source_id : int
            id of the source for which the timestamp should be stored
        ts : float
            timestamp that should be stored for this source
        """
        self.conn.execute(SQL_SET_SOURCE_TIME, (int(source_id), float(ts)))

    def get_source_time(self, source_id):
        """
        Returns a previously stored timestamp for the source with the given id
        or 0.0 if no timestamp has been stored yet.

        source_id : int
            id of the source for which the timestamp should be returned.
        """
        res = self.conn.execute(SQL_GET_SOURCE_TIME,
                                (int(source_id), )).fetchall()
        if len(res) == 1:
            return float(res[0][0])
        return 0.0

    def store_observation(self, ts, value, modality, station_id, source_id):
        """
        Stores a single observation for a single modality in the database.

        ts : float
            timestamp of the observation
        value : float
            value that has been measured
        modality : string
            name of the modality for which the value should be returned
        station_id : int
            id of the station at which the value was measured
        source_id : int
            id of the data source
        """
        self.conn.execute(SQL_STORE_OBSERVATION,
                          (float(ts), float(value), MODALITY_MAP[modality],
                           int(station_id), int(source_id)))

    def query_observations(self, modality, since=0.0, max_ts=1e20):
        """
        Queries all observations for the given modality which are not older than
        a given timestamp.

        modality : string
            name of the modality for which the value should be returned
        since : float
            lower bound (exclusive) for the observation timestamp
        max_ts : float
            upper bound (inclusive) for the observation timestamp
        """
        response = self.conn.execute(
            SQL_QUERY_OBSERVATIONS,
            (MODALITY_MAP[modality], since, max_ts)).fetchall()
        res = {}
        for row in response:
            station_id = row[2]
            if not station_id in res:
                res[station_id] = (row[0], row[1], row[3])
        return res

    def query_observations_for_station(self, station_id, since=0.0, max_ts=1e20):
        """
        Queries all available observations for the given station id up to the
        given timestamp.
        """
        response = self.conn.execute(
            SQL_QUERY_STATION_OBSERVATIONS,
            (station_id, since, max_ts)).fetchall()
        res = {}
        for row in response:
            modality_id = row[2]
            if modality_id in MODALITY_ID_MAP:
                modality = MODALITY_ID_MAP[modality_id]
                if not modality in res:
                    res[modality] = (row[0], row[1], row[3])
        return res

