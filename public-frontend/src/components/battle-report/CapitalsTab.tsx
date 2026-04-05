import { useState, useEffect } from 'react';
import { warApi } from '../../services/api';
import type { AllianceCapitalDetailExtended } from '../../types/reports';
import { RACE_COLORS, SHIP_CLASS_COLORS } from '../../constants/battleReport';

export function CapitalsTab() {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [capitalIntel, setCapitalIntel] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [expandedAlliance, setExpandedAlliance] = useState<number | null>(null);
  const [allianceDetails, setAllianceDetails] = useState<Map<number, AllianceCapitalDetailExtended>>(new Map());
  const [detailLoading, setDetailLoading] = useState<number | null>(null);

  useEffect(() => {
    const fetchCapitalIntel = async () => {
      try {
        setLoading(true);
        const data = await warApi.getCapitalIntel(30);
        setCapitalIntel(data);
      } catch (err) {
        console.error('Failed to load capital intel:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchCapitalIntel();
  }, []);

  const handleAllianceExpand = async (allianceId: number) => {
    if (expandedAlliance === allianceId) {
      setExpandedAlliance(null);
      return;
    }
    setExpandedAlliance(allianceId);
    if (!allianceDetails.has(allianceId)) {
      setDetailLoading(allianceId);
      try {
        const details = await warApi.getCapitalAllianceDetail(allianceId, 30);
        setAllianceDetails(prev => new Map(prev).set(allianceId, details));
      } catch (err) {
        console.error('Failed to load alliance detail:', err);
      }
      setDetailLoading(null);
    }
  };

  if (loading) {
    return (
      <div style={{
        background: 'linear-gradient(135deg, rgba(15,20,30,0.95) 0%, rgba(20,25,35,0.9) 100%)',
        borderRadius: '12px',
        border: '1px solid rgba(100, 150, 255, 0.1)',
        padding: '1.5rem'
      }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1rem' }}>
          {[1, 2, 3].map(i => <div key={i} className="skeleton" style={{ height: '200px' }} />)}
        </div>
      </div>
    );
  }

  if (!capitalIntel) {
    return (
      <div style={{
        background: 'linear-gradient(135deg, rgba(15,20,30,0.95) 0%, rgba(20,25,35,0.9) 100%)',
        borderRadius: '12px',
        border: '1px solid rgba(100, 150, 255, 0.1)',
        padding: '2rem',
        textAlign: 'center',
        color: 'rgba(255,255,255,0.4)'
      }}>
        Failed to load capital intelligence data
      </div>
    );
  }

  return (
    <div style={{
      background: 'linear-gradient(135deg, rgba(15,20,30,0.95) 0%, rgba(20,25,35,0.9) 100%)',
      borderRadius: '12px',
      border: '1px solid rgba(100, 150, 255, 0.1)',
      padding: '1.5rem'
    }}>
      <div style={{ display: 'grid', gap: '1.5rem' }}>
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <span style={{ fontSize: '1.25rem' }}>🚀</span>
          <h2 style={{ margin: 0, fontSize: '1rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: '#00ff88' }}>Capital Intelligence</h2>
          <span style={{ marginLeft: 'auto', fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase' }}>
            30-Day Activity
          </span>
        </div>

        {/* Summary Stats */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '1rem' }}>
          <SummaryCard
            label="Capital Engagements"
            value={capitalIntel.summary.total_engagements.toLocaleString()}
            color="#ff8800"
          />
          <SummaryCard
            label="Active Alliances"
            value={capitalIntel.summary.unique_alliances}
            color="#a855f7"
          />
          <SummaryCard
            label="Systems Active"
            value={capitalIntel.summary.systems_active}
            color="#00d4ff"
          />
        </div>

        {/* Top Capital Operators */}
        <div>
          <div style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.75rem' }}>
            Top Capital Operators
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {capitalIntel.top_alliances.slice(0, 10).map((alliance: { alliance_id: number; alliance_name: string; ticker: string; total_caps: number; titans: number; supers: number; dreads: number }) => (
              <AllianceCard
                key={alliance.alliance_id}
                alliance={alliance}
                isExpanded={expandedAlliance === alliance.alliance_id}
                isLoading={detailLoading === alliance.alliance_id}
                details={allianceDetails.get(alliance.alliance_id)}
                onToggle={() => handleAllianceExpand(alliance.alliance_id)}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function SummaryCard({ label, value, color }: { label: string; value: string | number; color: string }) {
  return (
    <div style={{
      padding: '1.25rem',
      background: `linear-gradient(135deg, ${color}08 0%, transparent 100%)`,
      borderRadius: '8px',
      border: `1px solid ${color}33`,
      borderLeft: `3px solid ${color}`,
      textAlign: 'center'
    }}>
      <p style={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.5rem' }}>{label}</p>
      <p style={{ fontSize: '2.25rem', fontWeight: 800, color, margin: 0, fontFamily: 'monospace', lineHeight: 1 }}>{value}</p>
    </div>
  );
}

interface AllianceCardProps {
  alliance: { alliance_id: number; alliance_name: string; ticker: string; total_caps: number; titans: number; supers: number; dreads: number };
  isExpanded: boolean;
  isLoading: boolean;
  details?: AllianceCapitalDetailExtended;
  onToggle: () => void;
}

function AllianceCard({ alliance, isExpanded, isLoading, details, onToggle }: AllianceCardProps) {
  return (
    <div
      style={{
        background: 'rgba(0,0,0,0.3)',
        borderRadius: '8px',
        border: '1px solid rgba(255,255,255,0.05)',
        overflow: 'hidden'
      }}
    >
      {/* Collapsed Header */}
      <div
        onClick={onToggle}
        style={{
          padding: '1rem',
          cursor: 'pointer',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <img
            src={`https://images.evetech.net/alliances/${alliance.alliance_id}/logo?size=64`}
            alt=""
            style={{ width: 40, height: 40, borderRadius: 4, border: '1px solid rgba(255,255,255,0.1)' }}
            onError={(e) => { e.currentTarget.style.display = 'none'; }}
          />
          <div>
            <div style={{ fontWeight: 600, marginBottom: '0.25rem', color: '#fff' }}>
              <span style={{ color: '#00d4ff' }}>[{alliance.ticker}]</span> {alliance.alliance_name}
            </div>
            <div style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.4)' }}>
              {details?.regions?.[0]?.region || 'Loading...'} {details?.regions?.[0]?.last_seen ? `• ${Math.floor((Date.now() - new Date(details.regions[0].last_seen).getTime()) / 3600000)}h ago` : ''}
            </div>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{ display: 'flex', gap: '1rem', fontSize: '0.8rem' }}>
            <span><span style={{ color: '#ff4444', fontWeight: 700, fontFamily: 'monospace' }}>{alliance.titans}</span> <span style={{ color: 'rgba(255,255,255,0.4)' }}>Titans</span></span>
            <span><span style={{ color: '#ff8800', fontWeight: 700, fontFamily: 'monospace' }}>{alliance.supers}</span> <span style={{ color: 'rgba(255,255,255,0.4)' }}>Supers</span></span>
            <span><span style={{ color: '#00d4ff', fontWeight: 700, fontFamily: 'monospace' }}>{alliance.dreads}</span> <span style={{ color: 'rgba(255,255,255,0.4)' }}>Dreads</span></span>
          </div>
          <span style={{ fontSize: '1rem', color: 'rgba(255,255,255,0.3)' }}>
            {isLoading ? '...' : isExpanded ? '▼' : '▶'}
          </span>
        </div>
      </div>

      {/* Expanded Content */}
      {isExpanded && details && (
        <ExpandedDetails details={details} />
      )}

      {/* Loading State */}
      {isExpanded && isLoading && (
        <div style={{
          padding: '2rem',
          borderTop: '1px solid rgba(255,255,255,0.05)',
          background: 'rgba(0,0,0,0.2)',
          textAlign: 'center',
          color: 'rgba(255,255,255,0.4)'
        }}>
          Loading alliance intel...
        </div>
      )}
    </div>
  );
}

function ExpandedDetails({ details }: { details: AllianceCapitalDetailExtended }) {
  return (
    <div style={{
      padding: '1rem',
      borderTop: '1px solid rgba(255,255,255,0.05)',
      background: 'rgba(0,0,0,0.2)',
      display: 'grid',
      gridTemplateColumns: 'repeat(2, 1fr)',
      gap: '1rem'
    }}>
      {/* Top Corps */}
      <div style={{ background: 'rgba(0,0,0,0.2)', borderRadius: '6px', padding: '0.75rem', border: '1px solid rgba(255,255,255,0.05)' }}>
        <div style={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.5rem' }}>
          Top Corps
        </div>
        {details.top_corps.slice(0, 3).map((corp) => {
          const pct = details.summary.total_engagements > 0
            ? Math.round((corp.engagements / details.summary.total_engagements) * 100)
            : 0;
          return (
            <div key={corp.corporation_id} style={{ marginBottom: '0.5rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: '0.25rem' }}>
                <span style={{ color: '#fff' }}>{corp.corporation_name}</span>
                <span style={{ color: '#00ff88', fontFamily: 'monospace' }}>{pct}%</span>
              </div>
              <div style={{ height: '4px', background: 'rgba(255,255,255,0.1)', borderRadius: '2px', overflow: 'hidden' }}>
                <div style={{ width: `${pct}%`, height: '100%', background: 'linear-gradient(90deg, #00d4ff, #00ff88)' }} />
              </div>
              <div style={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.3)', marginTop: '0.15rem' }}>
                {corp.engagements} ops • {corp.ships_used.slice(0, 2).join(', ')}
              </div>
            </div>
          );
        })}
      </div>

      {/* Fleet Composition */}
      <div style={{ background: 'rgba(0,0,0,0.2)', borderRadius: '6px', padding: '0.75rem', border: '1px solid rgba(255,255,255,0.05)' }}>
        <div style={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.5rem' }}>
          Fleet Composition
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
          {/* Race Distribution */}
          <div>
            <div style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.3)', marginBottom: '0.25rem' }}>By Race</div>
            {Object.entries(details.race_distribution)
              .filter(([, count]) => count > 0)
              .sort(([, a], [, b]) => b - a)
              .map(([race, count]) => {
                const total = Object.values(details.race_distribution).reduce((a, b) => a + b, 0);
                const pct = total > 0 ? Math.round((count / total) * 100) : 0;
                return (
                  <div key={race} style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', fontSize: '0.7rem', marginBottom: '0.15rem' }}>
                    <span style={{ width: 8, height: 8, borderRadius: '50%', background: RACE_COLORS[race] || '#888' }} />
                    <span style={{ color: 'rgba(255,255,255,0.7)' }}>{race.slice(0, 3)}</span>
                    <span style={{ color: 'rgba(255,255,255,0.4)', fontFamily: 'monospace' }}>{pct}%</span>
                  </div>
                );
              })}
          </div>
          {/* Ship Class Distribution */}
          <div>
            <div style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.3)', marginBottom: '0.25rem' }}>By Class</div>
            {['Dreadnought', 'Supercarrier', 'Titan'].map(cls => {
              const count = details.ships.filter(s => s.ship_class === cls).reduce((a, s) => a + s.engagements, 0);
              const total = details.summary.total_engagements;
              const pct = total > 0 ? Math.round((count / total) * 100) : 0;
              return pct > 0 ? (
                <div key={cls} style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', fontSize: '0.7rem', marginBottom: '0.15rem' }}>
                  <span style={{ width: 8, height: 8, borderRadius: '50%', background: SHIP_CLASS_COLORS[cls] }} />
                  <span style={{ color: 'rgba(255,255,255,0.7)' }}>{cls.slice(0, 5)}</span>
                  <span style={{ color: 'rgba(255,255,255,0.4)', fontFamily: 'monospace' }}>{pct}%</span>
                </div>
              ) : null;
            })}
          </div>
        </div>
      </div>

      {/* Timezone Pattern */}
      <div style={{ background: 'rgba(0,0,0,0.2)', borderRadius: '6px', padding: '0.75rem', border: '1px solid rgba(255,255,255,0.05)' }}>
        <div style={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.5rem' }}>
          Activity by Hour (EVE)
        </div>
        <div style={{ display: 'flex', alignItems: 'flex-end', height: '40px', gap: '2px' }}>
          {Array.from({ length: 24 }, (_, hour) => {
            const activity = details.hourly_activity?.find(h => h.hour === hour);
            const count = activity?.engagements || 0;
            const maxCount = Math.max(...(details.hourly_activity?.map(h => h.engagements) || [1]));
            const heightPct = maxCount > 0 ? (count / maxCount) * 100 : 0;
            return (
              <div
                key={hour}
                style={{
                  flex: 1,
                  height: `${Math.max(heightPct, 5)}%`,
                  background: heightPct > 70 ? '#ff8800' : '#00d4ff',
                  borderRadius: '1px',
                  opacity: heightPct > 0 ? 1 : 0.3
                }}
                title={`${hour}:00 - ${count} ops`}
              />
            );
          })}
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.55rem', color: 'rgba(255,255,255,0.3)', marginTop: '0.25rem' }}>
          <span>00</span><span>06</span><span>12</span><span>18</span><span>24</span>
        </div>
      </div>

      {/* Recent Activity */}
      <div style={{ background: 'rgba(0,0,0,0.2)', borderRadius: '6px', padding: '0.75rem', border: '1px solid rgba(255,255,255,0.05)' }}>
        <div style={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.5rem' }}>
          Recent Capital Kills
        </div>
        {details.recent_kills?.length > 0 ? (
          <div style={{ fontSize: '0.75rem' }}>
            {details.recent_kills.slice(0, 4).map((kill, idx) => (
              <div key={kill.killmail_id} style={{ marginBottom: '0.4rem', paddingBottom: '0.4rem', borderBottom: idx < 3 ? '1px solid rgba(255,255,255,0.05)' : 'none' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span>
                    <span style={{ color: '#ff8800' }}>{kill.attacker_ship}</span>
                    <span style={{ color: 'rgba(255,255,255,0.3)' }}> → </span>
                    <span style={{ color: '#ff4444' }}>{kill.victim_ship}</span>
                  </span>
                  <span style={{ color: 'rgba(255,255,255,0.3)', fontSize: '0.65rem', fontFamily: 'monospace' }}>
                    {new Date(kill.timestamp).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })}
                  </span>
                </div>
                <div style={{ color: 'rgba(255,255,255,0.3)', fontSize: '0.65rem' }}>
                  {kill.solar_system} • {kill.pilots_involved} pilot{kill.pilots_involved > 1 ? 's' : ''}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div style={{ color: 'rgba(255,255,255,0.3)', fontSize: '0.75rem' }}>No recent kills (7d)</div>
        )}
      </div>
    </div>
  );
}
