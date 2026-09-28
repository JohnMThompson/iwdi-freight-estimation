import { Fragment, useEffect } from 'react';
import { MapContainer, Marker, Polyline, Popup, TileLayer, useMap } from 'react-leaflet';
import L from 'leaflet';

const pin = (role) => L.divIcon({
  className: 'map-pin-wrap',
  html: `<span class="map-glyph map-glyph-${role}" aria-hidden="true"><b></b></span>`,
  iconSize: role === 'history' ? [20, 20] : [28, 30],
  iconAnchor: role === 'history' ? [10, 10] : [8, 29],
});

const icons = {
  origin: pin('origin'),
  target: pin('target'),
  known: pin('history'),
};

function FitLocations({ result }) {
  const map = useMap();
  useEffect(() => {
    if (!result) return;
    const points = [result.origin, result.destination, ...result.neighbors.map((item) => item.destination)]
      .map((point) => [point.latitude, point.longitude]);
    map.fitBounds(points, { padding: [34, 34], maxZoom: 6 });
  }, [map, result]);
  return null;
}

export default function FreightMap({ result }) {
  const center = result ? [result.destination.latitude, result.destination.longitude] : [39.5, -98.35];
  return (
    <MapContainer center={center} zoom={4} scrollWheelZoom className="freight-map">
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {result && <>
        <FitLocations result={result} />
        <Marker position={[result.origin.latitude, result.origin.longitude]} icon={icons.origin} title={`Ship from ${result.origin.name}`}>
          <Popup><strong>SHIP FROM</strong><br />{result.origin.name}</Popup>
        </Marker>
        <Marker position={[result.destination.latitude, result.destination.longitude]} icon={icons.target} title={`Selected destination ${result.destination.name}`}>
          <Popup><strong>{result.status === 'insufficient_data' ? 'SELECTED DESTINATION' : result.is_observed ? 'OBSERVED DESTINATION' : 'ESTIMATED DESTINATION'}</strong><br />{result.destination.zip} · {result.destination.name}</Popup>
        </Marker>
        {result.neighbors.map((neighbor) => <Fragment key={neighbor.destination.id}>
          <Polyline key={`${neighbor.destination.id}-line`} positions={[
            [result.destination.latitude, result.destination.longitude],
            [neighbor.destination.latitude, neighbor.destination.longitude],
          ]} pathOptions={{ color: '#397d73', weight: 2, opacity: 0.64, dashArray: '5 6' }} />
          {neighbor.destination.id !== result.destination.id && <Marker key={`${neighbor.destination.id}-marker`}
            position={[neighbor.destination.latitude, neighbor.destination.longitude]}
            icon={icons.known}
            title={`Contributing historical observation ${neighbor.destination.name}`}
          >
            <Popup><strong>CONTRIBUTING OBSERVATION</strong><br />{neighbor.destination.zip} · {neighbor.destination.name}<br />Observed ${neighbor.observed_cost.toLocaleString()} · {neighbor.distance_miles.toFixed(1)} mi</Popup>
          </Marker>}
        </Fragment>)}
      </>}
    </MapContainer>
  );
}
