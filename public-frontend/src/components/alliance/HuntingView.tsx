import React, { useEffect, useState } from 'react';
import type { HotZone, StrikeWindow, PriorityTarget, CounterDoctrine } from '../../types/hunting';
import {
  getHuntingHotZones,
  getHuntingStrikeWindow,
  getHuntingPriorityTargets,
  getHuntingCounterDoctrine,
  getGatecampAlerts,
  getEnemyDamageProfiles,
  getSystemDangerRadar,
  type GatecampAlert,
  type EnemyDamageProfile,
  type SystemDanger,
} from '../../services/allianceApi';
import { formatISKCompact } from '../../utils/format';

import { fontSize, color, spacing } from '../../styles/theme';

interface HuntingViewProps {
  allianceId: number;
  allianceName: string;
}

export const HuntingView: React.FC<HuntingViewProps> = ({ allianceId, allianceName }) => {
  const [hotZones, setHotZones] = useState<HotZone[]>([]);
  const [strikeWindow, setStrikeWindow] = useState<StrikeWindow | null>(null);
  const [targets, setTargets] = useState<PriorityTarget[]>([]);
  const [counterDoctrine, setCounterDoctrine] = useState<CounterDoctrine | null>(null);
  const [gatecampAlerts, setGatecampAlerts] = useState<GatecampAlert[]>([]);
  const [enemyDamageProfiles, setEnemyDamageProfiles] = useState<EnemyDamageProfile[]>([]);
  const [systemDangers, setSystemDangers] = useState<SystemDanger[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const [zones, window, tgts, doctrine] = await Promise.all([
          getHuntingHotZones(allianceId),
          getHuntingStrikeWindow(allianceId),
          getHuntingPriorityTargets(allianceId),
          getHuntingCounterDoctrine(allianceId)
        ]);
        setHotZones(zones);
        setStrikeWindow(window);
        setTargets(tgts);
        setCounterDoctrine(doctrine);

        // Fetch additional intel in background (non-blocking)
        getGatecampAlerts(allianceId, 60).then(setGatecampAlerts).catch(() => {});
        getEnemyDamageProfiles(allianceId, 30).then(setEnemyDamageProfiles).catch(() => {});
        getSystemDangerRadar(allianceId, 7).then(setSystemDangers).catch(() => {});
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load hunting data');
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [allianceId]);

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '16rem' }}>
        <div style={{ color: 'rgba(255,255,255,0.5)' }}>Loading hunting intel...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '16rem' }}>
        <div style={{ color: color.lossRed }}>{error}</div>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: spacing.lg }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: spacing.base, marginBottom: spacing.xs }}>
        <span style={{ fontSize: fontSize.h3 }}>🎯</span>
        <h2 style={{ fontSize: fontSize.lg, fontWeight: 700, color: '#fff', margin: 0 }}>HUNTING COMMAND CENTER</h2>
        <span style={{ color: 'rgba(255,255,255,0.5)', marginLeft: spacing.base, fontSize: fontSize.base }}>{allianceName}</span>
      </div>

      {/* Top Row: 3 Panels */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: spacing.lg }}>
        <StrikeWindowPanel data={strikeWindow} />
        <HotZonesPanel zones={hotZones} />
        <CounterDoctrinePanel doctrine={counterDoctrine} />
      </div>

      {/* Row 2: Gatecamp Alerts + Enemy Damage Profiles */}
      {(gatecampAlerts.length > 0 || enemyDamageProfiles.length > 0) && (
        <div style={{ display: 'grid', gridTemplateColumns: gatecampAlerts.length > 0 && enemyDamageProfiles.length > 0 ? '1fr 1fr' : '1fr', gap: spacing.lg }}>
          {/* Gatecamp / Hotspot Alerts */}
          {gatecampAlerts.length > 0 && (
            <GatecampAlertsPanel alerts={gatecampAlerts} />
          )}

          {/* Enemy Damage Profiles */}
          {enemyDamageProfiles.length > 0 && (
            <EnemyDamagePanel profiles={enemyDamageProfiles} />
          )}
        </div>
      )}

      {/* System Danger Radar */}
      {systemDangers.length > 0 && (
        <SystemDangerRadarPanel systems={systemDangers} />
      )}

      {/* Priority Targets Table */}
      <PriorityTargetsTable targets={targets} />
    </div>
  );
};

const StrikeWindowPanel: React.FC<{ data: StrikeWindow | null }> = ({ data }) => {
  if (!data) return null;
  return (
    <div style={{
      background: 'rgba(0,0,0,0.3)',
      border: '1px solid rgba(255,255,255,0.08)',
      borderLeft: '3px solid #3fb950',
      borderRadius: '6px',
      overflow: 'hidden',
    }}>
      <div style={{
        padding: '0.4rem 0.5rem',
        borderBottom: '1px solid rgba(255,255,255,0.08)',
        display: 'flex',
        alignItems: 'center',
        gap: spacing.md,
      }}>
        <span>⏰</span>
        <span style={{ fontSize: fontSize.xxs, fontWeight: 700, color: color.killGreen, textTransform: 'uppercase' }}>
          STRIKE WINDOW
        </span>
      </div>
      <div style={{ padding: spacing.base }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: spacing.md }}>
          <span style={{ fontSize: fontSize.tiny, color: 'rgba(255,255,255,0.5)' }}>Peak Hours:</span>
          <span style={{ fontSize: fontSize.xxs, color: color.dangerRed, fontWeight: 600 }}>
            {data.peak_hours.start}-{data.peak_hours.end} UTC ({data.peak_hours.pct}%)
          </span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: spacing.md }}>
          <span style={{ fontSize: fontSize.tiny, color: 'rgba(255,255,255,0.5)' }}>Weak Hours:</span>
          <span style={{ fontSize: fontSize.xxs, color: color.killGreen, fontWeight: 600 }}>
            {data.weak_hours.start}-{data.weak_hours.end} UTC ({data.weak_hours.pct}%)
          </span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: spacing.md }}>
          <span style={{ fontSize: fontSize.tiny, color: 'rgba(255,255,255,0.5)' }}>Last 24h:</span>
          <span style={{ fontSize: fontSize.xxs, color: '#fff' }}>
            {data.last_24h.kills} kills, {data.last_24h.capital_deployments} caps
          </span>
        </div>
        <div style={{
          marginTop: spacing.base,
          paddingTop: '0.5rem',
          borderTop: '1px solid rgba(255,255,255,0.08)',
          fontSize: fontSize.xxs,
          color: color.killGreen,
          fontWeight: 500,
        }}>
          {data.recommendation}
        </div>
      </div>
    </div>
  );
};

const HotZonesPanel: React.FC<{ zones: HotZone[] }> = ({ zones }) => {
  return (
    <div style={{
      background: 'rgba(0,0,0,0.3)',
      border: '1px solid rgba(255,255,255,0.08)',
      borderLeft: '3px solid #ff6600',
      borderRadius: '6px',
      overflow: 'hidden',
    }}>
      <div style={{
        padding: '0.4rem 0.5rem',
        borderBottom: '1px solid rgba(255,255,255,0.08)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: spacing.md }}>
          <span>📍</span>
          <span style={{ fontSize: fontSize.xxs, fontWeight: 700, color: color.brightOrange, textTransform: 'uppercase' }}>
            HOT ZONES
          </span>
        </div>
        <span style={{ fontSize: fontSize.micro, color: 'rgba(255,255,255,0.4)' }}>30d</span>
      </div>
      <div style={{ padding: spacing.xs }}>
        {zones.slice(0, 5).map((zone, i) => (
          <div key={zone.system_id} style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            padding: '0.3rem 0.4rem',
            marginBottom: '0.1rem',
            background: i < 3 ? 'rgba(255,102,0,0.1)' : 'transparent',
            borderRadius: '3px',
          }}>
            <span>
              <span style={{ fontSize: fontSize.tiny, color: 'rgba(255,255,255,0.4)', marginRight: spacing.md }}>{i + 1}.</span>
              <a
                href={`https://evemaps.dotlan.net/system/${zone.system_name}`}
                target="_blank"
                rel="noopener noreferrer"
                style={{ fontSize: fontSize.xxs, color: color.linkBlue, textDecoration: 'none' }}
              >
                {zone.system_name}
              </a>
            </span>
            <span style={{ fontSize: fontSize.tiny, color: 'rgba(255,255,255,0.5)' }}>
              {zone.total_activity.toLocaleString()} activity
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};

const CounterDoctrinePanel: React.FC<{ doctrine: CounterDoctrine | null }> = ({ doctrine }) => {
  const [showCounter, setShowCounter] = React.useState(false);

  if (!doctrine) return null;

  const damageColors: Record<string, string> = {
    kinetic: '#6B7280',
    thermal: '#EF4444',
    em: '#3B82F6',
    explosive: '#F59E0B'
  };

  const fleet = doctrine.recommended_fleet;

  return (
    <div style={{
      background: 'rgba(0,0,0,0.3)',
      border: '1px solid rgba(255,255,255,0.08)',
      borderLeft: '3px solid #a855f7',
      borderRadius: '6px',
      overflow: 'hidden',
    }}>
      <div style={{
        padding: '0.4rem 0.5rem',
        borderBottom: '1px solid rgba(255,255,255,0.08)',
        display: 'flex',
        alignItems: 'center',
        gap: spacing.md,
      }}>
        <span>🚀</span>
        <span style={{ fontSize: fontSize.xxs, fontWeight: 700, color: color.accentPurple, textTransform: 'uppercase' }}>
          COUNTER-DOCTRINE
        </span>
      </div>
      <div style={{ padding: spacing.base }}>
        {/* Their Meta */}
        <div style={{ fontSize: fontSize.micro, color: 'rgba(255,255,255,0.5)', marginBottom: spacing.sm }}>Their Meta:</div>
        {doctrine.their_meta.slice(0, 3).map((ship, i) => (
          <div key={ship.type_id} style={{
            display: 'flex',
            justifyContent: 'space-between',
            marginBottom: '0.2rem',
          }}>
            <span style={{ fontSize: fontSize.xxs, color: '#fff' }}>
              <span style={{ color: 'rgba(255,255,255,0.4)', marginRight: spacing.sm }}>#{i + 1}</span>
              {ship.ship}
            </span>
            <span style={{ fontSize: fontSize.xxs, color: 'rgba(255,255,255,0.5)' }}>{ship.pct}%</span>
          </div>
        ))}

        {/* Damage Profile Bars */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem', marginTop: spacing.base }}>
          {Object.entries(doctrine.damage_profile).map(([type, pct]) => (
            pct > 0 && (
              <div key={type} style={{ display: 'flex', alignItems: 'center', gap: spacing.md }}>
                <span style={{ fontSize: fontSize.micro, color: damageColors[type], width: '55px', textTransform: 'capitalize' }}>
                  {type}
                </span>
                <div style={{ flex: 1, height: '6px', background: 'rgba(255,255,255,0.1)', borderRadius: '3px', overflow: 'hidden' }}>
                  <div style={{
                    width: `${pct}%`,
                    height: '100%',
                    background: damageColors[type],
                    borderRadius: '3px',
                  }} />
                </div>
                <span style={{ fontSize: fontSize.micro, color: 'rgba(255,255,255,0.5)', width: '30px', textAlign: 'right' }}>
                  {pct}%
                </span>
              </div>
            )
          ))}
        </div>

        {/* Tank Recommendation */}
        <div style={{
          marginTop: spacing.base,
          paddingTop: '0.5rem',
          borderTop: '1px solid rgba(255,255,255,0.08)',
          fontSize: fontSize.xxs,
          color: color.teal,
          fontWeight: 500,
        }}>
          {doctrine.tank_recommendation}
        </div>

        {/* Counter Fleet Toggle */}
        <div
          onClick={() => setShowCounter(!showCounter)}
          style={{
            marginTop: spacing.base,
            padding: '0.35rem',
            background: showCounter ? 'rgba(168,85,247,0.2)' : 'rgba(168,85,247,0.1)',
            border: '1px solid rgba(168,85,247,0.3)',
            borderRadius: '4px',
            cursor: 'pointer',
            textAlign: 'center',
            fontSize: fontSize.tiny,
            color: color.accentPurple,
            fontWeight: 600,
            transition: 'all 0.15s',
          }}
        >
          {showCounter ? '▼ HIDE COUNTER FLEET' : '▶ SHOW COUNTER FLEET'}
        </div>

        {/* Counter Fleet Details */}
        {showCounter && (
          <div style={{ marginTop: spacing.md }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: spacing.xs }}>
              <div style={{ background: 'rgba(63,185,80,0.15)', padding: spacing.sm, borderRadius: '3px' }}>
                <div style={{ color: color.killGreen, fontWeight: 600, fontSize: fontSize.nano }}>DPS</div>
                <div style={{ color: '#fff', fontSize: fontSize.xxs }}>{fleet.dps.ship}</div>
              </div>
              <div style={{ background: 'rgba(88,166,255,0.15)', padding: spacing.sm, borderRadius: '3px' }}>
                <div style={{ color: color.linkBlue, fontWeight: 600, fontSize: fontSize.nano }}>LOGI</div>
                <div style={{ color: '#fff', fontSize: fontSize.xxs }}>{fleet.logi.ship}</div>
              </div>
              <div style={{ background: 'rgba(168,85,247,0.15)', padding: spacing.sm, borderRadius: '3px' }}>
                <div style={{ color: color.accentPurple, fontWeight: 600, fontSize: fontSize.nano }}>SUPPORT</div>
                <div style={{ color: '#fff', fontSize: fontSize.xxs }}>{fleet.support.ship}</div>
              </div>
              <div style={{ background: 'rgba(248,81,73,0.15)', padding: spacing.sm, borderRadius: '3px' }}>
                <div style={{ color: color.lossRed, fontWeight: 600, fontSize: fontSize.nano }}>TACKLE</div>
                <div style={{ color: '#fff', fontSize: fontSize.xxs }}>{fleet.tackle.ship}</div>
              </div>
            </div>
            <div style={{ marginTop: spacing.sm, fontSize: fontSize.micro, color: 'rgba(255,255,255,0.5)', fontStyle: 'italic' }}>
              {doctrine.reasoning}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

const PriorityTargetsTable: React.FC<{ targets: PriorityTarget[] }> = ({ targets }) => {
  const getWhaleIcon = (category: string) => {
    switch (category) {
      case 'whale': return '🐋';
      case 'shark': return '🦈';
      default: return '🐟';
    }
  };

  const formatISK = (value: number) => {
    if (value >= 1e9) return `${(value / 1e9).toFixed(1)}B`;
    if (value >= 1e6) return `${(value / 1e6).toFixed(0)}M`;
    return `${(value / 1e3).toFixed(0)}K`;
  };

  return (
    <div style={{
      background: 'rgba(0,0,0,0.3)',
      border: '1px solid rgba(255,255,255,0.08)',
      borderLeft: '3px solid #f59e0b',
      borderRadius: '6px',
      overflow: 'hidden',
    }}>
      <div style={{
        padding: spacing.base,
        borderBottom: '1px solid rgba(255,255,255,0.08)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: spacing.md }}>
          <span>🎯</span>
          <span style={{ fontSize: fontSize.xxs, fontWeight: 700, color: '#f59e0b', textTransform: 'uppercase' }}>
            PRIORITY TARGETS
          </span>
        </div>
        <span style={{ fontSize: fontSize.micro, color: 'rgba(255,255,255,0.4)' }}>
          Whale Score = (ISK × Deaths) / Efficiency
        </span>
      </div>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', fontSize: fontSize.xxs, borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.08)' }}>
              <th style={{ textAlign: 'left', padding: spacing.md, color: 'rgba(255,255,255,0.5)', fontWeight: 600, width: '30px' }}>#</th>
              <th style={{ textAlign: 'left', padding: spacing.md, color: 'rgba(255,255,255,0.5)', fontWeight: 600 }}>Pilot</th>
              <th style={{ textAlign: 'right', padding: spacing.md, color: 'rgba(255,255,255,0.5)', fontWeight: 600 }}>Whale</th>
              <th style={{ textAlign: 'right', padding: spacing.md, color: 'rgba(255,255,255,0.5)', fontWeight: 600 }}>ISK/Death</th>
              <th style={{ textAlign: 'right', padding: spacing.md, color: 'rgba(255,255,255,0.5)', fontWeight: 600 }}>Deaths</th>
              <th style={{ textAlign: 'left', padding: spacing.md, color: 'rgba(255,255,255,0.5)', fontWeight: 600 }}>Ships</th>
              <th style={{ textAlign: 'right', padding: spacing.md, color: 'rgba(255,255,255,0.5)', fontWeight: 600 }}>Active</th>
            </tr>
          </thead>
          <tbody>
            {targets.map((target, i) => (
              <tr key={target.character_id} style={{
                borderBottom: '1px solid rgba(255,255,255,0.03)',
                background: i < 3 ? 'rgba(245,158,11,0.08)' : 'transparent',
              }}>
                <td style={{ padding: spacing.md, color: 'rgba(255,255,255,0.4)' }}>{i + 1}</td>
                <td style={{ padding: spacing.md }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: spacing.md }}>
                    <img
                      src={`https://images.evetech.net/characters/${target.character_id}/portrait?size=32`}
                      alt=""
                      style={{
                        width: 24,
                        height: 24,
                        borderRadius: '2px',
                        border: '1px solid rgba(255,255,255,0.1)',
                      }}
                      onError={(e) => { e.currentTarget.style.display = 'none'; }}
                    />
                    <span>{getWhaleIcon(target.whale_category)}</span>
                    <a
                      href={`https://zkillboard.com/character/${target.character_id}/`}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{ color: color.linkBlue, textDecoration: 'none' }}
                    >
                      {target.character_name}
                    </a>
                  </div>
                </td>
                <td style={{ padding: spacing.md, textAlign: 'right', fontFamily: 'monospace', color: '#f59e0b', fontWeight: 600 }}>
                  {target.whale_score}
                </td>
                <td style={{ padding: spacing.md, textAlign: 'right', fontFamily: 'monospace', color: color.killGreen }}>
                  {formatISK(target.isk_per_death)}
                </td>
                <td style={{ padding: spacing.md, textAlign: 'right', fontFamily: 'monospace', color: color.lossRed }}>
                  {target.deaths}
                </td>
                <td style={{
                  padding: spacing.md,
                  color: 'rgba(255,255,255,0.7)',
                  maxWidth: '150px',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}>
                  {target.typical_ships.slice(0, 2).join(', ')}
                </td>
                <td style={{ padding: spacing.md, textAlign: 'right', color: 'rgba(255,255,255,0.5)' }}>
                  {target.last_active}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div style={{
        padding: '0.4rem 0.5rem',
        borderTop: '1px solid rgba(255,255,255,0.08)',
        fontSize: fontSize.micro,
        color: 'rgba(255,255,255,0.4)',
      }}>
        🐋 = Whale (70+) &nbsp;&nbsp; 🦈 = Shark (40-69) &nbsp;&nbsp; 🐟 = Fish (&lt;40)
      </div>
    </div>
  );
};

const GatecampAlertsPanel: React.FC<{ alerts: GatecampAlert[] }> = ({ alerts }) => {
  const severityColors: Record<string, string> = {
    critical: '#ff0000',
    high: '#ff6600',
    medium: '#ffcc00'
  };

  const campTypeLabels: Record<string, string> = {
    gatecamp: 'GATECAMP',
    targeted_hunt: 'HUNT',
    hotspot: 'HOTSPOT'
  };

  const formatDuration = (sec: number) => {
    if (sec >= 3600) return `${Math.floor(sec / 3600)}h ${Math.floor((sec % 3600) / 60)}m`;
    if (sec >= 60) return `${Math.floor(sec / 60)}m`;
    return `${sec}s`;
  };

  return (
    <div style={{
      background: 'rgba(0,0,0,0.3)',
      border: '1px solid rgba(255,255,255,0.08)',
      borderLeft: '3px solid #ff0000',
      borderRadius: '6px',
      overflow: 'hidden',
    }}>
      <div style={{
        padding: '0.4rem 0.5rem',
        borderBottom: '1px solid rgba(255,255,255,0.08)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: spacing.md }}>
          <span style={{ animation: 'pulse 2s infinite' }}>🚨</span>
          <span style={{ fontSize: fontSize.xxs, fontWeight: 700, color: color.pureRed, textTransform: 'uppercase' }}>
            LIVE ALERTS
          </span>
        </div>
        <span style={{ fontSize: fontSize.micro, color: 'rgba(255,255,255,0.4)' }}>
          last 60min
        </span>
      </div>
      <div style={{ padding: spacing.xs, maxHeight: '220px', overflowY: 'auto' }}>
        {alerts.map((alert) => (
          <div key={alert.system_id} style={{
            display: 'flex',
            alignItems: 'center',
            gap: spacing.md,
            padding: '0.35rem 0.4rem',
            marginBottom: spacing['2xs'],
            background: `${severityColors[alert.severity]}10`,
            borderRadius: '3px',
            borderLeft: `2px solid ${severityColors[alert.severity]}`,
          }}>
            <span style={{
              fontSize: fontSize.pico,
              fontWeight: 700,
              color: '#fff',
              background: severityColors[alert.severity],
              padding: '1px 4px',
              borderRadius: '2px',
              flexShrink: 0,
            }}>
              {alert.severity.toUpperCase()}
            </span>
            <span style={{
              fontSize: fontSize.pico,
              fontWeight: 600,
              color: severityColors[alert.severity],
              background: `${severityColors[alert.severity]}20`,
              padding: '1px 3px',
              borderRadius: '2px',
              flexShrink: 0,
            }}>
              {campTypeLabels[alert.camp_type] || alert.camp_type}
            </span>
            <a
              href={`https://evemaps.dotlan.net/system/${alert.system_name}`}
              target="_blank"
              rel="noopener noreferrer"
              style={{ fontSize: fontSize.xxs, color: color.linkBlue, textDecoration: 'none', fontWeight: 600 }}
            >
              {alert.system_name}
            </a>
            <span style={{ fontSize: fontSize.nano, color: 'rgba(255,255,255,0.4)', flex: 1 }}>
              {alert.region_name}
            </span>
            <span style={{ fontSize: fontSize.tiny, fontWeight: 700, color: color.lossRed, fontFamily: 'monospace' }}>
              {alert.kills}
            </span>
            <span style={{ fontSize: fontSize.pico, color: 'rgba(255,255,255,0.4)' }}>kills</span>
            {alert.pod_kills > 0 && (
              <span style={{ fontSize: fontSize.nano, color: color.brightOrange }}>
                ({alert.pod_kills} pods)
              </span>
            )}
            <span style={{ fontSize: fontSize.nano, color: 'rgba(255,255,255,0.3)' }}>
              {formatDuration(alert.duration_seconds)}
            </span>
          </div>
        ))}
      </div>
      <div style={{
        padding: '0.3rem 0.5rem',
        borderTop: '1px solid rgba(255,255,255,0.05)',
        fontSize: fontSize.pico,
        color: 'rgba(255,255,255,0.35)',
      }}>
        Systems with 3+ kills in the last hour in alliance territory
      </div>
    </div>
  );
};

const EnemyDamagePanel: React.FC<{ profiles: EnemyDamageProfile[] }> = ({ profiles }) => {
  const damageColors: Record<string, string> = {
    kinetic: '#6B7280',
    thermal: '#EF4444',
    em: '#3B82F6',
    explosive: '#F59E0B'
  };

  return (
    <div style={{
      background: 'rgba(0,0,0,0.3)',
      border: '1px solid rgba(255,255,255,0.08)',
      borderLeft: '3px solid #00bcd4',
      borderRadius: '6px',
      overflow: 'hidden',
    }}>
      <div style={{
        padding: '0.4rem 0.5rem',
        borderBottom: '1px solid rgba(255,255,255,0.08)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: spacing.md }}>
          <span>🔬</span>
          <span style={{ fontSize: fontSize.xxs, fontWeight: 700, color: color.teal, textTransform: 'uppercase' }}>
            ENEMY DAMAGE PROFILES
          </span>
        </div>
        <span style={{ fontSize: fontSize.micro, color: 'rgba(255,255,255,0.4)' }}>
          30d • tank advice per enemy
        </span>
      </div>
      <div style={{ padding: spacing.xs, maxHeight: '220px', overflowY: 'auto' }}>
        {profiles.map(enemy => (
          <div key={enemy.alliance_id} style={{
            padding: spacing.md,
            marginBottom: '0.2rem',
            background: 'rgba(0,188,212,0.05)',
            borderRadius: '4px',
          }}>
            {/* Enemy Header */}
            <div style={{ display: 'flex', alignItems: 'center', gap: spacing.md, marginBottom: spacing.sm }}>
              <img
                src={`https://images.evetech.net/alliances/${enemy.alliance_id}/logo?size=32`}
                alt=""
                style={{ width: 18, height: 18, borderRadius: 2 }}
                onError={(e) => { e.currentTarget.style.display = 'none'; }}
              />
              <span style={{ fontSize: fontSize.xxs, fontWeight: 600, color: '#fff', flex: 1 }}>
                {enemy.alliance_name}
              </span>
              <span style={{ fontSize: fontSize.nano, color: 'rgba(255,255,255,0.4)' }}>
                [{enemy.ticker}]
              </span>
              <span style={{ fontSize: fontSize.tiny, fontWeight: 700, color: color.lossRed, fontFamily: 'monospace' }}>
                {enemy.kills}
              </span>
              <span style={{ fontSize: fontSize.pico, color: 'rgba(255,255,255,0.4)' }}>kills</span>
            </div>

            {/* Damage Profile Bars */}
            <div style={{ display: 'flex', gap: '3px', marginBottom: spacing.xs }}>
              {Object.entries(enemy.damage_profile)
                .filter(([, pct]) => pct > 0)
                .sort(([, a], [, b]) => b - a)
                .map(([type, pct]) => (
                  <div key={type} style={{
                    flex: pct,
                    height: '6px',
                    background: damageColors[type] || '#888',
                    borderRadius: '2px',
                    minWidth: '4px',
                  }} title={`${type}: ${pct}%`} />
                ))
              }
            </div>

            {/* Bottom Row: Ships + Tank Rec */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', gap: spacing.sm }}>
                {enemy.top_ships.slice(0, 3).map((s, i) => (
                  <span key={i} style={{
                    fontSize: fontSize.nano,
                    color: 'rgba(255,255,255,0.5)',
                    background: 'rgba(255,255,255,0.05)',
                    padding: '1px 3px',
                    borderRadius: '2px',
                  }}>
                    {s.ship}
                  </span>
                ))}
              </div>
              <span style={{
                fontSize: fontSize.nano,
                fontWeight: 600,
                color: damageColors[enemy.primary_damage] || '#00bcd4',
              }}>
                → {enemy.tank_recommendation}
              </span>
            </div>
          </div>
        ))}
      </div>
      <div style={{
        padding: '0.3rem 0.5rem',
        borderTop: '1px solid rgba(255,255,255,0.05)',
        display: 'flex',
        gap: spacing.lg,
        fontSize: fontSize.pico,
      }}>
        {Object.entries(damageColors).map(([type, color]) => (
          <span key={type} style={{ display: 'flex', alignItems: 'center', gap: '0.2rem' }}>
            <span style={{ width: '8px', height: '8px', background: color, borderRadius: '1px', display: 'inline-block' }} />
            <span style={{ color: 'rgba(255,255,255,0.4)', textTransform: 'capitalize' }}>{type}</span>
          </span>
        ))}
      </div>
    </div>
  );
};

const SystemDangerRadarPanel: React.FC<{ systems: SystemDanger[] }> = ({ systems }) => {
  const dangerColors: Record<string, string> = {
    critical: '#ff0000',
    high: '#ff6600',
    medium: '#ffcc00',
    low: '#3fb950',
  };

  const maxDeaths = Math.max(...systems.map(s => s.total_deaths), 1);

  return (
    <div style={{
      background: 'rgba(0,0,0,0.3)',
      border: '1px solid rgba(255,255,255,0.08)',
      borderLeft: '3px solid #ff4444',
      borderRadius: '6px',
      overflow: 'hidden',
    }}>
      <div style={{
        padding: '0.4rem 0.5rem',
        borderBottom: '1px solid rgba(255,255,255,0.08)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: spacing.md }}>
          <span>📡</span>
          <span style={{ fontSize: fontSize.xxs, fontWeight: 700, color: color.dangerRed, textTransform: 'uppercase' }}>
            SYSTEM DANGER RADAR
          </span>
        </div>
        <span style={{ fontSize: fontSize.micro, color: 'rgba(255,255,255,0.4)' }}>
          7d • deadliest systems for your pilots
        </span>
      </div>
      <div style={{ padding: spacing.xs }}>
        {systems.slice(0, 10).map(sys => (
          <div key={sys.system_id} style={{
            padding: spacing.md,
            marginBottom: '0.2rem',
            background: `${dangerColors[sys.danger_level]}08`,
            borderRadius: '4px',
            borderLeft: `2px solid ${dangerColors[sys.danger_level]}`,
          }}>
            {/* Top row: System info + stats */}
            <div style={{ display: 'flex', alignItems: 'center', gap: spacing.base, marginBottom: spacing.sm }}>
              <span style={{
                fontSize: fontSize.pico,
                fontWeight: 700,
                color: '#fff',
                background: dangerColors[sys.danger_level],
                padding: '1px 4px',
                borderRadius: '2px',
                flexShrink: 0,
              }}>
                {sys.danger_level.toUpperCase()}
              </span>
              <a
                href={`https://evemaps.dotlan.net/system/${sys.system_name}`}
                target="_blank"
                rel="noopener noreferrer"
                style={{ fontSize: fontSize.xs, color: color.linkBlue, textDecoration: 'none', fontWeight: 700 }}
              >
                {sys.system_name}
              </a>
              <span style={{ fontSize: fontSize.nano, color: 'rgba(255,255,255,0.4)' }}>
                {sys.region_name} • {sys.security.toFixed(1)}
              </span>
              <div style={{ flex: 1 }} />
              <span style={{ fontSize: fontSize.xxs, fontWeight: 700, color: color.lossRed, fontFamily: 'monospace' }}>
                {sys.total_deaths}
              </span>
              <span style={{ fontSize: fontSize.nano, color: 'rgba(255,255,255,0.4)' }}>deaths</span>
              {sys.pod_deaths > 0 && (
                <span style={{ fontSize: fontSize.micro, color: color.brightOrange }}>
                  ({sys.pod_deaths} pods)
                </span>
              )}
              <span style={{ fontSize: fontSize.micro, color: 'rgba(255,255,255,0.5)', fontFamily: 'monospace' }}>
                {sys.deaths_per_day.toFixed(1)}/d
              </span>
              <span style={{ fontSize: fontSize.nano, color: color.lossRed }}>
                {formatISKCompact(sys.isk_lost)}
              </span>
            </div>

            {/* Bottom row: Hourly mini-chart + top attackers */}
            <div style={{ display: 'flex', alignItems: 'flex-end', gap: spacing.lg }}>
              {/* Hourly deaths mini-chart */}
              <div style={{ display: 'flex', alignItems: 'flex-end', gap: '1px', height: '18px', flexShrink: 0 }}>
                {sys.hourly_deaths.map((count, hour) => {
                  const maxH = Math.max(...sys.hourly_deaths, 1);
                  const h = maxH > 0 ? (count / maxH) * 18 : 0;
                  return (
                    <div
                      key={hour}
                      style={{
                        width: '3px',
                        height: `${Math.max(h, 1)}px`,
                        background: hour === sys.peak_hour ? '#ff4444' : count > 0 ? 'rgba(248,81,73,0.5)' : 'rgba(255,255,255,0.08)',
                        borderRadius: '1px',
                      }}
                      title={`${hour}:00 - ${count} deaths`}
                    />
                  );
                })}
              </div>
              <span style={{ fontSize: fontSize.pico, color: 'rgba(255,255,255,0.3)', flexShrink: 0 }}>
                peak {sys.peak_hour}:00
              </span>

              {/* Death bar */}
              <div style={{ flex: 1, height: '4px', background: 'rgba(255,255,255,0.05)', borderRadius: '2px', overflow: 'hidden' }}>
                <div style={{
                  width: `${(sys.total_deaths / maxDeaths) * 100}%`,
                  height: '100%',
                  background: dangerColors[sys.danger_level],
                  borderRadius: '2px',
                }} />
              </div>

              {/* Top attackers */}
              <div style={{ display: 'flex', gap: spacing.sm, flexShrink: 0 }}>
                {sys.top_attackers.slice(0, 3).map(atk => (
                  <span key={atk.alliance_id} style={{
                    fontSize: fontSize.pico,
                    color: 'rgba(255,255,255,0.5)',
                    background: 'rgba(248,81,73,0.1)',
                    padding: '1px 3px',
                    borderRadius: '2px',
                  }}>
                    {atk.ticker || atk.alliance_name.substring(0, 8)} ({atk.kills})
                  </span>
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>
      <div style={{
        padding: '0.3rem 0.5rem',
        borderTop: '1px solid rgba(255,255,255,0.05)',
        fontSize: fontSize.pico,
        color: 'rgba(255,255,255,0.35)',
      }}>
        Systems where your alliance members died most in the last 7 days • Bar chart shows hourly death distribution (red = peak)
      </div>
    </div>
  );
};

export default HuntingView;
