import { useState, useEffect, useRef } from 'react';
import { jumpApi } from '../../services/api/navigation';
import type { JumpShip, JumpRange, JumpRoute } from '../../types/navigation';
import { SYSTEM_PRESETS } from '../../types/navigation';

const SYSTEM_IDS: Record<string, number> = {
  'Jita': 30000142,
  'Amarr': 30002187,
  'Dodixie': 30002659,
  'Rens': 30002510,
  'Hek': 30002053,
  '1DQ1-A': 30004759,
  'R1O-GN': 30001198,
  'K-6K16': 30001339,
  'GE-8JV': 30001984,
  'HED-GP': 30001161,
  'Amamake': 30002537,
  'Tama': 30003837,
};

const PRESET_COLORS: Record<string, string> = {
  trade: '#3fb950',
  staging: '#f85149',
  lowsec: '#d29922',
};

const cardStyle: React.CSSProperties = {
  background: 'var(--bg-secondary)',
  border: '1px solid var(--border-color)',
  borderRadius: 8,
  padding: 16,
  marginBottom: 12,
};

const inputStyle: React.CSSProperties = {
  background: 'var(--bg-primary, #0d1117)',
  border: '1px solid var(--border-color)',
  borderRadius: 6,
  color: 'var(--text-primary, #e6edf3)',
  padding: '6px 10px',
  fontSize: '0.85rem',
  width: '100%',
  outline: 'none',
};

const labelStyle: React.CSSProperties = {
  fontSize: '0.85rem',
  color: 'var(--text-secondary, #8b949e)',
  marginBottom: 4,
  display: 'block',
};

const numberInputStyle: React.CSSProperties = {
  ...inputStyle,
  width: 60,
  textAlign: 'center' as const,
  fontFamily: 'monospace',
};

export function JumpPlanner() {
  const [ships, setShips] = useState<JumpShip[]>([]);
  const [selectedShip, setSelectedShip] = useState('');
  const [jdcLevel, setJdcLevel] = useState(5);
  const [jfLevel, setJfLevel] = useState(5);
  const [range, setRange] = useState<JumpRange | null>(null);
  const [origin, setOrigin] = useState('');
  const [destination, setDestination] = useState('');
  const [avoidJammed, setAvoidJammed] = useState(false);
  const [route, setRoute] = useState<JumpRoute | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const rangeDebounce = useRef<ReturnType<typeof setTimeout>>(undefined);

  useEffect(() => {
    jumpApi.getShips().then(res => {
      setShips(res.ships);
      if (res.ships.length > 0) {
        setSelectedShip(res.ships[0].name);
      }
    }).catch(() => setError('Failed to load jump-capable ships.'));
  }, []);

  useEffect(() => {
    if (!selectedShip) return;
    if (rangeDebounce.current) clearTimeout(rangeDebounce.current);
    rangeDebounce.current = setTimeout(() => {
      jumpApi.getRange(selectedShip, jdcLevel, jfLevel)
        .then(setRange)
        .catch(() => setRange(null));
    }, 300);
    return () => { if (rangeDebounce.current) clearTimeout(rangeDebounce.current); };
  }, [selectedShip, jdcLevel, jfLevel]);

  const handleCalculate = async () => {
    const originId = SYSTEM_IDS[origin];
    const destId = SYSTEM_IDS[destination];
    if (!originId || !destId) {
      setError(`Unknown system. Use a preset: ${Object.keys(SYSTEM_IDS).join(', ')}`);
      return;
    }
    if (!selectedShip) {
      setError('Select a ship first.');
      return;
    }
    setError('');
    setRoute(null);
    setLoading(true);
    try {
      const result = await jumpApi.calculateRoute({
        origin_id: originId,
        destination_id: destId,
        ship_name: selectedShip,
        jdc_level: jdcLevel,
        jf_level: jfLevel,
        avoid_jammed: avoidJammed,
      });
      setRoute(result);
      if (!result.route_possible && result.error_message) {
        setError(result.error_message);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Route calculation failed.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const secColor = (sec: number) => {
    if (sec > 0.5) return '#3fb950';
    if (sec > 0.0) return '#d29922';
    return '#f85149';
  };

  const grouped = SYSTEM_PRESETS.reduce<Record<string, typeof SYSTEM_PRESETS>>((acc, p) => {
    if (!acc[p.type]) acc[p.type] = [];
    acc[p.type].push(p);
    return acc;
  }, {});

  return (
    <div style={{ maxWidth: 900, margin: '0 auto' }}>
      {/* Ship & Skills */}
      <div style={cardStyle}>
        <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', alignItems: 'flex-end' }}>
          <div style={{ flex: '1 1 220px' }}>
            <label style={labelStyle}>Jump Ship</label>
            <select
              value={selectedShip}
              onChange={e => setSelectedShip(e.target.value)}
              style={{ ...inputStyle, cursor: 'pointer' }}
            >
              {ships.map(s => (
                <option key={s.name} value={s.name}>{s.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label style={labelStyle}>JDC Level</label>
            <input
              type="number"
              min={0}
              max={5}
              value={jdcLevel}
              onChange={e => setJdcLevel(Math.min(5, Math.max(0, Number(e.target.value))))}
              style={numberInputStyle}
            />
          </div>
          <div>
            <label style={labelStyle}>JF Level</label>
            <input
              type="number"
              min={0}
              max={5}
              value={jfLevel}
              onChange={e => setJfLevel(Math.min(5, Math.max(0, Number(e.target.value))))}
              style={numberInputStyle}
            />
          </div>
          <div style={{ paddingBottom: 2 }}>
            {range ? (
              <span style={{ fontFamily: 'monospace', fontSize: '0.85rem', color: '#00d4ff' }}>
                Range: {(range.effective_range ?? 0).toFixed(2)} LY
              </span>
            ) : (
              <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
                Calculating range...
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Origin / Destination */}
      <div style={cardStyle}>
        <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', alignItems: 'flex-end' }}>
          <div style={{ flex: '1 1 200px' }}>
            <label style={labelStyle}>Origin System</label>
            <input
              type="text"
              value={origin}
              onChange={e => setOrigin(e.target.value)}
              list="system-presets"
              placeholder="e.g. Jita"
              style={inputStyle}
            />
          </div>
          <div style={{ flex: '1 1 200px' }}>
            <label style={labelStyle}>Destination System</label>
            <input
              type="text"
              value={destination}
              onChange={e => setDestination(e.target.value)}
              list="system-presets"
              placeholder="e.g. 1DQ1-A"
              style={inputStyle}
            />
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, paddingBottom: 4 }}>
            <input
              type="checkbox"
              id="avoid-jammed"
              checked={avoidJammed}
              onChange={e => setAvoidJammed(e.target.checked)}
              style={{ accentColor: '#f85149' }}
            />
            <label htmlFor="avoid-jammed" style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', cursor: 'pointer' }}>
              Avoid Jammed
            </label>
          </div>
          <button
            onClick={handleCalculate}
            disabled={loading || !origin || !destination}
            style={{
              background: loading ? '#333' : '#00d4ff',
              color: '#000',
              border: 'none',
              borderRadius: 6,
              padding: '8px 20px',
              fontWeight: 600,
              fontSize: '0.85rem',
              cursor: loading ? 'not-allowed' : 'pointer',
              opacity: (!origin || !destination) ? 0.5 : 1,
            }}
          >
            {loading ? 'Calculating...' : 'Calculate Route'}
          </button>
        </div>
        <datalist id="system-presets">
          {SYSTEM_PRESETS.map(p => (
            <option key={p.name} value={p.name} label={`${p.name} (${p.region})`} />
          ))}
        </datalist>

        {/* Quick Select Buttons */}
        <div style={{ marginTop: 12, display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
          <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', marginRight: 4 }}>Quick:</span>
          {Object.entries(grouped).map(([type, presets]) => (
            <div key={type} style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
              {presets.map(p => (
                <button
                  key={p.name}
                  onClick={() => setDestination(p.name)}
                  style={{
                    background: 'transparent',
                    border: `1px solid ${PRESET_COLORS[type] || '#555'}`,
                    borderRadius: 4,
                    color: PRESET_COLORS[type] || '#ccc',
                    padding: '2px 8px',
                    fontSize: '0.7rem',
                    cursor: 'pointer',
                    opacity: destination === p.name ? 1 : 0.7,
                    fontWeight: destination === p.name ? 700 : 400,
                  }}
                >
                  {p.name}
                </button>
              ))}
              {type !== Object.keys(grouped).at(-1) && (
                <span style={{ color: '#333', margin: '0 2px' }}>|</span>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Error */}
      {error && (
        <div style={{
          ...cardStyle,
          borderColor: '#f85149',
          color: '#f85149',
          fontSize: '0.85rem',
          display: 'flex',
          alignItems: 'center',
          gap: 8,
        }}>
          <span style={{ fontWeight: 700 }}>ERROR</span>
          <span>{error}</span>
        </div>
      )}

      {/* Route Summary */}
      {route && (
        <div style={{
          ...cardStyle,
          borderColor: route.route_possible ? '#3fb950' : '#f85149',
        }}>
          <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap', alignItems: 'center' }}>
            <span style={{
              fontWeight: 700,
              fontSize: '0.85rem',
              color: route.route_possible ? '#3fb950' : '#f85149',
              textTransform: 'uppercase',
            }}>
              {route.route_possible ? 'Route Found' : 'No Route'}
            </span>
            {route.route_possible && (
              <>
                <Stat label="Jumps" value={route.total_jumps} />
                <Stat label="Distance" value={`${(route.total_distance ?? 0).toFixed(1)} LY`} />
                <Stat label="Fuel" value={route.total_fuel.toLocaleString()} />
                <Stat label="Est. Time" value={`${(route.total_time_minutes ?? 0).toFixed(0)} min`} />
                <Stat label="Ship" value={route.ship_name} color="#00d4ff" />
              </>
            )}
          </div>
        </div>
      )}

      {/* Waypoint Table */}
      {route && route.route_possible && route.waypoints.length > 0 && (
        <div style={{ ...cardStyle, padding: 0, overflow: 'hidden' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
            <thead>
              <tr style={{ background: 'var(--bg-tertiary, #161b22)' }}>
                {['#', 'System', 'Region', 'Security', 'Distance (LY)', 'Fuel', 'Status'].map(h => (
                  <th key={h} style={{
                    padding: '8px 10px', textAlign: 'left', fontWeight: 600,
                    fontSize: '0.7rem', textTransform: 'uppercase',
                    color: 'var(--text-secondary)', borderBottom: '1px solid var(--border-color)',
                  }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {route.waypoints.map((wp, i) => (
                <tr
                  key={i}
                  style={{
                    borderBottom: '1px solid var(--border-color)',
                    background: i % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.02)',
                  }}
                >
                  <td style={{ padding: '6px 10px', fontFamily: 'monospace', color: 'var(--text-secondary)' }}>
                    {i + 1}
                  </td>
                  <td style={{ padding: '6px 10px', fontWeight: 600, color: 'var(--text-primary, #e6edf3)' }}>
                    {wp.system.system_name}
                  </td>
                  <td style={{ padding: '6px 10px', color: 'var(--text-secondary)', fontSize: '0.7rem' }}>
                    {wp.system.region_name}
                  </td>
                  <td style={{ padding: '6px 10px' }}>
                    <span style={{
                      fontFamily: 'monospace',
                      color: secColor(wp.system.security),
                      fontWeight: 600,
                    }}>
                      {(wp.system.security ?? 0).toFixed(1)}
                    </span>
                  </td>
                  <td style={{ padding: '6px 10px', fontFamily: 'monospace' }}>
                    {(wp.distance_ly ?? 0) > 0 ? wp.distance_ly.toFixed(2) : '-'}
                  </td>
                  <td style={{ padding: '6px 10px', fontFamily: 'monospace', color: '#ff8800' }}>
                    {wp.fuel_required > 0 ? wp.fuel_required.toLocaleString() : '-'}
                  </td>
                  <td style={{ padding: '6px 10px', display: 'flex', gap: 6 }}>
                    {wp.jammed && <Badge text="JAMMED" color="#f85149" />}
                    {wp.has_station && <Badge text="STATION" color="#00d4ff" />}
                    {wp.is_cyno_system && <Badge text="CYNO" color="#d29922" />}
                    {!wp.jammed && !wp.has_station && !wp.is_cyno_system && (
                      <span style={{ color: 'var(--text-secondary)', fontSize: '0.7rem' }}>-</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

/* ---- Helper components ---- */

function Stat({ label, value, color }: { label: string; value: string | number; color?: string }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
      <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>
        {label}
      </span>
      <span style={{ fontFamily: 'monospace', fontWeight: 600, color: color || 'var(--text-primary, #e6edf3)' }}>
        {value}
      </span>
    </div>
  );
}

function Badge({ text, color }: { text: string; color: string }) {
  return (
    <span style={{ color, fontWeight: 700, fontSize: '0.7rem', textTransform: 'uppercase' as const }}>
      {text}
    </span>
  );
}
