async function request(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail || `Request failed (${response.status})`);
  }
  return response.json();
}

export const getOrigins = () => request('/api/origins');
export const getDestinations = (originId) => request(`/api/destinations?origin_id=${encodeURIComponent(originId)}`);
export const getEstimate = (payload) => request('/api/estimate', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(payload),
});
