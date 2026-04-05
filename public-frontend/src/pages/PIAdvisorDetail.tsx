import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import type { PIAdvisorOpportunity, PIAdvisorSkills, PlanetRecommendationItem } from '../types/production';
import { PI_PLANET_COLORS } from '../types/production';
import { formatISK } from '../utils/format';
import { piApi } from '../services/api/production';
import { PIProductionChainViz, buildChainDataFromAdvisor } from '../components/production/PIProductionChainViz';

const EVE_ICON = (typeId: number, size = 48) =>
  `https://images.evetech.net/types/${typeId}/icon?size=${size}`;

const TIER_BADGE_COLORS: Record<number, string> = {
  1: '#8b949e',
  2: '#3fb950',
  3: '#58a6ff',
  4: '#00d4ff',
};

function roiColor(roi: number): string {
  if (roi >= 20) return '#3fb950';
  if (roi >= 0) return '#d29922';
  return '#f85149';
}

interface LocationState {
  opportunity: PIAdvisorOpportunity;
  skills: PIAdvisorSkills;
}

export function PIAdvisorDetail() {
  const location = useLocation();
  const state = location.state as LocationState | null;

  if (!state?.opportunity) {
    return (
      <div style={{ maxWidth: 1200, margin: '0 auto', padding: '1.5rem 1rem' }}>
        <Link
          to="/production?tab=pi"
          style={{ color: '#00d4ff', textDecoration: 'none', fontSize: '0.85rem' }}
        >
          &larr; Back to PI Advisor
        </Link>
        <div style={{
          textAlign: 'center', padding: '3rem', marginTop: '2rem',
          background: 'var(--bg-secondary)', border: '1px solid var(--border-color)',
          borderRadius: 8, color: 'var(--text-secondary)',
        }}>
          <p>No opportunity data available. Navigate from the PI Advisor tab.</p>
        </div>
      </div>
    );
  }

  const opp = state.opportunity;
  const skills = state.skills;
  const chain = opp.production_chain || { p0_to_p1: {}, recipes: [] };
  const chainPrices = chain.prices || {};
  const chainTypeIds = chain.type_ids || {};

  // Build tier columns and connections
  const { columns: tierColumns, connections } = buildChainDataFromAdvisor(opp, chain);

  // Build P0 → planet_sources lookup
  const p0PlanetMap: Record<string, string[]> = {};
  for (const mat of opp.p0_materials || []) {
    p0PlanetMap[mat.type_name] = mat.planet_sources || [];
  }

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto', padding: '1.5rem 1rem' }}>
      {/* Back link */}
      <Link
        to="/production?tab=pi"
        style={{
          display: 'inline-flex', alignItems: 'center', gap: '0.5rem',
          marginBottom: '1rem', color: '#00d4ff', textDecoration: 'none', fontSize: '0.85rem',
        }}
      >
        &larr; Back to PI Advisor
      </Link>

      {/* Header card */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: '1rem',
        padding: '1rem 1.25rem', marginBottom: '1rem',
        background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: 8,
      }}>
        <img src={EVE_ICON(opp.type_id)} alt="" style={{ width: 48, height: 48, borderRadius: 8 }} />
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.35rem' }}>
            <span style={{ fontSize: '1.25rem', fontWeight: 700 }}>{opp.type_name}</span>
            <span style={{
              fontSize: '0.65rem', fontWeight: 700, padding: '2px 8px', borderRadius: 3,
              background: `${TIER_BADGE_COLORS[opp.tier]}22`,
              color: TIER_BADGE_COLORS[opp.tier],
            }}>P{opp.tier}</span>
          </div>
          <div style={{
            display: 'flex', gap: '1.25rem', flexWrap: 'wrap',
            fontSize: '0.8rem', fontFamily: 'monospace',
          }}>
            <span>Cost: <span style={{ color: '#f85149' }}>{formatISK(opp.input_cost)}</span></span>
            <span style={{ color: 'var(--text-secondary)' }}>&rarr;</span>
            <span>Value: <span style={{ color: '#3fb950' }}>{formatISK(opp.output_value)}</span></span>
            <span style={{ color: 'var(--text-secondary)' }}>&rarr;</span>
            <span>Profit: <span style={{ color: '#00d4ff' }}>{formatISK(opp.profit_per_hour)}/h</span></span>
            <span>ROI: <span style={{ color: roiColor(opp.roi_percent) }}>{opp.roi_percent.toFixed(1)}%</span></span>
          </div>
        </div>
      </div>

      {/* Feasibility bar */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap',
        padding: '0.65rem 1.25rem', marginBottom: '1rem',
        background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: 8,
        fontSize: '0.75rem',
      }}>
        <FeasibilityBadge
          label="Self-sufficient"
          feasible={opp.self_sufficient_feasible}
          planets={opp.self_sufficient_planets}
          maxPlanets={skills.max_planets}
        />
        <FeasibilityBadge
          label="Market buy"
          feasible={opp.market_buy_feasible}
          planets={opp.market_buy_planets}
          maxPlanets={skills.max_planets}
        />
        <span style={{ color: 'var(--text-secondary)', fontSize: '0.7rem' }}>|</span>
        <span style={{ color: 'var(--text-secondary)' }}>
          Strategy: <span style={{ color: '#ccc', fontWeight: 600 }}>{opp.production_layout.strategy.replace(/_/g, ' ')}</span>
        </span>
        <span style={{ color: '#8b949e', fontSize: '0.7rem', fontStyle: 'italic' }}>
          {opp.production_layout.summary}
        </span>
      </div>

      {/* Horizontal Production Chain with SVG connections */}
      <PIProductionChainViz
        tierColumns={tierColumns}
        connections={connections}
        finalProduct={{ name: opp.type_name, tier: opp.tier }}
        p0PlanetMap={p0PlanetMap}
        chainPrices={chainPrices}
        chainTypeIds={chainTypeIds}
      />

      {/* Extraction Planets */}
      {opp.optimal_planets && opp.optimal_planets.length > 0 && (
        <div style={{
          padding: '1rem 1.25rem',
          background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: 8,
        }}>
          <div style={{
            fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase',
            color: 'var(--text-secondary)', letterSpacing: '0.05em', marginBottom: '0.75rem',
          }}>
            Extraction Planets ({opp.optimal_planets.length})
          </div>

          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            {opp.optimal_planets.map(planet => {
              const pColor = PI_PLANET_COLORS[planet.planet_type] || '#8b949e';
              return (
                <div key={planet.planet_type} style={{
                  flex: '1 1 0', minWidth: 180,
                  padding: '0.35rem 0.5rem',
                  background: 'rgba(255,255,255,0.03)',
                  border: '1px solid rgba(255,255,255,0.06)',
                  borderLeft: `3px solid ${pColor}`,
                  borderRadius: 4,
                }}>
                  <span style={{
                    display: 'inline-block', fontSize: '0.6rem', fontWeight: 700, padding: '2px 8px',
                    borderRadius: 3, background: `${pColor}15`, border: `1px solid ${pColor}33`,
                    color: pColor, textTransform: 'capitalize', marginBottom: '0.3rem',
                  }}>
                    {planet.planet_type}
                  </span>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
                    {planet.provides.map(p0Name => {
                      const p1Name = chain.p0_to_p1[p0Name];
                      return (
                        <div key={p0Name} style={{
                          display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.75rem',
                        }}>
                          <span style={{ color: '#8b949e' }}>{p0Name}</span>
                          {p1Name && (
                            <>
                              <span style={{ color: 'var(--text-secondary)', fontSize: '0.65rem' }}>&rarr;</span>
                              <span style={{ color: '#ccc', fontWeight: 600 }}>{p1Name}</span>
                            </>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* System Finder */}
      <SystemFinder requiredPlanetTypes={opp.required_planet_types || []} />
    </div>
  );
}

// --- System Finder: find nearby systems with required planet types ---

interface SystemGroup {
  system_name: string;
  system_id: number;
  security: number;
  jumps: number;
  planets: PlanetRecommendationItem[];
  matchingTypes: string[];
  coverage: number;
}

function SystemFinder({ requiredPlanetTypes }: { requiredPlanetTypes: string[] }) {
  const [systemName, setSystemName] = useState('');
  const [jumpRange, setJumpRange] = useState(5);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<SystemGroup[] | null>(null);
  const [searchInfo, setSearchInfo] = useState<{ center: string; radius: number; systemsSearched: number } | null>(null);

  const requiredSet = new Set(requiredPlanetTypes.map(t => t.toLowerCase()));

  const handleSearch = async () => {
    const name = systemName.trim();
    if (!name) return;

    setLoading(true);
    setError(null);
    setResults(null);
    setSearchInfo(null);

    try {
      const data = await piApi.recommendPlanets({ system_name: name, jump_range: jumpRange });

      setSearchInfo({
        center: data.search_center,
        radius: data.search_radius,
        systemsSearched: data.systems_searched,
      });

      // Group planets by system
      const systemMap = new Map<number, SystemGroup>();

      for (const planet of data.recommendations) {
        let group = systemMap.get(planet.system_id);
        if (!group) {
          group = {
            system_name: planet.system_name,
            system_id: planet.system_id,
            security: planet.security,
            jumps: planet.jumps_from_home,
            planets: [],
            matchingTypes: [],
            coverage: 0,
          };
          systemMap.set(planet.system_id, group);
        }
        group.planets.push(planet);
      }

      // Calculate coverage per system
      for (const group of systemMap.values()) {
        const typesInSystem = new Set(group.planets.map(p => p.planet_type.toLowerCase()));
        group.matchingTypes = [...typesInSystem].filter(t => requiredSet.has(t));
        group.coverage = group.matchingTypes.length;
      }

      // Filter to systems that have at least 1 matching type, sort by coverage desc then jumps asc
      const sorted = [...systemMap.values()]
        .filter(g => g.coverage > 0)
        .sort((a, b) => b.coverage - a.coverage || a.jumps - b.jumps);

      setResults(sorted);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Search failed';
      if (typeof err === 'object' && err !== null && 'response' in err) {
        const resp = (err as { response?: { data?: { detail?: string } } }).response;
        setError(resp?.data?.detail || msg);
      } else {
        setError(msg);
      }
    } finally {
      setLoading(false);
    }
  };

  const secColor = (sec: number) => {
    if (sec >= 0.5) return '#3fb950';
    if (sec >= 0.0) return '#d29922';
    return '#f85149';
  };

  return (
    <div style={{
      padding: '1rem 1.25rem', marginTop: '1rem',
      background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: 8,
    }}>
      <div style={{
        fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase',
        color: 'var(--text-secondary)', letterSpacing: '0.05em', marginBottom: '0.75rem',
      }}>
        Find Nearby Systems
      </div>

      {/* Search bar */}
      <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap', marginBottom: '0.5rem' }}>
        <input
          type="text"
          value={systemName}
          onChange={e => setSystemName(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleSearch()}
          placeholder="System name (e.g. Jita)"
          style={{
            flex: '1 1 160px', minWidth: 120, padding: '0.4rem 0.6rem',
            background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.15)',
            borderRadius: 4, color: '#ccc', fontSize: '0.8rem', outline: 'none',
          }}
        />
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', fontSize: '0.75rem', color: '#8b949e' }}>
          <span>Range:</span>
          <select
            value={jumpRange}
            onChange={e => setJumpRange(Number(e.target.value))}
            style={{
              padding: '0.35rem 0.4rem', background: '#1a1a2e',
              border: '1px solid rgba(255,255,255,0.15)', borderRadius: 4, color: '#ccc',
              fontSize: '0.75rem', outline: 'none',
            }}
          >
            {[3, 5, 7, 10, 15].map(n => (
              <option key={n} value={n} style={{ background: '#1a1a2e', color: '#ccc' }}>{n}j</option>
            ))}
          </select>
        </div>
        <button
          onClick={handleSearch}
          disabled={loading || !systemName.trim()}
          style={{
            padding: '0.4rem 0.8rem', background: loading ? '#333' : '#00d4ff22',
            border: '1px solid #00d4ff44', borderRadius: 4, color: '#00d4ff',
            fontSize: '0.75rem', fontWeight: 600, cursor: loading ? 'wait' : 'pointer',
            opacity: !systemName.trim() ? 0.4 : 1,
          }}
        >
          {loading ? 'Searching...' : 'Search'}
        </button>
      </div>

      {/* Required types hint */}
      {requiredPlanetTypes.length > 0 && (
        <div style={{ display: 'flex', gap: '0.3rem', flexWrap: 'wrap', marginBottom: '0.5rem', alignItems: 'center' }}>
          <span style={{ fontSize: '0.65rem', color: '#6e7681' }}>Looking for:</span>
          {requiredPlanetTypes.map(pt => {
            const c = PI_PLANET_COLORS[pt] || '#8b949e';
            return (
              <span key={pt} style={{
                fontSize: '0.55rem', fontWeight: 700, padding: '1px 5px',
                borderRadius: 2, background: `${c}15`, border: `1px solid ${c}33`,
                color: c, textTransform: 'capitalize',
              }}>
                {pt}
              </span>
            );
          })}
        </div>
      )}

      {error && (
        <div style={{ fontSize: '0.75rem', color: '#f85149', padding: '0.5rem 0' }}>{error}</div>
      )}

      {/* Results */}
      {results !== null && (
        <div>
          {searchInfo && (
            <div style={{ fontSize: '0.65rem', color: '#6e7681', marginBottom: '0.5rem' }}>
              {results.length} systems with matching planets within {searchInfo.radius}j of {searchInfo.center}
              {' '}({searchInfo.systemsSearched} systems searched)
            </div>
          )}

          {results.length === 0 ? (
            <div style={{ fontSize: '0.75rem', color: '#8b949e', padding: '0.5rem 0' }}>
              No systems found with required planet types in range.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
              {results.slice(0, 25).map(sys => (
                <div key={sys.system_id} style={{
                  display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap',
                  padding: '0.35rem 0.5rem',
                  background: sys.coverage === requiredPlanetTypes.length
                    ? 'rgba(63,185,80,0.06)'
                    : 'rgba(255,255,255,0.02)',
                  border: `1px solid ${sys.coverage === requiredPlanetTypes.length
                    ? 'rgba(63,185,80,0.2)' : 'rgba(255,255,255,0.06)'}`,
                  borderRadius: 4,
                }}>
                  {/* System name */}
                  <span style={{
                    fontSize: '0.8rem', fontWeight: 600, color: '#ccc', minWidth: 100,
                  }}>
                    {sys.system_name}
                  </span>

                  {/* Security */}
                  <span style={{
                    fontSize: '0.65rem', fontFamily: 'monospace', fontWeight: 700,
                    color: secColor(sys.security), minWidth: 32,
                  }}>
                    {sys.security.toFixed(2)}
                  </span>

                  {/* Jumps */}
                  <span style={{
                    fontSize: '0.65rem', color: '#6e7681', minWidth: 28,
                  }}>
                    {sys.jumps}j
                  </span>

                  {/* Coverage badge */}
                  <span style={{
                    fontSize: '0.6rem', fontWeight: 700, padding: '1px 5px', borderRadius: 3,
                    background: sys.coverage === requiredPlanetTypes.length
                      ? 'rgba(63,185,80,0.15)' : 'rgba(255,255,255,0.06)',
                    color: sys.coverage === requiredPlanetTypes.length ? '#3fb950'
                      : sys.coverage >= requiredPlanetTypes.length / 2 ? '#d29922' : '#8b949e',
                  }}>
                    {sys.coverage}/{requiredPlanetTypes.length}
                  </span>

                  {/* Planet type badges */}
                  <div style={{ display: 'flex', gap: '0.2rem', flexWrap: 'wrap', flex: 1 }}>
                    {requiredPlanetTypes.map(pt => {
                      const has = sys.matchingTypes.includes(pt.toLowerCase());
                      const c = PI_PLANET_COLORS[pt] || '#8b949e';
                      const count = sys.planets.filter(p => p.planet_type.toLowerCase() === pt.toLowerCase()).length;
                      return (
                        <span key={pt} style={{
                          fontSize: '0.55rem', fontWeight: 700, padding: '1px 5px',
                          borderRadius: 2, textTransform: 'capitalize',
                          background: has ? `${c}15` : 'transparent',
                          border: `1px solid ${has ? c + '44' : 'rgba(255,255,255,0.08)'}`,
                          color: has ? c : '#444',
                          opacity: has ? 1 : 0.4,
                        }}>
                          {pt}{has && count > 1 ? ` ×${count}` : ''}
                        </span>
                      );
                    })}
                  </div>
                </div>
              ))}
              {results.length > 25 && (
                <div style={{ fontSize: '0.65rem', color: '#6e7681', textAlign: 'center', padding: '0.25rem' }}>
                  ... and {results.length - 25} more systems
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// --- Helper: Feasibility badge ---
function FeasibilityBadge({ label, feasible, planets, maxPlanets }: {
  label: string; feasible: boolean; planets: number; maxPlanets: number;
}) {
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: '0.3rem',
    }}>
      <span style={{ color: 'var(--text-secondary)' }}>{label}:</span>
      <span style={{
        fontWeight: 600, padding: '1px 6px', borderRadius: 3,
        background: feasible ? 'rgba(63,185,80,0.12)' : 'rgba(248,81,73,0.12)',
        color: feasible ? '#3fb950' : '#f85149',
        fontSize: '0.7rem',
      }}>
        {feasible ? `\u2713 ${planets}p` : `\u2717 need ${planets}p (max ${maxPlanets})`}
      </span>
    </span>
  );
}
