PyDWDApi
========

![Temperature map example](https://raw.githubusercontent.com/astoeckel/pydwdapi/master/docs/example_temperature.png)

*PyDWDApi* is a simple HTTP REST server which allows interpolated access to
weather data made available by the German Weather Service (Deutscher
Wetterdienst, DWD). Only yields sane results for locations within Germany.

Usage
-----

This program requires Python 3, including the Python packages `numpy`, `scipy`
and optionally `matplotlib`. You will also need a free GDS-FTP account which you
can request [here](http://www.dwd.de/DE/fachnutzer/dienstleister/grundversorgung/grundversorgung_node.html).

The HTTP server can be started using the following command line:
```bash
./pydwdapi <DWD FTP USER> <DWD FTP PASSWORD> <HTTP PORT>
```
Where the user name and password are your GDS-FTP account data. Note that the
HTTP server will only listen on localhost. If you intend to publish the service
on the internet, you should consider using a reverse proxy such as *nginx*.

You can now query the weather data from HTTP using the following URL:
```
http://localhost:<PORT>/api/1.0/weather?lat=<LATITUDE>&lon=<LONGITUDE>&alt=<ALTITUDE>
```
The parameters have the following meaning:

* _lat_: Latitude in degrees
* _lon_: Longitude in degrees
* _alt_: Altitude in meters above sea level

An example result might be the following (some keys may not be available at all
times):
```javascript
{
  "dt": 1469394848, // Unix timestamp of the modification date
  "coord": {
    "lon": 8.27, // Longitude
    "alt": 89, // Altitude in meters above sea level
    "lat": 50 // Latitude
  },
  "main": {
    "pressure": 1016.1965323811, // Pressure in hPa
    "humidity": 92.38411403302, // Humidity in percent
    "precipitation": 0.56107324500611, // Percipation mm/m^2 in one hour
    "temp": 21.02904617292 // Current temperature in celsius
  },
  "wind": {
    "deg": 124.42090068447, // Wind direction
    "speed": 1.609026767211, // Speed in m/s (avg. over 10 min)
    "max": 2.3990260798389 // Maximum wind speed in m/s (in 10 min)
  }
}
```

An instance of the server is publicly available at
```
https://somweyr.de/pydwdapi/api/1.0/weather?lat=<LATITUDE>&lon=<LONGITUDE>&alt=<ALTITUDE>
```
Please use this URL for testing purposes only.

Altitude data
-------------

The included altitude data for Germany was downloaded from the National Oceanic and
Atmospheric Administration (NOAA) of the National Centers for Environmental Information.
You can download your own data from [here](http://maps.ngdc.noaa.gov/viewers/wcs-client/).
Make sure to select the `ETIOI1 (ice)` layer and `ArcGIS ASCII Grid` as output format.


How it works
------------

### Step 1: Querying
The program is extremely simple. When a request is received, it downloads the
newest station data from the DWD GDS FTP server or reads it from a cache.

### Step 2: Coordinate association
The stations are then associated with their coordinates using a hand-crafted
table. The resulting compound data is stored in a NumPy structured array.

### Step 3: Interpolation
The individual modalities are interpolated for the given coordinate triple using
the SciPy radial basis function interpolator. A non-euclidean norm is used to
make sure that a spherical distance is used for the station-to-station distance.

Furthermore a higher weight is used for altitudinal differences, as these have a
potentially higher impact on weather data. E.g. data from the Zugspitze would
influence the data in the entirety of south Germany if the altitude would not
be weighted correctly.

ToDo
----

This project is not yet fully finished. The following features are planned:

* Interpolation of the general weather status code (clear, cloudy, rain, ...)
* Pretty map generation (currently only implemented for debugging)
* Make sure response JSON is compatible with `openweathermap`
* Automatically read altitude from the altitude map if not given in the query
* Perform some cross-validation experiments


Disclaimer
----------

This project was a little Sunday afternoon fun project. **Do not** use the
resulting data for any serious application. Interpolation between sparse weather
station data **may go terribly wrong**. This program is in no way affiliated
with or endorsed by the DWD.


License
-------

```
Simple REST HTTP Weather Server using DWD weather data for Germany
Copyright (C) 2016 Andreas Stöckel

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
```
