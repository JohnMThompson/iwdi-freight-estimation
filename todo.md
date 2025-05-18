# To Do

## Steps to Complete

- [X] Import all postal codes
  - Limit to USA only
- [X] Geocode all postal codes
  - This will be difficult given API rate limiting. Does a dataset already exist with lat/long for each Postal?
- [ ] Calculate nearest 3 known points for each unknown
  - [ ] Pre-batch somehow to reduce distance calcs
  - by 2 digit postals and adjacent?
  - States and adjacent?
  - [ ] Find 3 nearest
  - [ ] Average costs
  - [ ] Save the three nearest for each unknown point to visualize later?
