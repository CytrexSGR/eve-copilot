import { useState } from 'react';
import { DIFFICULTY_COLORS, WORMHOLE_CLASS_COLORS } from '../../constants/wormhole';
import type { WormholeOpportunity, WHResident, ShipBreakdown, SystemEffect, PrimeTime, RecentKill, StructureIntel, HunterAlliance, ResidentAlliance } from '../../types/wormhole';

import { fontSize, color, spacing } from '../../styles/theme';

interface HuntersTabProps {
  opportunities: WormholeOpportunity[];
  selectedClass: number | null;
  onClassChange: (cls: number | null) => void;
  loading?: boolean;
}

function formatTimeAgo(timestamp: string | null): string {
  if (!timestamp) return 'Unknown';
  const diff = Date.now() - new Date(timestamp).getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

function formatISK(value: number): string {
  if (value >= 1e12) return `${(value / 1e12).toFixed(1)}T`;
  if (value >= 1e9) return `${(value / 1e9).toFixed(1)}B`;
  if (value >= 1e6) return `${(value / 1e6).toFixed(1)}M`;
  return value.toLocaleString();
}

function ScoreBar({ score, breakdown }: { score: number; breakdown?: { activity: number; recency: number; weakness: number } }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: spacing.base }}>
      <div
        style={{
          width: '80px',
          height: '8px',
          background: 'rgba(0,0,0,0.3)',
          borderRadius: '4px',
          overflow: 'hidden',
          display: 'flex',
        }}
        title={breakdown ? `Activity: ${breakdown.activity}/40 | Recency: ${breakdown.recency}/30 | Weakness: ${breakdown.weakness}/30` : undefined}
      >
        {breakdown ? (
          <>
            <div style={{ width: `${(breakdown.activity / 100) * 100}%`, height: '100%', background: color.accentCyan }} />
            <div style={{ width: `${(breakdown.recency / 100) * 100}%`, height: '100%', background: color.warningOrange }} />
            <div style={{ width: `${(breakdown.weakness / 100) * 100}%`, height: '100%', background: color.safeGreen }} />
          </>
        ) : (
          <div
            style={{
              width: `${score}%`,
              height: '100%',
              background: score >= 80 ? '#00ff88' : score >= 60 ? '#ffcc00' : score >= 40 ? '#ff8800' : '#ff4444',
              borderRadius: '4px',
            }}
          />
        )}
      </div>
      <span style={{ fontSize: fontSize.base, fontWeight: 600, color: '#fff', minWidth: '24px' }}>
        {score}
      </span>
    </div>
  );
}

function HotBadge() {
  return (
    <span
      style={{
        fontSize: fontSize.micro,
        fontWeight: 700,
        padding: '0.15rem 0.35rem',
        background: 'rgba(255,68,68,0.3)',
        color: color.dangerRed,
        borderRadius: '3px',
        animation: 'pulse 2s infinite',
        textTransform: 'uppercase',
      }}
    >
      🔥 HOT
    </span>
  );
}

function StaticsBadges({ statics, whClass }: { statics: { code: string; destination: string }[]; whClass?: number }) {
  if (!statics || statics.length === 0) {
    // Special systems have dynamic connections
    if (whClass === 14) {
      return <span style={{ fontSize: fontSize.xxs, color: color.safeGreen }}>Dynamic (many connections)</span>;
    }
    if (whClass === 13) {
      return <span style={{ fontSize: fontSize.xxs, color: color.warningYellow }}>Shattered (roaming)</span>;
    }
    if (whClass && whClass >= 15 && whClass <= 18) {
      return <span style={{ fontSize: fontSize.xxs, color: color.dangerRed }}>Drifter WH (dangerous)</span>;
    }
    return <span style={{ fontSize: fontSize.xxs, color: 'rgba(255,255,255,0.3)' }}>No statics</span>;
  }

  const destColors: Record<string, string> = {
    'Highsec': '#00ff88',
    'Lowsec': '#ffcc00',
    'Nullsec': '#ff4444',
    'C1': '#4a9eff',
    'C2': '#4a9eff',
    'C3': '#00d4ff',
    'C4': '#00d4ff',
    'C5': '#ff8800',
    'C6': '#ff4444',
  };

  return (
    <div style={{ display: 'flex', gap: spacing.xs, flexWrap: 'wrap' }}>
      {statics.map((s, i) => (
        <span
          key={i}
          style={{
            fontSize: fontSize.tiny,
            padding: '0.1rem 0.3rem',
            background: `${destColors[s.destination] || '#888'}22`,
            color: destColors[s.destination] || '#888',
            borderRadius: '3px',
          }}
          title={`${s.code} → ${s.destination}`}
        >
          {s.code}→{s.destination}
        </span>
      ))}
    </div>
  );
}

function ShipBreakdownDisplay({ ships }: { ships: ShipBreakdown }) {
  const categories = [
    { key: 'capital', label: 'Capitals', color: color.dangerRed, icon: '⚓' },
    { key: 'battleship', label: 'Battleships', color: color.warningOrange, icon: '🚀' },
    { key: 'cruiser', label: 'Cruisers', color: color.warningYellow, icon: '🛸' },
    { key: 'destroyer', label: 'Destroyers', color: color.accentCyan, icon: '⚡' },
    { key: 'frigate', label: 'Frigates', color: color.safeGreen, icon: '✈' },
  ] as const;

  const hasShips = categories.some(c => ships[c.key].length > 0);
  if (!hasShips && ships.other.length === 0) return null;

  return (
    <div style={{ marginTop: spacing.base }}>
      <div style={{ fontSize: fontSize.xxs, color: 'rgba(255,255,255,0.4)', marginBottom: '0.35rem', textTransform: 'uppercase' }}>
        Ship Activity (7d)
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: spacing.base }}>
        {categories.map(({ key, label, color, icon }) => {
          const shipList = ships[key];
          if (shipList.length === 0) return null;
          return (
            <div
              key={key}
              style={{
                background: `${color}11`,
                border: `1px solid ${color}33`,
                borderRadius: '4px',
                padding: '0.35rem 0.5rem',
              }}
            >
              <div style={{ fontSize: fontSize.tiny, color, fontWeight: 600 }}>
                {icon} {label} ({shipList.length})
              </div>
              <div style={{ fontSize: fontSize.xxs, color: 'rgba(255,255,255,0.6)', marginTop: '0.2rem' }}>
                {shipList.slice(0, 4).join(', ')}
                {shipList.length > 4 && <span style={{ color: 'rgba(255,255,255,0.3)' }}> +{shipList.length - 4}</span>}
              </div>
            </div>
          );
        })}
      </div>

      {/* Threat Ships Warning */}
      {ships.threats.length > 0 && (
        <div
          style={{
            marginTop: spacing.base,
            padding: '0.35rem 0.5rem',
            background: 'rgba(255,68,68,0.1)',
            border: '1px solid rgba(255,68,68,0.3)',
            borderRadius: '4px',
            fontSize: fontSize.xxs,
          }}
        >
          <span style={{ color: color.dangerRed, fontWeight: 600 }}>⚠ Threat Ships: </span>
          <span style={{ color: 'rgba(255,255,255,0.7)' }}>{ships.threats.join(', ')}</span>
        </div>
      )}
    </div>
  );
}

function ResidentsList({ residents }: { residents: WHResident[] }) {
  if (!residents || residents.length === 0) {
    return (
      <div style={{ fontSize: fontSize.xs, color: 'rgba(255,255,255,0.4)', padding: '0.5rem 0' }}>
        No known residents
      </div>
    );
  }

  // Separate NPC and player corps
  const playerCorps = residents.filter(r => !r.is_npc);
  const npcCorps = residents.filter(r => r.is_npc);

  return (
    <div style={{ marginTop: spacing.base }}>
      {/* Player corporations - actual residents */}
      {playerCorps.length > 0 && (
        <>
          <div style={{ fontSize: fontSize.xxs, color: 'rgba(255,255,255,0.4)', marginBottom: '0.35rem', textTransform: 'uppercase' }}>
            Known Residents ({playerCorps.length})
          </div>
          {playerCorps.map((r, idx) => (
            <div
              key={r.corporation_id}
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '0.3rem 0',
                borderBottom: idx < playerCorps.length - 1 ? '1px solid rgba(255,255,255,0.05)' : 'none',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: spacing.base }}>
                <span style={{ fontSize: fontSize.xxs, color: 'rgba(255,255,255,0.4)' }}>[{r.ticker}]</span>
                <span style={{ fontSize: fontSize.sm, color: '#fff' }}>{r.name}</span>
                <a
                  href={`https://zkillboard.com/corporation/${r.corporation_id}/`}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={(e) => e.stopPropagation()}
                  style={{ fontSize: fontSize.micro, color: color.accentCyan, textDecoration: 'none' }}
                >
                  [zkill]
                </a>
              </div>
              <div style={{ fontSize: fontSize.xxs, color: 'rgba(255,255,255,0.5)' }}>
                <span style={{ color: color.safeGreen }}>{r.kills}K</span>
                {' / '}
                <span style={{ color: color.dangerRed }}>{r.losses}L</span>
              </div>
            </div>
          ))}
        </>
      )}

      {/* NPC factions - environmental hazards, not huntable */}
      {npcCorps.length > 0 && (
        <div style={{ marginTop: playerCorps.length > 0 ? '0.75rem' : 0 }}>
          <div style={{
            fontSize: fontSize.xxs,
            color: color.dangerRed,
            marginBottom: '0.35rem',
            textTransform: 'uppercase',
            display: 'flex',
            alignItems: 'center',
            gap: spacing.base,
          }}>
            ⚠️ Environmental Hazards
            <span style={{ color: 'rgba(255,255,255,0.3)', textTransform: 'none', fontSize: fontSize.micro }}>
              (NPC kills in system)
            </span>
          </div>
          {npcCorps.map((r, idx) => (
            <div
              key={r.corporation_id}
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                borderBottom: idx < npcCorps.length - 1 ? '1px solid rgba(255,68,68,0.1)' : 'none',
                background: 'rgba(255,68,68,0.05)',
                margin: '0 -0.5rem',
                padding: '0.3rem 0.5rem',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: spacing.base }}>
                <span style={{ fontSize: fontSize.xxs, color: 'rgba(255,255,255,0.4)' }}>[{r.ticker}]</span>
                <span style={{ fontSize: fontSize.sm, color: '#ff8888' }}>{r.name}</span>
              </div>
              <div style={{ fontSize: fontSize.xxs, color: color.dangerRed }}>
                {r.kills} player deaths
              </div>
            </div>
          ))}
        </div>
      )}

      {/* No player residents */}
      {playerCorps.length === 0 && npcCorps.length > 0 && (
        <div style={{ fontSize: fontSize.xs, color: 'rgba(255,255,255,0.4)', padding: '0.5rem 0', marginTop: spacing.base }}>
          No player residents detected
        </div>
      )}
    </div>
  );
}

function EffectBadge({ effect }: { effect: SystemEffect | null }) {
  if (!effect) return null;
  return (
    <span
      style={{
        fontSize: fontSize.tiny,
        padding: '0.15rem 0.4rem',
        background: `${effect.color}22`,
        color: effect.color,
        borderRadius: '3px',
        fontWeight: 600,
        display: 'inline-flex',
        alignItems: 'center',
        gap: spacing.xs,
      }}
      title={effect.bonus}
    >
      {effect.icon} {effect.name}
    </span>
  );
}

function PrimeTimeDisplay({ primeTime }: { primeTime: PrimeTime | null }) {
  if (!primeTime) return null;

  const tzColors = { EU: '#00d4ff', US: '#ff8800', AU: '#00ff88', Unknown: '#888' };
  const tzTimes = { EU: '17-23 UTC', US: '00-06 UTC', AU: '08-14 UTC', Unknown: '' };

  // Calculate "Other" (hours 7, 15-16) from the remaining percentage
  const otherPct = Math.max(0, 100 - primeTime.eu_pct - primeTime.us_pct - primeTime.au_pct);

  return (
    <div style={{ marginTop: spacing.base }}>
      <div style={{ fontSize: fontSize.xxs, color: 'rgba(255,255,255,0.4)', marginBottom: '0.35rem', textTransform: 'uppercase' }}>
        Prime Time Activity
      </div>
      <div style={{ display: 'flex', gap: spacing.lg, alignItems: 'center', flexWrap: 'wrap' }}>
        {/* Dominant TZ */}
        <span
          style={{
            fontSize: fontSize.sm,
            fontWeight: 600,
            color: tzColors[primeTime.dominant],
          }}
        >
          🕐 {primeTime.dominant} Prime
          <span style={{ fontSize: fontSize.tiny, fontWeight: 400, marginLeft: spacing.base, color: 'rgba(255,255,255,0.4)' }}>
            ({tzTimes[primeTime.dominant]})
          </span>
        </span>

        {/* Breakdown bars */}
        <div style={{ display: 'flex', gap: spacing.base, fontSize: fontSize.tiny, flexWrap: 'wrap' }}>
          {[
            { tz: 'EU', pct: primeTime.eu_pct, color: color.accentCyan },
            { tz: 'US', pct: primeTime.us_pct, color: color.warningOrange },
            { tz: 'AU', pct: primeTime.au_pct, color: color.safeGreen },
            ...(otherPct > 0 ? [{ tz: 'Other', pct: otherPct, color: '#666' }] : []),
          ].map(({ tz, pct, color }) => (
            <div key={tz} style={{ display: 'flex', alignItems: 'center', gap: spacing.xs }}>
              <span style={{ color }}>{tz}</span>
              <div
                style={{
                  width: '40px',
                  height: '6px',
                  background: 'rgba(0,0,0,0.3)',
                  borderRadius: '3px',
                  overflow: 'hidden',
                }}
              >
                <div style={{ width: `${pct}%`, height: '100%', background: color }} />
              </div>
              <span style={{ color: 'rgba(255,255,255,0.4)' }}>{pct}%</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function RecentKillsDisplay({ kills }: { kills: RecentKill[] }) {
  if (!kills || kills.length === 0) return null;

  const formatValue = (v: number) => {
    if (v >= 1e9) return `${(v / 1e9).toFixed(1)}B`;
    if (v >= 1e6) return `${(v / 1e6).toFixed(0)}M`;
    if (v >= 1e3) return `${(v / 1e3).toFixed(0)}K`;
    return v.toFixed(0);
  };

  const formatTime = (t: string | null) => {
    if (!t) return '?';
    const diff = Date.now() - new Date(t).getTime();
    const hours = Math.floor(diff / 3600000);
    if (hours < 24) return `${hours}h`;
    return `${Math.floor(hours / 24)}d`;
  };

  return (
    <div style={{ marginTop: spacing.base }}>
      <div style={{ fontSize: fontSize.xxs, color: 'rgba(255,255,255,0.4)', marginBottom: '0.35rem', textTransform: 'uppercase' }}>
        Recent Kills (7d)
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: spacing.xs }}>
        {kills.slice(0, 5).map((k) => (
          <a
            key={k.killmail_id}
            href={`https://zkillboard.com/kill/${k.killmail_id}/`}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              padding: '0.25rem 0.5rem',
              background: 'rgba(0,0,0,0.2)',
              borderRadius: '4px',
              fontSize: fontSize.xxs,
              color: '#fff',
              textDecoration: 'none',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: spacing.base }}>
              <span style={{ color: color.dangerRed }}>💀</span>
              <span style={{ color: color.warningYellow }}>{k.ship}</span>
              <span style={{ color: 'rgba(255,255,255,0.4)' }}>({k.victim})</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: spacing.lg }}>
              <span style={{ color: color.safeGreen }}>{formatValue(k.value)}</span>
              <span style={{ color: 'rgba(255,255,255,0.3)' }}>{formatTime(k.time)}</span>
            </div>
          </a>
        ))}
      </div>
    </div>
  );
}

function HunterAlliancesDisplay({ hunters }: { hunters: HunterAlliance[] }) {
  if (!hunters || hunters.length === 0) return null;

  return (
    <div style={{ marginTop: spacing.base }}>
      <div style={{
        fontSize: fontSize.xxs,
        color: color.dangerRed,
        marginBottom: '0.35rem',
        textTransform: 'uppercase',
        display: 'flex',
        alignItems: 'center',
        gap: spacing.base,
      }}>
        🎯 Active Hunters (30d)
        <span style={{ color: 'rgba(255,255,255,0.3)', textTransform: 'none', fontSize: fontSize.micro }}>
          (alliances with kills in system)
        </span>
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: spacing.base }}>
        {hunters.map((h) => (
          <a
            key={h.alliance_id}
            href={`https://zkillboard.com/alliance/${h.alliance_id}/`}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.35rem',
              padding: '0.25rem 0.5rem',
              background: 'rgba(255,68,68,0.1)',
              border: '1px solid rgba(255,68,68,0.3)',
              borderRadius: '4px',
              fontSize: fontSize.xxs,
              color: '#fff',
              textDecoration: 'none',
            }}
          >
            <span style={{ color: '#ff8888' }}>{h.name}</span>
            <span style={{ color: color.dangerRed, fontWeight: 600 }}>{h.kills}K</span>
          </a>
        ))}
      </div>
    </div>
  );
}

function ResidentAlliancesDisplay({ alliances }: { alliances: ResidentAlliance[] }) {
  if (!alliances || alliances.length === 0) return null;

  return (
    <div style={{ marginTop: spacing.base }}>
      <div style={{
        fontSize: fontSize.xxs,
        color: color.accentCyan,
        marginBottom: '0.35rem',
        textTransform: 'uppercase',
        display: 'flex',
        alignItems: 'center',
        gap: spacing.base,
      }}>
        🏠 Resident Alliances
        <span style={{ color: 'rgba(255,255,255,0.3)', textTransform: 'none', fontSize: fontSize.micro }}>
          (corps affiliated with)
        </span>
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: spacing.base }}>
        {alliances.map((a) => (
          <a
            key={a.alliance_id}
            href={`https://zkillboard.com/alliance/${a.alliance_id}/`}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.35rem',
              padding: '0.25rem 0.5rem',
              background: 'rgba(0,212,255,0.1)',
              border: '1px solid rgba(0,212,255,0.3)',
              borderRadius: '4px',
              fontSize: fontSize.xxs,
              color: '#fff',
              textDecoration: 'none',
            }}
          >
            <span style={{ color: '#88ddff' }}>{a.name}</span>
            <span style={{ color: 'rgba(255,255,255,0.4)' }}>({a.corps} corps)</span>
          </a>
        ))}
      </div>
    </div>
  );
}

function StructureIntelDisplay({ structures }: { structures: StructureIntel | null }) {
  if (!structures || structures.total_lost === 0) return null;

  const formatValue = (v: number) => {
    if (v >= 1e9) return `${(v / 1e9).toFixed(1)}B`;
    return `${(v / 1e6).toFixed(0)}M`;
  };

  return (
    <div
      style={{
        marginTop: spacing.base,
        padding: spacing.base,
        background: 'rgba(255,136,0,0.1)',
        border: '1px solid rgba(255,136,0,0.3)',
        borderRadius: '4px',
      }}
    >
      <div style={{ fontSize: fontSize.xxs, color: color.warningOrange, fontWeight: 600, marginBottom: '0.35rem' }}>
        🏗️ STRUCTURE LOSSES (30d)
      </div>
      <div style={{ display: 'flex', gap: spacing.xl, fontSize: fontSize.xxs }}>
        <span>
          <span style={{ color: '#fff' }}>{structures.total_lost}</span>
          <span style={{ color: 'rgba(255,255,255,0.4)' }}> lost</span>
        </span>
        <span>
          <span style={{ color: color.safeGreen }}>{formatValue(structures.total_value)}</span>
          <span style={{ color: 'rgba(255,255,255,0.4)' }}> value</span>
        </span>
        {structures.citadels > 0 && (
          <span style={{ color: color.dangerRed }}>{structures.citadels} Citadel{structures.citadels > 1 ? 's' : ''}</span>
        )}
        {structures.engineering > 0 && (
          <span style={{ color: color.accentCyan }}>{structures.engineering} Eng</span>
        )}
        {structures.refineries > 0 && (
          <span style={{ color: color.warningYellow }}>{structures.refineries} Refinery</span>
        )}
      </div>
      {structures.recent.length > 0 && (
        <div style={{ fontSize: fontSize.tiny, color: 'rgba(255,255,255,0.5)', marginTop: spacing.xs }}>
          Recent: {structures.recent.map((s) => s.type).join(', ')}
        </div>
      )}
    </div>
  );
}

function ScoreBreakdownDisplay({ breakdown }: { breakdown: { activity: number; recency: number; weakness: number } }) {
  const items = [
    { label: 'Activity', value: breakdown.activity, max: 40, color: color.accentCyan, desc: 'Kill volume (2pts/kill)' },
    { label: 'Recency', value: breakdown.recency, max: 30, color: color.warningOrange, desc: 'How recent is activity' },
    { label: 'Weakness', value: breakdown.weakness, max: 30, color: color.safeGreen, desc: 'Fewer residents = easier' },
  ];

  return (
    <div style={{ marginTop: spacing.base }}>
      <div style={{ fontSize: fontSize.xxs, color: 'rgba(255,255,255,0.4)', marginBottom: '0.35rem', textTransform: 'uppercase' }}>
        Score Breakdown
      </div>
      <div style={{ display: 'flex', gap: spacing.xl }}>
        {items.map((item) => (
          <div key={item.label} style={{ flex: 1 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: fontSize.xxs, marginBottom: '0.2rem' }}>
              <span style={{ color: item.color }}>{item.label}</span>
              <span style={{ color: 'rgba(255,255,255,0.5)' }}>{item.value}/{item.max}</span>
            </div>
            <div
              style={{
                height: '4px',
                background: 'rgba(0,0,0,0.3)',
                borderRadius: '2px',
                overflow: 'hidden',
              }}
              title={item.desc}
            >
              <div
                style={{
                  width: `${(item.value / item.max) * 100}%`,
                  height: '100%',
                  background: item.color,
                }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function OpportunityCard({ opp, rank }: { opp: WormholeOpportunity; rank: number }) {
  const [expanded, setExpanded] = useState(false);

  const zkillUrl = `https://zkillboard.com/system/${opp.system_id}/`;
  const classColor = WORMHOLE_CLASS_COLORS[opp.wormhole_class] || '#888';

  return (
    <div
      style={{
        background: 'rgba(0,0,0,0.2)',
        borderRadius: '8px',
        borderLeft: `3px solid ${DIFFICULTY_COLORS[opp.difficulty]}`,
        overflow: 'hidden',
        cursor: 'pointer',
        transition: 'background 0.2s',
      }}
      onClick={() => setExpanded(!expanded)}
    >
      {/* Main Header - Always visible */}
      <div style={{ padding: '0.75rem 1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: spacing.lg, flexWrap: 'wrap' }}>
          {/* Rank */}
          <span
            style={{
              fontSize: fontSize.lg,
              fontWeight: 700,
              color: rank <= 3 ? ['#ffd700', '#c0c0c0', '#cd7f32'][rank - 1] : 'rgba(255,255,255,0.3)',
              minWidth: '28px',
            }}
          >
            #{rank}
          </span>

          {/* System Name */}
          <div style={{ display: 'flex', alignItems: 'center', gap: spacing.base }}>
            <span style={{ fontSize: fontSize.lg, fontWeight: 600, color: '#fff' }}>{opp.system_name}</span>
            <a
              href={zkillUrl}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
              style={{ fontSize: fontSize.tiny, color: color.accentCyan, textDecoration: 'none' }}
            >
              [zkill]
            </a>
          </div>

          {/* Class Badge */}
          <span
            style={{
              fontSize: fontSize.xxs,
              padding: '0.15rem 0.4rem',
              background: `${classColor}22`,
              color: classColor,
              borderRadius: '3px',
              fontWeight: 600,
            }}
          >
            C{opp.wormhole_class}
          </span>

          {/* Hot Badge */}
          {opp.is_hot && <HotBadge />}

          {/* Effect Badge */}
          <EffectBadge effect={opp.effect} />

          {/* Score */}
          <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: spacing.lg }}>
            <ScoreBar score={opp.opportunity_score} breakdown={opp.score_breakdown} />

            {/* Difficulty */}
            <span
              style={{
                fontSize: fontSize.tiny,
                padding: '0.15rem 0.4rem',
                background: `${DIFFICULTY_COLORS[opp.difficulty]}22`,
                color: DIFFICULTY_COLORS[opp.difficulty],
                borderRadius: '3px',
                fontWeight: 600,
              }}
            >
              {opp.difficulty}
            </span>
          </div>
        </div>

        {/* Quick Stats Row */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: spacing["2xl"],
            marginTop: spacing.base,
            fontSize: fontSize.xs,
            color: 'rgba(255,255,255,0.5)',
          }}
        >
          <StaticsBadges statics={opp.statics} whClass={opp.wormhole_class} />

          <span>
            <span style={{ color: opp.kills_24h >= 3 ? '#ff8800' : 'inherit' }}>
              {opp.kills_24h} kills/24h
            </span>
            {' • '}
            {opp.kills_7d} kills/7d
          </span>

          <span>{formatISK(opp.isk_destroyed_7d)} ISK</span>

          {opp.resident_corps > 0 && (
            <span>{opp.resident_corps} corp{opp.resident_corps > 1 ? 's' : ''}</span>
          )}

          <span style={{ marginLeft: 'auto', color: 'rgba(255,255,255,0.4)' }}>
            Last: {formatTimeAgo(opp.last_activity)}
          </span>

          <span style={{ color: expanded ? '#00d4ff' : 'rgba(255,255,255,0.3)' }}>
            {expanded ? '▼' : '▶'}
          </span>
        </div>
      </div>

      {/* Expanded Details */}
      {expanded && (
        <div
          style={{
            padding: '0 1rem 1rem 1rem',
            borderTop: '1px solid rgba(255,255,255,0.1)',
            marginTop: '0',
          }}
        >
          {/* Score Breakdown */}
          <ScoreBreakdownDisplay breakdown={opp.score_breakdown} />

          {/* Ship Breakdown */}
          <ShipBreakdownDisplay ships={opp.ships} />

          {/* Residents */}
          <ResidentsList residents={opp.residents} />

          {/* Resident Alliances */}
          <ResidentAlliancesDisplay alliances={opp.resident_alliances} />

          {/* Active Hunters */}
          <HunterAlliancesDisplay hunters={opp.hunters} />

          {/* Prime Time */}
          <PrimeTimeDisplay primeTime={opp.prime_time} />

          {/* Recent Kills */}
          <RecentKillsDisplay kills={opp.recent_kills} />

          {/* Structure Intel */}
          <StructureIntelDisplay structures={opp.structures} />

          {/* 24h Activity Highlight */}
          {opp.kills_24h > 0 && (
            <div
              style={{
                marginTop: spacing.lg,
                padding: spacing.base,
                background: 'rgba(255,136,0,0.1)',
                borderRadius: '4px',
                fontSize: fontSize.xs,
              }}
            >
              <span style={{ color: color.warningOrange, fontWeight: 600 }}>24h Activity: </span>
              <span style={{ color: 'rgba(255,255,255,0.7)' }}>
                {opp.kills_24h} kills • {formatISK(opp.isk_destroyed_24h)} destroyed
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function HuntersTab({ opportunities, selectedClass, onClassChange, loading }: HuntersTabProps) {
  return (
    <div style={{ marginTop: spacing.xl }}>
      {/* Filter Bar */}
      <div
        style={{
          display: 'flex',
          gap: spacing.xl,
          alignItems: 'center',
          padding: spacing.xl,
          background: 'rgba(0,0,0,0.2)',
          borderRadius: '8px',
          marginBottom: spacing.xl,
        }}
      >
        <span style={{ fontSize: fontSize.sm, color: 'rgba(255,255,255,0.6)' }}>Filter:</span>
        <select
          value={selectedClass ?? ''}
          onChange={(e) => onClassChange(e.target.value ? parseInt(e.target.value) : null)}
          style={{
            padding: '0.5rem 0.75rem',
            background: '#1a1a2e',
            border: '1px solid rgba(255,255,255,0.2)',
            borderRadius: '4px',
            color: '#fff',
            cursor: 'pointer',
            outline: 'none',
          }}
        >
          <option value="" style={{ background: '#1a1a2e', color: '#fff' }}>All Classes</option>
          <optgroup label="Standard" style={{ background: '#1a1a2e', color: '#fff' }}>
            {[1, 2, 3, 4, 5, 6].map((c) => (
              <option key={c} value={c} style={{ background: '#1a1a2e', color: '#fff' }}>C{c}</option>
            ))}
          </optgroup>
          <optgroup label="Special" style={{ background: '#1a1a2e', color: '#fff' }}>
            <option value="13" style={{ background: '#1a1a2e', color: color.warningYellow }}>C13 (Shattered)</option>
            <option value="14" style={{ background: '#1a1a2e', color: color.safeGreen }}>Thera</option>
            <option value="15" style={{ background: '#1a1a2e', color: color.dangerRed }}>Sentinel</option>
            <option value="16" style={{ background: '#1a1a2e', color: color.dangerRed }}>Barbican</option>
            <option value="17" style={{ background: '#1a1a2e', color: color.dangerRed }}>Vidette</option>
            <option value="18" style={{ background: '#1a1a2e', color: color.dangerRed }}>Conflux</option>
          </optgroup>
        </select>

        {/* Legend */}
        <div style={{ marginLeft: 'auto', display: 'flex', gap: spacing.xl, fontSize: fontSize.xxs }}>
          <span style={{ color: 'rgba(255,255,255,0.4)' }}>Score:</span>
          <span><span style={{ color: color.accentCyan }}>●</span> Activity</span>
          <span><span style={{ color: color.warningOrange }}>●</span> Recency</span>
          <span><span style={{ color: color.safeGreen }}>●</span> Weakness</span>
        </div>
      </div>

      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: spacing.xl }}>
        <h3 style={{ fontSize: fontSize.lg, fontWeight: 600, color: color.dangerRed, margin: 0 }}>
          🎯 HUNTING OPPORTUNITIES
        </h3>
        <span style={{ fontSize: fontSize.xxs, color: 'rgba(255,255,255,0.4)' }}>
          Ranked by opportunity score (activity + recency + weakness)
        </span>
      </div>

      {/* Opportunity List */}
      {loading ? (
        <div style={{ color: 'rgba(255,255,255,0.4)', textAlign: 'center', padding: spacing["3xl"] }}>
          Loading opportunities...
        </div>
      ) : !opportunities || opportunities.length === 0 ? (
        <div style={{ color: 'rgba(255,255,255,0.4)', textAlign: 'center', padding: spacing["3xl"] }}>
          No opportunities found with current filters
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: spacing.lg }}>
          {opportunities.map((opp, i) => (
            <OpportunityCard key={opp.system_id} opp={opp} rank={i + 1} />
          ))}
        </div>
      )}

      {/* Footer Info */}
      <div
        style={{
          marginTop: spacing.xl,
          padding: spacing.lg,
          background: 'rgba(0,0,0,0.2)',
          borderRadius: '6px',
          fontSize: fontSize.xxs,
          color: 'rgba(255,255,255,0.4)',
        }}
      >
        <strong style={{ color: 'rgba(255,255,255,0.6)' }}>Scoring:</strong> Activity (kills × 2, max 40) +
        Recency (5-30 based on last kill) + Weakness (10-30 based on resident count) = Total (0-100)
      </div>
    </div>
  );
}
