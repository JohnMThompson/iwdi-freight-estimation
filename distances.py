import pandas as pd
from geopy.distance import great_circle

# Combine origins and destinations

df = pd.read_pickle('./data/geocoded_locations.pkl')
df['key'] = 0

origins = df.head(2)
destinations = df.iloc[2:]

lanes = origins.merge(destinations, on='key')
lanes = lanes.rename(columns={'postal_x': 'origin_postal',
                              'lat_x': 'origin_lat',
                              'lon_x': 'origin_lon',
                              'postal_y': 'destination_postal',
                              'lat_y': 'destination_lat',
                              'lon_y': 'destination_lon'
                              })
lanes.drop('key', axis=1, inplace=True)

# Find distances

distances = []

for index,row in lanes.iterrows():
    origin_lookup = (row['origin_lat'], row['origin_lon'])
    destination_lookup = (row['destination_lat'], row['destination_lon'])
    gc_distance = great_circle(origin_lookup, destination_lookup)
    record = [row['origin_postal'], row['destination_postal'], gc_distance.km]
    distances.append(record)

lane_distances = pd.DataFrame(distances, columns = ['origin_postal', 'destination_postal', 'distance_km'])
lane_distances.to_pickle('./data/lane_distances.pkl')


###########################
