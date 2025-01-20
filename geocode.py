import pandas as pd
from geopy.geocoders import Nominatim

# Import Data

known_lanes = pd.read_csv('./data/iwdi-known-lanes.csv')
all_destinations = pd.read_csv('./data/all-destinations.csv')

# Prep Data

origin_lanes = known_lanes['Origin Postal'].astype(str)
origin_lanes = origin_lanes.drop_duplicates().tolist()
destination_lanes = all_destinations.loc[all_destinations['Destination Country'] == 'US']
destination_lanes = destination_lanes['Destination Postal']
destination_lanes = destination_lanes.tolist()
combined_locations = origin_lanes  + destination_lanes

# Geocode

geolocator = Nominatim(user_agent="app")


geocoded_locations = []
n = 0

# Sets limit on number of iterations. Testing only. 
ncl = 50

combined_locations = combined_locations[:ncl]

for postal in combined_locations:
    location = geolocator.geocode(postal)
    row = [postal, location.latitude, location.longitude]
    geocoded_locations.append(row)
    n = n+1
    print(str(round((n/ncl)*100,1))+"%")

geocoded_locations = pd.DataFrame(geocoded_locations, columns = ['postal', 'lat', 'lon'])
geocoded_locations.to_pickle('./data/geocoded_locations.pkl')
