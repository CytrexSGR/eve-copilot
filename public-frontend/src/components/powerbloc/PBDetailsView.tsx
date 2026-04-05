/**
 * PowerBloc OverviewView Component
 *
 * Alliance-style layout: CombinedTimeline, 7 compact cards, participation trends,
 * burnout/attrition, alliance heatmap, and bottom 3-column section.
 */

import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { powerblocApi } from '../../services/api/powerbloc';
import type { PBDetailsResponse } from '../../types/powerbloc';
import { PBCombinedTimelineCard } from './PBCombinedTimelineCard';
import {
  OffensiveCard,
  DefensiveCard,
  CapitalCard,
  PilotCard,
  GeographyCard,
  ActivityCard,
  HuntingCard,
} from './overview';

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------
interface PBDetailsViewProps {
  leaderId: number;
  days: number;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------
const ALLIANCE_COLORS = [
  '#58a6ff', '#a855f7', '#3fb950', '#f85149', '#ff8800',
  '#ffcc00', '#00bcd4', '#e040fb', '#ff5252', '#69f0ae',
];

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------
function PBDetailsView({ leaderId, days }: PBDetailsViewProps) {
  const [data, setData] = useState<PBDetailsResponse | null>(null);
  const [offensiveData, setOffensiveData] = useState<any>(null);
  const [defensiveData, setDefensiveData] = useState<any>(null);
  const [capitalsData, setCapitalsData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    Promise.all([
      powerblocApi.getDetails(leaderId, days),
      powerblocApi.getOffensive(leaderId, days),
      powerblocApi.getDefensive(leaderId, days),
      powerblocApi.getCapitals(leaderId, days),
    ])
      .then(([details, offensive, defensive, capitals]) => {
        if (!cancelled) {
          setData(details);
          setOffensiveData(offensive);
          setDefensiveData(defensive);
          setCapitalsData(capitals);
        }
      })
      .catch((err) => { if (!cancelled) setError(err.message || 'Failed to load details'); })
      .finally(() => { if (!cancelled) setLoading(false); });

    return () => { cancelled = true; };
  }, [leaderId, days]);

  if (loading) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', padding: '0.75rem' }}>
        <div className="skeleton" style={{ height: '200px', borderRadius: '8px' }} />
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '0.75rem' }}>
          {Array.from({ length: 7 }, (_, i) => (
            <div key={i} className="skeleton" style={{ height: '180px', borderRadius: '6px' }} />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', padding: '3rem' }}>
        <span style={{ color: '#f85149', fontSize: '0.9rem' }}>{error}</span>
      </div>
    );
  }

  if (!data) return null;

  const { participation_trends, burnout_index, attrition, alliance_heatmap, top_enemies, coalition_allies, recommendations } = data;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', padding: '0.75rem' }}>
      {/* COMBINED TIMELINE */}
      <PBCombinedTimelineCard offensiveData={offensiveData} defensiveData={defensiveData} days={days} />

      {/* COMPACT SUMMARY CARDS - Responsive grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '0.75rem' }}>
        <OffensiveCard data={offensiveData} />
        <DefensiveCard data={defensiveData} />
        <CapitalCard data={capitalsData} />
        <PilotCard data={data} />
        <GeographyCard data={offensiveData} />
        <ActivityCard data={data} days={days} />
        <HuntingCard data={offensiveData} days={days} />
      </div>

      {/* PARTICIPATION TRENDS */}
      {participation_trends && participation_trends.daily.length > 0 && (
        <ParticipationTrendsSection trends={participation_trends} />
      )}

      {/* BURNOUT INDEX + ATTRITION TRACKER */}
      {(burnout_index || attrition) && (
        <div style={{ display: 'grid', gridTemplateColumns: burnout_index && attrition ? '1fr 1fr' : '1fr', gap: '0.75rem' }}>
          {burnout_index && burnout_index.daily.length > 0 && (
            <BurnoutSection burnout={burnout_index} />
          )}
          {attrition && attrition.summary.retained > 0 && (
            <AttritionSection attrition={attrition} />
          )}
        </div>
      )}

      {/* ALLIANCE ACTIVITY HEATMAP */}
      {alliance_heatmap && alliance_heatmap.length > 0 && (
        <AllianceHeatmapSection heatmap={alliance_heatmap} />
      )}

      {/* BOTTOM 3-COLUMN: Enemies, Allies, Recommendations */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.75rem' }}>
        <TopEnemiesSection enemies={top_enemies} />
        <CoalitionAlliesSection allies={coalition_allies} />
        <RecommendationsSection recs={recommendations} />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Section: Participation Trends
// ---------------------------------------------------------------------------
function ParticipationTrendsSection({ trends }: { trends: PBDetailsResponse['participation_trends'] }) {
  const { daily, trend } = trends;
  const valid = daily.filter((d) => d.day !== null);
  if (valid.length === 0) return null;

  const trendColor = trend.kills === 'increasing' ? '#3fb950' : trend.kills === 'decreasing' ? '#f85149' : '#ffcc00';
  const trendLabel = trend.kills === 'increasing' ? 'RISING' : trend.kills === 'decreasing' ? 'FALLING' : 'STABLE';
  const trendArrow = trend.kills === 'increasing' ? '↑' : trend.kills === 'decreasing' ? '↓' : '→';

  return (
    <div style={{
      background: 'rgba(0,0,0,0.3)',
      borderRadius: '6px',
      border: '1px solid rgba(255,255,255,0.08)',
      padding: '0.5rem',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
          <span style={{ fontSize: '0.7rem', fontWeight: 700, color: '#58a6ff', textTransform: 'uppercase' }}>
            Participation Trends
          </span>
          <span style={{
            fontSize: '0.55rem',
            fontWeight: 700,
            padding: '1px 5px',
            borderRadius: '3px',
            background: `${trendColor}33`,
            color: trendColor,
          }}>
            {trendArrow} {trendLabel}
          </span>
        </div>
        <span style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.4)' }}>{valid.length}d</span>
      </div>

      {/* Kills + Deaths bars */}
      <div style={{ display: 'flex', gap: '2px', height: '60px', alignItems: 'flex-end' }}>
        {(() => {
          const maxVal = Math.max(...valid.map(d => Math.max(d.kills, d.deaths)), 1);
          return valid.map((d, i) => (
            <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '1px', height: '100%', justifyContent: 'flex-end' }}>
              <div style={{ height: `${(d.kills / maxVal) * 100}%`, minHeight: d.kills > 0 ? '2px' : 0, background: '#3fb950', borderRadius: '1px 1px 0 0', opacity: 0.8 }} title={`${d.day}: ${d.kills} kills`} />
              <div style={{ height: `${(d.deaths / maxVal) * 100}%`, minHeight: d.deaths > 0 ? '2px' : 0, background: '#f85149', borderRadius: '0 0 1px 1px', opacity: 0.8 }} title={`${d.day}: ${d.deaths} deaths`} />
            </div>
          ));
        })()}
      </div>

      {/* Pilot Activity Line */}
      <div style={{ marginTop: '0.3rem', display: 'flex', gap: '2px', height: '20px', alignItems: 'flex-end' }}>
        {(() => {
          const maxPilots = Math.max(...valid.map(d => d.active_pilots), 1);
          return valid.map((d, i) => (
            <div key={i} style={{
              flex: 1,
              height: `${(d.active_pilots / maxPilots) * 100}%`,
              minHeight: d.active_pilots > 0 ? '2px' : 0,
              background: '#a855f7',
              borderRadius: '1px',
              opacity: 0.7,
            }} title={`${d.day}: ${d.active_pilots} active pilots`} />
          ));
        })()}
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '0.25rem' }}>
        <span style={{ fontSize: '0.5rem', color: 'rgba(255,255,255,0.4)' }}>{valid[0]?.day?.slice(5) || ''}</span>
        <div style={{ display: 'flex', gap: '0.75rem', fontSize: '0.5rem' }}>
          <span><span style={{ color: '#3fb950' }}>■</span> Kills</span>
          <span><span style={{ color: '#f85149' }}>■</span> Deaths</span>
          <span><span style={{ color: '#a855f7' }}>■</span> Active Pilots</span>
        </div>
        <span style={{ fontSize: '0.5rem', color: 'rgba(255,255,255,0.4)' }}>{valid[valid.length - 1]?.day?.slice(5) || ''}</span>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Section: Burnout Index
// ---------------------------------------------------------------------------
function BurnoutSection({ burnout }: { burnout: PBDetailsResponse['burnout_index'] }) {
  const { daily, summary } = burnout;
  const valid = daily.filter((d) => d.day !== null);
  if (valid.length === 0) return null;

  const statusColor = summary.status === 'healthy' ? '#3fb950' : summary.status === 'warning' ? '#ffcc00' : '#f85149';
  const riskLabel = summary.status?.toUpperCase() || 'UNKNOWN';

  return (
    <div style={{
      background: 'rgba(0,0,0,0.3)',
      borderRadius: '6px',
      border: '1px solid rgba(255,255,255,0.08)',
      borderLeft: `3px solid ${statusColor}`,
      padding: '0.5rem',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
          <span style={{ fontSize: '0.7rem', fontWeight: 700, color: '#ff6600', textTransform: 'uppercase' }}>
            Burnout Index
          </span>
          <span style={{
            fontSize: '0.5rem', fontWeight: 700, padding: '1px 5px', borderRadius: '3px',
            background: `${statusColor}33`, color: statusColor,
          }}>
            {riskLabel}
          </span>
        </div>
        <span style={{ fontSize: '0.7rem', fontWeight: 700, color: '#fff', fontFamily: 'monospace' }}>
          {(isFinite(summary.avg_kills_per_pilot) ? summary.avg_kills_per_pilot : 0).toFixed(1)} kills/pilot
        </span>
      </div>

      {/* Chart */}
      <div style={{ display: 'flex', gap: '2px', height: '50px', alignItems: 'flex-end' }}>
        {(() => {
          const maxKpp = Math.max(...valid.map(d => d.kills_per_pilot), 0.1);
          return valid.map((d, i) => (
            <div key={i} style={{
              flex: 1,
              height: `${(d.kills_per_pilot / maxKpp) * 100}%`,
              minHeight: d.kills_per_pilot > 0 ? '2px' : 0,
              background: d.kills_per_pilot > maxKpp * 0.7 ? '#f85149' : d.kills_per_pilot > maxKpp * 0.4 ? '#ff6600' : '#ffcc00',
              borderRadius: '1px',
              opacity: 0.8,
            }} title={`${d.day}: ${d.kills_per_pilot.toFixed(1)} kills/pilot, ${d.active_pilots} pilots`} />
          ));
        })()}
      </div>
      <div style={{ display: 'flex', gap: '2px', height: '20px', alignItems: 'flex-end', marginTop: '2px' }}>
        {(() => {
          const maxP = Math.max(...valid.map(d => d.active_pilots), 1);
          return valid.map((d, i) => (
            <div key={i} style={{
              flex: 1,
              height: `${(d.active_pilots / maxP) * 100}%`,
              minHeight: d.active_pilots > 0 ? '2px' : 0,
              background: '#58a6ff',
              borderRadius: '1px',
              opacity: 0.6,
            }} title={`${d.day}: ${d.active_pilots} active pilots`} />
          ));
        })()}
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '0.2rem', fontSize: '0.5rem' }}>
        <span style={{ color: 'rgba(255,255,255,0.3)' }}>{valid[0]?.day?.slice(5)}</span>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <span><span style={{ color: '#ff6600' }}>■</span> Kills/Pilot</span>
          <span><span style={{ color: '#58a6ff' }}>■</span> Active Pilots</span>
        </div>
        <span style={{ color: 'rgba(255,255,255,0.3)' }}>{valid[valid.length - 1]?.day?.slice(5)}</span>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Section: Attrition Tracker
// ---------------------------------------------------------------------------
function AttritionSection({ attrition }: { attrition: PBDetailsResponse['attrition'] }) {
  const { summary } = attrition;
  const statusColor = summary.status === 'healthy' ? '#3fb950' : summary.status === 'warning' ? '#ffcc00' : '#f85149';

  return (
    <div style={{
      background: 'rgba(0,0,0,0.3)',
      borderRadius: '6px',
      border: '1px solid rgba(255,255,255,0.08)',
      borderLeft: `3px solid ${statusColor}`,
      overflow: 'hidden',
    }}>
      <div style={{
        padding: '0.4rem 0.5rem',
        borderBottom: '1px solid rgba(255,255,255,0.08)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <span style={{ fontSize: '0.7rem', fontWeight: 700, color: '#f85149', textTransform: 'uppercase' }}>
          Attrition Tracker
        </span>
        <span style={{
          fontSize: '0.5rem', fontWeight: 700, padding: '1px 5px', borderRadius: '3px',
          background: `${statusColor}33`, color: statusColor, textTransform: 'uppercase',
        }}>
          {summary.status}
        </span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.3rem', padding: '0.4rem 0.5rem' }}>
        <div style={{ textAlign: 'center', padding: '0.3rem', background: 'rgba(255,255,255,0.03)', borderRadius: '3px' }}>
          <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#fff', fontFamily: 'monospace' }}>
            {(isFinite(summary.retention_rate) ? summary.retention_rate : 0).toFixed(0)}%
          </div>
          <div style={{ fontSize: '0.5rem', color: 'rgba(255,255,255,0.4)' }}>RETENTION</div>
        </div>
        <div style={{ textAlign: 'center', padding: '0.3rem', background: 'rgba(255,255,255,0.03)', borderRadius: '3px' }}>
          <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#3fb950', fontFamily: 'monospace' }}>
            {summary.retained}
          </div>
          <div style={{ fontSize: '0.5rem', color: 'rgba(255,255,255,0.4)' }}>RETAINED</div>
        </div>
        <div style={{ textAlign: 'center', padding: '0.3rem', background: 'rgba(255,255,255,0.03)', borderRadius: '3px' }}>
          <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#f85149', fontFamily: 'monospace' }}>
            {summary.first_half_pilots - summary.retained}
          </div>
          <div style={{ fontSize: '0.5rem', color: 'rgba(255,255,255,0.4)' }}>DEPARTED</div>
        </div>
      </div>

      {/* Retention bar */}
      <div style={{ padding: '0 0.5rem 0.5rem' }}>
        <div style={{ background: 'rgba(255,255,255,0.05)', borderRadius: '3px', height: '12px', overflow: 'hidden' }}>
          <div style={{
            height: '100%',
            width: `${Math.min(summary.retention_rate, 100)}%`,
            background: `linear-gradient(90deg, ${statusColor}, ${statusColor}88)`,
            borderRadius: '3px',
            transition: 'width 0.5s',
          }} />
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '0.2rem', fontSize: '0.5rem', color: 'rgba(255,255,255,0.4)' }}>
          <span>1st half: {summary.first_half_pilots} pilots</span>
          <span>2nd half: {summary.second_half_pilots} pilots</span>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Section: Alliance Activity Heatmap
// ---------------------------------------------------------------------------
function AllianceHeatmapSection({ heatmap }: { heatmap: PBDetailsResponse['alliance_heatmap'] }) {
  return (
    <div style={{
      background: 'rgba(0,0,0,0.3)',
      borderRadius: '6px',
      border: '1px solid rgba(255,255,255,0.08)',
      overflow: 'hidden',
    }}>
      <div style={{
        padding: '0.4rem 0.5rem',
        borderBottom: '1px solid rgba(255,255,255,0.08)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <span style={{ fontSize: '0.7rem', fontWeight: 700, color: '#00bcd4', textTransform: 'uppercase' }}>
          Alliance Activity Heatmap
        </span>
        <span style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.4)' }}>
          {heatmap.length} alliances
        </span>
      </div>

      {/* Hour Labels */}
      <div style={{ padding: '0.25rem 0.5rem 0' }}>
        <div style={{ display: 'flex', marginLeft: '160px' }}>
          {Array.from({ length: 24 }, (_, h) => (
            <div key={h} style={{ flex: 1, textAlign: 'center', fontSize: '0.45rem', color: 'rgba(255,255,255,0.3)', minWidth: '18px' }}>
              {h % 3 === 0 ? `${h}` : ''}
            </div>
          ))}
        </div>
      </div>

      {/* Alliance Rows */}
      <div style={{ padding: '0 0.5rem 0.5rem', maxHeight: '260px', overflowY: 'auto' }}>
        {heatmap.map((a, aIdx) => {
          const maxH = Math.max(...a.hours, 1);
          const baseColor = ALLIANCE_COLORS[aIdx % ALLIANCE_COLORS.length];
          return (
            <div key={a.alliance_id} style={{ display: 'flex', alignItems: 'center', marginBottom: '2px' }}>
              <div style={{ width: '160px', display: 'flex', alignItems: 'center', gap: '0.3rem', flexShrink: 0 }}>
                <img
                  src={`https://images.evetech.net/alliances/${a.alliance_id}/logo?size=32`}
                  alt=""
                  style={{ width: 16, height: 16, borderRadius: '2px' }}
                  onError={(e) => { e.currentTarget.style.display = 'none'; }}
                />
                <span style={{ color: '#ccc', fontSize: '0.65rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '100px' }}>
                  {a.name}
                </span>
                <span style={{ color: '#666', fontSize: '0.55rem' }}>[{a.ticker}]</span>
              </div>
              <div style={{ display: 'flex', flex: 1 }}>
                {a.hours.map((val, hour) => {
                  const intensity = val / maxH;
                  return (
                    <div
                      key={hour}
                      style={{
                        flex: 1,
                        height: '16px',
                        minWidth: '18px',
                        background: intensity > 0 ? baseColor : 'transparent',
                        opacity: intensity > 0 ? 0.15 + intensity * 0.85 : 0,
                        borderRadius: '1px',
                        margin: '0 0.5px',
                      }}
                      title={`${a.name} @ ${String(hour).padStart(2, '0')}:00 - ${val} activity`}
                    />
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Section: Top Enemies
// ---------------------------------------------------------------------------
function TopEnemiesSection({ enemies }: { enemies: PBDetailsResponse['top_enemies'] }) {
  return (
    <div style={{
      background: 'rgba(0,0,0,0.3)',
      borderRadius: '6px',
      border: '1px solid rgba(255,255,255,0.08)',
      overflow: 'hidden',
    }}>
      <div style={{
        padding: '0.4rem 0.5rem',
        borderBottom: '1px solid rgba(255,255,255,0.08)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <span style={{ fontSize: '0.7rem', fontWeight: 700, color: '#ff6600', textTransform: 'uppercase' }}>
          Top Enemies
        </span>
        <span style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.4)' }}>
          {enemies.length} enemies
        </span>
      </div>
      <div style={{ padding: '0.25rem', maxHeight: '280px', overflowY: 'auto' }}>
        {enemies.slice(0, 10).map((enemy, i) => (
          <Link key={i} to={`/alliance/${enemy.alliance_id}`} style={{ textDecoration: 'none' }}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem',
              padding: '0.35rem 0.4rem',
              marginBottom: '0.15rem',
              background: 'rgba(255,102,0,0.08)',
              borderRadius: '3px',
              borderLeft: '2px solid #ff6600',
              cursor: 'pointer',
              transition: 'background 0.15s',
            }}>
              <img
                src={`https://images.evetech.net/alliances/${enemy.alliance_id}/logo?size=32`}
                alt=""
                style={{ width: 20, height: 20, borderRadius: '2px' }}
                onError={(e) => { e.currentTarget.style.display = 'none'; }}
              />
              <span style={{ fontSize: '0.7rem', fontWeight: 600, color: '#fff', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {enemy.alliance_name}
              </span>
              <span style={{ fontSize: '0.55rem', color: 'rgba(255,255,255,0.4)' }}>[{enemy.ticker}]</span>
              <span style={{ fontSize: '0.7rem', fontWeight: 700, color: '#ff6600', fontFamily: 'monospace' }}>
                {enemy.kills}
              </span>
              <span style={{ fontSize: '0.55rem', color: 'rgba(255,255,255,0.4)' }}>kills</span>
            </div>
          </Link>
        ))}
        {enemies.length === 0 && <div style={{ color: '#666', fontSize: '0.75rem', textAlign: 'center', padding: '1rem' }}>No enemies detected</div>}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Section: Coalition Allies
// ---------------------------------------------------------------------------
function CoalitionAlliesSection({ allies }: { allies: PBDetailsResponse['coalition_allies'] }) {
  return (
    <div style={{
      background: 'rgba(0,0,0,0.3)',
      borderRadius: '6px',
      border: '1px solid rgba(255,255,255,0.08)',
      overflow: 'hidden',
    }}>
      <div style={{
        padding: '0.4rem 0.5rem',
        borderBottom: '1px solid rgba(255,255,255,0.08)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <span style={{ fontSize: '0.7rem', fontWeight: 700, color: '#3fb950', textTransform: 'uppercase' }}>
          Coalition Allies
        </span>
        <span style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.4)' }}>
          {allies.length} allies
        </span>
      </div>
      <div style={{ padding: '0.25rem', maxHeight: '280px', overflowY: 'auto' }}>
        {allies.slice(0, 10).map((ally, i) => (
          <Link key={i} to={`/alliance/${ally.alliance_id}`} style={{ textDecoration: 'none' }}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem',
              padding: '0.35rem 0.4rem',
              marginBottom: '0.15rem',
              background: 'rgba(63,185,80,0.08)',
              borderRadius: '3px',
              borderLeft: '2px solid #3fb950',
              cursor: 'pointer',
              transition: 'background 0.15s',
            }}>
              <img
                src={`https://images.evetech.net/alliances/${ally.alliance_id}/logo?size=32`}
                alt=""
                style={{ width: 20, height: 20, borderRadius: '2px' }}
                onError={(e) => { e.currentTarget.style.display = 'none'; }}
              />
              <span style={{ fontSize: '0.7rem', fontWeight: 600, color: '#fff', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {ally.alliance_name}
              </span>
              <span style={{ fontSize: '0.55rem', color: 'rgba(255,255,255,0.4)' }}>[{ally.ticker}]</span>
            </div>
          </Link>
        ))}
        {allies.length === 0 && <div style={{ color: '#666', fontSize: '0.75rem', textAlign: 'center', padding: '1rem' }}>No allies detected</div>}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Section: Recommendations
// ---------------------------------------------------------------------------
function RecommendationsSection({ recs }: { recs: PBDetailsResponse['recommendations'] }) {
  const sorted = [...recs].sort((a, b) => a.priority - b.priority);

  return (
    <div style={{
      background: 'rgba(0,0,0,0.3)',
      borderRadius: '6px',
      border: '1px solid rgba(255,255,255,0.08)',
      overflow: 'hidden',
    }}>
      <div style={{
        padding: '0.4rem 0.5rem',
        borderBottom: '1px solid rgba(255,255,255,0.08)',
      }}>
        <span style={{ fontSize: '0.7rem', fontWeight: 700, color: '#a855f7', textTransform: 'uppercase' }}>
          Recommendations
        </span>
      </div>
      <div style={{ padding: '0.25rem', maxHeight: '280px', overflowY: 'auto' }}>
        {sorted.slice(0, 5).map((rec, i) => {
          const catColor = rec.category === 'offensive' ? '#f85149'
            : rec.category === 'defensive' ? '#3fb950'
            : rec.category === 'economic' ? '#ffcc00'
            : rec.category === 'strategic' ? '#58a6ff'
            : '#a855f7';
          return (
            <div key={i} style={{
              display: 'flex',
              alignItems: 'flex-start',
              gap: '0.4rem',
              padding: '0.3rem 0.4rem',
              marginBottom: '0.15rem',
              background: `${catColor}15`,
              borderRadius: '3px',
              borderLeft: `2px solid ${catColor}`,
            }}>
              <span style={{
                fontSize: '0.5rem',
                fontWeight: 700,
                color: '#fff',
                background: catColor,
                padding: '1px 4px',
                borderRadius: '2px',
                textTransform: 'uppercase',
                flexShrink: 0,
              }}>
                {rec.category}
              </span>
              <span style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.8)', lineHeight: 1.3 }}>
                {rec.text}
              </span>
            </div>
          );
        })}
        {sorted.length === 0 && <div style={{ color: '#666', fontSize: '0.75rem', textAlign: 'center', padding: '1rem' }}>No recommendations</div>}
      </div>
    </div>
  );
}

export { PBDetailsView };
export default PBDetailsView;
