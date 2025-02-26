import pandas as pd
from geopy.geocoders import Nominatim

known = pd.read_pickle('./data/known.pkl')

# Geocode

postal = known['destination_postal']
postal = postal.to_list()

geolocator = Nominatim(user_agent="app")

geocoded_locations = []

for postal in postal:
    try:
        location = geolocator.geocode(postal, timeout=10)
    except Exception as e:
        pass
    row = [postal, location.latitude, location.longitude]
    geocoded_locations.append(row)
    print(row)

geocoded_locations = pd.DataFrame(geocoded_locations, columns = ['destination_postal', 'lat', 'lon'])
geocoded_locations.to_pickle('./data/geocoded_known.pkl')