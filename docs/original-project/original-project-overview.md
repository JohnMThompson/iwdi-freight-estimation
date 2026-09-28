# Using Spatial Tools to Estimate Freight Costs

**Twin Cities Alteryx User Group — 2018**

## Overview

This project explored the use of spatial analysis and inverse distance weighting (IDW) to estimate truck freight costs for destinations where historical freight data was unavailable.

The business problem was straightforward: when pricing prospective business, freight costs needed to be estimated quickly for locations that may not have been served previously. Existing historical freight data covered only a small portion of the possible destination network, making direct historical lookup impossible for many locations.

The proposed solution used the geographic relationship between known freight observations to interpolate an estimated cost for unknown destinations.

---

## The Business Problem

There are more than 32,000 ZIP codes in the United States, while a typical year of shipment history might contain freight observations for only approximately 220 destinations from a particular origin.

This creates a sparse-data problem:

- Freight costs are known for destinations previously served.
- Freight costs are unknown for most potential destinations.
- Sales and pricing teams still need reasonable freight estimates for prospective customers.
- Estimates need to be generated quickly enough to support the pricing process.

The goal was not to perfectly predict future freight costs. The goal was to produce a reasonable estimate using the historical information already available.

---

## Why Use Spatial Analysis?

Freight costs have an inherent geographic structure.

Locations near one another will often have more similar freight characteristics than locations that are far apart. This suggests that known freight observations surrounding an unknown destination can provide useful information about the likely freight cost at that destination.

This idea relates to **Tobler's First Law of Geography**:

> Everything is related to everything else, but near things are more related than distant things.

Rather than explicitly constructing geographic regions or attempting to model every characteristic affecting freight prices, spatial interpolation can use the geographic structure already present in historical freight observations.

---

## Inverse Distance Weighting

The method selected for the project was **Inverse Distance Weighting (IDW)**.

IDW estimates an unknown value using nearby observations. Observations closer to the unknown location receive greater influence than observations farther away.

The general concept is:

1. Identify an unknown destination.
2. Find nearby destinations with known historical freight costs.
3. Calculate the distance between the unknown destination and each known destination.
4. Assign greater weight to closer observations.
5. Calculate a weighted average of the known freight costs.

Conceptually:

    Estimated Cost =
        Sum(Weight × Known Freight Cost)
        --------------------------------
                   Sum(Weight)

with the weight determined by distance:

    Weight = 1 / Distance^p

where `p` controls how quickly the influence of an observation decreases as distance increases.

The essential principle is simple:

**The closer a known point is to the unknown point, the more influence it has on the estimate.**

---

## Example

Consider an unknown destination surrounded by three known freight observations:

| Known Freight Cost | Distance from Unknown Destination |
| ---: | ---: |
| $1,623 | 13.5 miles |
| $1,688 | 127.1 miles |
| $2,309 | 260.5 miles |

A simple average would treat all three observations equally, despite the first observation being dramatically closer to the unknown destination.

IDW instead gives the nearby $1,623 observation much greater influence.

Using the inverse-distance calculation, the resulting estimated freight cost is approximately:

**$1,626**

The estimate therefore remains close to the geographically nearest known freight observation while still incorporating information from the other surrounding observations.

---

## Why This Approach Was Attractive

One advantage of the spatial approach was its simplicity.

Traditional freight-estimation models can require explicit modeling of factors such as:

- Origin regions
- Destination regions
- Distance
- Geographic characteristics
- Market characteristics
- Other explanatory variables

IDW instead relies on the spatial structure already contained within historical freight observations.

The observed freight price at a location is itself the result of many underlying factors. By using nearby observed prices, the model can indirectly incorporate some of those effects without explicitly modeling each one.

This results in a method that is:

- Easy to understand
- Easy to explain
- Relatively simple to maintain
- Based directly on historical freight observations
- Capable of estimating locations without direct shipment history

---

## Implementation in Alteryx

The model was originally implemented using Alteryx spatial tools.

The workflow:

1. Loaded historical freight observations.
2. Associated shipment destinations with geographic coordinates.
3. Identified locations requiring estimated freight costs.
4. Calculated spatial distances between known and unknown locations.
5. Identified the nearest known freight observations.
6. Applied inverse-distance weighting.
7. Generated estimated freight costs for previously unknown destinations.

This demonstrated that relatively sophisticated spatial analysis could be implemented using a visual analytics workflow without requiring a traditional programming environment.

---

## Tableau Front End

The resulting freight estimates were exposed through an interactive Tableau application.

The interface allowed users to:

- Select an origin.
- Filter or select destination ZIP codes.
- View known and estimated freight locations geographically.
- Explore estimated freight costs across the United States.
- View minimum, average, and maximum linehaul estimates.
- Interact with individual destinations on the map.

Known freight observations and interpolated estimates were visually distinguished.

The Tableau application served as the user-facing layer while Alteryx performed the underlying data preparation and spatial estimation.

---

## Limitations

IDW does not create information where none exists.

Its usefulness depends on the availability and geographic density of historical observations.

Potential limitations include:

- Sparse historical freight coverage
- Large distances between an unknown destination and the nearest known observations
- Geographic barriers that make physically nearby locations economically different
- Regional freight-market differences
- Changes in freight markets over time
- Locations where geographic proximity does not correspond well with freight-market similarity

As the distance to available observations increases, the resulting estimate should be treated with greater caution.

The method is therefore best understood as interpolation from an existing freight network rather than a comprehensive model of the freight market.

---

## Intended Use

The primary business use case was supporting rapid pricing of prospective customers.

When Sales requested pricing for a potential customer, freight estimates were needed to construct an expected delivered cost and proposed customer price.

For this purpose, the freight estimate did not need to perfectly predict the eventual freight invoice.

It needed to be:

- Reasonable
- Fast
- Consistent
- Explainable
- Sufficiently accurate for preliminary customer pricing

This made a lightweight spatial interpolation method particularly well suited to the problem.

---

## Key Idea

The central insight of the project was that incomplete historical freight data still contains useful information about locations that have never been directly observed.

Instead of requiring a freight observation for every possible destination, the geographic relationships among existing observations can be used to estimate missing values.

In short:

> Use what is known about nearby locations to estimate what is unknown.

The result was a simple and explainable freight-estimation method built around the spatial structure already present in historical transportation data.
