# To Do

## Steps to Complete

- [ ] Import all postal codes
  - Limit to USA only
- [ ] Geocode all postal codes
  - This will be difficult given API rate limiting. Does a dataset already exist with lat/long for each Postal?
- [ ] Calculate distance between all postal codes
  - Cross join of all postal codes
- [ ] Find 3 nearest neighbors with cost data for every postal
  - If a postal has cost data, we don't calculate nearest
