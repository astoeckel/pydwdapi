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

import http.server
import json
import urllib.parse
import socketserver

import logging
logger = logging.getLogger("pydwdapi")


def create_server(api, port=8080, interface="127.0.0.1"):
    """
    Creates a new HTTP server instance which serves api requests.

    api : PyDWDApi
        Instance of the PyDWDApi class from which the data is read.
    port : int
        Port number on which the HTTP server should listen.
    interface : str
        Local ip address of the network interface the HTTP server should listen
        on.
    """

    class Handler(http.server.BaseHTTPRequestHandler):
        def _send_json(self, http_code, obj):
            # Make sure only one response is sent
            if self.done:
                return
            self.done = True

            # Write the response header, including the error code
            self.send_response(http_code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()

            # Write the file
            self.wfile.write(
                json.dumps(obj, indent=2, sort_keys=True).encode("utf-8"))

        def _error(self, http_code, msg):
            self._send_json(http_code, {"error": msg})

        def _handle_api_1_0_weather(self, o, q):
            """
            Handles queries to the /api/1.0/weather url.
            """
            q = urllib.parse.parse_qs(o.query, keep_blank_values=True)
            try:
                lat = float(q["lat"][0])
                lon = float(q["lon"][0])
                alt = float(q["alt"][0]) if "alt" in q else None
            except Exception:
                logger.exception("Error while parsing the arguments")
                self._error(400, "Invalid query")
                return

            # Query the weather data and fetch the response
            api.update()
            return api.query_interpolated(lat, lon, alt)

        def _handle_api_1_0_station(self, o, q):
            """
            Handles queries to the /api/1.0/station url.
            """
            try:
                if ("id" in q) == ("ids" in q):
                    self._error(400, "Either id or ids must be specified")
                    return
                if "id" in q:
                    station_ids = map(int, q["id"])
                else:
                    station_ids = map(int, q["ids"][0].split(","))
                ts = float(q["ts"]) if "ts" in q else None
            except Exception:
                logger.exception("Error while parsing the arguments")
                self._error(400, "Invalid query")
                return

            # Query the weather data and fetch the response
            api.update()
            return api.query_stations(station_ids, ts)

        def _handle_api_1_0_stations(self, o, q):
            """
            Handles queries to the /api/1.0/stations url.
            """
            return sorted(api.stations.name_and_location_list())

        def do_GET(self):
            """
            Responds to a user's GET request. This function implements the basic
            routing and error handling.
            """
            self.done = False
            try:
                # Make sure the URL is correct
                o = urllib.parse.urlparse(self.path)
                q = urllib.parse.parse_qs(o.query, keep_blank_values=True)
                if o.path == "/api/1.0/weather":
                    response = self._handle_api_1_0_weather(o, q)
                elif o.path == "/api/1.0/station":
                    response = self._handle_api_1_0_station(o, q)
                elif o.path == "/api/1.0/stations":
                    response = self._handle_api_1_0_stations(o, q)
                else:
                    self._error(404,
                                "Requested file " + o.path + " not found!")
                    return
            except:
                logger.exception("Error while processing the request")
                self._error(500, "Internal error")
                return

            self._send_json(200, response)

    class Server(socketserver.TCPServer):
        allow_reuse_address = True
        timeout = 60.0

        def handle_timeout(self):
            try:
                api.update()
            except Exception:
                logger.exception("Exception while updating the data")

    # Create the server and return it
    httpd = Server((interface, port), Handler)
    return httpd

