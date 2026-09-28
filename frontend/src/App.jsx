import { useEffect, useMemo, useState } from 'react';
import { getDestinations, getEstimate, getOrigins } from './api.js';
import FreightMap from './Map.jsx';

const money = (value) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(value);
const DEFAULTS = { k: 5, power: 2, maxDistance: 600 };
const COVERAGE_LABELS = {
  strong: 'Strong',
  moderate: 'Moderate',
  limited: 'Limited',
  sparse: 'Sparse',
  none: 'No nearby evidence',
};

function CoverageSummary({ result }) {
  if (!result) return <div className="coverage-summary"><span className="field-label">COVERAGE</span><strong className="coverage-pending">Shown with estimate</strong></div>;
  if (result.status === 'observed') return <div className="coverage-summary"><span className="field-label">COVERAGE</span><strong className="coverage-pending">Direct historical rate</strong><small>No interpolation needed</small></div>;

  const coverage = result.coverage;
  const level = coverage?.level || 'none';
  const filled = { strong: 4, moderate: 3, limited: 2, sparse: 1, none: 0 }[level];
  const used = coverage?.used_observation_count || 0;
  const eligible = coverage?.eligible_observation_count || 0;
  const nearest = coverage?.nearest_observation_distance_miles;
  const furthest = coverage?.furthest_contributing_observation_distance_miles;
  return (
    <div className={`coverage-summary coverage-${level}`}>
      <span className="field-label">COVERAGE</span>
      <div className="coverage-rating" aria-label={`Coverage: ${COVERAGE_LABELS[level]}`}>
        <span className="coverage-dots" aria-hidden="true">{[0, 1, 2, 3].map((index) => <i key={index} className={index < filled ? 'is-filled' : ''} />)}</span>
        <strong>{COVERAGE_LABELS[level]}</strong>
      </div>
      <small>{used} used · {eligible} eligible within {result.max_observation_distance_miles} mi</small>
      {nearest !== null && furthest !== null && <small>{nearest.toFixed(0)}–{furthest.toFixed(0)} mi from destination</small>}
    </div>
  );
}

export default function App() {
  const [origins, setOrigins] = useState([]);
  const [originId, setOriginId] = useState('');
  const [destinations, setDestinations] = useState([]);
  const [destinationZip, setDestinationZip] = useState('');
  const [k, setK] = useState(DEFAULTS.k);
  const [power, setPower] = useState(DEFAULTS.power);
  const [maxDistance, setMaxDistance] = useState(DEFAULTS.maxDistance);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    getOrigins().then((rows) => {
      setOrigins(rows);
      if (rows.length) setOriginId(rows[0].id);
    }).catch((err) => setError(err.message));
  }, []);

  useEffect(() => {
    if (!originId) return;
    getDestinations(originId).then((rows) => {
      setDestinations(rows);
      setDestinationZip(rows.find((row) => !row.has_observation)?.zip || rows[0]?.zip || '');
      setResult(null);
    }).catch((err) => setError(err.message));
  }, [originId]);

  const destination = useMemo(() => destinations.find((row) => row.zip === destinationZip), [destinations, destinationZip]);

  async function submit(event) {
    event.preventDefault();
    if (!originId || !destinationZip) return;
    setLoading(true);
    setError('');
    try {
      setResult(await getEstimate({
        origin_id: originId,
        destination_zip: destinationZip,
        k: Number(k),
        p: Number(power),
        max_observation_distance_miles: Number(maxDistance),
      }));
    } catch (err) {
      setError(err.message);
      setResult(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="page-shell">
      <header className="topbar">
        <a className="wordmark" href="#top"><span className="brand-mark">F</span><span>FIELDNOTE <small>FREIGHT INTELLIGENCE</small></span></a>
        <div className="topbar-right"><span className="status-dot" /> SYNTHETIC DATASET <span className="topbar-divider" /> PROTOTYPE · 01</div>
      </header>

      <section className="intro" id="top">
        <div className="intro-copy">
          <div className="eyebrow"><span>PRICING TOOLKIT</span><span className="eyebrow-line" /> SPATIAL ESTIMATION</div>
          <h1>A clearer view of<br /><em>what freight might cost.</em></h1>
          <p>Estimate a lane from the places you already know.<br />Every number is grounded in nearby observed rates.</p>
        </div>
      </section>

      <section className="workspace">
        <aside className="control-panel">
          <div className="section-kicker"><span>01</span> DEFINE YOUR LANE</div>
          <form onSubmit={submit}>
            <label className="field-label" htmlFor="origin">SHIP FROM</label>
            <div className="select-wrap"><span className="field-symbol origin-symbol">↗</span>
              <select id="origin" value={originId} onChange={(event) => { setOriginId(event.target.value); setResult(null); }}>
                {origins.map((row) => <option value={row.id} key={row.id}>{row.name}</option>)}
              </select><span className="select-chevron">⌄</span>
            </div>
            <label className="field-label second-label" htmlFor="destination">SHIP TO</label>
            <div className="select-wrap"><span className="field-symbol target-symbol">◎</span>
              <select id="destination" value={destinationZip} onChange={(event) => { setDestinationZip(event.target.value); setResult(null); }}>
                {destinations.map((row) => <option value={row.zip} key={row.zip}>{row.zip} · {row.name} {row.has_observation ? '· known' : '· estimate'}</option>)}
              </select><span className="select-chevron">⌄</span>
            </div>
            {destination && <div className="destination-hint"><span className="hint-dot" />{destination.has_observation ? 'Known lane' : 'No exact history'}<span className="hint-coordinate">{destination.name}</span></div>}

            <details className="advanced-options">
              <summary><span className="advanced-icon">⌘</span> Advanced Options <span className="advanced-chevron">⌄</span></summary>
              <div className="advanced-content">
                <div className="setting-row">
                  <div><label className="field-label" htmlFor="neighbors">NEAREST OBSERVATIONS (K)</label><p className="setting-caption">Maximum number used in the estimate</p></div>
                  <select className="compact-select" id="neighbors" value={k} onChange={(event) => { setK(Number(event.target.value)); setResult(null); }}>{[3, 4, 5, 6, 8, 10].map((value) => <option key={value}>{value}</option>)}</select>
                </div>
                <div className="setting-row">
                  <div><label className="field-label" htmlFor="power">DISTANCE INFLUENCE (P)</label><p className="setting-caption">Higher values emphasize closer lanes</p></div>
                  <select className="compact-select" id="power" value={power} onChange={(event) => { setPower(Number(event.target.value)); setResult(null); }}>{[1, 1.5, 2, 2.5, 3].map((value) => <option key={value} value={value}>p = {value}</option>)}</select>
                </div>
                <div className="setting-row radius-row">
                  <div><label className="field-label" htmlFor="max-distance">MAX OBSERVATION DISTANCE</label><p className="setting-caption">Farther observations are excluded</p></div>
                  <div className="distance-input"><input id="max-distance" type="number" min="1" max="5000" step="1" required value={maxDistance} onChange={(event) => { setMaxDistance(event.target.value); setResult(null); }} /><span>mi</span></div>
                </div>
                <button className="restore-defaults" type="button" onClick={() => { setK(DEFAULTS.k); setPower(DEFAULTS.power); setMaxDistance(DEFAULTS.maxDistance); setResult(null); }}>Restore defaults</button>
                <p className="advanced-footnote">600 miles is an initial working limit, not a validated cutoff.</p>
              </div>
            </details>
            <button className="estimate-button" type="submit" disabled={loading || !destinationZip}>
              <span>{loading ? 'CALCULATING…' : 'ESTIMATE THIS LANE'}</span><span className="button-arrow">↗</span>
            </button>
          </form>
          {error && <div className="error-box">{error}. Confirm the API is running at localhost:8000.</div>}
          <div className="method-note"><span className="note-icon">i</span><p><strong>A simple, explainable model.</strong><br />Nearby historical destinations carry more weight. No black box, just distance and observed cost.</p></div>
        </aside>

        <section className="results-area">
          <div className="results-heading"><div><div className="section-kicker"><span>03</span> LANE ESTIMATE</div><h2>{result?.status === 'insufficient_data' ? 'Not enough nearby evidence' : result ? `${result.origin.name} → ${result.destination.name}` : 'Your estimate, explained.'}</h2></div><div className={`estimate-badge ${result?.status === 'insufficient_data' ? 'badge-insufficient' : ''}`}><span className="badge-dot" /> {result ? (result.status === 'insufficient_data' ? 'INSUFFICIENT DATA' : result.is_observed ? 'OBSERVED RATE' : 'IDW ESTIMATE') : 'READY WHEN YOU ARE'}</div></div>
          <div className="results-grid">
          <div className="map-column">
          <div className="map-frame"><FreightMap result={result} />
            <div className="map-label"><span className="map-label-mark">⌖</span> {result ? result.destination.zip : 'UNITED STATES'} <span className="map-label-separator">/</span> {result ? result.destination.name.toUpperCase() : 'LANE MAP'}</div>
            <div className="map-legend"><span><i className="legend-origin" />From</span><span><i className="legend-target" />To</span><span><i className="legend-history" />Used history</span><span><i className="legend-link" />IDW link</span></div>
            {!result && <div className="map-empty"><span className="empty-crosshair">⌖</span><strong>Choose a destination to begin</strong><span>Your lane and nearby observations will appear here.</span></div>}
          </div>

          <div className="estimate-summary">
            <div className={`cost-block ${result?.status === 'insufficient_data' ? 'cost-unavailable' : ''}`}><span className="field-label">{result?.is_observed ? 'OBSERVED LINEHAUL' : 'ESTIMATED LINEHAUL'}</span><div className="cost-value">{result?.estimated_cost != null ? money(result.estimated_cost) : result?.status === 'insufficient_data' ? 'NO ESTIMATE' : <span className="cost-placeholder">— — —</span>}{result?.estimated_cost != null && <span className="cost-unit">USD / LOAD</span>}</div></div>
            <div className="summary-divider" />
            <CoverageSummary result={result} />
          </div>
          {result?.coverage && <div className="coverage-explainer">Coverage describes the count and proximity of historical evidence; it is not a probability or calibrated accuracy measure.</div>}

          {result?.status === 'insufficient_data' && <div className="insufficient-note"><span className="note-icon">i</span><p>{result.message} The search was limited to {result.max_observation_distance_miles} miles and was not expanded.{result.nearest_available_observation_distance_miles != null && <> The nearest historical destination is {result.nearest_available_observation_distance_miles.toFixed(0)} miles away.</>}</p></div>}
          </div>
          <div className="observations-section">
            <div className="observations-title"><div><div className="section-kicker"><span>04</span> THE SUPPORTING EVIDENCE</div><h3>{result?.status === 'insufficient_data' ? 'No contributing observations' : 'Nearby known lanes'}</h3></div><span className="table-count">{result ? `${result.neighbors.length} OBSERVATIONS` : 'AWAITING ESTIMATE'}</span></div>
            <div className="observation-table-wrap"><table><thead><tr><th>DESTINATION</th><th>OBSERVED<br />LINEHAUL</th><th>DISTANCE</th><th>WEIGHT</th><th>CONTRIBUTION</th></tr></thead><tbody>
              {result?.neighbors.map((item, index) => <tr key={item.destination.id}><td><span className="row-index">0{index + 1}</span><span className="destination-cell"><strong>{item.destination.zip}</strong><small>{item.destination.name}</small></span></td><td>{money(item.observed_cost)}</td><td>{item.distance_miles.toFixed(0)} <span className="cell-unit">mi</span></td><td><span className="weight-cell">{(item.normalized_weight * 100).toFixed(1)}<small>%</small><i><b style={{ width: `${item.normalized_weight * 100}%` }} /></i></span></td><td>{money(item.contribution)}</td></tr>)}
              {!result && <tr><td colSpan="5" className="empty-table">Request an estimate to see the historical lanes behind it.</td></tr>}
              {result?.status === 'insufficient_data' && <tr><td colSpan="5" className="empty-table">No observations for this origin are within {result.max_observation_distance_miles} miles of this destination.</td></tr>}
            </tbody></table></div>
            {result?.status === 'estimated' && <div className="table-footnote">Weight share sums to 100%. Contribution = observed linehaul × normalized IDW weight. Only observations within the selected radius are eligible.</div>}
          </div>
          </div>
        </section>
      </section>

      <footer className="footer"><span>FIELDNOTE <small>FREIGHT INTELLIGENCE</small></span><p>Synthetic observations · Straight-line distances · For demonstration only</p><span className="footer-method">INVERSE DISTANCE WEIGHTING <b>·</b> V1.0</span></footer>
    </main>
  );
}
