/**
 * Shared Defensive Tab - Vulnerability Intelligence Dashboard
 *
 * Unified component for Alliance, Corporation, and PowerBloc entities.
 * Comprehensive 11-panel loss analysis and defensive assessment:
 * - Death Timeline (30-day activity with safe/danger hours)
 * - Defensive Performance (K/D, efficiency, capital losses)
 * - Danger Systems (avoid zones)
 * - Damage Taken Profile
 * - E-War Threats
 * - Threat Profile (engagement sizes)
 * - Death-Prone Pilots
 * - Ship & Doctrine Analysis
 * - Geographic Intelligence (heatmap + regions)
 * - Top Threats (corps/alliances)
 */

import { useState, useEffect } from 'react';
import type { EntityViewProps, FetcherMap } from './types';
import * as allianceApi from '../../services/allianceApi';
import { corpApi } from '../../services/corporationApi';
import { powerblocApi } from '../../services/api/powerbloc';

import { fontSize, color, spacing } from '../../styles/theme';
import { ThreatPanel, CapitalRadarPanel, LogiScorePanel } from './ThreatIntelPanels';

// ============================================================================
// Unified Data Interface (superset of all 3 entity types)
// ============================================================================

interface DefensiveData {
  summary: {
    total_deaths: number;
    isk_lost: string | number;
    avg_loss_value: string | number;
    max_loss_value: number;
    total_kills: number;
    efficiency: number;
    kd_ratio: number;
    solo_death_pct: number;
    capital_losses: number;
  };
  threat_profile: {
    solo_ganked: { deaths: number; percentage: number };
    small: { deaths: number; percentage: number };
    medium: { deaths: number; percentage: number };
    large: { deaths: number; percentage: number };
    blob: { deaths: number; percentage: number };
  };
  death_prone_pilots: Array<{
    character_id: number;
    character_name: string | null;
    deaths: number;
    kills: number;
    death_pct: number;
    avg_loss_value: number;
    last_ship_lost: string | null;
  }>;
  ship_losses: Array<{
    ship_class: string;
    count: number;
    percentage: number;
  }>;
  doctrine_weakness: Array<{
    ship_name: string;
    count: number;
    percentage: number;
  }>;
  loss_analysis: {
    total_deaths: number;
    pvp_deaths: number;
    pve_deaths: number;
    solo_deaths: number;
    avg_attacker_count: number;
    avg_death_value: number;
    capital_losses: number;
  };
  death_heatmap: Array<{
    system_id: number;
    system_name: string;
    region_name: string;
    deaths: number;
    deaths_per_day: number;
    is_camp: boolean;
  }>;
  loss_regions: Array<{
    region_id: number;
    region_name: string;
    deaths: number;
    percentage: number;
    unique_systems: number;
  }>;
  death_timeline: Array<{
    day: string;
    deaths: number;
    active_pilots: number;
  }>;
  capital_losses?: {
    capital_losses: number;
    capital_loss_pct: number;
    carrier_losses: number;
    dread_losses: number;
    fax_losses: number;
    super_titan_losses: number;
    avg_capital_loss_value: number;
  } | null;
  top_threats: Array<{
    corporation_id: number;
    corporation_name: string | null;
    kills_by_them: number;
    isk_destroyed_by_them: string | number;
    last_kill_time: string | null;
  }>;
  safe_danger_hours: {
    safe_start: number;
    safe_end: number;
    danger_start: number;
    danger_end: number;
  };
  damage_taken?: Array<{
    damage_type: string;
    percentage: number;
  }>;
  ewar_threats?: Array<{
    ewar_type: string;
    count: number;
    percentage: number;
  }>;
  danger_systems?: Array<{
    system_id: number;
    system_name: string;
    region_name: string;
    deaths: number;
    deaths_per_day: number;
    kills: number;
    danger_score: number;
    is_gatecamp: boolean;
  }>;
}

// ============================================================================
// Fetcher Map
// ============================================================================

const defensiveFetchers: FetcherMap<DefensiveData> = {
  alliance: (entityId, days) =>
    allianceApi.getDefensiveStats(entityId, days) as Promise<DefensiveData>,
  corporation: (entityId, days) =>
    corpApi.getDefensiveStats(entityId, days) as Promise<DefensiveData>,
  powerbloc: (entityId, days) =>
    powerblocApi.getDefensive(entityId, days) as Promise<DefensiveData>,
};

// ============================================================================
// Main Component
// ============================================================================

export function DefensiveView({ entityType, entityId, days }: EntityViewProps) {
  const [data, setData] = useState<DefensiveData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    defensiveFetchers[entityType](entityId, days)
      .then(setData)
      .catch((err: Error) => {
        console.error('Failed to load defensive stats:', err);
        setError(err.message);
      })
      .finally(() => setLoading(false));
  }, [entityType, entityId, days]);

  if (loading) {
    return (
      <div style={{ padding: spacing["3xl"], textAlign: 'center', color: color.textSecondary }}>
        Loading defensive intelligence...
      </div>
    );
  }

  if (error || !data) {
    return (
      <div style={{ padding: spacing["3xl"], textAlign: 'center', color: color.lossRed }}>
        Failed to load defensive stats: {error || 'Unknown error'}
      </div>
    );
  }

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: spacing.base }}>
      {/* Row 1: Death Timeline with Safe/Danger Hours (Full Width) */}
      <div style={{ gridColumn: '1 / -1' }}>
        <DeathTimelinePanel timeline={data.death_timeline} safeDangerHours={data.safe_danger_hours} />
      </div>

      {/* Row 2: Defensive Performance (full-width) */}
      <div style={{ gridColumn: '1 / -1' }}>
        <LossSummaryPanel summary={data.summary} analysis={data.loss_analysis} capitalLosses={data.capital_losses} />
      </div>

      {/* Row 3: Danger Systems (Full Width) */}
      <div style={{ gridColumn: '1 / -1' }}>
        <DangerSystemsPanel systems={data.danger_systems || []} />
      </div>

      {/* Row 4: Damage Taken | E-War Threats | Threat Profile */}
      <DamageTakenPanel profile={data.damage_taken || []} />
      <EWarThreatsPanel threats={data.ewar_threats || []} />
      <ThreatProfilePanel profile={data.threat_profile} />

      {/* Row 5: Death-Prone Pilots | Ship Losses | Doctrine Weakness */}
      <DeathPronePilotsPanel pilots={data.death_prone_pilots} />
      <ShipDoctrinePanel losses={data.ship_losses} doctrine={data.doctrine_weakness} />
      <GeographicPanel heatmap={data.death_heatmap} regions={data.loss_regions} />

      {/* Row 6: Top Threats (Full Width) */}
      <div style={{ gridColumn: '1 / -1' }}>
        <TopThreatsPanel threats={data.top_threats} />
      </div>

      {/* Row 7: Killmail Intelligence — Threat Composition | Capital Radar | Logi Scores */}
      <ThreatPanel entityType={entityType} entityId={entityId} days={days} />
      <CapitalRadarPanel entityType={entityType} entityId={entityId} days={days} />
      <LogiScorePanel entityType={entityType} entityId={entityId} days={days} />
    </div>
  );
}

// ============================================================================
// Panel 1: Loss Summary (Enhanced with Capital Details)
// ============================================================================

function LossSummaryPanel({
  summary,
  analysis,
  capitalLosses
}: {
  summary: DefensiveData['summary'];
  analysis: DefensiveData['loss_analysis'];
  capitalLosses?: DefensiveData['capital_losses'];
}) {
  const kdColor = getKDColor(summary.kd_ratio);
  const effColor = getEfficiencyColor(summary.efficiency);
  const pvpPct = analysis.total_deaths > 0 ? (100 * analysis.pvp_deaths / analysis.total_deaths) : 0;
  const pvePct = analysis.total_deaths > 0 ? (100 * analysis.pve_deaths / analysis.total_deaths) : 0;

  return (
    <div style={{ background: 'rgba(0,0,0,0.3)', borderRadius: '8px', padding: spacing.base, borderLeft: '2px solid #f85149' }}>
      <div style={{ fontSize: fontSize.xxs, textTransform: 'uppercase', color: color.textSecondary, marginBottom: spacing.md }}>
        • DEFENSIVE PERFORMANCE
      </div>
      <div style={{ display: 'flex', gap: spacing.sm, fontSize: fontSize.xs }}>
        <div style={{ flex: 1, minWidth: '70px' }}>
          <div style={{ color: color.textSecondary, fontSize: fontSize.micro }}>ISK Lost</div>
          <div style={{ fontSize: fontSize.lg, color: color.warningOrange, fontFamily: 'monospace' }}>
            {(Number(summary.isk_lost) / 1e12).toFixed(1)}T
          </div>
        </div>
        <div style={{ flex: 1, minWidth: '70px' }}>
          <div style={{ color: color.textSecondary, fontSize: fontSize.micro }}>Efficiency</div>
          <div style={{ fontSize: fontSize.lg, color: effColor, fontFamily: 'monospace' }}>
            {summary.efficiency.toFixed(1)}%
          </div>
        </div>
        <div style={{ flex: 1, minWidth: '60px' }}>
          <div style={{ color: color.textSecondary, fontSize: fontSize.micro }}>K/D</div>
          <div style={{ fontSize: fontSize.lg, color: kdColor, fontFamily: 'monospace' }}>
            {summary.kd_ratio.toFixed(2)}
          </div>
        </div>
        <div style={{ flex: 1, minWidth: '80px' }}>
          <div style={{ color: color.textSecondary, fontSize: fontSize.micro }}>PvP Deaths</div>
          <div style={{ fontSize: fontSize.base, color: color.dangerRed, fontFamily: 'monospace' }}>
            {analysis.pvp_deaths} ({pvpPct.toFixed(0)}%)
          </div>
        </div>
        <div style={{ flex: 1, minWidth: '80px' }}>
          <div style={{ color: color.textSecondary, fontSize: fontSize.micro }}>PvE Deaths</div>
          <div style={{ fontSize: fontSize.base, color: color.warningOrange, fontFamily: 'monospace' }}>
            {analysis.pve_deaths} ({pvePct.toFixed(0)}%)
          </div>
        </div>
        <div style={{ flex: 1, minWidth: '60px' }}>
          <div style={{ color: color.textSecondary, fontSize: fontSize.micro }}>Solo %</div>
          <div style={{ fontSize: fontSize.lg, color: color.brightOrange, fontFamily: 'monospace' }}>
            {summary.solo_death_pct.toFixed(1)}%
          </div>
        </div>
        <div style={{ flex: 1, minWidth: '70px' }}>
          <div style={{ color: color.textSecondary, fontSize: fontSize.micro }}>Avg Atk</div>
          <div style={{ fontSize: fontSize.lg, color: '#c9d1d9', fontFamily: 'monospace' }}>
            {analysis.avg_attacker_count.toFixed(1)}
          </div>
        </div>
        <div style={{ flex: 1, minWidth: '70px' }}>
          <div style={{ color: color.textSecondary, fontSize: fontSize.micro }}>Avg Value</div>
          <div style={{ fontSize: fontSize.lg, color: '#c9d1d9', fontFamily: 'monospace' }}>
            {(analysis.avg_death_value / 1e6).toFixed(0)}M
          </div>
        </div>
        <div style={{ flex: 1, minWidth: '70px' }}>
          <div style={{ color: color.textSecondary, fontSize: fontSize.micro }}>Capitals</div>
          <div style={{ fontSize: fontSize.lg, color: summary.capital_losses > 0 ? '#ff0000' : '#666', fontFamily: 'monospace' }}>
            {summary.capital_losses}
          </div>
        </div>
        {capitalLosses && (
          <div style={{ flex: 1, minWidth: '110px' }}>
            <div style={{ color: color.textSecondary, fontSize: fontSize.micro }}>Car/Dread/FAX/Super</div>
            <div style={{ fontSize: fontSize.base, color: '#c9d1d9', fontFamily: 'monospace' }}>
              {capitalLosses.carrier_losses}/{capitalLosses.dread_losses}/{capitalLosses.fax_losses}/{capitalLosses.super_titan_losses}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ============================================================================
// Panel 2: Damage Taken Profile
// ============================================================================

function DamageTakenPanel({ profile }: { profile: NonNullable<DefensiveData['damage_taken']> }) {
  const DAMAGE_COLORS: Record<string, string> = {
    EM: '#58a6ff',
    Thermal: '#f85149',
    Kinetic: '#8b949e',
    Explosive: '#d29922',
    Mixed: '#a855f7'
  };

  return (
    <div style={{ background: 'rgba(0,0,0,0.3)', borderRadius: '8px', padding: spacing.base, borderLeft: '2px solid #ff8800' }}>
      <div style={{ fontSize: fontSize.xxs, textTransform: 'uppercase', color: color.textSecondary, marginBottom: spacing.sm }}>
        • DAMAGE TAKEN PROFILE
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: spacing.sm }}>
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

// ============================================================================
// Panel 3: E-War Threats
// ============================================================================

function EWarThreatsPanel({ threats }: { threats: NonNullable<DefensiveData['ewar_threats']> }) {
  const getEWarIcon = (type: string) => {
    if (type.includes('Bubble') || type.includes('Field')) return '🔮';
    if (type.includes('Neut')) return '⚡';
    if (type.includes('ECM')) return '📻';
    if (type.includes('Damp')) return '📉';
    if (type.includes('Web')) return '🕸️';
    if (type.includes('Scram')) return '🔒';
    if (type.includes('Disruptor')) return '📍';
    return '🔧';
  };

  return (
    <div style={{ background: 'rgba(0,0,0,0.3)', borderRadius: '8px', padding: spacing.base, borderLeft: '2px solid #a855f7', maxHeight: '280px', overflowY: 'auto' }}>
      <div style={{ fontSize: fontSize.xxs, textTransform: 'uppercase', color: color.textSecondary, marginBottom: spacing.sm }}>
        • E-WAR THREATS ({threats.length})
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: spacing.xs }}>
        {threats.map((e, i) => (
          <div key={i} style={{
            display: 'flex',
            alignItems: 'center',
            gap: spacing.sm,
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

// ============================================================================
// Panel 4: Danger Systems
// ============================================================================

function DangerSystemsPanel({ systems }: { systems: NonNullable<DefensiveData['danger_systems']> }) {
  return (
    <div style={{
      background: 'rgba(0,0,0,0.3)',
      borderRadius: '8px',
      padding: spacing.base,
      borderLeft: '2px solid #dc2626',
      gridColumn: '1 / -1'
    }}>
      <div style={{ fontSize: fontSize.xxs, textTransform: 'uppercase', color: color.textSecondary, marginBottom: spacing.sm }}>
        • DANGER SYSTEMS - AVOID ZONES ({systems.length})
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: spacing.xs, maxHeight: '350px', overflowY: 'auto' }}>
        {systems.map((sys) => {
          const scoreColor = sys.danger_score > 80 ? '#ff0000'
            : sys.danger_score > 60 ? '#ff4444'
            : '#ff8800';

          return (
            <a
              key={sys.system_id}
              href={`/system/${sys.system_id}`}
              style={{
                background: sys.is_gatecamp ? 'rgba(255,0,0,0.1)' : 'rgba(0,0,0,0.2)',
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
                  {sys.is_gatecamp && '🚨'}
                  {sys.system_name}
                </span>
                <span style={{ fontSize: fontSize.nano, color: color.textSecondary, whiteSpace: 'nowrap' }}>
                  {sys.region_name}
                </span>
                <span style={{
                  fontSize: fontSize.pico,
                  fontWeight: 700,
                  background: scoreColor,
                  color: '#fff',
                  padding: '1px 4px',
                  borderRadius: '2px',
                  whiteSpace: 'nowrap'
                }}>
                  {sys.danger_score.toFixed(0)}%
                </span>
              </div>
              <div style={{ display: 'flex', gap: spacing.md, fontSize: fontSize.micro, color: color.textSecondary, whiteSpace: 'nowrap' }}>
                <span>💀 {sys.deaths}</span>
                <span>📊 {sys.deaths_per_day.toFixed(1)}/d</span>
                {sys.kills > 0 && <span>🎯 {sys.kills}</span>}
              </div>
            </a>
          );
        })}
      </div>
    </div>
  );
}

// ============================================================================
// Panel 5: Threat Profile
// ============================================================================

function ThreatProfilePanel({ profile }: { profile: DefensiveData['threat_profile'] }) {
  const engagements = [
    { label: 'Solo Ganked (\u22643)', key: 'solo_ganked' as const, color: color.pureRed },
    { label: 'Small (4-10)', key: 'small' as const, color: color.dangerRed },
    { label: 'Medium (11-30)', key: 'medium' as const, color: color.brightOrange },
    { label: 'Large (31-100)', key: 'large' as const, color: color.warningOrange },
    { label: 'Blob (>100)', key: 'blob' as const, color: '#cc0000' },
  ];

  return (
    <div style={{ background: 'rgba(0,0,0,0.3)', borderRadius: '8px', padding: spacing.base, borderLeft: '2px solid #ff0000' }}>
      <div style={{ fontSize: fontSize.xxs, textTransform: 'uppercase', color: color.textSecondary, marginBottom: spacing.sm }}>
        • THREAT PROFILE
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: spacing.sm, fontSize: fontSize.xxs }}>
        {engagements.map((eng) => {
          const data = profile[eng.key];
          return (
            <div key={eng.key}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.1rem', color: '#c9d1d9' }}>
                <span>{eng.label}</span>
                <span style={{ fontFamily: 'monospace' }}>{data.deaths} ({data.percentage.toFixed(1)}%)</span>
              </div>
              <div style={{ background: 'rgba(255,255,255,0.05)', borderRadius: '2px', height: '8px', overflow: 'hidden' }}>
                <div style={{ background: eng.color, height: '100%', width: `${data.percentage}%`, transition: 'width 0.3s' }} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ============================================================================
// Panel 6: Death-Prone Pilots
// ============================================================================

function DeathPronePilotsPanel({ pilots }: { pilots: DefensiveData['death_prone_pilots'] }) {
  return (
    <div style={{ background: 'rgba(0,0,0,0.3)', borderRadius: '8px', padding: spacing.base, borderLeft: '2px solid #dc2626', maxHeight: '280px', display: 'flex', flexDirection: 'column' }}>
      <div style={{ fontSize: fontSize.xxs, textTransform: 'uppercase', color: color.textSecondary, marginBottom: spacing.sm, flexShrink: 0 }}>
        • DEATH-PRONE PILOTS ({pilots.length})
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: spacing.sm, flex: 1, overflowY: 'auto' }}>
        {pilots.map((pilot) => (
          <a
            key={pilot.character_id}
            href={`https://zkillboard.com/character/${pilot.character_id}/`}
            target="_blank"
            rel="noopener noreferrer"
            style={{ background: 'rgba(0,0,0,0.2)', padding: '0.25rem 0.4rem', borderRadius: '4px', fontSize: fontSize.xxs, borderLeft: '2px solid #dc2626', textDecoration: 'none', color: 'inherit' }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: spacing.sm }}>
              <img
                src={`https://images.evetech.net/characters/${pilot.character_id}/portrait?size=32`}
                alt=""
                style={{ width: '20px', height: '20px', borderRadius: '2px' }}
              />
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 600, color: '#c9d1d9' }}>{pilot.character_name || 'Unknown'}</div>
                <div style={{ fontSize: fontSize.tiny, color: color.textSecondary, marginTop: '0.1rem' }}>
                  {pilot.deaths} deaths • {pilot.death_pct.toFixed(1)}% death rate • {pilot.last_ship_lost || 'Unknown ship'}
                </div>
              </div>
              <div style={{ fontSize: fontSize.lg, color: pilot.death_pct > 50 ? '#ff0000' : pilot.death_pct > 20 ? '#ff8800' : '#ffcc00' }}>
                {pilot.death_pct > 50 ? '🔴' : pilot.death_pct > 20 ? '🟠' : '🟡'}
              </div>
            </div>
          </a>
        ))}
      </div>
    </div>
  );
}

// ============================================================================
// Panel 7: Ship & Doctrine Analysis (Tabbed)
// ============================================================================

function ShipDoctrinePanel({
  losses,
  doctrine
}: {
  losses: DefensiveData['ship_losses'];
  doctrine: DefensiveData['doctrine_weakness'];
}) {
  const [tab, setTab] = useState<'ships' | 'doctrine'>('ships');

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
          Ship Classes
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
          Doctrine Weakness
        </button>
      </div>

      {tab === 'ships' ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: spacing.sm, fontSize: fontSize.xxs, flex: 1, overflowY: 'auto' }}>
          {losses.map((loss) => (
            <div key={loss.ship_class}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.1rem', color: '#c9d1d9' }}>
                <span>{loss.ship_class}</span>
                <span style={{ fontFamily: 'monospace' }}>{loss.count} ({loss.percentage.toFixed(1)}%)</span>
              </div>
              <div style={{ background: 'rgba(255,255,255,0.05)', borderRadius: '2px', height: '8px', overflow: 'hidden' }}>
                <div style={{ background: getShipLossColor(loss.ship_class), height: '100%', width: `${loss.percentage}%`, transition: 'width 0.3s' }} />
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: spacing.sm, fontSize: fontSize.xxs, flex: 1, overflowY: 'auto' }}>
          {doctrine.map((ship) => (
            <div key={ship.ship_name}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.1rem', color: '#c9d1d9' }}>
                <span>{ship.ship_name}</span>
                <span style={{ fontFamily: 'monospace' }}>{ship.count} ({ship.percentage.toFixed(1)}%)</span>
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

// ============================================================================
// Panel 8: Geographic Intelligence (Tabbed)
// ============================================================================

function GeographicPanel({
  heatmap,
  regions
}: {
  heatmap: DefensiveData['death_heatmap'];
  regions: DefensiveData['loss_regions'];
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
          Death Heatmap
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
          Loss Regions
        </button>
      </div>

      {tab === 'systems' ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: spacing.sm, flex: 1, overflowY: 'auto' }}>
          {heatmap.map((zone) => (
            <a
              key={zone.system_id}
              href={`/system/${zone.system_id}`}
              style={{ background: 'rgba(0,0,0,0.2)', padding: '0.25rem 0.4rem', borderRadius: '4px', fontSize: fontSize.xxs, borderLeft: `2px solid ${zone.is_camp ? '#ff0000' : '#00bcd4'}`, textDecoration: 'none', color: 'inherit' }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600, color: '#c9d1d9' }}>
                    {zone.is_camp && <span style={{ marginRight: spacing.sm }}>🚨</span>}
                    {zone.system_name}
                  </div>
                  <div style={{ fontSize: fontSize.tiny, color: color.textSecondary, marginTop: '0.1rem' }}>
                    {zone.region_name} • {zone.deaths_per_day.toFixed(2)}/day
                  </div>
                </div>
                <div style={{ fontSize: fontSize.lg, color: color.dangerRed, fontFamily: 'monospace' }}>
                  {zone.deaths}
                </div>
              </div>
            </a>
          ))}
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: spacing.sm, fontSize: fontSize.xxs, flex: 1, overflowY: 'auto' }}>
          {regions.map((region) => (
            <div key={region.region_id}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.1rem', color: '#c9d1d9' }}>
                <span>{region.region_name} ({region.unique_systems} sys)</span>
                <span style={{ fontFamily: 'monospace' }}>{region.deaths || 0} ({region.percentage.toFixed(1)}%)</span>
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

// ============================================================================
// Panel 9: Death Timeline (Full Width)
// ============================================================================

function DeathTimelinePanel({
  timeline,
  safeDangerHours
}: {
  timeline: DefensiveData['death_timeline'];
  safeDangerHours: DefensiveData['safe_danger_hours'];
}) {
  const deaths = timeline.map((t) => t.deaths || 0);
  const pilots = timeline.map((t) => t.active_pilots || 0);
  const trend = calculateTrend(timeline);
  const avgDeaths = deaths.length > 0 ? deaths.reduce((sum, d) => sum + d, 0) / deaths.length : 0;
  const last3 = deaths.slice(-3).reduce((sum, d) => sum + d, 0) / 3;
  const peakDeaths = Math.max(...deaths, 0);

  // Single Y-axis for BOTH metrics - round up to nearest 100
  const maxValue = Math.max(...deaths, ...pilots, 0);
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
  const deathPoints = deaths.map((d, i) => ({
    x: padding.left + (i / Math.max(deaths.length - 1, 1)) * dataWidth,
    y: padding.top + dataHeight - (d / Math.max(yAxisMax, 1)) * dataHeight
  }));

  const pilotPoints = pilots.map((p, i) => ({
    x: padding.left + (i / Math.max(pilots.length - 1, 1)) * dataWidth,
    y: padding.top + dataHeight - (p / Math.max(yAxisMax, 1)) * dataHeight
  }));

  const deathPathD = deathPoints.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');
  const pilotPathD = pilotPoints.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');

  // X-axis labels (smart sampling)
  const maxXLabels = 10;
  const step = Math.ceil(timeline.length / maxXLabels);
  const xLabelIndices = timeline.map((_, i) => i).filter((i, idx) => idx % step === 0 || i === timeline.length - 1);

  return (
    <div style={{ background: 'rgba(0,0,0,0.3)', borderRadius: '8px', padding: spacing.base, borderLeft: '2px solid #10b981', gridColumn: '1 / -1' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: spacing.sm }}>
        <div style={{ fontSize: fontSize.xxs, textTransform: 'uppercase', color: color.textSecondary }}>
          • DEATH TIMELINE ({timeline.length} days) {trend}
        </div>
        {/* Legend */}
        <div style={{ display: 'flex', gap: spacing.lg, fontSize: fontSize.micro, color: color.textSecondary }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: spacing.xs }}>
            <div style={{ width: '10px', height: '2px', background: color.dangerRed }} />
            <span>Deaths</span>
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
              <text key={i} x={deathPoints[i]?.x || 0} y={chartHeight - 8} textAnchor="middle" fontSize="9" fill="#6e7681" fontFamily="monospace">
                {label}
              </text>
            );
          })}

          {/* Death Line (red, left Y-axis) */}
          <path d={deathPathD} fill="none" stroke="#ff4444" strokeWidth="2.5" />

          {/* Pilot Line (blue, right Y-axis) */}
          <path d={pilotPathD} fill="none" stroke="#58a6ff" strokeWidth="2" opacity="0.8" />

          {/* Death data points */}
          {deathPoints.filter((_, i) => i % Math.max(1, Math.floor(deathPoints.length / 30)) === 0).map((p, i) => (
            <circle key={`death-${i}`} cx={p.x} cy={p.y} r="2.5" fill="#ff4444" />
          ))}

          {/* Pilot data points */}
          {pilotPoints.filter((_, i) => i % Math.max(1, Math.floor(pilotPoints.length / 30)) === 0).map((p, i) => (
            <circle key={`pilot-${i}`} cx={p.x} cy={p.y} r="2" fill="#58a6ff" />
          ))}
        </svg>
      </div>

      {/* Stats Grid with Safe/Danger Hours */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: spacing.sm, fontSize: fontSize.xs }}>
        <div>
          <div style={{ color: color.textSecondary, fontSize: fontSize.tiny }}>Avg Deaths/Day</div>
          <div style={{ fontSize: fontSize.h4, color: '#c9d1d9', fontFamily: 'monospace', fontWeight: 700 }}>
            {avgDeaths.toFixed(1)}
          </div>
        </div>
        <div>
          <div style={{ color: color.textSecondary, fontSize: fontSize.tiny }}>Last 3 Days</div>
          <div style={{ fontSize: fontSize.h4, color: trend === '\u2B06\uFE0F' ? '#ff0000' : trend === '\u2B07\uFE0F' ? '#3fb950' : '#ffcc00', fontFamily: 'monospace', fontWeight: 700 }}>
            {last3.toFixed(1)}
          </div>
        </div>
        <div>
          <div style={{ color: color.textSecondary, fontSize: fontSize.tiny }}>Peak Deaths</div>
          <div style={{ fontSize: fontSize.h4, color: color.dangerRed, fontFamily: 'monospace', fontWeight: 700 }}>
            {peakDeaths}
          </div>
        </div>
        <div>
          <div style={{ color: color.textSecondary, fontSize: fontSize.tiny }}>🟢 Safe Hours</div>
          <div style={{ fontSize: fontSize.lg, color: color.killGreen, fontFamily: 'monospace', fontWeight: 700 }}>
            {safeDangerHours.safe_start}:00-{safeDangerHours.safe_end}:00
          </div>
        </div>
        <div>
          <div style={{ color: color.textSecondary, fontSize: fontSize.tiny }}>🔴 Danger Hours</div>
          <div style={{ fontSize: fontSize.lg, color: color.dangerRed, fontFamily: 'monospace', fontWeight: 700 }}>
            {safeDangerHours.danger_start}:00-{safeDangerHours.danger_end}:00
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Panel 10: Top Threats (2-Column Grid)
// ============================================================================

function TopThreatsPanel({ threats }: { threats: DefensiveData['top_threats'] }) {
  return (
    <div style={{ background: 'rgba(0,0,0,0.3)', borderRadius: '8px', padding: spacing.base, borderLeft: '2px solid #64748b', gridColumn: '1 / -1', maxHeight: '400px', overflowY: 'auto' }}>
      <div style={{ fontSize: fontSize.xxs, textTransform: 'uppercase', color: color.textSecondary, marginBottom: spacing.sm }}>
        • TOP THREATS ({threats.length} corps/alliances)
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: spacing.sm }}>
        {threats.map((threat) => {
          const lastKill = threat.last_kill_time ? new Date(threat.last_kill_time) : null;
          const hoursAgo = lastKill ? Math.floor((Date.now() - lastKill.getTime()) / 3600000) : null;

          return (
            <a
              key={threat.corporation_id}
              href={`https://zkillboard.com/corporation/${threat.corporation_id}/`}
              target="_blank"
              rel="noopener noreferrer"
              style={{ background: 'rgba(0,0,0,0.2)', padding: '0.3rem 0.5rem', borderRadius: '4px', fontSize: fontSize.xxs, borderLeft: '2px solid #64748b', textDecoration: 'none', color: 'inherit', display: 'flex', alignItems: 'center', gap: spacing.sm }}
            >
              <img
                src={`https://images.evetech.net/corporations/${threat.corporation_id}/logo?size=32`}
                alt=""
                style={{ width: '18px', height: '18px', borderRadius: '2px' }}
                onError={(e) => { e.currentTarget.style.display = 'none'; }}
              />
              <div style={{ flex: 1, fontWeight: 600, color: '#c9d1d9', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {threat.corporation_name || 'Unknown'}
              </div>
              <div style={{ fontSize: fontSize.xxs, color: color.pureRed, fontFamily: 'monospace', whiteSpace: 'nowrap' }}>
                {threat.kills_by_them}
              </div>
              <div style={{ fontSize: fontSize.xxs, color: color.warningOrange, fontFamily: 'monospace', whiteSpace: 'nowrap' }}>
                {(Number(threat.isk_destroyed_by_them) / 1e9).toFixed(1)}B
              </div>
              {hoursAgo !== null && (
                <div style={{ fontSize: fontSize.tiny, color: hoursAgo < 24 ? '#ff0000' : hoursAgo < 168 ? '#ff8800' : '#8b949e', whiteSpace: 'nowrap' }}>
                  {hoursAgo < 1 ? 'now' : hoursAgo < 24 ? `${hoursAgo}h` : `${Math.floor(hoursAgo / 24)}d`}
                </div>
              )}
            </a>
          );
        })}
      </div>
    </div>
  );
}

// ============================================================================
// Utility Functions
// ============================================================================

function getKDColor(kd: number): string {
  if (kd >= 2.0) return '#3fb950';
  if (kd >= 1.0) return '#ffcc00';
  return '#f85149';
}

function getEfficiencyColor(eff: number): string {
  if (eff >= 70) return '#3fb950';
  if (eff >= 50) return '#ffcc00';
  return '#f85149';
}

function getShipLossColor(shipClass: string): string {
  const colors: Record<string, string> = {
    Frigate: '#ff8800',
    Destroyer: '#ff6600',
    Cruiser: '#ff4444',
    Battlecruiser: '#ff2222',
    Battleship: '#ff0000',
    Capital: '#cc0000',
    Capsule: '#666',
    Structure: '#992222',
    Industrial: '#aa4400',
    'Fighter/Drone': '#cc4400',
    Deployable: '#dd5500',
    Other: '#8b949e',
  };
  return colors[shipClass] || '#8b949e';
}

function calculateTrend(timeline: { day: string; deaths?: number }[]): string {
  if (timeline.length < 7) return '\u2192';
  const last3 = timeline.slice(-3).reduce((sum, d) => sum + (d.deaths || 0), 0) / 3;
  const prev4 = timeline.slice(-7, -3).reduce((sum, d) => sum + (d.deaths || 0), 0) / 4;
  const diff = ((last3 - prev4) / (prev4 || 1)) * 100;
  if (diff > 15) return '\u2B06\uFE0F'; // Deaths increasing = bad
  if (diff < -15) return '\u2B07\uFE0F'; // Deaths decreasing = good
  return '\u2192';
}
