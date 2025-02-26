import pandas as pd

############
### Plan ###
############

# Iterate through all zips
# Join all known zips
# Calc distances
# Retain top 3 closest
# Calc cost for zip

df = pd.read_pickle('./data/zips.pkl')
known = pd.read_pickle('./data/geocoded_known.pkl')
