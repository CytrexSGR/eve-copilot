/**
 * Shared Offensive Tab - Military Intelligence Dashboard
 *
 * Unified component for Alliance, Corporation, and PowerBloc entities.
 * Comprehensive 12-panel offensive capability assessment:
 * - Kill Timeline (30-day activity)
 * - Combat Performance (K/D, efficiency, solo %)
 * - Hot Systems (kill zones detection)
 * - Damage Dealt Profile
 * - E-War Usage
 * - Engagement Profile (solo/small/medium/large/blob)
 * - Solo Killers (dangerous pilots)
 * - Geographic Analysis (systems + regions)
 * - Ship/Doctrine Profile
 * - Effective Doctrines
 * - Kill Velocity Trends
 * - Top Victims (30 corps)
 * - Victim Tank Profile (PowerBloc only)
 */

import { useState, useEffect } from 'react';
import type { EntityViewProps, FetcherMap } from './types';
import * as allianceApi from '../../services/allianceApi';
import { corpApi } from '../../services/corporationApi';
import { powerblocApi } from '../../services/api/powerbloc';
import type { VictimTankProfile } from '../../services/api/powerbloc';

import { fontSize, color, spacing } from '../../styles/theme';

// ============================================================================
// Unified Data Interface (superset of all 3 entity types)
// ============================================================================

interface OffensiveData {
  summary: {
    total_kills: number;
    isk_destroyed: string;
    avg_kill_value: string;
    max_kill_value: number;
    kd_ratio: number;
    solo_kill_pct: number;
    capital_kills: number;
    efficiency: number;
  };
  engagement_profile: {
    solo: { kills: number; percentage: number };
    small: { kills: number; percentage: number };
    medium: { kills: number; percentage: number };
    large: { kills: number; percentage: number };
    blob: { kills: number; percentage: number };
  };
  solo_killers: Array<{
    character_id: number;
    character_name: string;
    solo_kills: number;
    avg_solo_kill_value: number;
    primary_ship: string | null;
  }>;
  doctrine_profile: Array<{
    ship_name: string;
    ship_class: string;
    count: number;
    percentage: number;
  }>;
  ship_losses_inflicted: Array<{
    ship_class: string;
    count: number;
    percentage: number;
  }>;
  victim_analysis: {
    total_kills: number;
    pvp_kills: number;
    pve_kills: number;
    gank_kills: number;
    avg_victim_value: number;
    capital_kills: number;
  };
  kill_heatmap: Array<{
    system_id: number;
    system_name: string;
    region_name: string;
    kills: number;
    activity?: string;
    kills_per_day?: number;
    is_gatecamp: boolean;
  }>;
  hunting_regions: Array<{
    region_id: number;
    region_name: string;
    kills: number;
    percentage: number;
    unique_systems: number;
  }>;
  kill_timeline: Array<{
    day: string;
    kills: number;
    active_pilots: number;
  }>;
  hunting_hours?: {
    peak_start: number;
    peak_end: number;
    safe_start: number;
    safe_end: number;
  };
  hot_systems?: Array<{
    system_id: number;
    system_name: string;
    region_name: string;
    kills: number;
    deaths: number;
    avg_kill_value: number;
    kill_score: number;
    is_gatecamp: boolean;
  }>;
  damage_dealt?: Array<{
    damage_type: string;
    percentage: number;
  }>;
  ewar_usage?: Array<{
    ewar_type: string;
    count: number;
    percentage: number;
  }>;
  effective_doctrines?: Array<{
    ship_class: string;
    kills: number;
    deaths: number;
    kd_ratio: number;
    isk_efficiency: number;
  }>;
  kill_velocity?: Array<{
    ship_class: string;
    recent_kills: number;
    previous_kills: number;
    velocity_pct: number;
    status: string;
  }>;
  capital_threat?: {
    capital_kills: number;
    capital_kill_pct: number;
    carrier_kills: number;
    dread_kills: number;
    super_titan_kills: number;
    avg_capital_kill_value: number;
  } | null;
  top_victims: Array<{
    corporation_id: number;
    corporation_name: string | null;
    kills_on_them: number;
    isk_destroyed: string;
  }>;
}

// ============================================================================
// Fetcher Map
// ============================================================================

const offensiveFetchers: FetcherMap<OffensiveData> = {
  alliance: (entityId, days) =>
    allianceApi.getOffensiveStats(entityId, days) as unknown as Promise<OffensiveData>,
  corporation: (entityId, days) =>
    corpApi.getOffensiveStats(entityId, days) as Promise<OffensiveData>,
  powerbloc: (entityId, days) =>
    powerblocApi.getOffensive(entityId, days) as unknown as Promise<OffensiveData>,
};

// ============================================================================
// Main Component
// ============================================================================

export function OffensiveView({ entityType, entityId, days }: EntityViewProps) {
  const [data, setData] = useState<OffensiveData | null>(null);
  const [victimTank, setVictimTank] = useState<VictimTankProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);

    if (entityType === 'powerbloc') {
      // Fetch both offensive stats and victim tank profile in parallel
      Promise.all([
        offensiveFetchers[entityType](entityId, days),
        powerblocApi.getVictimTankProfile(entityId, days).catch(() => null)
      ])
        .then(([offensiveData, tankData]) => {
          setData(offensiveData);
          setVictimTank(tankData);
        })
        .catch((err: Error) => {
          console.error('Failed to load offensive stats:', err);
          setError(err.message);
        })
        .finally(() => setLoading(false));
    } else {
      offensiveFetchers[entityType](entityId, days)
        .then(setData)
        .catch((err: Error) => {
          console.error('Failed to load offensive stats:', err);
          setError(err.message);
        })
        .finally(() => setLoading(false));
    }
  }, [entityType, entityId, days]);

  if (loading) {
    return (
      <div style={{ padding: spacing["3xl"], textAlign: 'center', color: color.textSecondary }}>
        Loading offensive intelligence...
      </div>
    );
  }

  if (error || !data) {
    return (
      <div style={{ padding: spacing["3xl"], textAlign: 'center', color: color.lossRed }}>
        Failed to load offensive stats: {error || 'Unknown error'}
      </div>
    );
  }

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: spacing.base }}>
      {/* Row 1: Kill Timeline (Full Width) */}
      <KillTimelinePanel timeline={data.kill_timeline} huntingHours={data.hunting_hours || { peak_start: 0, peak_end: 0, safe_start: 0, safe_end: 0 }} />

      {/* Row 2: Combat Performance (Full Width) */}
      <div style={{ gridColumn: '1 / -1' }}>
        <CombatSummaryPanel summary={data.summary} analysis={data.victim_analysis} capitalThreat={data.capital_threat} />
      </div>

      {/* Row 3: Hot Systems (Full Width) */}
      <HotSystemsPanel systems={data.hot_systems || []} />

      {/* Row 4: Damage Dealt | E-War Usage | Engagement Profile */}
      <DamageDealtPanel profile={data.damage_dealt || []} />
      <EWarUsagePanel usage={data.ewar_usage || []} />
      <EngagementProfilePanel profile={data.engagement_profile} />

      {/* Row 5: Solo Killers | Geographic | Ship/Doctrine */}
      <SoloKillersPanel killers={data.solo_killers} />
      <GeographicPanel heatmap={data.kill_heatmap} regions={data.hunting_regions} />
      <ShipDoctrinePanel shipClasses={data.ship_losses_inflicted} doctrine={data.doctrine_profile} />

      {/* Row 6: Effective Doctrines | Kill Velocity (spans 2 cols) */}
      <EffectiveDoctrinesPanel doctrines={data.effective_doctrines || []} />
      <div style={{ gridColumn: 'span 2' }}>
        <KillVelocityPanel velocity={data.kill_velocity || []} />
      </div>

      {/* Row 7: Victim Tank Profile (PowerBloc only, Full Width) */}
      {entityType === 'powerbloc' && victimTank && victimTank.killmails_analyzed > 0 && (
        <VictimTankPanel profile={victimTank} />
      )}

      {/* Row 8: Top Victims (Full Width) */}
      <TopVictimsPanel victims={data.top_victims} />
    </div>
  );
}

// ============================================================================
// Utility Functions
// ============================================================================

function getEfficiencyColor(eff: number): string {
  if (eff >= 70) return '#3fb950';
  if (eff >= 50) return '#ffcc00';
  return '#f85149';
}

function getKDColor(kd: number): string {
  if (kd >= 2.0) return '#3fb950';
  if (kd >= 1.0) return '#ffcc00';
  return '#f85149';
}

function calculateTrend(timeline: { day: string; kills?: number }[]): string {
  if (timeline.length < 7) return '\u2192';
  const last3 = timeline.slice(-3).reduce((sum, d) => sum + (d.kills || 0), 0) / 3;
  const prev4 = timeline.slice(-7, -3).reduce((sum, d) => sum + (d.kills || 0), 0) / 4;
  const diff = ((last3 - prev4) / (prev4 || 1)) * 100;
  if (diff > 15) return '\u2B06\uFE0F';
  if (diff < -15) return '\u2B07\uFE0F';
  return '\u2192';
}

// ============================================================================
// Panel Components
// ============================================================================

function CombatSummaryPanel({
  summary,
  analysis,
  capitalThreat
}: {
  summary: OffensiveData['summary'];
  analysis: OffensiveData['victim_analysis'];
  capitalThreat?: OffensiveData['capital_threat'];
}) {
  const kdColor = getKDColor(summary.kd_ratio);
  const effColor = getEfficiencyColor(summary.efficiency);
  const pvpPct = analysis.total_kills > 0 ? (100 * analysis.pvp_kills / analysis.total_kills) : 0;
  const pveGankPct = analysis.total_kills > 0 ? (100 * (analysis.pve_kills + analysis.gank_kills) / analysis.total_kills) : 0;

  return (
    <div style={{ background: 'rgba(0,0,0,0.3)', borderRadius: '8px', padding: spacing.md, borderLeft: '2px solid #3fb950' }}>
      <div style={{ fontSize: fontSize.xxs, textTransform: 'uppercase', color: color.textSecondary, marginBottom: spacing.sm }}>
        {'\u2022'} COMBAT PERFORMANCE
      </div>

      <div style={{ display: 'flex', gap: spacing.sm, fontSize: fontSize.xs }}>
        <div style={{ flex: 1, minWidth: '70px' }}>
          <div style={{ color: color.textSecondary, fontSize: fontSize.micro }}>ISK Destroyed</div>
          <div style={{ fontSize: fontSize.lg, color: color.killGreen, fontFamily: 'monospace' }}>
            {(Number(summary.isk_destroyed) / 1e12).toFixed(1)}T
          </div>
        </div>

        <div style={{ flex: 1, minWidth: '70px' }}>
          <div style={{ color: color.textSecondary, fontSize: fontSize.micro }}>Efficiency</div>
          <div style={{ fontSize: fontSize.lg, color: effColor, fontFamily: 'monospace' }}>
            {summary.efficiency}%
          </div>
        </div>

        <div style={{ flex: 1, minWidth: '60px' }}>
          <div style={{ color: color.textSecondary, fontSize: fontSize.micro }}>K/D</div>
          <div style={{ fontSize: fontSize.lg, color: kdColor, fontFamily: 'monospace' }}>
            {summary.kd_ratio.toFixed(2)}
          </div>
        </div>

        <div style={{ flex: 1, minWidth: '80px' }}>
          <div style={{ color: color.textSecondary, fontSize: fontSize.micro }}>PvP Kills</div>
          <div style={{ fontSize: fontSize.base, color: color.killGreen, fontFamily: 'monospace' }}>
            {analysis.pvp_kills} ({pvpPct.toFixed(0)}%)
          </div>
        </div>

        <div style={{ flex: 1, minWidth: '80px' }}>
          <div style={{ color: color.textSecondary, fontSize: fontSize.micro }}>PvE/Gank</div>
          <div style={{ fontSize: fontSize.base, color: color.linkBlue, fontFamily: 'monospace' }}>
            {analysis.pve_kills}/{analysis.gank_kills} ({pveGankPct.toFixed(0)}%)
          </div>
        </div>

        <div style={{ flex: 1, minWidth: '60px' }}>
          <div style={{ color: color.textSecondary, fontSize: fontSize.micro }}>Solo %</div>
          <div style={{ fontSize: fontSize.lg, color: color.accentPurple, fontFamily: 'monospace' }}>
            {summary.solo_kill_pct.toFixed(1)}%
          </div>
        </div>

        <div style={{ flex: 1, minWidth: '70px' }}>
          <div style={{ color: color.textSecondary, fontSize: fontSize.micro }}>Avg Value</div>
          <div style={{ fontSize: fontSize.lg, color: '#c9d1d9', fontFamily: 'monospace' }}>
            {(analysis.avg_victim_value / 1e6).toFixed(0)}M
          </div>
        </div>

        <div style={{ flex: 1, minWidth: '70px' }}>
          <div style={{ color: color.textSecondary, fontSize: fontSize.micro }}>Capitals</div>
          <div style={{ fontSize: fontSize.lg, color: summary.capital_kills > 0 ? '#ff0000' : '#666', fontFamily: 'monospace' }}>
            {summary.capital_kills}
          </div>
        </div>

        {capitalThreat && capitalThreat.capital_kills > 0 && (
          <div style={{ flex: 1, minWidth: '100px' }}>
            <div style={{ color: color.textSecondary, fontSize: fontSize.micro }}>Carrier/Dread/Super</div>
            <div style={{ fontSize: fontSize.base, color: '#c9d1d9', fontFamily: 'monospace' }}>
              {capitalThreat.carrier_kills}/{capitalThreat.dread_kills}/{capitalThreat.super_titan_kills}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function EngagementProfilePanel({ profile }: { profile: OffensiveData['engagement_profile'] }) {
  const types = [
    { key: 'solo', label: 'Solo (\u22643)', color: color.killGreen },
    { key: 'small', label: 'Small (4-10)', color: color.linkBlue },
    { key: 'medium', label: 'Medium (11-30)', color: color.accentPurple },
    { key: 'large', label: 'Large (31-100)', color: color.warningOrange },
    { key: 'blob', label: 'Blob (>100)', color: color.lossRed },
  ] as const;

  return (
    <div style={{ background: 'rgba(0,0,0,0.3)', borderRadius: '8px', padding: spacing.base, borderLeft: '2px solid #58a6ff' }}>
      <div style={{ fontSize: fontSize.xxs, textTransform: 'uppercase', color: color.textSecondary, marginBottom: spacing.sm }}>
        {'\u2022'} ENGAGEMENT PROFILE
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: spacing.sm }}>
        {types.map(({ key, label, color }) => {
          const data = profile[key];
          return (
            <div key={key}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: fontSize.xxs, marginBottom: spacing['2xs'] }}>
                <span style={{ color: '#c9d1d9' }}>{label}</span>
                <span style={{ color, fontFamily: 'monospace' }}>{data.kills} ({data.percentage}%)</span>
              </div>
              <div style={{ height: '8px', background: 'rgba(0,0,0,0.3)', borderRadius: '4px', overflow: 'hidden' }}>
                <div style={{ height: '100%', width: `${data.percentage}%`, background: color, transition: 'width 0.3s' }} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function SoloKillersPanel({ killers }: { killers: OffensiveData['solo_killers'] }) {
  return (
    <div style={{ background: 'rgba(0,0,0,0.3)', borderRadius: '8px', padding: spacing.base, borderLeft: '2px solid #f85149', maxHeight: '280px', overflowY: 'auto' }}>
      <div style={{ fontSize: fontSize.xxs, textTransform: 'uppercase', color: color.textSecondary, marginBottom: spacing.sm }}>
        {'\u2022'} SOLO KILLERS ({killers.length})
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
        {killers.slice(0, 20).map((killer) => (
          <a
            key={killer.character_id}
            href={`https://zkillboard.com/character/${killer.character_id}/`}
            target="_blank"
            rel="noopener noreferrer"
            style={{ background: 'rgba(0,0,0,0.2)', padding: '0.25rem 0.35rem', borderRadius: '4px', fontSize: fontSize.xxs, borderLeft: '2px solid #f85149', textDecoration: 'none', color: 'inherit', display: 'flex', alignItems: 'center', gap: spacing.sm }}
          >
            <img
              src={`https://images.evetech.net/characters/${killer.character_id}/portrait?size=32`}
              alt=""
              style={{ width: '20px', height: '20px', borderRadius: '3px' }}
            />
            <div style={{ flex: 1 }}>
              <div style={{ color: '#c9d1d9', fontWeight: 600 }}>{killer.character_name || 'Unknown'}</div>
              <div style={{ fontSize: fontSize.tiny, color: color.textSecondary }}>
                {killer.solo_kills} solo kills {'\u2022'} {(killer.avg_solo_kill_value / 1e6).toFixed(1)}M avg {'\u2022'} {killer.primary_ship || 'Various'}
              </div>
            </div>
          </a>
        ))}
      </div>
    </div>
  );
}

function ShipDoctrinePanel({
  shipClasses,
  doctrine
}: {
  shipClasses: OffensiveData['ship_losses_inflicted'];
  doctrine: OffensiveData['doctrine_profile'];
}) {
  const [tab, setTab] = useState<'ships' | 'doctrine'>('ships');

  const colorMap: Record<string, string> = {
    Frigate: '#3fb950',
    Destroyer: '#58a6ff',
    Cruiser: '#a855f7',
    Battlecruiser: '#ff8800',
    Battleship: '#ff4444',
    Capital: '#ff0000',
    Capsule: '#666',
    Structure: '#9333ea',
    Industrial: '#10b981',
    'Fighter/Drone': '#06b6d4',
    Deployable: '#f59e0b',
    Other: '#8b949e',
  };

  return (
    <div style={{ background: 'rgba(0,0,0,0.3)', borderRadius: '8px', padding: spacing.base, borderLeft: '2px solid #ff8800', maxHeight: '280px', display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', gap: spacing.sm, marginBottom: spacing.sm, flexShrink: 0 }}>
        <button
          onClick={() => setTab('ships')}
          style={{
            background: tab === 'ships' ? 'rgba(255,136,0,0.2)' : 'transparent',
            border: `1px solid ${tab === 'ships' ? '#ff8800' : '#3d444d'}`,
            padding: '0.2rem 0.5rem',
            borderRadius: '4px',
            fontSize: fontSize.tiny,
            color: tab === 'ships' ? '#ff8800' : '#8b949e',
            cursor: 'pointer',
            textTransform: 'uppercase',
            fontWeight: 600
          }}
        >
          Victims by Class
        </button>
        <button
          onClick={() => setTab('doctrine')}
          style={{
            background: tab === 'doctrine' ? 'rgba(168,85,247,0.2)' : 'transparent',
            border: `1px solid ${tab === 'doctrine' ? '#a855f7' : '#3d444d'}`,
            padding: '0.2rem 0.5rem',
            borderRadius: '4px',
            fontSize: fontSize.tiny,
            color: tab === 'doctrine' ? '#a855f7' : '#8b949e',
            cursor: 'pointer',
            textTransform: 'uppercase',
            fontWeight: 600
          }}
        >
          Attack Doctrine
        </button>
      </div>

      {tab === 'ships' ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: spacing.sm, fontSize: fontSize.xxs, flex: 1, overflowY: 'auto' }}>
          {shipClasses.map((sc) => (
            <div key={sc.ship_class}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.1rem', color: '#c9d1d9' }}>
                <span>{sc.ship_class}</span>
                <span style={{ fontFamily: 'monospace', color: colorMap[sc.ship_class] || '#8b949e' }}>
                  {sc.count} ({sc.percentage}%)
                </span>
              </div>
              <div style={{ background: 'rgba(255,255,255,0.05)', borderRadius: '2px', height: '8px', overflow: 'hidden' }}>
                <div style={{ background: colorMap[sc.ship_class] || '#8b949e', height: '100%', width: `${sc.percentage}%`, transition: 'width 0.3s' }} />
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: spacing.sm, fontSize: fontSize.xxs, flex: 1, overflowY: 'auto' }}>
          {doctrine.slice(0, 15).map((ship) => (
            <div key={ship.ship_name}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.1rem', color: '#c9d1d9' }}>
                <span>{ship.ship_name}</span>
                <span style={{ fontFamily: 'monospace', color: color.accentPurple }}>{ship.count} ({ship.percentage}%)</span>
              </div>
              <div style={{ background: 'rgba(255,255,255,0.05)', borderRadius: '2px', height: '6px', overflow: 'hidden' }}>
                <div style={{ background: color.accentPurple, height: '100%', width: `${ship.percentage}%`, transition: 'width 0.3s' }} />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}


function GeographicPanel({
  heatmap,
  regions
}: {
  heatmap: OffensiveData['kill_heatmap'];
  regions: OffensiveData['hunting_regions'];
}) {
  const [tab, setTab] = useState<'systems' | 'regions'>('systems');

  return (
    <div style={{ background: 'rgba(0,0,0,0.3)', borderRadius: '8px', padding: spacing.base, borderLeft: '2px solid #00bcd4', maxHeight: '280px', display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', gap: spacing.sm, marginBottom: spacing.sm, flexShrink: 0 }}>
        <button
          onClick={() => setTab('systems')}
          style={{
            background: tab === 'systems' ? 'rgba(0,188,212,0.2)' : 'transparent',
            border: `1px solid ${tab === 'systems' ? '#00bcd4' : '#3d444d'}`,
            padding: '0.2rem 0.5rem',
            borderRadius: '4px',
            fontSize: fontSize.tiny,
            color: tab === 'systems' ? '#00bcd4' : '#8b949e',
            cursor: 'pointer',
            textTransform: 'uppercase',
            fontWeight: 600
          }}
        >
          Kill Heatmap
        </button>
        <button
          onClick={() => setTab('regions')}
          style={{
            background: tab === 'regions' ? 'rgba(147,51,234,0.2)' : 'transparent',
            border: `1px solid ${tab === 'regions' ? '#9333ea' : '#3d444d'}`,
            padding: '0.2rem 0.5rem',
            borderRadius: '4px',
            fontSize: fontSize.tiny,
            color: tab === 'regions' ? '#9333ea' : '#8b949e',
            cursor: 'pointer',
            textTransform: 'uppercase',
            fontWeight: 600
          }}
        >
          Hunting Regions
        </button>
      </div>

      {tab === 'systems' ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: spacing.sm, flex: 1, overflowY: 'auto' }}>
          {heatmap.slice(0, 20).map((zone) => (
            <a
              key={zone.system_id}
              href={`/system/${zone.system_id}`}
              style={{ background: 'rgba(0,0,0,0.2)', padding: '0.25rem 0.4rem', borderRadius: '4px', fontSize: fontSize.xxs, borderLeft: `2px solid ${zone.is_gatecamp ? '#ff0000' : '#00bcd4'}`, textDecoration: 'none', color: 'inherit' }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600, color: '#c9d1d9' }}>
                    {zone.is_gatecamp && <span style={{ marginRight: spacing.sm }}>{'\uD83D\uDEA8'}</span>}
                    {zone.system_name}
                  </div>
                  <div style={{ fontSize: fontSize.tiny, color: color.textSecondary, marginTop: '0.1rem' }}>
                    {zone.region_name} {'\u2022'} {zone.activity || 'active'}
                  </div>
                </div>
                <div style={{ fontSize: fontSize.lg, color: color.teal, fontFamily: 'monospace' }}>
                  {zone.kills}
                </div>
              </div>
            </a>
          ))}
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: spacing.sm, fontSize: fontSize.xxs, flex: 1, overflowY: 'auto' }}>
          {regions.slice(0, 15).map((region) => (
            <div key={region.region_id}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.1rem', color: '#c9d1d9' }}>
                <span>{region.region_name} ({region.unique_systems} sys)</span>
                <span style={{ fontFamily: 'monospace', color: '#9333ea' }}>
                  {region.kills || 0} ({region.percentage}%)
                </span>
              </div>
              <div style={{ background: 'rgba(255,255,255,0.05)', borderRadius: '2px', height: '8px', overflow: 'hidden' }}>
                <div style={{ background: '#9333ea', height: '100%', width: `${region.percentage}%`, transition: 'width 0.3s' }} />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function KillTimelinePanel({
  timeline,
  huntingHours
}: {
  timeline: OffensiveData['kill_timeline'];
  huntingHours: NonNullable<OffensiveData['hunting_hours']>;
}) {
  const kills = timeline.map(d => d.kills || 0);
  const pilots = timeline.map(d => d.active_pilots || 0);
  const trend = calculateTrend(timeline);
  const avgKills = kills.length > 0 ? kills.reduce((sum, k) => sum + k, 0) / kills.length : 0;
  const last3 = kills.length >= 3 ? kills.slice(-3).reduce((sum, k) => sum + k, 0) / 3 : 0;
  const peakKills = Math.max(...kills, 0);

  // Single Y-axis for BOTH metrics - round up to nearest 100
  const maxValue = Math.max(...kills, ...pilots, 0);
  const yAxisMax = Math.max(Math.ceil(maxValue / 100) * 100, 100);

  // Generate Y-axis labels in steps of 100
  const yStep = 100;
  const yLabels: number[] = [];
  for (let i = 0; i <= yAxisMax; i += yStep) {
    yLabels.push(i);
  }

  // Line chart dimensions
  const chartWidth = 900;
  const chartHeight = 100;
  const padding = { top: 5, right: 35, bottom: 25, left: 45 };
  const dataWidth = chartWidth - padding.left - padding.right;
  const dataHeight = chartHeight - padding.top - padding.bottom;

  // Calculate points (BOTH using same Y-axis)
  const killPoints = kills.map((k, i) => ({
    x: padding.left + (i / Math.max(kills.length - 1, 1)) * dataWidth,
    y: padding.top + dataHeight - (k / Math.max(yAxisMax, 1)) * dataHeight
  }));

  const pilotPoints = pilots.map((p, i) => ({
    x: padding.left + (i / Math.max(pilots.length - 1, 1)) * dataWidth,
    y: padding.top + dataHeight - (p / Math.max(yAxisMax, 1)) * dataHeight
  }));

  const killPathD = killPoints.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');
  const pilotPathD = pilotPoints.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');

  // X-axis labels (smart sampling)
  const maxXLabels = 10;
  const step = Math.ceil(timeline.length / maxXLabels);
  const xLabelIndices = timeline.map((_, i) => i).filter((i, idx) => idx % step === 0 || i === timeline.length - 1);

  return (
    <div style={{ background: 'rgba(0,0,0,0.3)', borderRadius: '8px', padding: spacing.base, borderLeft: '2px solid #10b981', gridColumn: '1 / -1' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: spacing.sm }}>
        <div style={{ fontSize: fontSize.xxs, textTransform: 'uppercase', color: color.textSecondary }}>
          {'\u2022'} KILL TIMELINE ({timeline.length} days) {trend}
        </div>
        {/* Legend */}
        <div style={{ display: 'flex', gap: spacing.base, fontSize: fontSize.micro, color: color.textSecondary }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: spacing.xs }}>
            <div style={{ width: '10px', height: '2px', background: color.killGreen }} />
            <span>Kills</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: spacing.xs }}>
            <div style={{ width: '10px', height: '2px', background: color.linkBlue }} />
            <span>Active Pilots</span>
          </div>
        </div>
      </div>

      {/* Line Chart */}
      <div style={{ marginBottom: spacing.sm, display: 'flex', justifyContent: 'center' }}>
        <svg width={chartWidth} height={chartHeight} style={{ display: 'block' }}>
          {/* Y-axis grid + labels (single axis for both metrics) */}
          {yLabels.map((value, i) => {
            const y = padding.top + dataHeight - (value / yAxisMax) * dataHeight;
            return (
              <g key={i}>
                <line x1={padding.left} y1={y} x2={chartWidth - padding.right} y2={y} stroke="rgba(255,255,255,0.08)" strokeWidth="1" />
                <text x={padding.left - 5} y={y + 3} textAnchor="end" fontSize="9" fill="#6e7681" fontFamily="monospace">
                  {value}
                </text>
              </g>
            );
          })}

          {/* X-axis labels */}
          {xLabelIndices.map(i => {
            const date = new Date(timeline[i]?.day || '');
            const label = `${date.getMonth() + 1}/${date.getDate()}`;
            return (
              <text key={i} x={killPoints[i]?.x || 0} y={chartHeight - 8} textAnchor="middle" fontSize="9" fill="#6e7681" fontFamily="monospace">
                {label}
              </text>
            );
          })}

          {/* Kill Line (green) */}
          <path d={killPathD} fill="none" stroke="#3fb950" strokeWidth="2.5" />

          {/* Pilot Line (blue) */}
          <path d={pilotPathD} fill="none" stroke="#58a6ff" strokeWidth="2" opacity="0.8" />

          {/* Data points - Kills */}
          {killPoints.filter((_, i) => i % Math.max(1, Math.floor(killPoints.length / 30)) === 0).map((p, i) => (
            <circle key={`kill-${i}`} cx={p.x} cy={p.y} r="2.5" fill="#3fb950" />
          ))}

          {/* Data points - Pilots */}
          {pilotPoints.filter((_, i) => i % Math.max(1, Math.floor(pilotPoints.length / 30)) === 0).map((p, i) => (
            <circle key={`pilot-${i}`} cx={p.x} cy={p.y} r="2" fill="#58a6ff" />
          ))}
        </svg>
      </div>

      {/* Stats Grid with Peak Hours */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: spacing.sm, fontSize: fontSize.xs }}>
        <div>
          <div style={{ color: color.textSecondary, fontSize: fontSize.tiny }}>Avg Kills/Day</div>
          <div style={{ fontSize: fontSize.h4, color: '#c9d1d9', fontFamily: 'monospace', fontWeight: 700 }}>
            {avgKills.toFixed(1)}
          </div>
        </div>
        <div>
          <div style={{ color: color.textSecondary, fontSize: fontSize.tiny }}>Last 3 Days</div>
          <div style={{ fontSize: fontSize.h4, color: trend === '\u2B06\uFE0F' ? '#3fb950' : trend === '\u2B07\uFE0F' ? '#ff0000' : '#ffcc00', fontFamily: 'monospace', fontWeight: 700 }}>
            {last3.toFixed(1)}
          </div>
        </div>
        <div>
          <div style={{ color: color.textSecondary, fontSize: fontSize.tiny }}>Peak Kills</div>
          <div style={{ fontSize: fontSize.h4, color: color.killGreen, fontFamily: 'monospace', fontWeight: 700 }}>
            {peakKills}
          </div>
        </div>
        <div>
          <div style={{ color: color.textSecondary, fontSize: fontSize.tiny }}>{'\uD83C\uDFAF'} Peak Hours</div>
          <div style={{ fontSize: fontSize.lg, color: '#22c55e', fontFamily: 'monospace', fontWeight: 700 }}>
            {huntingHours?.peak_start || 0}:00-{huntingHours?.peak_end || 0}:00
          </div>
        </div>
        <div>
          <div style={{ color: color.textSecondary, fontSize: fontSize.tiny }}>{'\u23F0'} Low Activity</div>
          <div style={{ fontSize: fontSize.lg, color: color.textSecondary, fontFamily: 'monospace', fontWeight: 700 }}>
            {huntingHours?.safe_start || 0}:00-{huntingHours?.safe_end || 0}:00
          </div>
        </div>
      </div>
    </div>
  );
}

function TopVictimsPanel({ victims }: { victims: OffensiveData['top_victims'] }) {
  return (
    <div style={{ background: 'rgba(0,0,0,0.3)', borderRadius: '8px', padding: spacing.base, borderLeft: '2px solid #64748b', gridColumn: '1 / -1', maxHeight: '400px', overflowY: 'auto' }}>
      <div style={{ fontSize: fontSize.xxs, textTransform: 'uppercase', color: color.textSecondary, marginBottom: spacing.sm }}>
        {'\u2022'} TOP VICTIMS ({victims.length} corps)
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: spacing.xs }}>
        {victims.slice(0, 30).map((victim) => (
          <a
            key={victim.corporation_id}
            href={`/corporation/${victim.corporation_id}?tab=overview`}
            style={{ background: 'rgba(0,0,0,0.2)', padding: '0.3rem 0.5rem', borderRadius: '4px', fontSize: fontSize.xxs, borderLeft: '2px solid #64748b', textDecoration: 'none', color: 'inherit', display: 'flex', alignItems: 'center', gap: spacing.base }}
          >
            <img
              src={`https://images.evetech.net/corporations/${victim.corporation_id}/logo?size=32`}
              alt=""
              style={{ width: '18px', height: '18px', borderRadius: '2px' }}
              onError={(e) => { e.currentTarget.style.display = 'none'; }}
            />
            <div style={{ flex: 1, fontWeight: 600, color: '#c9d1d9', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {victim.corporation_name || 'Unknown'}
            </div>
            <div style={{ fontSize: fontSize.xxs, color: color.killGreen, fontFamily: 'monospace', whiteSpace: 'nowrap' }}>
              {victim.kills_on_them}
            </div>
            <div style={{ fontSize: fontSize.xxs, color: color.warningOrange, fontFamily: 'monospace', whiteSpace: 'nowrap' }}>
              {(Number(victim.isk_destroyed) / 1e9).toFixed(1)}B
            </div>
          </a>
        ))}
      </div>
    </div>
  );
}

// ============================================================================
// Phase 5 Offensive Intelligence Panels
// ============================================================================

function DamageDealtPanel({ profile }: { profile: OffensiveData['damage_dealt'] }) {
  const DAMAGE_COLORS: Record<string, string> = {
    EM: '#58a6ff',
    Thermal: '#f85149',
    Kinetic: '#8b949e',
    Explosive: '#d29922',
    Mixed: '#a855f7'
  };

  if (!profile || profile.length === 0) {
    return (
      <div style={{ background: 'rgba(0,0,0,0.3)', borderRadius: '8px', padding: spacing.base, borderLeft: '2px solid #0ea5e9' }}>
        <div style={{ fontSize: fontSize.xxs, textTransform: 'uppercase', color: color.textSecondary, marginBottom: spacing.sm }}>
          {'\u2022'} DAMAGE DEALT PROFILE
        </div>
        <div style={{ fontSize: fontSize.tiny, color: '#666', textAlign: 'center', padding: spacing.xl }}>No data</div>
      </div>
    );
  }

  return (
    <div style={{ background: 'rgba(0,0,0,0.3)', borderRadius: '8px', padding: spacing.base, borderLeft: '2px solid #0ea5e9' }}>
      <div style={{ fontSize: fontSize.xxs, textTransform: 'uppercase', color: color.textSecondary, marginBottom: spacing.sm }}>
        {'\u2022'} DAMAGE DEALT PROFILE
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: spacing.xs }}>
        {profile.map((d) => (
          <div key={d.damage_type}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.1rem', fontSize: fontSize.xxs }}>
              <span style={{ color: '#c9d1d9' }}>{d.damage_type}</span>
              <span style={{ fontFamily: 'monospace', color: DAMAGE_COLORS[d.damage_type] }}>
                {d.percentage.toFixed(1)}%
              </span>
            </div>
            <div style={{ background: 'rgba(255,255,255,0.05)', borderRadius: '2px', height: '8px' }}>
              <div style={{
                background: DAMAGE_COLORS[d.damage_type],
                height: '100%',
                width: `${d.percentage}%`,
                borderRadius: '2px'
              }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function EWarUsagePanel({ usage }: { usage: OffensiveData['ewar_usage'] }) {
  const getEWarIcon = (type: string) => {
    if (type.includes('Bubble') || type.includes('Field')) return '\uD83D\uDD2E';
    if (type.includes('Neut')) return '\u26A1';
    if (type.includes('ECM')) return '\uD83D\uDCFB';
    if (type.includes('Damp')) return '\uD83D\uDCC9';
    if (type.includes('Web')) return '\uD83D\uDD78\uFE0F';
    if (type.includes('Scram')) return '\uD83D\uDD12';
    if (type.includes('Disruptor')) return '\uD83D\uDCCD';
    return '\uD83D\uDD27';
  };

  if (!usage || usage.length === 0) {
    return (
      <div style={{ background: 'rgba(0,0,0,0.3)', borderRadius: '8px', padding: spacing.base, borderLeft: '2px solid #a855f7', maxHeight: '280px', overflowY: 'auto' }}>
        <div style={{ fontSize: fontSize.xxs, textTransform: 'uppercase', color: color.textSecondary, marginBottom: spacing.sm }}>
          {'\u2022'} E-WAR USAGE (0)
        </div>
        <div style={{ fontSize: fontSize.tiny, color: '#666', textAlign: 'center', padding: spacing.xl }}>No data</div>
      </div>
    );
  }

  return (
    <div style={{ background: 'rgba(0,0,0,0.3)', borderRadius: '8px', padding: spacing.base, borderLeft: '2px solid #a855f7', maxHeight: '280px', overflowY: 'auto' }}>
      <div style={{ fontSize: fontSize.xxs, textTransform: 'uppercase', color: color.textSecondary, marginBottom: spacing.sm }}>
        {'\u2022'} E-WAR USAGE ({usage.length})
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: spacing.xs }}>
        {usage.map((e, i) => (
          <div key={i} style={{
            display: 'flex',
            alignItems: 'center',
            gap: spacing.md,
            padding: '0.3rem 0.4rem',
            background: i < 3 ? 'rgba(168,85,247,0.1)' : 'transparent',
            borderRadius: '3px'
          }}>
            <span style={{ fontSize: fontSize.sm }}>{getEWarIcon(e.ewar_type)}</span>
            <span style={{ fontSize: fontSize.tiny, color: '#fff', flex: 1 }}>{e.ewar_type}</span>
            <span style={{ fontSize: fontSize.tiny, fontWeight: 600, color: color.accentPurple, fontFamily: 'monospace' }}>
              {e.count}x
            </span>
            <span style={{ fontSize: fontSize.nano, color: 'rgba(255,255,255,0.4)' }}>
              {e.percentage.toFixed(0)}%
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function HotSystemsPanel({ systems }: { systems: OffensiveData['hot_systems'] }) {
  if (!systems || systems.length === 0) {
    return (
      <div style={{
        background: 'rgba(0,0,0,0.3)',
        borderRadius: '8px',
        padding: spacing.base,
        borderLeft: '2px solid #14b8a6',
        gridColumn: '1 / -1'
      }}>
        <div style={{ fontSize: fontSize.xxs, textTransform: 'uppercase', color: color.textSecondary, marginBottom: spacing.sm }}>
          {'\u2022'} HOT SYSTEMS - KILL ZONES (0)
        </div>
        <div style={{ fontSize: fontSize.tiny, color: '#666', textAlign: 'center', padding: spacing.xl }}>No hot systems</div>
      </div>
    );
  }

  return (
    <div style={{
      background: 'rgba(0,0,0,0.3)',
      borderRadius: '8px',
      padding: spacing.base,
      borderLeft: '2px solid #14b8a6',
      gridColumn: '1 / -1'
    }}>
      <div style={{ fontSize: fontSize.xxs, textTransform: 'uppercase', color: color.textSecondary, marginBottom: spacing.sm }}>
        {'\u2022'} HOT SYSTEMS - KILL ZONES ({systems.length})
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: spacing.xs, maxHeight: '350px', overflowY: 'auto' }}>
        {systems.map((sys) => {
          const scoreColor = sys.kill_score > 80 ? '#22c55e'
            : sys.kill_score > 60 ? '#84cc16'
            : '#ffcc00';

          return (
            <a
              key={sys.system_id}
              href={`/system/${sys.system_id}`}
              style={{
                background: sys.is_gatecamp ? 'rgba(34,197,94,0.08)' : 'rgba(0,0,0,0.2)',
                padding: '0.3rem 0.4rem',
                borderRadius: '4px',
                borderLeft: `3px solid ${scoreColor}`,
                textDecoration: 'none',
                color: 'inherit',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: spacing.base
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: spacing.md, flex: 1, minWidth: 0 }}>
                <span style={{ fontSize: fontSize.xxs, fontWeight: 700, color: '#c9d1d9', whiteSpace: 'nowrap' }}>
                  {sys.is_gatecamp && '\uD83D\uDEA8'}
                  {sys.system_name}
                </span>
                <span style={{ fontSize: fontSize.nano, color: color.textSecondary, whiteSpace: 'nowrap' }}>
                  {sys.region_name}
                </span>
                <span style={{
                  fontSize: fontSize.pico,
                  fontWeight: 700,
                  background: scoreColor,
                  color: '#000',
                  padding: '1px 4px',
                  borderRadius: '2px',
                  whiteSpace: 'nowrap'
                }}>
                  {sys.kill_score.toFixed(0)}%
                </span>
              </div>
              <div style={{ display: 'flex', gap: spacing.md, fontSize: fontSize.micro, color: color.textSecondary, whiteSpace: 'nowrap' }}>
                <span>{'\uD83C\uDFAF'} {sys.kills}</span>
                <span>{'\uD83D\uDC80'} {sys.deaths}</span>
                <span>{'\uD83D\uDCB0'} {(sys.avg_kill_value / 1e6).toFixed(0)}M</span>
              </div>
            </a>
          );
        })}
      </div>
    </div>
  );
}

function EffectiveDoctrinesPanel({ doctrines }: { doctrines: OffensiveData['effective_doctrines'] }) {
  if (!doctrines || doctrines.length === 0) {
    return (
      <div style={{
        background: 'rgba(0,0,0,0.3)',
        borderRadius: '8px',
        padding: spacing.base,
        borderLeft: '2px solid #84cc16',
        maxHeight: '280px',
        overflowY: 'auto'
      }}>
        <div style={{ fontSize: fontSize.xxs, textTransform: 'uppercase', color: color.textSecondary, marginBottom: spacing.sm }}>
          {'\u2022'} EFFECTIVE DOCTRINES (K/D {'\u2265'}2.0)
        </div>
        <div style={{ fontSize: fontSize.tiny, color: '#666', textAlign: 'center', padding: spacing.xl }}>No data</div>
      </div>
    );
  }

  return (
    <div style={{
      background: 'rgba(0,0,0,0.3)',
      borderRadius: '8px',
      padding: spacing.base,
      borderLeft: '2px solid #84cc16',
      maxHeight: '280px',
      overflowY: 'auto'
    }}>
      <div style={{ fontSize: fontSize.xxs, textTransform: 'uppercase', color: color.textSecondary, marginBottom: spacing.sm }}>
        {'\u2022'} EFFECTIVE DOCTRINES (K/D {'\u2265'}2.0)
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: spacing.xs }}>
        {doctrines.map((doc) => (
          <div key={doc.ship_class} style={{
            background: 'rgba(132,204,22,0.08)',
            padding: spacing.md,
            borderRadius: '4px',
            borderLeft: '2px solid #84cc16'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.2rem' }}>
              <span style={{ fontSize: fontSize.xxs, fontWeight: 600, color: '#c9d1d9' }}>{doc.ship_class}</span>
              <span style={{ fontSize: fontSize.tiny, fontWeight: 700, color: '#84cc16', fontFamily: 'monospace' }}>
                {doc.kd_ratio.toFixed(2)} K/D
              </span>
            </div>
            <div style={{ fontSize: fontSize.micro, color: color.textSecondary }}>
              {doc.kills}K / {doc.deaths}D {'\u2022'} {doc.isk_efficiency.toFixed(1)}% ISK eff
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function KillVelocityPanel({ velocity }: { velocity: OffensiveData['kill_velocity'] }) {
  if (!velocity || velocity.length === 0) {
    return (
      <div style={{
        background: 'rgba(0,0,0,0.3)',
        borderRadius: '8px',
        padding: spacing.base,
        borderLeft: '2px solid #06b6d4',
        maxHeight: '280px',
        overflowY: 'auto'
      }}>
        <div style={{ fontSize: fontSize.xxs, textTransform: 'uppercase', color: color.textSecondary, marginBottom: spacing.sm }}>
          {'\u2022'} KILL VELOCITY TRENDS
        </div>
        <div style={{ fontSize: fontSize.tiny, color: '#666', textAlign: 'center', padding: spacing.xl }}>No data</div>
      </div>
    );
  }

  return (
    <div style={{
      background: 'rgba(0,0,0,0.3)',
      borderRadius: '8px',
      padding: spacing.base,
      borderLeft: '2px solid #06b6d4',
      maxHeight: '280px',
      overflowY: 'auto'
    }}>
      <div style={{ fontSize: fontSize.xxs, textTransform: 'uppercase', color: color.textSecondary, marginBottom: spacing.sm }}>
        {'\u2022'} KILL VELOCITY TRENDS
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: spacing.xs }}>
        {velocity.map((v) => {
          const statusColor = v.status === 'ESCALATING' ? '#22c55e'
            : v.status === 'DECLINING' ? '#f85149'
            : '#ffcc00';
          const maxKills = Math.max(v.recent_kills, v.previous_kills, 1);

          return (
            <div key={v.ship_class} style={{
              padding: spacing.md,
              background: v.status === 'ESCALATING' ? 'rgba(34,197,94,0.08)' : 'transparent',
              borderRadius: '4px',
              borderLeft: `2px solid ${statusColor}`
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.2rem' }}>
                <span style={{ fontSize: fontSize.xxs, color: '#fff' }}>{v.ship_class}</span>
                <span style={{
                  fontSize: fontSize.pico,
                  fontWeight: 700,
                  background: statusColor,
                  color: '#000',
                  padding: '2px 5px',
                  borderRadius: '2px'
                }}>
                  {v.status}
                </span>
              </div>
              <div style={{ display: 'flex', gap: spacing.sm, marginBottom: '0.2rem' }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: fontSize.pico, color: color.textSecondary }}>Previous</div>
                  <div style={{
                    height: '4px',
                    background: 'rgba(255,255,255,0.2)',
                    width: `${(v.previous_kills / maxKills) * 100}%`,
                    borderRadius: '2px'
                  }} />
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: fontSize.pico, color: color.textSecondary }}>Recent</div>
                  <div style={{
                    height: '4px',
                    background: statusColor,
                    width: `${(v.recent_kills / maxKills) * 100}%`,
                    borderRadius: '2px'
                  }} />
                </div>
                <span style={{
                  fontSize: fontSize.micro,
                  fontWeight: 700,
                  color: statusColor,
                  fontFamily: 'monospace',
                  minWidth: '50px'
                }}>
                  {v.velocity_pct > 0 ? '+' : ''}{v.velocity_pct.toFixed(0)}%
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ============================================================================
// Victim Tank Profile Panel - Dogma-based analysis of enemy tank weaknesses
// (PowerBloc only)
// ============================================================================

function VictimTankPanel({ profile }: { profile: VictimTankProfile }) {
  const dmgTypeColors: Record<string, string> = {
    EM: '#58a6ff',
    THERMAL: '#ff8800',
    KINETIC: '#8b949e',
    EXPLOSIVE: '#f85149',
  };

  const weaknessColors: Record<string, string> = {
    EXPLOIT: '#f85149',
    SOFT: '#ffcc00',
    NORMAL: '#3fb950',
  };

  return (
    <div style={{
      gridColumn: '1 / -1',
      background: 'rgba(0,0,0,0.3)',
      borderRadius: '8px',
      padding: spacing.base,
      borderLeft: '2px solid #e879f9'
    }}>
      <div style={{ fontSize: fontSize.xxs, textTransform: 'uppercase', color: color.textSecondary, marginBottom: spacing.base }}>
        {'\u2022'} VICTIM TANK PROFILE ({profile.killmails_analyzed} fits analyzed)
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: spacing.lg }}>
        {/* Tank Type Distribution */}
        <div style={{ background: 'rgba(0,0,0,0.2)', padding: spacing.base, borderRadius: '6px' }}>
          <div style={{ fontSize: fontSize.tiny, color: color.textSecondary, marginBottom: spacing.md }}>TANK DISTRIBUTION</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: spacing.sm }}>
            {[
              { type: 'Shield', value: profile.tank_distribution.shield, color: color.linkBlue },
              { type: 'Armor', value: profile.tank_distribution.armor, color: color.warningOrange },
              { type: 'Hull', value: profile.tank_distribution.hull, color: color.textSecondary },
            ].map(({ type, value, color }) => (
              <div key={type}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: fontSize.xxs, marginBottom: '0.1rem' }}>
                  <span style={{ color: '#c9d1d9' }}>{type}</span>
                  <span style={{ color, fontFamily: 'monospace', fontWeight: 600 }}>{value}%</span>
                </div>
                <div style={{ height: '6px', background: 'rgba(255,255,255,0.05)', borderRadius: '3px', overflow: 'hidden' }}>
                  <div style={{ height: '100%', width: `${value}%`, background: color, transition: 'width 0.3s' }} />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Resist Weaknesses */}
        <div style={{ background: 'rgba(0,0,0,0.2)', padding: spacing.base, borderRadius: '6px' }}>
          <div style={{ fontSize: fontSize.tiny, color: color.textSecondary, marginBottom: spacing.md }}>RESIST WEAKNESSES</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: spacing.xs }}>
            {profile.resist_weaknesses.map((rw) => (
              <div key={rw.damage_type} style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '0.25rem 0.4rem',
                background: rw.weakness_level === 'EXPLOIT' ? 'rgba(248,81,73,0.15)' : 'transparent',
                borderRadius: '4px',
                borderLeft: `3px solid ${dmgTypeColors[rw.damage_type] || '#8b949e'}`
              }}>
                <span style={{ fontSize: fontSize.xxs, color: '#c9d1d9' }}>{rw.damage_type}</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: spacing.md }}>
                  <span style={{ fontSize: fontSize.xxs, fontFamily: 'monospace', color: color.textSecondary }}>
                    {rw.avg_resist.toFixed(0)}%
                  </span>
                  <span style={{
                    fontSize: fontSize.pico,
                    fontWeight: 700,
                    background: weaknessColors[rw.weakness_level],
                    color: '#000',
                    padding: '1px 4px',
                    borderRadius: '2px'
                  }}>
                    {rw.weakness_level}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Fleet Effectiveness */}
        <div style={{ background: 'rgba(0,0,0,0.2)', padding: spacing.base, borderRadius: '6px' }}>
          <div style={{ fontSize: fontSize.tiny, color: color.textSecondary, marginBottom: spacing.md }}>FLEET EFFECTIVENESS</div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: spacing.base }}>
            <div>
              <div style={{ fontSize: fontSize.nano, color: '#666' }}>Avg Victim EHP</div>
              <div style={{ fontSize: fontSize.lg, color: '#e879f9', fontFamily: 'monospace' }}>
                {(profile.fleet_effectiveness.avg_victim_ehp / 1000).toFixed(1)}k
              </div>
            </div>
            <div>
              <div style={{ fontSize: fontSize.nano, color: '#666' }}>Est. Fleet DPS</div>
              <div style={{ fontSize: fontSize.lg, color: color.lossRed, fontFamily: 'monospace' }}>
                {(profile.fleet_effectiveness.estimated_fleet_dps / 1000).toFixed(1)}k
              </div>
            </div>
            <div>
              <div style={{ fontSize: fontSize.nano, color: '#666' }}>Avg TTK</div>
              <div style={{ fontSize: fontSize.lg, color: color.warningYellow, fontFamily: 'monospace' }}>
                {profile.fleet_effectiveness.avg_time_to_kill_seconds.toFixed(1)}s
              </div>
            </div>
            <div>
              <div style={{ fontSize: fontSize.nano, color: '#666' }}>Overkill</div>
              <div style={{ fontSize: fontSize.lg, color: color.killGreen, fontFamily: 'monospace' }}>
                {profile.fleet_effectiveness.overkill_ratio.toFixed(1)}x
              </div>
            </div>
          </div>
        </div>

        {/* Top Ship Classes */}
        <div style={{ background: 'rgba(0,0,0,0.2)', padding: spacing.base, borderRadius: '6px' }}>
          <div style={{ fontSize: fontSize.tiny, color: color.textSecondary, marginBottom: spacing.md }}>TOP VICTIM CLASSES</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem', maxHeight: '120px', overflowY: 'auto' }}>
            {profile.top_ship_classes.slice(0, 6).map((sc) => (
              <div key={sc.ship_class} style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '0.2rem 0.3rem',
                fontSize: fontSize.tiny,
                background: 'rgba(255,255,255,0.03)',
                borderRadius: '3px'
              }}>
                <span style={{ color: '#c9d1d9' }}>{sc.ship_class}</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: spacing.sm }}>
                  <span style={{ fontFamily: 'monospace', color: color.textSecondary }}>{sc.count}</span>
                  <div style={{ display: 'flex', gap: spacing['2xs'] }}>
                    {sc.shield_pct > 0 && (
                      <span style={{ fontSize: fontSize.pico, color: color.linkBlue }}>{'\uD83D\uDEE1'}{sc.shield_pct.toFixed(0)}%</span>
                    )}
                    {sc.armor_pct > 0 && (
                      <span style={{ fontSize: fontSize.pico, color: color.warningOrange }}>{'\u2699'}{sc.armor_pct.toFixed(0)}%</span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
