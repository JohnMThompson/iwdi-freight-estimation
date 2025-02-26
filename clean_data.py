import pandas as pd


### Clean uszips.csv ###

# Import data and assign types

df = pd.read_csv('./data/uszips.csv', dtype={'zip': 'string', 'lat':'float32', 'lon': 'float32', 'state_id': 'string'})

# Remove territories
state_to_exclude = ['PR', 'VI', 'GU', 'AS']
df = df[~df['state_id'].isin(state_to_exclude)]

# Only want to keep zip, lat, long
cols_to_keep = ['zip', 'lat', 'lng', 'state_id']
df = df[cols_to_keep]

# write to pickle file
df.to_pickle('./data/zips.pkl')

import pandas as pd
from geopy.geocoders import Nominatim

### Clean known lanes ###

known = pd.read_csv('./data/iwdi-known-lanes.csv', 
                    dtype={
                        'Origin Postal': 'string', 'Destination Postal': 'string'
                        }, 
                    usecols=[
                        'Origin Postal', 'Destination Postal', 'Destination Country', 'Linehaul'
                        ])

# Remove destinations in Canada and remove country column

known = known[~known['Destination Country'].isin(['CA'])]
known = known.drop('Destination Country', axis=1)

# Rename columns

col_names = {
    'Origin Postal': 'origin_postal',
    'Destination Postal': 'destination_postal',
    'Linehaul': 'linehaul'
}
known = known.rename(columns=col_names)

# Convert linehaul column to int

known['linehaul'] = known['linehaul'].replace({'\$': '', '€': '', ',': ''}, regex=True)
known['linehaul'] = pd.to_numeric(known['linehaul'])
known['linehaul'] = known['linehaul'].astype(int)

# write to pickle file
known.to_pickle('./data/known.pkl')

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

