import { useState, useEffect } from 'react';
import { freightApi } from '../../services/api/shopping';
import type { FreightRoute, FreightCalculation } from '../../types/shopping';

function formatIsk(value: number): string {
  return value.toLocaleString(undefined, { maximumFractionDigits: 0 }) + ' ISK';
}

function getTransportRecommendation(volumeM3: number): { label: string; color: string } {
  if (volumeM3 > 360_000) return { label: 'Jump Freighter', color: '#00d4ff' };
  if (volumeM3 > 60_000) return { label: 'Freighter', color: '#ff8800' };
  if (volumeM3 > 10_000) return { label: 'DST / Blockade Runner', color: '#d29922' };
  return { label: 'T1 Industrial', color: '#3fb950' };
}

function getRouteTypeBadge(routeType: string): { label: string; color: string } {
  const upper = routeType.toUpperCase();
  if (upper.includes('JF') || upper.includes('JUMP')) return { label: 'JF', color: '#00d4ff' };
  return { label: 'Hauler', color: '#3fb950' };
}

export function FreightCalculator() {
  const [routes, setRoutes] = useState<FreightRoute[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedRoute, setSelectedRoute] = useState<FreightRoute | null>(null);
  const [volume, setVolume] = useState<number>(0);
  const [collateral, setCollateral] = useState<number>(0);
  const [result, setResult] = useState<FreightCalculation | null>(null);
  const [calculating, setCalculating] = useState(false);
  const [hoveredRow, setHoveredRow] = useState<number | null>(null);

  useEffect(() => {
    freightApi.getRoutes(true)
      .then((data) => setRoutes(data.routes || []))
      .catch(() => setRoutes([]))
      .finally(() => setLoading(false));
  }, []);

  const handleSelectRoute = (route: FreightRoute) => {
    setSelectedRoute(route);
    setResult(null);
    setVolume(0);
    setCollateral(0);
  };

  const handleCalculate = async () => {
    if (!selectedRoute) return;
    setCalculating(true);
    try {
      const calc = await freightApi.calculate(selectedRoute.id, volume, collateral);
      setResult(calc);
    } catch {
      setResult(null);
    } finally {
      setCalculating(false);
    }
  };

  const volumeWarning = selectedRoute && volume > selectedRoute.max_volume;
  const collateralWarning = selectedRoute && collateral > selectedRoute.max_collateral;
  const transport = volume > 0 ? getTransportRecommendation(volume) : null;

  if (loading) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center', color: '#8b949e', fontSize: '0.85rem' }}>
        Loading routes...
      </div>
    );
  }

  if (routes.length === 0) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center', color: '#8b949e', fontSize: '0.85rem' }}>
        No freight routes available
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      {/* Routes Table */}
      <div style={{
        background: 'var(--bg-secondary)',
        border: '1px solid var(--border-color)',
        borderRadius: '8px',
        overflow: 'hidden',
      }}>
        <div style={{ padding: '0.75rem 1rem', borderBottom: '1px solid var(--border-color)' }}>
          <span style={{ fontSize: '0.85rem', fontWeight: 600, color: '#e6edf3' }}>
            Available Routes
          </span>
        </div>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-color)' }}>
                {['Route Name', 'From \u2192 To', 'Type', 'Base Price', 'Max Volume', 'Max Collateral'].map((h) => (
                  <th key={h} style={{
                    padding: '0.5rem 0.75rem',
                    textAlign: 'left',
                    color: '#8b949e',
                    fontWeight: 500,
                    fontSize: '0.7rem',
                    textTransform: 'uppercase',
                    letterSpacing: '0.04em',
                  }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {routes.map((route) => {
                const badge = getRouteTypeBadge(route.route_type);
                const isSelected = selectedRoute?.id === route.id;
                const isHovered = hoveredRow === route.id;
                return (
                  <tr
                    key={route.id}
                    onClick={() => handleSelectRoute(route)}
                    onMouseEnter={() => setHoveredRow(route.id)}
                    onMouseLeave={() => setHoveredRow(null)}
                    style={{
                      cursor: 'pointer',
                      borderBottom: '1px solid var(--border-color)',
                      border: isSelected ? '1px solid #00d4ff' : undefined,
                      background: isSelected
                        ? 'rgba(0, 212, 255, 0.06)'
                        : isHovered
                          ? 'rgba(255, 255, 255, 0.03)'
                          : 'transparent',
                      transition: 'background 0.15s',
                    }}
                  >
                    <td style={{ padding: '0.5rem 0.75rem', color: '#e6edf3' }}>
                      {route.name}
                      {route.notes && (
                        <div style={{ fontSize: '0.7rem', color: '#8b949e', marginTop: '2px' }}>
                          {route.notes}
                        </div>
                      )}
                    </td>
                    <td style={{ padding: '0.5rem 0.75rem', color: '#c9d1d9' }}>
                      {route.start_system_name || `System ${route.start_system_id}`}
                      {' \u2192 '}
                      {route.end_system_name || `System ${route.end_system_id}`}
                    </td>
                    <td style={{ padding: '0.5rem 0.75rem' }}>
                      <span style={{
                        display: 'inline-block',
                        padding: '2px 8px',
                        borderRadius: '4px',
                        fontSize: '0.7rem',
                        fontWeight: 600,
                        color: badge.color,
                        background: badge.color + '18',
                        border: `1px solid ${badge.color}44`,
                      }}>{badge.label}</span>
                    </td>
                    <td style={{ padding: '0.5rem 0.75rem', fontFamily: 'monospace', color: '#e6edf3' }}>
                      {formatIsk(route.base_price)}
                    </td>
                    <td style={{ padding: '0.5rem 0.75rem', fontFamily: 'monospace', color: '#c9d1d9' }}>
                      {route.max_volume.toLocaleString()} m\u00B3
                    </td>
                    <td style={{ padding: '0.5rem 0.75rem', fontFamily: 'monospace', color: '#c9d1d9' }}>
                      {formatIsk(route.max_collateral)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Calculator Panel */}
      {selectedRoute && (
        <div style={{
          background: 'var(--bg-secondary)',
          border: '1px solid var(--border-color)',
          borderRadius: '8px',
          padding: '1rem',
        }}>
          <div style={{ marginBottom: '1rem' }}>
            <span style={{ fontSize: '0.85rem', fontWeight: 600, color: '#00d4ff' }}>
              {selectedRoute.name}:
            </span>
            <span style={{ fontSize: '0.85rem', color: '#c9d1d9', marginLeft: '0.5rem' }}>
              {selectedRoute.start_system_name || `System ${selectedRoute.start_system_id}`}
              {' \u2192 '}
              {selectedRoute.end_system_name || `System ${selectedRoute.end_system_id}`}
            </span>
          </div>

          <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', alignItems: 'flex-start' }}>
            {/* Volume Input */}
            <div style={{ flex: '1 1 200px' }}>
              <label style={{ display: 'block', fontSize: '0.7rem', color: '#8b949e', marginBottom: '4px', textTransform: 'uppercase' }}>
                Volume (m\u00B3)
              </label>
              <input
                type="number"
                min={0}
                value={volume || ''}
                onChange={(e) => { setVolume(Number(e.target.value)); setResult(null); }}
                placeholder="0"
                style={{
                  width: '100%',
                  padding: '0.5rem 0.75rem',
                  background: 'var(--bg-primary)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '6px',
                  color: '#e6edf3',
                  fontFamily: 'monospace',
                  fontSize: '0.85rem',
                  outline: 'none',
                  boxSizing: 'border-box',
                }}
              />
              {volume > 0 && (
                <div style={{ fontSize: '0.7rem', color: '#8b949e', marginTop: '3px', fontFamily: 'monospace' }}>
                  {volume.toLocaleString()} m\u00B3
                </div>
              )}
              {volumeWarning && (
                <div style={{ fontSize: '0.7rem', color: '#d29922', marginTop: '3px' }}>
                  Exceeds max volume ({selectedRoute.max_volume.toLocaleString()} m\u00B3)
                </div>
              )}
            </div>

            {/* Collateral Input */}
            <div style={{ flex: '1 1 200px' }}>
              <label style={{ display: 'block', fontSize: '0.7rem', color: '#8b949e', marginBottom: '4px', textTransform: 'uppercase' }}>
                Collateral (ISK)
              </label>
              <input
                type="number"
                min={0}
                value={collateral || ''}
                onChange={(e) => { setCollateral(Number(e.target.value)); setResult(null); }}
                placeholder="0"
                style={{
                  width: '100%',
                  padding: '0.5rem 0.75rem',
                  background: 'var(--bg-primary)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '6px',
                  color: '#e6edf3',
                  fontFamily: 'monospace',
                  fontSize: '0.85rem',
                  outline: 'none',
                  boxSizing: 'border-box',
                }}
              />
              {collateral > 0 && (
                <div style={{ fontSize: '0.7rem', color: '#8b949e', marginTop: '3px', fontFamily: 'monospace' }}>
                  {formatIsk(collateral)}
                </div>
              )}
              {collateralWarning && (
                <div style={{ fontSize: '0.7rem', color: '#d29922', marginTop: '3px' }}>
                  Exceeds max collateral ({formatIsk(selectedRoute.max_collateral)})
                </div>
              )}
            </div>

            {/* Calculate Button */}
            <div style={{ flex: '0 0 auto', alignSelf: 'flex-end', paddingBottom: '2px' }}>
              <button
                onClick={handleCalculate}
                disabled={calculating || volume <= 0}
                style={{
                  padding: '0.5rem 1.5rem',
                  background: calculating || volume <= 0 ? '#21262d' : '#00d4ff',
                  color: calculating || volume <= 0 ? '#484f58' : '#0d1117',
                  border: 'none',
                  borderRadius: '6px',
                  fontWeight: 600,
                  fontSize: '0.85rem',
                  cursor: calculating || volume <= 0 ? 'not-allowed' : 'pointer',
                  transition: 'background 0.15s',
                }}
              >
                {calculating ? 'Calculating...' : 'Calculate'}
              </button>
            </div>
          </div>

          {/* Transport Recommendation */}
          {transport && (
            <div style={{ marginTop: '0.75rem', fontSize: '0.7rem', color: '#8b949e' }}>
              Recommended ship:{' '}
              <span style={{
                display: 'inline-block',
                padding: '1px 8px',
                borderRadius: '4px',
                fontWeight: 600,
                color: transport.color,
                background: transport.color + '18',
                border: `1px solid ${transport.color}44`,
                fontSize: '0.7rem',
              }}>{transport.label}</span>
            </div>
          )}

          {/* Result Card */}
          {result && (
            <div style={{
              marginTop: '1rem',
              background: 'var(--bg-primary)',
              border: '1px solid var(--border-color)',
              borderRadius: '8px',
              padding: '1rem',
            }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '0.7rem', color: '#8b949e', textTransform: 'uppercase' }}>Base Price</span>
                  <span style={{ fontFamily: 'monospace', fontSize: '0.85rem', color: '#c9d1d9' }}>
                    {formatIsk(result.base_price)}
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '0.7rem', color: '#8b949e', textTransform: 'uppercase' }}>
                    Volume Charge
                    <span style={{ fontSize: '0.65rem', marginLeft: '4px', opacity: 0.7 }}>
                      ({selectedRoute.rate_per_m3.toLocaleString()} ISK/m\u00B3)
                    </span>
                  </span>
                  <span style={{ fontFamily: 'monospace', fontSize: '0.85rem', color: '#c9d1d9' }}>
                    {formatIsk(result.volume_charge)}
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '0.7rem', color: '#8b949e', textTransform: 'uppercase' }}>
                    Collateral Charge
                    <span style={{ fontSize: '0.65rem', marginLeft: '4px', opacity: 0.7 }}>
                      ({(selectedRoute.collateral_pct * 100).toFixed(1)}%)
                    </span>
                  </span>
                  <span style={{ fontFamily: 'monospace', fontSize: '0.85rem', color: '#c9d1d9' }}>
                    {formatIsk(result.collateral_charge)}
                  </span>
                </div>

                {/* Divider */}
                <div style={{ borderTop: '1px solid var(--border-color)', margin: '0.25rem 0' }} />

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '0.85rem', fontWeight: 600, color: '#e6edf3' }}>Total Price</span>
                  <span style={{
                    fontFamily: 'monospace',
                    fontSize: '1.1rem',
                    fontWeight: 700,
                    color: '#00d4ff',
                  }}>
                    {formatIsk(result.price)}
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
