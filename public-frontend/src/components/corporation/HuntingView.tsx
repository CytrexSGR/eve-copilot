/**
 * Corporation Hunting Tab - ENHANCED
 *
 * Intelligence Command perspective - where/when to find this corporation.
 * Enhancements:
 * - Threat Summary Panel (threat level, avg daily activity, counter-doctrine)
 * - Activity Timeline Panel (sparkline + trend)
 * - Color-coded Strike Windows (kill/death heatmap)
 * - Gatecamp Alerts (detects ambush systems)
 * - Counter-Doctrine Recommendations
 */

import { useState, useEffect } from 'react';
import { corpApi } from '../../services/corporationApi';
import { HuntingScoreBoard } from '../shared/HuntingScoreBoard';
import type {
  HuntingOverview,
  HotZone,
  TopPilot,
  Doctrine,
  TimezoneActivity,
  ActivityTimeline,
} from '../../types/corporation';

interface HuntingViewProps {
  corpId: number;
  days: number;
}

export function HuntingView({ corpId, days }: HuntingViewProps) {
  const [data, setData] = useState<{
    overview: HuntingOverview | null;
    hotZones: HotZone[];
    pilots: TopPilot[];
    doctrines: Doctrine[];
    timezone: TimezoneActivity[];
    timeline: ActivityTimeline | null;
  }>({
    overview: null,
    hotZones: [],
    pilots: [],
    doctrines: [],
    timezone: [],
    timeline: null,
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [overview, hotZones, pilots, doctrines, timezone, timeline] = await Promise.all([
          corpApi.getHuntingOverview(corpId, days),
          corpApi.getHotZones(corpId, days),
          corpApi.getTopPilots(corpId, days),
          corpApi.getDoctrines(corpId, days),
          corpApi.getTimezoneActivity(corpId, days),
          corpApi.getActivityTimeline(corpId, days),
        ]);
        setData({ overview, hotZones, pilots, doctrines, timezone, timeline });
      } catch (err) {
        console.error('Failed to fetch hunting data:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [corpId, days]);

  if (loading) {
    return <div style={{ padding: '2rem', textAlign: 'center', color: '#8b949e' }}>Loading...</div>;
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
      {/* Row 1: Threat Summary (full width) */}
      <ThreatSummaryPanel overview={data.overview} hotZones={data.hotZones} doctrines={data.doctrines} timeline={data.timeline} />

      {/* Row 2: Activity Timeline + Strike Windows */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
        <ActivityTimelinePanel timeline={data.timeline} />
        <StrikeWindowsPanel overview={data.overview} timezone={data.timezone} />
      </div>

      {/* Row 3: Hot Zones + Target Pilots + Doctrines */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.75rem' }}>
        <HotZonesPanel zones={data.hotZones} />
        <TargetPilotsPanel pilots={data.pilots} />
        <DoctrinesPanel doctrines={data.doctrines} />
      </div>

      {/* Row 4: Hunting Opportunity Scores (Full Width) */}
      <HuntingScoreBoard days={days} />
    </div>
  );
}

/**
 * ENHANCEMENT 1: Threat Summary Panel
 * Shows threat level, avg daily activity, peak hour, primary system, counter-doctrine
 */
function ThreatSummaryPanel({
  overview,
  hotZones,
  doctrines,
  timeline,
}: {
  overview: HuntingOverview | null;
  hotZones: HotZone[];
  doctrines: Doctrine[];
  timeline: ActivityTimeline | null;
}) {
  if (!overview || !timeline) return null;

  const threatColor = {
    low: '#3fb950',
    medium: '#ff8800',
    high: '#f85149',
  }[overview.threat_level];

  const trendIcon = {
    increasing: '📈',
    decreasing: '📉',
    stable: '→',
  }[timeline.trend];

  const topShip = doctrines[0]?.ship_name || 'Unknown';
  const counterShip = getCounterShip(topShip);

  return (
    <div
      style={{
        background: 'rgba(0,0,0,0.3)',
        borderRadius: '8px',
        padding: '0.5rem 0.75rem',
        borderLeft: `3px solid ${threatColor}`,
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        fontSize: '0.75rem',
      }}
    >
      {/* Threat Badge */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <div
          style={{
            background: threatColor,
            color: '#000',
            padding: '0.15rem 0.4rem',
            borderRadius: '4px',
            fontSize: '0.7rem',
            fontWeight: 600,
            textTransform: 'uppercase',
          }}
        >
          {overview.threat_level} THREAT
        </div>
        <span style={{ color: '#8b949e' }}>•</span>
        <span style={{ color: '#c9d1d9' }}>
          {trendIcon} <strong>{timeline.avg_daily_activity.toFixed(0)}</strong> avg daily activity
        </span>
      </div>

      {/* Quick Intel */}
      <div style={{ display: 'flex', gap: '1rem', color: '#8b949e' }}>
        <span>
          Peak <strong style={{ color: '#3fb950' }}>{overview.peak_activity_hour ?? '??'}:00</strong> EVE
        </span>
        <span>•</span>
        <span>
          Primary <strong style={{ color: '#58a6ff' }}>{hotZones[0]?.system_name || 'Unknown'}</strong>
        </span>
        <span>•</span>
        <span>
          Flies <strong style={{ color: '#a855f7' }}>{topShip}</strong> → Counter{' '}
          <strong style={{ color: '#ff8800' }}>{counterShip}</strong>
        </span>
      </div>
    </div>
  );
}

/**
 * ENHANCEMENT 2: Activity Timeline Panel
 * Compact sparkline + trend indicator
 */
function ActivityTimelinePanel({ timeline }: { timeline: ActivityTimeline | null }) {
  if (!timeline?.days || timeline.days.length === 0) {
    return (
      <div
        style={{
          background: 'rgba(0,0,0,0.3)',
          borderRadius: '8px',
          padding: '0.75rem',
          borderLeft: '2px solid #8b949e',
        }}
      >
        <div style={{ fontSize: '0.7rem', color: '#8b949e' }}>No activity data</div>
      </div>
    );
  }

  const maxActivity = Math.max(...timeline.days.map((d) => d.total_activity), 1);
  const trendColor = {
    increasing: '#3fb950',
    decreasing: '#f85149',
    stable: '#58a6ff',
  }[timeline.trend];

  const trendIcon = {
    increasing: '⬆️',
    decreasing: '⬇️',
    stable: '→',
  }[timeline.trend];

  return (
    <div
      style={{
        background: 'rgba(0,0,0,0.3)',
        borderRadius: '8px',
        padding: '0.75rem',
        borderLeft: `2px solid ${trendColor}`,
      }}
    >
      {/* Header */}
      <div
        style={{
          fontSize: '0.7rem',
          textTransform: 'uppercase',
          color: '#8b949e',
          marginBottom: '0.5rem',
          display: 'flex',
          justifyContent: 'space-between',
        }}
      >
        <span>• ACTIVITY TIMELINE ({timeline.days.length}D)</span>
        <span style={{ color: trendColor }}>
          {trendIcon} {timeline.trend.toUpperCase()}
        </span>
      </div>

      {/* Sparkline */}
      <div style={{ display: 'flex', alignItems: 'flex-end', gap: '1px', height: '60px', marginBottom: '0.5rem' }}>
        {timeline.days.map((day, i) => {
          const heightPct = (day.total_activity / maxActivity) * 100;
          return (
            <div
              key={i}
              style={{
                flex: 1,
                height: `${heightPct}%`,
                background: trendColor,
                opacity: 0.3 + (heightPct / 100) * 0.7,
                borderRadius: '2px',
              }}
              title={`${day.day}: ${day.total_activity} activity (${day.kills}K/${day.deaths}D)`}
            />
          );
        })}
      </div>

      {/* Stats */}
      <div style={{ fontSize: '0.7rem', color: '#c9d1d9', display: 'flex', justifyContent: 'space-between' }}>
        <span>
          Avg <strong>{timeline.avg_daily_activity.toFixed(0)}</strong>/day
        </span>
        <span style={{ color: '#8b949e' }}>
          Last 3d avg <strong>{(timeline.days.slice(-3).reduce((sum, d) => sum + d.total_activity, 0) / 3).toFixed(0)}</strong>
        </span>
      </div>
    </div>
  );
}

/**
 * ENHANCEMENT 3: Strike Windows Panel - Color-coded heatmap
 * Green = kills dominant, Red = deaths dominant, Blue = balanced
 */
function StrikeWindowsPanel({
  overview,
  timezone,
}: {
  overview: HuntingOverview | null;
  timezone: TimezoneActivity[];
}) {
  const maxActivity = Math.max(...timezone.map((t) => t.activity), 1);
  const peakHour = overview?.peak_activity_hour ?? null;

  return (
    <div
      style={{
        background: 'rgba(0,0,0,0.3)',
        borderRadius: '8px',
        padding: '0.75rem',
        borderLeft: '2px solid #3fb950',
      }}
    >
      <div style={{ fontSize: '0.7rem', textTransform: 'uppercase', color: '#8b949e', marginBottom: '0.5rem' }}>
        • STRIKE WINDOWS (EVE TIME)
      </div>

      {peakHour !== null && (
        <div style={{ fontSize: '0.75rem', color: '#3fb950', marginBottom: '0.5rem' }}>
          Peak Activity: {peakHour.toString().padStart(2, '0')}:00
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(12, 1fr)', gap: '0.2rem' }}>
        {timezone.map((t) => {
          const heightPct = (t.activity / maxActivity) * 100;
          // Color-coding: Green if more kills, Red if more deaths, Blue if balanced
          let color;
          if (t.kills > t.deaths * 1.5) {
            color = `rgba(63, 185, 80, ${0.2 + heightPct / 100})`;
          } else if (t.deaths > t.kills * 1.5) {
            color = `rgba(248, 81, 73, ${0.2 + heightPct / 100})`;
          } else {
            color = `rgba(88, 166, 255, ${0.2 + heightPct / 100})`;
          }

          return (
            <div
              key={t.hour}
              style={{
                height: `${30 + heightPct * 0.6}px`,
                background: t.hour === peakHour ? '#3fb950' : color,
                borderRadius: '2px',
                display: 'flex',
                alignItems: 'flex-end',
                justifyContent: 'center',
                fontSize: '0.6rem',
                color: '#fff',
                paddingBottom: '0.1rem',
              }}
              title={`${t.hour}:00 - ${t.activity} activity (${t.kills}K/${t.deaths}D)`}
            >
              {t.hour}
            </div>
          );
        })}
      </div>
    </div>
  );
}

/**
 * ENHANCEMENT 4: Hot Zones Panel with Gatecamp Alerts
 */
function HotZonesPanel({ zones }: { zones: HotZone[] }) {
  const gatecamps = zones.filter((z) => z.is_gatecamp);

  return (
    <div
      style={{
        background: 'rgba(0,0,0,0.3)',
        borderRadius: '8px',
        padding: '0.75rem',
        borderLeft: '2px solid #ff8800',
        maxHeight: '400px',
        overflowY: 'auto',
      }}
    >
      <div style={{ fontSize: '0.7rem', textTransform: 'uppercase', color: '#8b949e', marginBottom: '0.5rem' }}>
        • HOT ZONES ({zones.length})
        {gatecamps.length > 0 && (
          <span style={{ color: '#f85149', marginLeft: '0.5rem' }}>⚠️ {gatecamps.length} GATECAMPS</span>
        )}
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
        {zones.slice(0, 15).map((zone) => (
          <div
            key={zone.system_id}
            style={{
              background: 'rgba(0,0,0,0.2)',
              padding: '0.25rem 0.4rem',
              borderRadius: '4px',
              fontSize: '0.7rem',
              borderLeft: zone.is_gatecamp ? '2px solid #f85149' : '2px solid #ff8800',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', color: '#c9d1d9' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                <span style={{ fontWeight: 600 }}>{zone.system_name}</span>
                {zone.is_gatecamp && (
                  <span style={{ color: '#f85149', fontSize: '0.65rem', fontWeight: 600 }}>⚠️ CAMP</span>
                )}
              </div>
              <span style={{ color: '#8b949e' }}>{zone.activity} kills</span>
            </div>
            <div style={{ fontSize: '0.65rem', color: '#8b949e', marginTop: '0.1rem' }}>
              {zone.region_name} • {zone.kills}K/{zone.deaths}D • {zone.efficiency}% eff
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/**
 * Target Pilots Panel
 */
function TargetPilotsPanel({ pilots }: { pilots: TopPilot[] }) {
  return (
    <div
      style={{
        background: 'rgba(0,0,0,0.3)',
        borderRadius: '8px',
        padding: '0.75rem',
        borderLeft: '2px solid #f85149',
        maxHeight: '400px',
        overflowY: 'auto',
      }}
    >
      <div style={{ fontSize: '0.7rem', textTransform: 'uppercase', color: '#8b949e', marginBottom: '0.5rem' }}>
        • TARGET PILOTS ({pilots.length})
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
        {pilots.slice(0, 20).map((pilot) => (
          <div
            key={pilot.character_id}
            style={{
              background: 'rgba(0,0,0,0.2)',
              padding: '0.25rem 0.4rem',
              borderRadius: '4px',
              fontSize: '0.7rem',
              borderLeft: pilot.has_capital_kills ? '2px solid #ff0000' : '2px solid #f85149',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                <img
                  src={`https://images.evetech.net/characters/${pilot.character_id}/portrait?size=32`}
                  alt={pilot.character_name || 'Unknown'}
                  style={{ width: '20px', height: '20px', borderRadius: '3px' }}
                />
                <span style={{ color: '#c9d1d9', fontWeight: 600 }}>
                  {pilot.character_name || 'Unknown'}
                </span>
                {pilot.has_capital_kills && (
                  <span style={{ color: '#ff0000', fontSize: '0.65rem' }}>🚀 CAP</span>
                )}
              </div>
              <span style={{ color: '#3fb950' }}>{pilot.kills} kills</span>
            </div>
            <div style={{ fontSize: '0.65rem', color: '#8b949e', marginTop: '0.1rem' }}>
              {(parseFloat(pilot.isk_destroyed) / 1e9).toFixed(1)}B ISK destroyed
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/**
 * ENHANCEMENT 5: Doctrines Panel with Counter-Doctrine Recommendations
 */
function DoctrinesPanel({ doctrines }: { doctrines: Doctrine[] }) {
  return (
    <div
      style={{
        background: 'rgba(0,0,0,0.3)',
        borderRadius: '8px',
        padding: '0.75rem',
        borderLeft: '2px solid #a855f7',
        maxHeight: '400px',
        overflowY: 'auto',
      }}
    >
      <div style={{ fontSize: '0.7rem', textTransform: 'uppercase', color: '#8b949e', marginBottom: '0.5rem' }}>
        • DOCTRINE ANALYSIS ({doctrines.length})
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
        {doctrines.slice(0, 15).map((doctrine, idx) => {
          const counter = idx < 3 ? getCounterShip(doctrine.ship_name) : null;
          return (
            <div key={doctrine.ship_name} style={{ marginBottom: '0.1rem' }}>
              <div
                style={{
                  background: 'rgba(0,0,0,0.2)',
                  padding: '0.2rem 0.35rem',
                  borderRadius: '4px',
                  fontSize: '0.7rem',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                  <span style={{ color: '#c9d1d9' }}>{doctrine.ship_name}</span>
                  <span style={{ fontSize: '0.65rem', color: '#6e7681' }}>({doctrine.ship_group})</span>
                </div>
                <span style={{ color: '#8b949e' }}>
                  {doctrine.count} ({doctrine.percentage}%)
                </span>
              </div>
              {counter && (
                <div
                  style={{
                    fontSize: '0.65rem',
                    color: '#ff8800',
                    marginLeft: '0.5rem',
                    marginTop: '0.1rem',
                  }}
                >
                  → Counter: {counter}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

/**
 * Counter-doctrine map
 */
function getCounterShip(ship: string): string {
  const counters: Record<string, string> = {
    Cerberus: 'Muninn, Eagle',
    Muninn: 'Zealot, Eagle',
    Eagle: 'Muninn, Cerberus',
    Zealot: 'Muninn, Eagle',
    Ishtar: 'Muninn, Eagle',
    Vagabond: 'Muninn, Zealot',
    Jackdaw: 'Svipul, Hecate',
    Svipul: 'Jackdaw, Confessor',
    Hecate: 'Jackdaw, Svipul',
    Confessor: 'Svipul, Jackdaw',
    Brutix: 'Ferox, Hurricane',
    Ferox: 'Brutix, Eagle',
    Hurricane: 'Ferox, Brutix',
    Maller: 'Caracal, Moa',
    Caracal: 'Maller, Arbitrator',
    Moa: 'Caracal, Maller',
    Vexor: 'Caracal, Moa',
    Stabber: 'Caracal, Moa',
    Thorax: 'Caracal, Moa',
  };
  return counters[ship] || 'Adapt doctrine';
}
