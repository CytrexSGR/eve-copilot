import { useState, useEffect } from 'react';
import { marketApi } from '../../services/api/market';
import type { ArbitrageRoutesResponse } from '../../types/market';
import { formatISKCompact } from '../../utils/format';
import { usePersonalizedScore } from '../../hooks/usePersonalizedScore';
import type { OpportunityInput } from '../../hooks/usePersonalizedScore';
import { RecommendationBanner } from '../recommendations';
import { useAuth } from '../../hooks/useAuth';

const CARGO_OPTIONS = [
  { label: 'Frigate (1K m\u00B3)', value: 1000 },
  { label: 'Hauler (5K m\u00B3)', value: 5000 },
  { label: 'T1 Indy (20K m\u00B3)', value: 20000 },
  { label: 'DST (60K m\u00B3)', value: 60000 },
  { label: 'Freighter (800K m\u00B3)', value: 800000 },
];

export function ArbitrageTab() {
  const { score } = usePersonalizedScore();
  const { isLoggedIn } = useAuth();
  const [routes, setRoutes] = useState<ArbitrageRoutesResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedRoute, setExpandedRoute] = useState<number | null>(null);

  // Filter state
  const [cargoCapacity, setCargoCapacity] = useState(60000);
  const [maxJumps, setMaxJumps] = useState(15);
  const [minProfit, setMinProfit] = useState(10_000_000);
  const [turnover, setTurnover] = useState<string>('');
  const [maxCompetition, setMaxCompetition] = useState<string>('');

  const fetchRoutes = () => {
    setLoading(true);
    setError(null);
    marketApi.getArbitrageRoutes({
      cargo_capacity: cargoCapacity,
      max_jumps: maxJumps,
      min_profit_per_trip: minProfit,
      turnover: turnover || undefined,
      max_competition: maxCompetition || undefined,
    })
      .then(setRoutes)
      .catch(err => setError(err.message || 'Failed to load routes'))
      .finally(() => setLoading(false));
  };

  // Auto-fetch on mount
  useEffect(() => { fetchRoutes(); }, []);

  const safetyColor = (s: string) =>
    s === 'safe' ? '#3fb950' : s === 'caution' ? '#ffcc00' : '#f85149';

  const riskColor = (r: string) =>
    r === 'low' ? '#3fb950' : r === 'medium' ? '#ffcc00' : '#f85149';

  return (
    <div>
      {/* Filter Bar */}
      <div style={{
        display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '1rem',
        padding: '0.5rem 0.75rem', background: 'rgba(0,0,0,0.3)',
        border: '1px solid rgba(255,255,255,0.08)', borderRadius: 8,
        alignItems: 'flex-end', minHeight: 42,
      }}>
        <div>
          <div style={{ fontSize: '0.55rem', color: '#6e7681', marginBottom: '0.15rem', textTransform: 'uppercase', fontWeight: 700, letterSpacing: '0.03em' }}>Cargo</div>
          <select
            value={cargoCapacity}
            onChange={e => setCargoCapacity(Number(e.target.value))}
            style={{
              padding: '0.3rem 0.4rem', background: 'rgba(0,0,0,0.4)',
              border: '1px solid rgba(255,255,255,0.1)', borderRadius: 4,
              color: '#c9d1d9', fontSize: '0.75rem', outline: 'none',
            }}
          >
            {CARGO_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </div>
        <div>
          <div style={{ fontSize: '0.55rem', color: '#6e7681', marginBottom: '0.15rem', textTransform: 'uppercase', fontWeight: 700, letterSpacing: '0.03em' }}>Max Jumps</div>
          <input type="number" value={maxJumps} onChange={e => setMaxJumps(Number(e.target.value))} min={1} max={50}
            style={{ width: 56, padding: '0.3rem 0.4rem', background: 'rgba(0,0,0,0.4)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 4, color: '#c9d1d9', fontSize: '0.75rem', outline: 'none' }}
          />
        </div>
        <div>
          <div style={{ fontSize: '0.55rem', color: '#6e7681', marginBottom: '0.15rem', textTransform: 'uppercase', fontWeight: 700, letterSpacing: '0.03em' }}>Min Profit</div>
          <select value={minProfit} onChange={e => setMinProfit(Number(e.target.value))}
            style={{ padding: '0.3rem 0.4rem', background: 'rgba(0,0,0,0.4)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 4, color: '#c9d1d9', fontSize: '0.75rem', outline: 'none' }}
          >
            <option value={1000000}>1M ISK</option>
            <option value={5000000}>5M ISK</option>
            <option value={10000000}>10M ISK</option>
            <option value={50000000}>50M ISK</option>
            <option value={100000000}>100M ISK</option>
          </select>
        </div>
        <div>
          <div style={{ fontSize: '0.55rem', color: '#6e7681', marginBottom: '0.15rem', textTransform: 'uppercase', fontWeight: 700, letterSpacing: '0.03em' }}>Turnover</div>
          <select value={turnover} onChange={e => setTurnover(e.target.value)}
            style={{ padding: '0.3rem 0.4rem', background: 'rgba(0,0,0,0.4)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 4, color: '#c9d1d9', fontSize: '0.75rem', outline: 'none' }}
          >
            <option value="">Any</option>
            <option value="instant">Instant</option>
            <option value="fast">Fast</option>
            <option value="moderate">Moderate</option>
          </select>
        </div>
        <div>
          <div style={{ fontSize: '0.55rem', color: '#6e7681', marginBottom: '0.15rem', textTransform: 'uppercase', fontWeight: 700, letterSpacing: '0.03em' }}>Competition</div>
          <select value={maxCompetition} onChange={e => setMaxCompetition(e.target.value)}
            style={{ padding: '0.3rem 0.4rem', background: 'rgba(0,0,0,0.4)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 4, color: '#c9d1d9', fontSize: '0.75rem', outline: 'none' }}
          >
            <option value="">Any</option>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
          </select>
        </div>
        <button onClick={fetchRoutes} disabled={loading}
          style={{
            padding: '0.3rem 0.9rem', background: loading ? 'rgba(0,0,0,0.4)' : 'transparent',
            border: '1px solid #00d4ff', borderRadius: 4, color: '#00d4ff',
            cursor: loading ? 'not-allowed' : 'pointer', fontSize: '0.75rem', fontWeight: 700,
            transition: 'background 0.15s',
          }}
          onMouseEnter={e => { if (!loading) (e.target as HTMLButtonElement).style.background = 'rgba(0,212,255,0.12)'; }}
          onMouseLeave={e => { if (!loading) (e.target as HTMLButtonElement).style.background = 'transparent'; }}
        >{loading ? 'Loading...' : 'Search Routes'}</button>
      </div>

      {/* Fee Assumption Banner */}
      {routes?.fee_assumptions && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: '0.5rem',
          padding: '0.3rem 0.75rem', marginBottom: '0.5rem',
          background: 'rgba(88,166,255,0.06)',
          border: '1px solid rgba(88,166,255,0.15)', borderRadius: 6,
          fontSize: '0.6rem', color: '#8b949e',
        }}>
          <span style={{ color: '#58a6ff', fontWeight: 700 }}>NET PROFIT</span>
          <span>after {routes.fee_assumptions.broker_fee_pct}% broker + {routes.fee_assumptions.sales_tax_pct}% tax</span>
          <span style={{ color: '#6e7681' }}>({routes.fee_assumptions.skill_assumption})</span>
        </div>
      )}

      {/* Error */}
      {error && (
        <div style={{
          padding: '0.6rem 1rem', background: 'rgba(248,81,73,0.1)',
          border: '1px solid rgba(248,81,73,0.3)', borderRadius: 8,
          color: '#f85149', marginBottom: '1rem', fontSize: '0.8rem',
        }}>
          {error}
        </div>
      )}

      {/* Loading */}
      {loading && <div className="skeleton" style={{ height: 300 }} />}

      {/* Route Results */}
      {!loading && routes && (
        <div>
          {routes.routes.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '3rem', color: '#6e7681', fontSize: '0.8rem' }}>
              No profitable routes found with current filters. Try adjusting min profit or max jumps.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {routes.routes.map((route, idx) => {
                const arbInput: OpportunityInput = {
                  type: 'arbitrage',
                  capitalRequired: route.summary.total_buy_cost,
                  estimatedProfit: route.summary.total_profit,
                  estimatedTimeHours: route.logistics.profit_per_hour > 0
                    ? route.summary.total_profit / route.logistics.profit_per_hour
                    : undefined,
                  cargoVolume: route.summary.total_volume,
                  recommendedShip: route.logistics.recommended_ship,
                  riskScore: route.route_risk === 'low' ? 15 : route.route_risk === 'medium' ? 50 : 80,
                };
                const arbPs = isLoggedIn ? score(arbInput) : null;
                return (
                <div key={idx} style={{
                  background: 'var(--bg-secondary)',
                  border: '1px solid var(--border-color)',
                  borderRadius: 8, overflow: 'hidden',
                }}>
                  {/* Route Header (clickable) */}
                  <div
                    onClick={() => setExpandedRoute(expandedRoute === idx ? null : idx)}
                    style={{
                      padding: '0.6rem 0.75rem', cursor: 'pointer',
                      display: 'flex', alignItems: 'center', gap: '0.75rem',
                      transition: 'background 0.15s',
                    }}
                    onMouseEnter={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.02)')}
                    onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                  >
                    {/* Left: destination + safety + jumps */}
                    <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                      <span style={{ fontWeight: 700, fontSize: '0.85rem', color: '#c9d1d9' }}>{route.destination_hub}</span>
                      <span style={{
                        fontSize: '0.55rem', padding: '1px 5px', borderRadius: 3,
                        background: `${safetyColor(route.safety)}22`,
                        border: `1px solid ${safetyColor(route.safety)}44`,
                        color: safetyColor(route.safety), fontWeight: 700,
                        textTransform: 'uppercase', letterSpacing: '0.03em',
                      }}>{route.safety}</span>
                      <span style={{ fontSize: '0.65rem', color: '#6e7681', fontFamily: 'monospace' }}>
                        {route.jumps}J
                      </span>
                      <span style={{ fontSize: '0.6rem', color: '#6e7681' }}>
                        {route.summary.total_items} items
                      </span>
                      {/* Compact personalized recommendation */}
                      {isLoggedIn && arbPs && <RecommendationBanner ps={arbPs} compact />}
                    </div>

                    {/* Right: stat badges */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexShrink: 0 }}>
                      <span style={{
                        padding: '0.15rem 0.4rem', borderRadius: 3,
                        background: 'rgba(63,185,80,0.12)', border: '1px solid rgba(63,185,80,0.25)',
                        color: '#3fb950', fontSize: '0.75rem', fontWeight: 700, fontFamily: 'monospace',
                      }}>
                        {formatISKCompact(route.summary.net_total_profit ?? route.summary.total_profit)}
                      </span>
                      <span style={{
                        padding: '0.15rem 0.4rem', borderRadius: 3,
                        background: 'rgba(255,204,0,0.12)', border: '1px solid rgba(255,204,0,0.25)',
                        color: '#ffcc00', fontSize: '0.75rem', fontWeight: 700, fontFamily: 'monospace',
                      }}>
                        {(route.summary.net_roi_percent ?? route.summary.roi_percent).toFixed(1)}%
                      </span>
                      <span style={{
                        padding: '0.15rem 0.4rem', borderRadius: 3,
                        background: 'rgba(139,148,158,0.1)', border: '1px solid rgba(139,148,158,0.2)',
                        color: '#c9d1d9', fontSize: '0.7rem', fontWeight: 600, fontFamily: 'monospace',
                      }}>
                        {formatISKCompact(route.summary.net_profit_per_jump ?? route.summary.profit_per_jump)}/J
                      </span>
                      <span style={{ color: '#6e7681', fontSize: '0.7rem', marginLeft: '0.25rem' }}>
                        {expandedRoute === idx ? '\u25B2' : '\u25BC'}
                      </span>
                    </div>
                  </div>

                  {/* Expanded: Item List */}
                  {expandedRoute === idx && (
                    <div style={{ borderTop: '1px solid var(--border-color)' }}>
                      {/* Logistics Summary - inline badges */}
                      <div style={{
                        display: 'flex', gap: '0.5rem', padding: '0.5rem 0.75rem',
                        flexWrap: 'wrap', alignItems: 'center',
                        borderBottom: '1px solid rgba(255,255,255,0.04)',
                        background: 'rgba(0,0,0,0.15)',
                      }}>
                        <span style={{
                          padding: '0.15rem 0.4rem', borderRadius: 3,
                          background: 'rgba(88,166,255,0.12)', border: '1px solid rgba(88,166,255,0.25)',
                          color: '#58a6ff', fontSize: '0.65rem', fontWeight: 600,
                        }}>
                          Ship: {route.logistics.recommended_ship}
                        </span>
                        <span style={{
                          padding: '0.15rem 0.4rem', borderRadius: 3,
                          background: 'rgba(139,148,158,0.1)', border: '1px solid rgba(139,148,158,0.2)',
                          color: '#c9d1d9', fontSize: '0.65rem', fontWeight: 600,
                        }}>
                          Trip: {route.logistics.round_trip_time}
                        </span>
                        <span style={{
                          padding: '0.15rem 0.4rem', borderRadius: 3,
                          background: 'rgba(63,185,80,0.12)', border: '1px solid rgba(63,185,80,0.25)',
                          color: '#3fb950', fontSize: '0.65rem', fontWeight: 700, fontFamily: 'monospace',
                        }}>
                          {formatISKCompact(route.logistics.net_profit_per_hour ?? route.logistics.profit_per_hour)}/h
                        </span>
                        <span style={{
                          padding: '0.15rem 0.4rem', borderRadius: 3,
                          background: `${riskColor(route.route_risk)}15`,
                          border: `1px solid ${riskColor(route.route_risk)}40`,
                          color: riskColor(route.route_risk), fontSize: '0.6rem', fontWeight: 700,
                          textTransform: 'uppercase', letterSpacing: '0.03em',
                        }}>
                          {route.route_risk} risk
                        </span>
                      </div>

                      {/* Items Table */}
                      <div style={{ padding: '0.25rem 0.5rem 0.5rem' }}>
                        {/* Table Header */}
                        <div style={{
                          display: 'grid', gridTemplateColumns: '2fr 1fr 1fr 1fr 0.8fr 0.8fr',
                          padding: '0.3rem 0.5rem', fontWeight: 700,
                          color: '#6e7681', borderBottom: '1px solid rgba(255,255,255,0.06)',
                          textTransform: 'uppercase', fontSize: '0.55rem', letterSpacing: '0.04em',
                        }}>
                          <span>Item</span><span style={{ textAlign: 'right' }}>Buy</span>
                          <span style={{ textAlign: 'right' }}>Sell</span><span style={{ textAlign: 'right' }}>Margin</span>
                          <span style={{ textAlign: 'right' }}>Qty</span><span style={{ textAlign: 'right' }}>Turnover</span>
                        </div>
                        {/* Table Rows */}
                        {route.items.slice(0, 20).map((item, i) => (
                          <div key={i} style={{
                            display: 'grid', gridTemplateColumns: '2fr 1fr 1fr 1fr 0.8fr 0.8fr',
                            padding: '0.25rem 0.5rem',
                            borderBottom: '1px solid rgba(255,255,255,0.03)',
                            fontSize: '0.7rem',
                          }}>
                            <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: '#c9d1d9' }}>
                              {item.type_name}
                            </span>
                            <span style={{ textAlign: 'right', fontFamily: 'monospace', color: '#f85149' }}>
                              {formatISKCompact(item.buy_price_source)}
                            </span>
                            <span style={{ textAlign: 'right', fontFamily: 'monospace', color: '#3fb950' }}>
                              {formatISKCompact(item.sell_price_dest)}
                            </span>
                            <span style={{
                              textAlign: 'right', fontFamily: 'monospace',
                              color: (item.net_margin_pct ?? 0) >= 5 ? '#3fb950'
                                : (item.net_margin_pct ?? 0) >= 2 ? '#ffcc00'
                                : '#f85149',
                            }}>
                              {item.net_margin_pct != null
                                ? `${item.net_margin_pct.toFixed(1)}%`
                                : item.buy_price_source > 0
                                  ? `${(((item.sell_price_dest - item.buy_price_source) / item.buy_price_source) * 100).toFixed(1)}%`
                                  : '—'}
                            </span>
                            <span style={{ textAlign: 'right', fontFamily: 'monospace', color: '#8b949e' }}>
                              {item.quantity.toLocaleString()}
                            </span>
                            <span style={{ textAlign: 'right', color: '#6e7681', textTransform: 'capitalize', fontSize: '0.65rem' }}>
                              {item.turnover}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
