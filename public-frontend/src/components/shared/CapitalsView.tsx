/**
 * Shared Capitals Tab - Capital Fleet Intelligence Dashboard
 *
 * Unified component for Alliance, Corporation, and PowerBloc entities.
 * 6 panel functions covering 9 intelligence categories:
 * 1. Enhanced Summary (K/D, Efficiency, ISK metrics, primary hotspot, peak activity)
 * 2. Fleet Composition (by capital type)
 * 3. Ship Details (top 20 specific ships)
 * 4. Capital Timeline (30-day activity with sparkline)
 * 5. Geographic Hotspots (top systems)
 * 6. Top Killers (pilot leaderboard)
 * 7. Top Losers (vulnerable pilots)
 * 8. Capital Engagements (size analysis)
 * 9. Recent Activity (last 20 killmails)
 */

import { useState, useEffect } from 'react';
import type { EntityViewProps, FetcherMap } from './types';
import * as allianceApi from '../../services/allianceApi';
import { corpApi } from '../../services/corporationApi';
import { powerblocApi } from '../../services/api/powerbloc';

import { fontSize, color, spacing } from '../../styles/theme';

// ============================================================================
// Unified Data Interface (superset of all 3 entity types)
// ============================================================================

interface CapitalsData {
  summary: {
    capital_kills: number;
    capital_losses: number;
    isk_destroyed: string;
    isk_lost: string;
    unique_pilots: number;
    kd_ratio: number;
    efficiency: number;
  };
  fleet_composition: Array<{
    capital_type: string;
    total_activity?: number;
    kills: number;
    losses: number;
    kills_pct?: number;
    losses_pct?: number;
    percentage?: number;
  }>;
  ship_details: Array<{
    ship_name: string;
    capital_type: string;
    total_activity?: number;
    kills: number;
    losses: number;
    avg_value: number;
  }>;
  capital_timeline: Array<{
    day: string;
    kills: number;
    losses: number;
  }>;
  geographic_hotspots: Array<{
    system_id: number;
    system_name: string;
    region_name: string;
    activity: number;
    kills: number;
    losses: number;
  }>;
  top_killers: Array<{
    character_id: number;
    character_name: string | null;
    capital_kills: number;
    isk_destroyed: string;
    primary_ship: string | null;
  }>;
  top_losers: Array<{
    character_id: number;
    character_name: string | null;
    capital_losses: number;
    isk_lost: string;
    last_ship_lost: string | null;
  }>;
  capital_engagements?: Array<{
    engagement_size: string;
    total: number;
    kills: number;
    losses: number;
  }>;
  recent_activity?: Array<{
    killmail_id: number;
    killmail_time: string;
    isk_value: number;
    activity_type: string;
    ship_name: string;
    capital_type?: string;
    system_name: string | null;
    pilot_name: string | null;
    character_id: number | null;
  }>;
}

// ============================================================================
// Fetcher Map
// ============================================================================

const capitalsFetchers: FetcherMap<CapitalsData> = {
  alliance: (entityId, days) =>
    allianceApi.getCapitalIntel(entityId, days) as Promise<CapitalsData>,
  corporation: (entityId, days) =>
    corpApi.getCapitalIntel(entityId, days) as Promise<CapitalsData>,
  powerbloc: (entityId, days) =>
    powerblocApi.getCapitals(entityId, days) as unknown as Promise<CapitalsData>,
};

// ============================================================================
// Main Component
// ============================================================================

export function CapitalsView({ entityType, entityId, days }: EntityViewProps) {
  const [data, setData] = useState<CapitalsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [summaryTab, setSummaryTab] = useState<'composition' | 'engagements'>('composition');
  const [detailsTab, setDetailsTab] = useState<'ships' | 'geography'>('ships');
  const [pilotsTab, setPilotsTab] = useState<'killers' | 'losers'>('killers');

  useEffect(() => {
    setLoading(true);
    capitalsFetchers[entityType](entityId, days)
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [entityType, entityId, days]);

  if (loading || !data) {
    return <div style={{ padding: spacing["3xl"], textAlign: 'center', color: color.textSecondary }}>Loading...</div>;
  }

  if (data.summary.capital_kills === 0 && data.summary.capital_losses === 0) {
    return (
      <div style={{ background: 'rgba(0,0,0,0.3)', borderRadius: '8px', padding: spacing["3xl"], textAlign: 'center', color: color.textSecondary }}>
        No capital activity detected in the last {days} days
      </div>
    );
  }

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: spacing.base }}>
      <SummaryPanel summary={data.summary} hotspots={data.geographic_hotspots} timeline={data.capital_timeline} />
      <FleetCompositionEngagements
        composition={data.fleet_composition}
        engagements={data.capital_engagements}
        tab={summaryTab}
        setTab={setSummaryTab}
      />
      <ShipDetailsGeography
        ships={data.ship_details}
        hotspots={data.geographic_hotspots}
        tab={detailsTab}
        setTab={setDetailsTab}
      />
      <TopPilotsPanel
        killers={data.top_killers}
        losers={data.top_losers}
        tab={pilotsTab}
        setTab={setPilotsTab}
      />
      <TimelinePanel timeline={data.capital_timeline} />
      <RecentActivityPanel activity={data.recent_activity || []} />
    </div>
  );
}

// ============================================================================
// Panel Components
// ============================================================================

function SummaryPanel({
  summary,
  hotspots,
  timeline
}: {
  summary: CapitalsData['summary'];
  hotspots: CapitalsData['geographic_hotspots'];
  timeline: CapitalsData['capital_timeline'];
}) {
  const safeKd = isFinite(summary.kd_ratio) ? summary.kd_ratio : 0;
  const safeEff = isFinite(summary.efficiency) ? summary.efficiency : 0;
  const kdColor = safeKd >= 2.0 ? '#3fb950' : safeKd >= 1.0 ? '#ffcc00' : '#f85149';
  const effColor = safeEff >= 70 ? '#3fb950' : safeEff >= 50 ? '#ffcc00' : '#f85149';

  // Find primary hotspot (highest activity)
  const primaryHotspot = hotspots.length > 0 ? hotspots[0] : null;

  // Find peak activity day
  const peakDay = timeline.length > 0
    ? timeline.reduce((max, day) => ((day.kills + day.losses) > (max.kills + max.losses) ? day : max), timeline[0])
    : null;

  return (
    <div style={{ background: 'rgba(0,0,0,0.3)', borderRadius: '8px', padding: spacing.base, borderLeft: '2px solid #ff0000' }}>
      <div style={{ fontSize: fontSize.xxs, textTransform: 'uppercase', color: color.textSecondary, marginBottom: spacing.md }}>
        {'\u2022'} CAPITAL SUMMARY
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: spacing.base, fontSize: fontSize.xs }}>
        <div>
          <div style={{ color: color.textSecondary }}>Kills</div>
          <div style={{ fontSize: fontSize.h4, color: color.killGreen }}>{summary.capital_kills}</div>
        </div>
        <div>
          <div style={{ color: color.textSecondary }}>Losses</div>
          <div style={{ fontSize: fontSize.h4, color: color.lossRed }}>{summary.capital_losses}</div>
        </div>
        <div>
          <div style={{ color: color.textSecondary }}>K/D</div>
          <div style={{ fontSize: fontSize.h4, color: kdColor }}>{safeKd.toFixed(2)}</div>
        </div>
        <div>
          <div style={{ color: color.textSecondary }}>
            Efficiency <span style={{ color: color.textTertiary, fontSize: fontSize.nano }}>(Capital Ships Only)</span>
          </div>
          <div style={{ fontSize: fontSize.h4, color: effColor }}>{safeEff.toFixed(1)}%</div>
        </div>
        <div>
          <div style={{ color: color.textSecondary }}>ISK Destroyed</div>
          <div style={{ fontSize: '0.9rem', color: color.killGreen }}>{(Number(summary.isk_destroyed) / 1e12).toFixed(1)}T</div>
        </div>
        <div>
          <div style={{ color: color.textSecondary }}>ISK Lost</div>
          <div style={{ fontSize: '0.9rem', color: color.lossRed }}>{(Number(summary.isk_lost) / 1e12).toFixed(1)}T</div>
        </div>
      </div>
      <div style={{ marginTop: spacing.base, fontSize: fontSize.tiny, color: color.textSecondary, display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
        <div>{summary.unique_pilots} unique capital pilots</div>
        {primaryHotspot && (
          <div>
            Primary Hotspot: <span style={{ color: color.teal }}>{primaryHotspot.system_name}</span> ({primaryHotspot.activity} engagements)
          </div>
        )}
        {peakDay && (
          <div>
            Peak Activity: <span style={{ color: color.emerald }}>{peakDay.day}</span> ({peakDay.kills + peakDay.losses} capitals)
          </div>
        )}
      </div>
    </div>
  );
}

function FleetCompositionEngagements({
  composition,
  engagements,
  tab,
  setTab,
}: {
  composition: CapitalsData['fleet_composition'];
  engagements: CapitalsData['capital_engagements'];
  tab: 'composition' | 'engagements';
  setTab: (t: 'composition' | 'engagements') => void;
}) {
  const getCapitalColor = (type: string) => {
    if (type === 'Carrier') return '#58a6ff';
    if (type === 'Dreadnought') return '#ff8800';
    if (type === 'Force Auxiliary') return '#3fb950';
    if (type === 'Supercarrier') return '#a855f7';
    if (type === 'Titan') return '#ff0000';
    return '#8b949e';
  };

  const engagementColors: Record<string, string> = {
    solo: '#f85149',
    small: '#ff8800',
    medium: '#ffcc00',
    large: '#3fb950',
    blob: '#a855f7',
  };

  return (
    <div style={{ background: 'rgba(0,0,0,0.3)', borderRadius: '8px', padding: spacing.base, borderLeft: '2px solid #a855f7', maxHeight: '280px', overflowY: 'auto' }}>
      <div style={{ display: 'flex', gap: spacing.sm, marginBottom: spacing.md }}>
        <button
          onClick={() => setTab('composition')}
          style={{
            flex: 1,
            padding: '0.2rem 0.5rem',
            fontSize: fontSize.tiny,
            background: tab === 'composition' ? '#a855f7' : 'rgba(168,85,247,0.2)',
            color: '#c9d1d9',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
          }}
        >
          FLEET COMPOSITION
        </button>
        <button
          onClick={() => setTab('engagements')}
          style={{
            flex: 1,
            padding: '0.2rem 0.5rem',
            fontSize: fontSize.tiny,
            background: tab === 'engagements' ? '#a855f7' : 'rgba(168,85,247,0.2)',
            color: '#c9d1d9',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
          }}
        >
          ENGAGEMENT SIZES
        </button>
      </div>

      {tab === 'composition' ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: spacing.sm }}>
          {composition.map((item) => (
            <div
              key={item.capital_type}
              style={{
                background: 'rgba(0,0,0,0.2)',
                padding: '0.25rem 0.4rem',
                borderRadius: '4px',
                fontSize: fontSize.xxs,
                borderLeft: `2px solid ${getCapitalColor(item.capital_type)}`,
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.2rem' }}>
                <span style={{ color: '#c9d1d9' }}>{item.capital_type}</span>
                <span style={{ fontSize: fontSize.tiny, color: color.textSecondary }}>
                  {item.kills_pct?.toFixed(1)}% kills {'\u2022'} {item.losses_pct?.toFixed(1)}% losses
                </span>
              </div>
              <div style={{ fontSize: fontSize.tiny, color: color.textSecondary }}>
                {item.kills} kills {'\u2022'} {item.losses} losses
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: spacing.sm }}>
          {(() => {
            const maxTotal = Math.max(...(engagements || []).map((e) => e.total), 1);
            return (engagements || [])
              .sort((a, b) => b.total - a.total)
              .map((item) => {
                const barWidth = (item.total / maxTotal) * 100;
                return (
                  <div
                    key={item.engagement_size}
                    style={{
                      background: 'rgba(0,0,0,0.2)',
                      padding: '0.25rem 0.4rem',
                      borderRadius: '4px',
                      fontSize: fontSize.xxs,
                      borderLeft: `2px solid ${engagementColors[item.engagement_size] || '#8b949e'}`,
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: spacing.sm }}>
                      <span style={{ color: '#c9d1d9', textTransform: 'capitalize' }}>{item.engagement_size}</span>
                      <span style={{ color: color.textSecondary }}>{item.total} total</span>
                    </div>
                    <div style={{ background: `${engagementColors[item.engagement_size] || '#8b949e'}33`, borderRadius: '2px', height: '8px', marginBottom: '0.2rem', overflow: 'hidden' }}>
                      <div
                        style={{
                          background: engagementColors[item.engagement_size] || '#8b949e',
                          height: '100%',
                          width: `${barWidth}%`,
                        }}
                      />
                    </div>
                    <div style={{ fontSize: fontSize.tiny, color: color.textSecondary }}>
                      {item.kills} kills {'\u2022'} {item.losses} losses
                    </div>
                  </div>
                );
              });
          })()}
        </div>
      )}
    </div>
  );
}

function ShipDetailsGeography({
  ships,
  hotspots,
  tab,
  setTab,
}: {
  ships: CapitalsData['ship_details'];
  hotspots: CapitalsData['geographic_hotspots'];
  tab: 'ships' | 'geography';
  setTab: (t: 'ships' | 'geography') => void;
}) {
  const getCapitalColor = (type: string) => {
    if (type === 'Carrier') return '#58a6ff';
    if (type === 'Dreadnought') return '#ff8800';
    if (type === 'Force Auxiliary') return '#3fb950';
    if (type === 'Supercarrier') return '#a855f7';
    if (type === 'Titan') return '#ff0000';
    return '#8b949e';
  };

  return (
    <div style={{ background: 'rgba(0,0,0,0.3)', borderRadius: '8px', padding: spacing.base, borderLeft: '2px solid #ff8800', maxHeight: '350px', overflowY: 'auto' }}>
      <div style={{ display: 'flex', gap: spacing.sm, marginBottom: spacing.md }}>
        <button
          onClick={() => setTab('ships')}
          style={{
            flex: 1,
            padding: '0.2rem 0.5rem',
            fontSize: fontSize.tiny,
            background: tab === 'ships' ? '#ff8800' : 'rgba(255,136,0,0.2)',
            color: '#c9d1d9',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
          }}
        >
          SHIP DETAILS
        </button>
        <button
          onClick={() => setTab('geography')}
          style={{
            flex: 1,
            padding: '0.2rem 0.5rem',
            fontSize: fontSize.tiny,
            background: tab === 'geography' ? '#ff8800' : 'rgba(255,136,0,0.2)',
            color: '#c9d1d9',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
          }}
        >
          HOTSPOTS
        </button>
      </div>

      {tab === 'ships' ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: spacing.sm }}>
          {ships.slice(0, 20).map((ship) => (
            <div
              key={`${ship.ship_name}-${ship.capital_type}`}
              style={{
                background: 'rgba(0,0,0,0.2)',
                padding: '0.25rem 0.4rem',
                borderRadius: '4px',
                fontSize: fontSize.xxs,
                borderLeft: `2px solid ${getCapitalColor(ship.capital_type)}`,
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.2rem' }}>
                <span style={{ color: '#c9d1d9' }}>{ship.ship_name}</span>
                <span style={{ color: getCapitalColor(ship.capital_type) }}>{ship.capital_type}</span>
              </div>
              <div style={{ fontSize: fontSize.tiny, color: color.textSecondary }}>
                {ship.kills} kills {'\u2022'} {ship.losses} losses {'\u2022'} {(ship.avg_value / 1e9).toFixed(1)}B avg
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: spacing.sm }}>
          {hotspots.map((spot) => (
            <a
              key={spot.system_id}
              href={`/system/${spot.system_id}`}
              style={{
                background: 'rgba(0,0,0,0.2)',
                padding: '0.25rem 0.4rem',
                borderRadius: '4px',
                fontSize: fontSize.xxs,
                borderLeft: '2px solid #00bcd4',
                textDecoration: 'none',
                color: 'inherit',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.2rem' }}>
                <span style={{ color: '#c9d1d9' }}>{spot.system_name}</span>
                <span style={{ color: color.textSecondary }}>{spot.activity} total</span>
              </div>
              <div style={{ fontSize: fontSize.tiny, color: color.textSecondary }}>
                {spot.region_name} {'\u2022'} {spot.kills} kills {'\u2022'} {spot.losses} losses
              </div>
            </a>
          ))}
        </div>
      )}
    </div>
  );
}

function TopPilotsPanel({
  killers,
  losers,
  tab,
  setTab,
}: {
  killers: CapitalsData['top_killers'];
  losers: CapitalsData['top_losers'];
  tab: 'killers' | 'losers';
  setTab: (t: 'killers' | 'losers') => void;
}) {
  return (
    <div style={{ background: 'rgba(0,0,0,0.3)', borderRadius: '8px', padding: spacing.base, borderLeft: '2px solid #3fb950', maxHeight: '350px', overflowY: 'auto' }}>
      <div style={{ display: 'flex', gap: spacing.sm, marginBottom: spacing.md }}>
        <button
          onClick={() => setTab('killers')}
          style={{
            flex: 1,
            padding: '0.2rem 0.5rem',
            fontSize: fontSize.tiny,
            background: tab === 'killers' ? '#3fb950' : 'rgba(63,185,80,0.2)',
            color: '#c9d1d9',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
          }}
        >
          TOP KILLERS
        </button>
        <button
          onClick={() => setTab('losers')}
          style={{
            flex: 1,
            padding: '0.2rem 0.5rem',
            fontSize: fontSize.tiny,
            background: tab === 'losers' ? '#3fb950' : 'rgba(63,185,80,0.2)',
            color: '#c9d1d9',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
          }}
        >
          TOP LOSERS
        </button>
      </div>

      {tab === 'killers' ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: spacing.sm }}>
          {killers.map((pilot, idx) => (
            <a
              key={pilot.character_id}
              href={`https://zkillboard.com/character/${pilot.character_id}/`}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                background: 'rgba(0,0,0,0.2)',
                padding: '0.25rem 0.4rem',
                borderRadius: '4px',
                fontSize: fontSize.xxs,
                borderLeft: '2px solid #3fb950',
                textDecoration: 'none',
                color: 'inherit',
                display: 'flex',
                gap: spacing.md,
                alignItems: 'center',
              }}
            >
              <img
                src={`https://images.evetech.net/characters/${pilot.character_id}/portrait?size=32`}
                alt=""
                style={{ width: '20px', height: '20px', borderRadius: '2px' }}
              />
              <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.1rem' }}>
                  <span style={{ color: '#c9d1d9' }}>
                    #{idx + 1} {pilot.character_name || 'Unknown'}
                  </span>
                  <span style={{ color: color.killGreen }}>{pilot.capital_kills} kills</span>
                </div>
                <div style={{ fontSize: fontSize.tiny, color: color.textSecondary }}>
                  {(Number(pilot.isk_destroyed) / 1e12).toFixed(1)}T ISK {'\u2022'} {pilot.primary_ship || 'Unknown'}
                </div>
              </div>
            </a>
          ))}
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: spacing.sm }}>
          {(losers || []).map((pilot, idx) => (
            <a
              key={pilot.character_id}
              href={`https://zkillboard.com/character/${pilot.character_id}/`}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                background: 'rgba(0,0,0,0.2)',
                padding: '0.25rem 0.4rem',
                borderRadius: '4px',
                fontSize: fontSize.xxs,
                borderLeft: '2px solid #f85149',
                textDecoration: 'none',
                color: 'inherit',
                display: 'flex',
                gap: spacing.md,
                alignItems: 'center',
              }}
            >
              <img
                src={`https://images.evetech.net/characters/${pilot.character_id}/portrait?size=32`}
                alt=""
                style={{ width: '20px', height: '20px', borderRadius: '2px' }}
              />
              <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.1rem' }}>
                  <span style={{ color: '#c9d1d9' }}>
                    #{idx + 1} {pilot.character_name || 'Unknown'}
                  </span>
                  <span style={{ color: color.lossRed }}>{pilot.capital_losses} losses</span>
                </div>
                <div style={{ fontSize: fontSize.tiny, color: color.textSecondary }}>
                  {(Number(pilot.isk_lost) / 1e12).toFixed(1)}T ISK {'\u2022'} {pilot.last_ship_lost || 'Unknown'}
                </div>
              </div>
            </a>
          ))}
        </div>
      )}
    </div>
  );
}

function TimelinePanel({ timeline }: { timeline: CapitalsData['capital_timeline'] }) {
  const maxActivity = Math.max(...timeline.map((d) => d.kills + d.losses), 1);

  const generateSparkline = (days: CapitalsData['capital_timeline']): string => {
    if (days.length === 0) return '';
    const bars = ['\u2581', '\u2582', '\u2583', '\u2584', '\u2585', '\u2586', '\u2587', '\u2588'];
    const values = days.map((d) => d.kills + d.losses);
    const max = Math.max(...values, 1);
    return values
      .slice(-30)
      .map((v) => bars[Math.min(Math.floor((v / max) * bars.length), bars.length - 1)])
      .join('');
  };

  const calculateTrend = (days: CapitalsData['capital_timeline']): { indicator: string; color: string } => {
    if (days.length < 7) return { indicator: '\u2192', color: color.linkBlue };
    const recentAvg = days.slice(-3).reduce((sum, d) => sum + d.kills + d.losses, 0) / 3;
    const priorAvg = days.slice(-7, -3).reduce((sum, d) => sum + d.kills + d.losses, 0) / 4;
    const change = priorAvg > 0 ? ((recentAvg - priorAvg) / priorAvg) * 100 : 0;
    if (change > 15) return { indicator: '\u2B06\uFE0F', color: color.killGreen };
    if (change < -15) return { indicator: '\u2B07\uFE0F', color: color.lossRed };
    return { indicator: '\u2192', color: color.linkBlue };
  };

  const trend = calculateTrend(timeline);
  const sparkline = generateSparkline(timeline);

  return (
    <div style={{ background: 'rgba(0,0,0,0.3)', borderRadius: '8px', padding: spacing.base, borderLeft: '2px solid #10b981', gridColumn: '1 / -1', maxHeight: '320px', overflowY: 'auto' }}>
      <div style={{ fontSize: fontSize.xxs, textTransform: 'uppercase', color: color.textSecondary, marginBottom: spacing.md, display: 'flex', justifyContent: 'space-between' }}>
        <span>{'\u2022'} CAPITAL TIMELINE (30 DAYS)</span>
        <span style={{ color: trend.color, fontSize: fontSize.h4 }}>{trend.indicator}</span>
      </div>
      <div style={{ fontFamily: 'monospace', fontSize: '1.5rem', letterSpacing: '0.15rem', marginBottom: spacing.base, color: color.emerald, lineHeight: '1.5' }}>
        {sparkline}
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: spacing.sm }}>
        {timeline
          .slice()
          .reverse()
          .slice(0, 15)
          .map((day) => {
            const activity = day.kills + day.losses;
            const barWidth = (activity / maxActivity) * 100;
            return (
              <div
                key={day.day}
                style={{
                  background: 'rgba(0,0,0,0.2)',
                  padding: '0.25rem 0.4rem',
                  borderRadius: '4px',
                  fontSize: fontSize.xxs,
                  borderLeft: '2px solid #10b981',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.2rem' }}>
                  <span style={{ color: '#c9d1d9' }}>{day.day}</span>
                  <span style={{ color: color.textSecondary }}>{activity} total</span>
                </div>
                <div style={{ fontSize: fontSize.tiny, color: color.textSecondary, display: 'flex', gap: spacing.base, alignItems: 'center' }}>
                  <span>{day.kills} kills {'\u2022'} {day.losses} losses</span>
                  <div style={{ flex: 1, background: 'rgba(16,185,129,0.2)', borderRadius: '2px', height: '8px', overflow: 'hidden' }}>
                    <div style={{ background: color.emerald, height: '100%', width: `${barWidth}%` }} />
                  </div>
                </div>
              </div>
            );
          })}
      </div>
    </div>
  );
}

function RecentActivityPanel({ activity }: { activity: NonNullable<CapitalsData['recent_activity']> }) {
  const activityList = activity || [];
  return (
    <div style={{ background: 'rgba(0,0,0,0.3)', borderRadius: '8px', padding: spacing.base, borderLeft: '2px solid #7c2d12', gridColumn: '1 / -1', maxHeight: '350px', overflowY: 'auto' }}>
      <div style={{ fontSize: fontSize.xxs, textTransform: 'uppercase', color: color.textSecondary, marginBottom: spacing.md }}>
        {'\u2022'} RECENT CAPITAL ACTIVITY ({activityList.length})
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: spacing.sm }}>
        {activityList.map((a) => (
          <a
            key={`${a.killmail_id}-${a.pilot_name || 'unknown'}`}
            href={`https://zkillboard.com/kill/${a.killmail_id}/`}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              background: 'rgba(0,0,0,0.2)',
              padding: '0.25rem 0.4rem',
              borderRadius: '4px',
              fontSize: fontSize.xxs,
              borderLeft: a.activity_type === 'kill' ? '2px solid #3fb950' : '2px solid #f85149',
              textDecoration: 'none',
              color: 'inherit',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.1rem', alignItems: 'center' }}>
              <span style={{ color: '#c9d1d9', display: 'flex', gap: spacing.sm, alignItems: 'center' }}>
                {a.character_id && (
                  <img
                    src={`https://images.evetech.net/characters/${a.character_id}/portrait?size=32`}
                    alt={a.pilot_name || 'Unknown'}
                    style={{ width: '20px', height: '20px', borderRadius: '2px' }}
                  />
                )}
                {a.ship_name} {'\u2022'} {a.pilot_name || 'Unknown'}
              </span>
              <span style={{ color: a.activity_type === 'kill' ? '#3fb950' : '#f85149' }}>
                {a.activity_type.toUpperCase()}
              </span>
            </div>
            <div style={{ fontSize: fontSize.tiny, color: color.textSecondary }}>
              {(a.isk_value / 1e9).toFixed(1)}B ISK {'\u2022'} {a.system_name || 'Unknown'} {'\u2022'} {new Date(a.killmail_time).toLocaleDateString()}
            </div>
          </a>
        ))}
      </div>
    </div>
  );
}
