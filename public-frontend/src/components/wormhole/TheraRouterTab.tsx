import { useState, useEffect } from 'react';
import { wormholeApi } from '../../services/api/wormhole';
import type {
  TheraConnection,
  TheraRoute,
  TheraStatus,
  ShipSize,
} from '../../types/thera';

// Common system presets for quick selection
const SYSTEM_PRESETS = [
  // Trade Hubs
  { name: 'Jita', region: 'The Forge', type: 'trade' },
  { name: 'Amarr', region: 'Domain', type: 'trade' },
  { name: 'Dodixie', region: 'Sinq Laison', type: 'trade' },
  { name: 'Rens', region: 'Heimatar', type: 'trade' },
  { name: 'Hek', region: 'Metropolis', type: 'trade' },
  // Nullsec Staging
  { name: '1DQ1-A', region: 'Delve', type: 'staging' },
  { name: 'R1O-GN', region: 'Tribute', type: 'staging' },
  { name: 'K-6K16', region: 'Geminate', type: 'staging' },
  { name: 'M-OEE8', region: 'Tribute', type: 'staging' },
  { name: 'D-PNP9', region: 'Curse', type: 'staging' },
  { name: 'GE-8JV', region: 'Catch', type: 'staging' },
  { name: 'HED-GP', region: 'Catch', type: 'staging' },
  { name: 'YZ-LQL', region: 'Malpais', type: 'staging' },
  // Lowsec
  { name: 'Amamake', region: 'Heimatar', type: 'lowsec' },
  { name: 'Tama', region: 'The Citadel', type: 'lowsec' },
  { name: 'Oulley', region: 'Placid', type: 'lowsec' },
];

// Color constants
const CLASS_COLORS: Record<string, string> = {
  hs: '#00ff88',
  ls: '#ffcc00',
  ns: '#ff4444',
  c1: '#4488ff',
  c2: '#4488ff',
  c3: '#00ff88',
  c4: '#00ff88',
  c5: '#ff8800',
  c6: '#ff2222',
};

const SIZE_COLORS: Record<ShipSize, string> = {
  medium: '#888888',
  large: '#00d4ff',
  xlarge: '#ff8800',
  capital: '#ff2222',
};

const SIZE_LABELS: Record<ShipSize, string> = {
  medium: 'Medium',
  large: 'Large',
  xlarge: 'X-Large',
  capital: 'Capital',
};

// Utility functions
function formatHours(hours: number): string {
  if (hours < 1) return '<1h';
  if (hours < 24) return `${hours}h`;
  return `${Math.floor(hours / 24)}d ${hours % 24}h`;
}

function getClassColor(secClass: string): string {
  return CLASS_COLORS[secClass.toLowerCase()] || '#888888';
}

// Sub-components
function StatusBadge({ status }: { status: TheraStatus }) {
  const isHealthy = status.status === 'healthy' && status.eve_scout_reachable;
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
      fontSize: '0.75rem',
      color: isHealthy ? '#00ff88' : '#ff4444',
    }}>
      <span style={{
        width: '8px',
        height: '8px',
        borderRadius: '50%',
        background: isHealthy ? '#00ff88' : '#ff4444',
        boxShadow: isHealthy ? '0 0 6px #00ff88' : '0 0 6px #ff4444',
      }} />
      EVE-Scout: {isHealthy ? 'Online' : 'Offline'}
      {status.cache_age_seconds !== undefined && status.cache_age_seconds > 0 && (
        <span style={{ color: 'rgba(255,255,255,0.5)' }}>
          (cached {Math.floor(status.cache_age_seconds / 60)}m ago)
        </span>
      )}
    </div>
  );
}

function RouteResult({ route }: { route: TheraRoute }) {
  const isTheraRecommended = route.recommended === 'thera';
  const hasTheraRoute = route.thera_route !== null;

  return (
    <div style={{
      background: 'rgba(0,0,0,0.3)',
      borderRadius: '8px',
      padding: '1rem',
      marginTop: '1rem',
    }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '1rem',
        paddingBottom: '0.75rem',
        borderBottom: '1px solid rgba(255,255,255,0.1)',
      }}>
        <div>
          <span style={{ color: 'rgba(255,255,255,0.6)', fontSize: '0.75rem' }}>
            {route.origin.region_name || 'Unknown'}
          </span>
          <span style={{ margin: '0 0.5rem', color: 'rgba(255,255,255,0.3)' }}>→</span>
          <span style={{ color: 'rgba(255,255,255,0.6)', fontSize: '0.75rem' }}>
            {route.destination.region_name || 'Unknown'}
          </span>
        </div>
        <div style={{
          padding: '0.25rem 0.75rem',
          borderRadius: '4px',
          background: isTheraRecommended ? 'rgba(0,255,136,0.2)' : 'rgba(136,136,136,0.2)',
          color: isTheraRecommended ? '#00ff88' : '#888888',
          fontWeight: 700,
          fontSize: '0.75rem',
          textTransform: 'uppercase',
        }}>
          {isTheraRecommended ? '🗺️ THERA' : '➡️ DIRECT'} RECOMMENDED
        </div>
      </div>

      {/* Comparison */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: '1rem',
      }}>
        {/* Direct Route */}
        <div style={{
          padding: '0.75rem',
          borderRadius: '6px',
          background: !isTheraRecommended ? 'rgba(0,255,136,0.1)' : 'rgba(255,255,255,0.05)',
          border: !isTheraRecommended ? '1px solid rgba(0,255,136,0.3)' : '1px solid rgba(255,255,255,0.1)',
        }}>
          <div style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.5)', marginBottom: '0.25rem' }}>
            DIRECT ROUTE
          </div>
          <div style={{ fontSize: '1.5rem', fontWeight: 700, fontFamily: 'monospace' }}>
            {route.direct_jumps} <span style={{ fontSize: '0.75rem', fontWeight: 400 }}>jumps</span>
          </div>
        </div>

        {/* Thera Route */}
        <div style={{
          padding: '0.75rem',
          borderRadius: '6px',
          background: isTheraRecommended ? 'rgba(0,255,136,0.1)' : 'rgba(255,255,255,0.05)',
          border: isTheraRecommended ? '1px solid rgba(0,255,136,0.3)' : '1px solid rgba(255,255,255,0.1)',
          opacity: hasTheraRoute ? 1 : 0.5,
        }}>
          <div style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.5)', marginBottom: '0.25rem' }}>
            VIA THERA
          </div>
          {hasTheraRoute ? (
            <>
              <div style={{ fontSize: '1.5rem', fontWeight: 700, fontFamily: 'monospace' }}>
                {route.thera_route!.total_jumps} <span style={{ fontSize: '0.75rem', fontWeight: 400 }}>jumps</span>
              </div>
              <div style={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.5)', marginTop: '0.25rem' }}>
                Entry: {route.thera_route!.entry_connection.in_system_name} ({route.thera_route!.entry_jumps}J)
                <br />
                Exit: {route.thera_route!.exit_connection.in_system_name} ({route.thera_route!.exit_jumps}J)
              </div>
            </>
          ) : (
            <div style={{ fontSize: '0.85rem', color: 'rgba(255,255,255,0.4)' }}>
              No viable route
            </div>
          )}
        </div>
      </div>

      {/* Savings */}
      {hasTheraRoute && route.savings.jumps_saved > 0 && (
        <div style={{
          marginTop: '1rem',
          padding: '0.5rem 0.75rem',
          borderRadius: '4px',
          background: 'rgba(0,255,136,0.1)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}>
          <span style={{ color: '#00ff88', fontWeight: 600 }}>
            Save {route.savings.jumps_saved} jumps ({(route.savings.percentage ?? 0).toFixed(1)}%)
          </span>
          {route.savings.estimated_time_saved_minutes && (
            <span style={{ color: 'rgba(255,255,255,0.6)', fontSize: '0.75rem' }}>
              ~{(route.savings.estimated_time_saved_minutes ?? 0).toFixed(0)} min saved
            </span>
          )}
        </div>
      )}

      {/* Route Visualization */}
      {hasTheraRoute && <RouteVisualization route={route} />}
    </div>
  );
}

function RouteVisualization({ route }: { route: TheraRoute }) {
  if (!route.thera_route) return null;

  const { entry_connection, exit_connection, entry_jumps, exit_jumps } = route.thera_route;

  return (
    <div style={{
      marginTop: '1.25rem',
      padding: '1rem',
      background: 'rgba(255,204,0,0.05)',
      borderRadius: '6px',
      border: '1px solid rgba(255,204,0,0.2)',
    }}>
      <div style={{
        fontSize: '0.7rem',
        color: 'rgba(255,255,255,0.5)',
        marginBottom: '0.75rem',
        textTransform: 'uppercase',
        fontWeight: 600,
      }}>
        Thera Route Waypoints
      </div>

      {/* Visual Route */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '0.5rem',
        flexWrap: 'wrap',
        fontFamily: 'monospace',
      }}>
        {/* Origin */}
        <RouteNode
          name={route.origin.system_name}
          subtitle={route.origin.region_name}
          color="#00d4ff"
        />

        {/* Arrow to Entry */}
        <RouteArrow jumps={entry_jumps} />

        {/* Entry WH */}
        <RouteNode
          name={entry_connection.in_system_name}
          subtitle={`Entry WH (${entry_connection.wh_type})`}
          color="#ffcc00"
          icon="⭕"
        />

        {/* Arrow to Thera */}
        <RouteArrow jumps={1} label="WH" />

        {/* Thera */}
        <RouteNode
          name="Thera"
          subtitle="J-Space Hub"
          color="#ff8800"
          icon="🌀"
          highlight
        />

        {/* Arrow to Exit */}
        <RouteArrow jumps={1} label="WH" />

        {/* Exit WH */}
        <RouteNode
          name={exit_connection.in_system_name}
          subtitle={`Exit WH (${exit_connection.wh_type})`}
          color="#ffcc00"
          icon="⭕"
        />

        {/* Arrow to Destination */}
        <RouteArrow jumps={exit_jumps} />

        {/* Destination */}
        <RouteNode
          name={route.destination.system_name}
          subtitle={route.destination.region_name}
          color="#00ff88"
          icon="🎯"
        />
      </div>

      {/* Legend */}
      <div style={{
        marginTop: '0.75rem',
        paddingTop: '0.5rem',
        borderTop: '1px solid rgba(255,255,255,0.1)',
        display: 'flex',
        gap: '1rem',
        fontSize: '0.65rem',
        color: 'rgba(255,255,255,0.4)',
      }}>
        <span>⭕ = Wormhole Connection</span>
        <span>🌀 = Thera System</span>
        <span>Total: {route.thera_route.total_jumps} jumps</span>
      </div>
    </div>
  );
}

function RouteNode({
  name,
  subtitle,
  color,
  icon,
  highlight,
}: {
  name: string;
  subtitle?: string;
  color: string;
  icon?: string;
  highlight?: boolean;
}) {
  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      padding: '0.5rem 0.75rem',
      background: highlight ? 'rgba(255,136,0,0.15)' : 'rgba(0,0,0,0.3)',
      borderRadius: '6px',
      border: `1px solid ${color}40`,
      minWidth: '80px',
    }}>
      {icon && <span style={{ fontSize: '0.9rem', marginBottom: '0.15rem' }}>{icon}</span>}
      <span style={{
        color,
        fontWeight: 600,
        fontSize: '0.75rem',
        whiteSpace: 'nowrap',
      }}>
        {name}
      </span>
      {subtitle && (
        <span style={{
          color: 'rgba(255,255,255,0.4)',
          fontSize: '0.6rem',
          marginTop: '0.15rem',
          whiteSpace: 'nowrap',
        }}>
          {subtitle}
        </span>
      )}
    </div>
  );
}

function RouteArrow({ jumps, label }: { jumps: number; label?: string }) {
  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      padding: '0 0.25rem',
    }}>
      <span style={{
        color: 'rgba(255,255,255,0.6)',
        fontSize: '0.85rem',
      }}>
        →
      </span>
      <span style={{
        color: 'rgba(255,255,255,0.5)',
        fontSize: '0.6rem',
        marginTop: '0.1rem',
      }}>
        {label || `${jumps}J`}
      </span>
    </div>
  );
}

function ConnectionsTable({ connections }: { connections: TheraConnection[] }) {
  const theraConns = connections.filter(c => c.out_system_name === 'Thera');
  const turnurConns = connections.filter(c => c.out_system_name === 'Turnur');

  return (
    <div style={{ marginTop: '1.5rem' }}>
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '0.75rem',
      }}>
        <h3 style={{ margin: 0, fontSize: '0.9rem', fontWeight: 600 }}>
          Active Connections
        </h3>
        <div style={{ display: 'flex', gap: '1rem', fontSize: '0.75rem' }}>
          <span style={{ color: '#ffcc00' }}>
            Thera: <strong>{theraConns.length}</strong>
          </span>
          <span style={{ color: '#00d4ff' }}>
            Turnur: <strong>{turnurConns.length}</strong>
          </span>
        </div>
      </div>

      <div style={{
        background: 'rgba(0,0,0,0.2)',
        borderRadius: '6px',
        overflow: 'hidden',
      }}>
        {/* Header */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1.2fr 0.6fr 0.7fr 0.5fr 0.6fr',
          padding: '0.5rem 0.75rem',
          background: 'rgba(255,255,255,0.05)',
          fontSize: '0.65rem',
          fontWeight: 600,
          color: 'rgba(255,255,255,0.5)',
          textTransform: 'uppercase',
        }}>
          <span>System</span>
          <span>Region</span>
          <span>Sec</span>
          <span>Ship Size</span>
          <span>Hub</span>
          <span>Expires</span>
        </div>

        {/* Rows */}
        <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
          {connections.length === 0 ? (
            <div style={{
              padding: '2rem',
              textAlign: 'center',
              color: 'rgba(255,255,255,0.4)',
            }}>
              No connections available
            </div>
          ) : (
            connections.map((conn, idx) => (
              <div
                key={conn.id}
                style={{
                  display: 'grid',
                  gridTemplateColumns: '1fr 1.2fr 0.6fr 0.7fr 0.5fr 0.6fr',
                  padding: '0.5rem 0.75rem',
                  fontSize: '0.75rem',
                  borderTop: idx > 0 ? '1px solid rgba(255,255,255,0.05)' : 'none',
                  background: idx % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.02)',
                }}
              >
                <span style={{ fontWeight: 500 }}>{conn.in_system_name}</span>
                <span style={{ color: 'rgba(255,255,255,0.6)' }}>{conn.in_region_name}</span>
                <span style={{
                  display: 'inline-block',
                  padding: '0.1rem 0.3rem',
                  borderRadius: '3px',
                  background: `${getClassColor(conn.in_system_class)}20`,
                  color: getClassColor(conn.in_system_class),
                  fontWeight: 600,
                  fontSize: '0.65rem',
                  textTransform: 'uppercase',
                }}>
                  {conn.in_system_class}
                </span>
                <span style={{
                  color: SIZE_COLORS[conn.max_ship_size],
                  fontSize: '0.7rem',
                }}>
                  {SIZE_LABELS[conn.max_ship_size]}
                </span>
                <span style={{
                  color: conn.out_system_name === 'Thera' ? '#ffcc00' : '#00d4ff',
                  fontSize: '0.7rem',
                }}>
                  {conn.out_system_name === 'Thera' ? 'T' : 'TR'}
                </span>
                <span style={{
                  color: conn.remaining_hours <= 2 ? '#ff4444' : conn.remaining_hours <= 6 ? '#ffcc00' : 'rgba(255,255,255,0.6)',
                  fontFamily: 'monospace',
                  fontSize: '0.7rem',
                }}>
                  {formatHours(conn.remaining_hours)}
                </span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

// Main component
export function TheraRouterTab() {
  // State
  const [fromSystem, setFromSystem] = useState('');
  const [toSystem, setToSystem] = useState('');
  const [shipSize, setShipSize] = useState<ShipSize>('large');
  const [route, setRoute] = useState<TheraRoute | null>(null);
  const [connections, setConnections] = useState<TheraConnection[]>([]);
  const [status, setStatus] = useState<TheraStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch connections and status on mount
  useEffect(() => {
    const fetchData = async () => {
      try {
        const [connData, statusData] = await Promise.all([
          wormholeApi.getTheraConnections('all'),
          wormholeApi.getTheraStatus(),
        ]);
        setConnections(connData.connections);
        setStatus(statusData);
      } catch (err) {
        console.error('Failed to fetch Thera data:', err);
      }
    };
    fetchData();
  }, []);

  // Calculate route
  const handleCalculate = async () => {
    if (!fromSystem.trim() || !toSystem.trim()) {
      setError('Please enter both origin and destination systems');
      return;
    }

    setLoading(true);
    setError(null);
    setRoute(null);

    try {
      const result = await wormholeApi.calculateTheraRoute(
        fromSystem.trim(),
        toSystem.trim(),
        shipSize
      );
      setRoute(result);
    } catch (err: any) {
      console.error('Route calculation failed:', err);
      setError(err.response?.data?.detail || 'Failed to calculate route');
    } finally {
      setLoading(false);
    }
  };

  // Handle enter key
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !loading) {
      handleCalculate();
    }
  };

  return (
    <div style={{ padding: '1rem 0' }}>
      {/* Status */}
      {status && (
        <div style={{ marginBottom: '1rem' }}>
          <StatusBadge status={status} />
        </div>
      )}

      {/* Route Calculator */}
      <div style={{
        background: 'rgba(0,0,0,0.2)',
        borderRadius: '8px',
        padding: '1rem',
      }}>
        <h3 style={{
          margin: '0 0 1rem 0',
          fontSize: '0.85rem',
          fontWeight: 600,
          color: 'rgba(255,255,255,0.8)',
        }}>
          Route Calculator
        </h3>

        {/* System Presets Datalist */}
        <datalist id="system-presets">
          <optgroup label="Trade Hubs">
            {SYSTEM_PRESETS.filter(s => s.type === 'trade').map(s => (
              <option key={s.name} value={s.name}>{s.region}</option>
            ))}
          </optgroup>
          <optgroup label="Nullsec Staging">
            {SYSTEM_PRESETS.filter(s => s.type === 'staging').map(s => (
              <option key={s.name} value={s.name}>{s.region}</option>
            ))}
          </optgroup>
          <optgroup label="Lowsec">
            {SYSTEM_PRESETS.filter(s => s.type === 'lowsec').map(s => (
              <option key={s.name} value={s.name}>{s.region}</option>
            ))}
          </optgroup>
        </datalist>

        <div style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr auto auto',
          gap: '0.75rem',
          alignItems: 'end',
        }}>
          {/* From System */}
          <div>
            <label style={{
              display: 'block',
              fontSize: '0.7rem',
              color: 'rgba(255,255,255,0.5)',
              marginBottom: '0.25rem',
            }}>
              From System
            </label>
            <input
              type="text"
              list="system-presets"
              value={fromSystem}
              onChange={(e) => setFromSystem(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type or select..."
              style={{
                width: '100%',
                padding: '0.5rem 0.75rem',
                background: 'rgba(0,0,0,0.3)',
                border: '1px solid rgba(255,255,255,0.1)',
                borderRadius: '4px',
                color: '#fff',
                fontSize: '0.85rem',
                outline: 'none',
              }}
            />
          </div>

          {/* To System */}
          <div>
            <label style={{
              display: 'block',
              fontSize: '0.7rem',
              color: 'rgba(255,255,255,0.5)',
              marginBottom: '0.25rem',
            }}>
              To System
            </label>
            <input
              type="text"
              list="system-presets"
              value={toSystem}
              onChange={(e) => setToSystem(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type or select..."
              style={{
                width: '100%',
                padding: '0.5rem 0.75rem',
                background: 'rgba(0,0,0,0.3)',
                border: '1px solid rgba(255,255,255,0.1)',
                borderRadius: '4px',
                color: '#fff',
                fontSize: '0.85rem',
                outline: 'none',
              }}
            />
          </div>

          {/* Ship Size */}
          <div>
            <label style={{
              display: 'block',
              fontSize: '0.7rem',
              color: 'rgba(255,255,255,0.5)',
              marginBottom: '0.25rem',
            }}>
              Ship Size
            </label>
            <select
              value={shipSize}
              onChange={(e) => setShipSize(e.target.value as ShipSize)}
              style={{
                padding: '0.5rem 0.75rem',
                background: 'rgba(0,0,0,0.3)',
                border: '1px solid rgba(255,255,255,0.1)',
                borderRadius: '4px',
                color: '#fff',
                fontSize: '0.85rem',
                cursor: 'pointer',
                outline: 'none',
              }}
            >
              <option value="medium">Medium</option>
              <option value="large">Large</option>
              <option value="xlarge">X-Large</option>
              <option value="capital">Capital</option>
            </select>
          </div>

          {/* Calculate Button */}
          <button
            onClick={handleCalculate}
            disabled={loading || !fromSystem.trim() || !toSystem.trim()}
            style={{
              padding: '0.5rem 1.5rem',
              background: loading ? 'rgba(255,255,255,0.1)' : '#ffcc00',
              border: 'none',
              borderRadius: '4px',
              color: loading ? 'rgba(255,255,255,0.5)' : '#000',
              fontSize: '0.85rem',
              fontWeight: 600,
              cursor: loading ? 'not-allowed' : 'pointer',
              transition: 'all 0.2s',
            }}
          >
            {loading ? 'Calculating...' : 'Calculate'}
          </button>
        </div>

        {/* Quick Select Buttons */}
        <div style={{
          marginTop: '0.75rem',
          display: 'flex',
          gap: '0.5rem',
          flexWrap: 'wrap',
          alignItems: 'center',
        }}>
          <span style={{
            fontSize: '0.65rem',
            color: 'rgba(255,255,255,0.4)',
            marginRight: '0.25rem',
          }}>
            Quick:
          </span>
          {/* Trade Hub Buttons */}
          {['Jita', 'Amarr', 'Dodixie', 'Rens'].map(hub => (
            <button
              key={hub}
              onClick={() => setToSystem(hub)}
              style={{
                padding: '0.2rem 0.5rem',
                background: toSystem === hub ? 'rgba(0,255,136,0.2)' : 'rgba(255,255,255,0.05)',
                border: toSystem === hub ? '1px solid rgba(0,255,136,0.4)' : '1px solid rgba(255,255,255,0.1)',
                borderRadius: '3px',
                color: toSystem === hub ? '#00ff88' : 'rgba(255,255,255,0.6)',
                fontSize: '0.7rem',
                cursor: 'pointer',
                transition: 'all 0.15s',
              }}
            >
              {hub}
            </button>
          ))}
          <span style={{
            width: '1px',
            height: '14px',
            background: 'rgba(255,255,255,0.2)',
            margin: '0 0.25rem',
          }} />
          {/* Staging Buttons */}
          {['1DQ1-A', 'K-6K16', 'GE-8JV'].map(staging => (
            <button
              key={staging}
              onClick={() => setToSystem(staging)}
              style={{
                padding: '0.2rem 0.5rem',
                background: toSystem === staging ? 'rgba(255,68,68,0.2)' : 'rgba(255,255,255,0.05)',
                border: toSystem === staging ? '1px solid rgba(255,68,68,0.4)' : '1px solid rgba(255,255,255,0.1)',
                borderRadius: '3px',
                color: toSystem === staging ? '#ff4444' : 'rgba(255,255,255,0.6)',
                fontSize: '0.7rem',
                cursor: 'pointer',
                transition: 'all 0.15s',
              }}
            >
              {staging}
            </button>
          ))}
        </div>

        {/* Error */}
        {error && (
          <div style={{
            marginTop: '1rem',
            padding: '0.5rem 0.75rem',
            background: 'rgba(255,68,68,0.2)',
            borderRadius: '4px',
            color: '#ff4444',
            fontSize: '0.8rem',
          }}>
            {error}
          </div>
        )}

        {/* Result */}
        {route && <RouteResult route={route} />}
      </div>

      {/* Connections Table */}
      <ConnectionsTable connections={connections} />
    </div>
  );
}
