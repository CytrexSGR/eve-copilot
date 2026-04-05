// src/components/alliance/WormholeView.tsx - WH Empire View (Controlled Systems)
import { formatISKCompact } from '../../utils/format';
import type { SovThreatsResponse } from '../../services/allianceApi';

import { fontSize, color, spacing } from '../../styles/theme';

interface SystemEffect {
  name: string | null;
  color: string;
  bonuses: string;
  icon: string;
}

interface SystemStatic {
  type: string;
  target_class: number | null;
  max_ship: string | null;
}

interface EconomicPotential {
  monthly_isk: number;
  label: string;
  gas_income: number;
  blue_loot_income: number;
}

interface ControlledSystem {
  system_id: number;
  system_name: string;
  wh_class: number;
  resident_corps: number;
  kills: number;
  losses: number;
  last_activity: string | null;
  activity_score: number;
  effect: SystemEffect | null;
  statics: SystemStatic[];
  economic_potential: EconomicPotential;
}

interface Visitor {
  alliance_id: number;
  alliance_name: string;
  kills_in_our_space: number;
  losses_in_our_space: number;
  systems_visited: number;
  last_seen: string | null;
  threat_level: 'high' | 'medium' | 'low';
}

interface Threat {
  killmail_id: number;
  system_id: number;
  system_name: string;
  ship_type_id: number;
  ship_name: string;
  value: number;
  time: string | null;
  attacker_alliance_id: number | null;
  attacker_alliance_name: string;
}

interface ClassDistribution {
  wh_class: number;
  count: number;
}

export interface AllianceWormholeEmpire {
  alliance_id: number;
  period_days: number;
  summary: {
    total_systems: number;
    total_corps: number;
    monthly_potential_isk: number;
    total_kills: number;
    total_losses: number;
    has_empire: boolean;
  };
  controlled_systems: ControlledSystem[];
  visitors: Visitor[];
  threats: Threat[];
  class_distribution: ClassDistribution[];
}

interface WormholeViewProps {
  intel: AllianceWormholeEmpire | null;
  loading: boolean;
  sovThreats?: SovThreatsResponse | null;
  sovThreatsLoading?: boolean;
}

const WH_CLASS_COLORS: Record<number, string> = {
  1: '#58a6ff',
  2: '#3fb950',
  3: '#ffcc00',
  4: '#ff6600',
  5: '#f85149',
  6: '#a855f7',
  // Special wormholes
  13: '#ec4899',  // Shattered
  14: '#00ffff',  // Thera
  15: '#ff00ff',  // Drifter
  16: '#ff00ff',
  17: '#ff00ff',
  18: '#ff00ff',
};

const THREAT_COLORS: Record<string, string> = {
  high: '#f85149',
  medium: '#ff6600',
  low: '#ffcc00',
};

const getClassColor = (whClass: number): string => {
  return WH_CLASS_COLORS[whClass] || '#58a6ff';
};

const getClassLabel = (whClass: number): string => {
  // Special wormhole classes
  if (whClass === 13) return 'Shattered';
  if (whClass === 14) return 'Thera';
  if (whClass >= 15 && whClass <= 18) return 'Drifter';
  return `C${whClass}`;
};

const formatTimeAgo = (isoDate: string | null): string => {
  if (!isoDate) return 'Unknown';
  const date = new Date(isoDate);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffHours / 24);

  if (diffDays > 0) return `${diffDays}d ago`;
  if (diffHours > 0) return `${diffHours}h ago`;
  return 'Just now';
};

const THREAT_LEVEL_COLORS: Record<string, string> = {
  CRITICAL: '#ff0000',
  HIGH: '#ff6600',
  MODERATE: '#ffcc00',
  LOW: '#3fb950',
  NONE: '#888888',
};

export function WormholeView({ intel, loading, sovThreats, sovThreatsLoading }: WormholeViewProps) {
  if (loading) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: spacing.lg }}>
        <div className="skeleton" style={{ height: '80px', borderRadius: '6px' }} />
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: spacing.lg }}>
          <div className="skeleton" style={{ height: '300px', borderRadius: '6px' }} />
          <div className="skeleton" style={{ height: '300px', borderRadius: '6px' }} />
        </div>
      </div>
    );
  }

  if (!intel || !intel.summary.has_empire) {
    return (
      <div style={{
        padding: spacing["3xl"],
        textAlign: 'center',
        color: 'rgba(255,255,255,0.5)',
        background: 'rgba(0,0,0,0.3)',
        borderRadius: '6px',
        border: '1px solid rgba(255,255,255,0.08)',
      }}>
        <div style={{ fontSize: fontSize.h1, marginBottom: spacing.base }}>🌀</div>
        <div style={{ fontSize: fontSize.sm, marginBottom: spacing.xs }}>No Wormhole Empire</div>
        <div style={{ fontSize: fontSize.tiny, color: 'rgba(255,255,255,0.3)' }}>
          This alliance has no detected presence in J-Space
        </div>
      </div>
    );
  }

  const { summary, controlled_systems, visitors, threats, class_distribution } = intel;
  const maxClassCount = Math.max(...class_distribution.map(c => c.count), 1);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: spacing.lg }}>
      {/* HERO STATS - Empire Overview */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(5, 1fr)',
        gap: spacing.base,
        background: 'rgba(0,0,0,0.3)',
        borderRadius: '6px',
        border: '1px solid rgba(255,255,255,0.08)',
        padding: spacing.lg,
      }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: fontSize.h3, fontWeight: 700, color: color.accentPurple, fontFamily: 'monospace' }}>
            {summary.total_systems}
          </div>
          <div style={{ fontSize: fontSize.micro, color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase' }}>Systems</div>
        </div>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: fontSize.h3, fontWeight: 700, color: color.linkBlue, fontFamily: 'monospace' }}>
            {summary.total_corps}
          </div>
          <div style={{ fontSize: fontSize.micro, color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase' }}>Corps Active</div>
        </div>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: fontSize.h3, fontWeight: 700, color: color.warningYellow, fontFamily: 'monospace' }}>
            {formatISKCompact(summary.monthly_potential_isk)}
          </div>
          <div style={{ fontSize: fontSize.micro, color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase' }}>ISK/Month Potential</div>
        </div>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: fontSize.h3, fontWeight: 700, color: color.killGreen, fontFamily: 'monospace' }}>
            {summary.total_kills}
          </div>
          <div style={{ fontSize: fontSize.micro, color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase' }}>Kills</div>
        </div>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: fontSize.h3, fontWeight: 700, color: color.lossRed, fontFamily: 'monospace' }}>
            {summary.total_losses}
          </div>
          <div style={{ fontSize: fontSize.micro, color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase' }}>Losses</div>
        </div>
      </div>

      {/* ROW 1: Controlled Systems + Class Distribution */}
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: spacing.lg }}>
        {/* CONTROLLED SYSTEMS */}
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
            alignItems: 'center',
            gap: spacing.sm,
          }}>
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: color.accentPurple }} />
            <span style={{ fontSize: fontSize.xxs, fontWeight: 700, color: color.accentPurple, textTransform: 'uppercase' }}>
              Controlled Systems
            </span>
            <span style={{ fontSize: fontSize.micro, color: 'rgba(255,255,255,0.4)', marginLeft: 'auto' }}>
              {controlled_systems.length} holes
            </span>
          </div>
          <div style={{ padding: spacing.xs, maxHeight: '320px', overflowY: 'auto' }}>
            {controlled_systems.map((sys) => (
              <div key={sys.system_id} style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: spacing.base,
                padding: '0.4rem 0.5rem',
                marginBottom: spacing.xs,
                background: 'rgba(255,255,255,0.02)',
                borderRadius: '4px',
                borderLeft: `3px solid ${getClassColor(sys.wh_class)}`,
              }}>
                {/* Class Badge */}
                <div style={{
                  minWidth: '32px',
                  textAlign: 'center',
                  padding: '0.15rem 0',
                  background: `${getClassColor(sys.wh_class)}22`,
                  borderRadius: '3px',
                }}>
                  <div style={{ fontSize: fontSize.xxs, fontWeight: 700, color: getClassColor(sys.wh_class) }}>
                    {getClassLabel(sys.wh_class)}
                  </div>
                </div>

                {/* System Info */}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: spacing.sm, marginBottom: '0.2rem' }}>
                    <span style={{ fontSize: fontSize.xxs, fontWeight: 600, color: '#fff' }}>
                      {sys.system_name}
                    </span>
                    {sys.effect && (
                      <span style={{
                        fontSize: fontSize.pico,
                        padding: '1px 4px',
                        background: `${sys.effect.color}22`,
                        color: sys.effect.color,
                        borderRadius: '2px',
                        fontWeight: 600,
                      }} title={sys.effect.bonuses}>
                        {sys.effect.icon} {sys.effect.name}
                      </span>
                    )}
                  </div>

                  {/* Stats Row */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: spacing.base, fontSize: fontSize.nano }}>
                    <span style={{ color: 'rgba(255,255,255,0.5)' }}>
                      {sys.resident_corps} corp{sys.resident_corps !== 1 ? 's' : ''}
                    </span>
                    <span style={{ color: color.killGreen }}>{sys.kills} kills</span>
                    <span style={{ color: color.lossRed }}>{sys.losses} losses</span>
                  </div>

                  {/* Statics */}
                  {sys.statics.length > 0 && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: spacing.xs, marginTop: '0.2rem' }}>
                      <span style={{ fontSize: fontSize.pico, color: 'rgba(255,255,255,0.3)' }}>Statics:</span>
                      {sys.statics.map((st, i) => (
                        <span key={i} style={{
                          fontSize: fontSize.pico,
                          padding: '1px 3px',
                          background: 'rgba(255,255,255,0.08)',
                          borderRadius: '2px',
                          color: st.target_class ? getClassColor(st.target_class) : 'rgba(255,255,255,0.5)',
                        }}>
                          {st.type} → {st.target_class ? `C${st.target_class}` : '?'}
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                {/* Economic Potential */}
                <div style={{ textAlign: 'right', minWidth: '70px' }}>
                  <div style={{ fontSize: fontSize.tiny, fontWeight: 600, color: color.warningYellow, fontFamily: 'monospace' }}>
                    {formatISKCompact(sys.economic_potential.monthly_isk)}
                  </div>
                  <div style={{ fontSize: fontSize.pico, color: 'rgba(255,255,255,0.4)' }}>
                    {sys.economic_potential.label}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* CLASS DISTRIBUTION + VISITORS */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: spacing.lg }}>
          {/* CLASS DISTRIBUTION */}
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
              alignItems: 'center',
              gap: spacing.sm,
            }}>
              <span style={{ width: 6, height: 6, borderRadius: '50%', background: color.linkBlue }} />
              <span style={{ fontSize: fontSize.xxs, fontWeight: 700, color: color.linkBlue, textTransform: 'uppercase' }}>
                WH Class Breakdown
              </span>
            </div>
            <div style={{ padding: spacing.base }}>
              {class_distribution.map((cls) => (
                <div key={cls.wh_class} style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: spacing.base,
                  marginBottom: spacing.md,
                }}>
                  <span style={{
                    fontSize: fontSize.tiny,
                    fontWeight: 600,
                    color: getClassColor(cls.wh_class),
                    minWidth: '35px',
                  }}>
                    {getClassLabel(cls.wh_class)}
                  </span>
                  <div style={{
                    flex: 1,
                    height: '12px',
                    background: 'rgba(255,255,255,0.05)',
                    borderRadius: '2px',
                    overflow: 'hidden',
                  }}>
                    <div style={{
                      width: `${(cls.count / maxClassCount) * 100}%`,
                      height: '100%',
                      background: getClassColor(cls.wh_class),
                      opacity: 0.7,
                    }} />
                  </div>
                  <span style={{
                    fontSize: fontSize.micro,
                    color: 'rgba(255,255,255,0.6)',
                    fontFamily: 'monospace',
                    minWidth: '20px',
                    textAlign: 'right',
                  }}>
                    {cls.count}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* VISITORS/THREATS TO CONTROLLED SPACE */}
          <div style={{
            background: 'rgba(0,0,0,0.3)',
            borderRadius: '6px',
            border: '1px solid rgba(255,255,255,0.08)',
            overflow: 'hidden',
            flex: 1,
          }}>
            <div style={{
              padding: '0.4rem 0.5rem',
              borderBottom: '1px solid rgba(255,255,255,0.08)',
              display: 'flex',
              alignItems: 'center',
              gap: spacing.sm,
            }}>
              <span style={{ width: 6, height: 6, borderRadius: '50%', background: color.brightOrange }} />
              <span style={{ fontSize: fontSize.xxs, fontWeight: 700, color: color.brightOrange, textTransform: 'uppercase' }}>
                Visitors in Territory
              </span>
            </div>
            <div style={{ padding: spacing.xs, maxHeight: '180px', overflowY: 'auto' }}>
              {visitors.length > 0 ? visitors.map((visitor) => (
                <div key={visitor.alliance_id} style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: spacing.md,
                  padding: '0.3rem 0.4rem',
                  marginBottom: '0.1rem',
                  background: `${THREAT_COLORS[visitor.threat_level]}11`,
                  borderRadius: '3px',
                  borderLeft: `2px solid ${THREAT_COLORS[visitor.threat_level]}`,
                }}>
                  <img
                    src={`https://images.evetech.net/alliances/${visitor.alliance_id}/logo?size=32`}
                    alt=""
                    style={{ width: 18, height: 18, borderRadius: '2px' }}
                    onError={(e) => { e.currentTarget.style.display = 'none'; }}
                  />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: fontSize.tiny, color: '#fff', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {visitor.alliance_name}
                    </div>
                    <div style={{ fontSize: fontSize.pico, color: 'rgba(255,255,255,0.4)' }}>
                      {visitor.systems_visited} system{visitor.systems_visited !== 1 ? 's' : ''} • {formatTimeAgo(visitor.last_seen)}
                    </div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <span style={{ fontSize: fontSize.nano, color: THREAT_COLORS[visitor.threat_level], fontWeight: 600 }}>
                      {visitor.kills_in_our_space} kills
                    </span>
                  </div>
                </div>
              )) : (
                <div style={{ padding: spacing.base, color: 'rgba(255,255,255,0.3)', fontSize: fontSize.tiny }}>
                  No visitors detected
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* ROW 2: Recent Threats in Controlled Space */}
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
          alignItems: 'center',
          gap: spacing.sm,
        }}>
          <span style={{ width: 6, height: 6, borderRadius: '50%', background: color.lossRed }} />
          <span style={{ fontSize: fontSize.xxs, fontWeight: 700, color: color.lossRed, textTransform: 'uppercase' }}>
            Recent Losses in Territory
          </span>
          <span style={{ fontSize: fontSize.micro, color: 'rgba(255,255,255,0.4)', marginLeft: 'auto' }}>
            hostile activity
          </span>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: spacing.xs, padding: spacing.xs, maxHeight: '200px', overflowY: 'auto' }}>
          {threats.length > 0 ? threats.map((threat) => (
            <a
              key={threat.killmail_id}
              href={`https://zkillboard.com/kill/${threat.killmail_id}/`}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: spacing.md,
                padding: '0.35rem 0.4rem',
                background: 'rgba(248,81,73,0.08)',
                borderRadius: '3px',
                borderLeft: '2px solid #f85149',
                textDecoration: 'none',
              }}
            >
              <img
                src={`https://images.evetech.net/types/${threat.ship_type_id}/icon?size=32`}
                alt=""
                style={{ width: 24, height: 24, borderRadius: '2px' }}
                onError={(e) => { e.currentTarget.style.display = 'none'; }}
              />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: fontSize.tiny, color: '#fff', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {threat.ship_name}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: spacing.sm, fontSize: fontSize.nano }}>
                  <span style={{ color: 'rgba(255,255,255,0.4)' }}>{threat.system_name}</span>
                  <span style={{ color: 'rgba(255,255,255,0.3)' }}>by</span>
                  <span style={{ color: color.brightOrange, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {threat.attacker_alliance_name}
                  </span>
                </div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{
                  fontSize: fontSize.micro,
                  fontWeight: 600,
                  color: color.lossRed,
                  fontFamily: 'monospace',
                }}>
                  {formatISKCompact(threat.value)}
                </div>
                <div style={{ fontSize: fontSize.pico, color: 'rgba(255,255,255,0.4)' }}>
                  {formatTimeAgo(threat.time)}
                </div>
              </div>
            </a>
          )) : (
            <div style={{ padding: spacing.base, color: 'rgba(255,255,255,0.3)', fontSize: fontSize.tiny, gridColumn: '1 / -1' }}>
              No recent losses in controlled territory
            </div>
          )}
        </div>
      </div>

      {/* SOV THREATS SECTION - WH activity in alliance's sovereignty space */}
      {sovThreatsLoading && (
        <div className="skeleton" style={{ height: '200px', borderRadius: '6px' }} />
      )}

      {sovThreats?.has_sovereignty && sovThreats.data && (
        <div style={{
          background: 'rgba(0,0,0,0.3)',
          borderRadius: '6px',
          border: '1px solid rgba(255,255,255,0.08)',
          borderLeft: `3px solid ${THREAT_LEVEL_COLORS[sovThreats.data.summary.overall_threat_level]}`,
          overflow: 'hidden',
        }}>
          {/* SOV Threats Header */}
          <div style={{
            padding: '0.5rem 0.75rem',
            borderBottom: '1px solid rgba(255,255,255,0.08)',
            display: 'flex',
            alignItems: 'center',
            gap: spacing.base,
          }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: THREAT_LEVEL_COLORS[sovThreats.data.summary.overall_threat_level] }} />
            <span style={{ fontSize: fontSize.xs, fontWeight: 700, color: THREAT_LEVEL_COLORS[sovThreats.data.summary.overall_threat_level], textTransform: 'uppercase' }}>
              WH Threats to SOV Space
            </span>
            <span style={{
              fontSize: fontSize.nano,
              fontWeight: 700,
              padding: '2px 6px',
              borderRadius: '3px',
              background: `${THREAT_LEVEL_COLORS[sovThreats.data.summary.overall_threat_level]}33`,
              color: THREAT_LEVEL_COLORS[sovThreats.data.summary.overall_threat_level],
            }}>
              {sovThreats.data.summary.overall_threat_level}
            </span>
            <span style={{ fontSize: fontSize.nano, color: 'rgba(255,255,255,0.4)', marginLeft: 'auto' }}>
              {sovThreats.data.period_days}d analysis
            </span>
          </div>

          {/* SOV Threats Stats Row */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(6, 1fr)',
            gap: spacing.base,
            padding: '0.5rem 0.75rem',
            borderBottom: '1px solid rgba(255,255,255,0.05)',
            background: 'rgba(0,0,0,0.2)',
          }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: fontSize.lg, fontWeight: 700, color: '#fff', fontFamily: 'monospace' }}>
                {sovThreats.data.summary.total_wh_systems.toLocaleString()}
              </div>
              <div style={{ fontSize: fontSize.pico, color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase' }}>WH Systems</div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: fontSize.lg, fontWeight: 700, color: color.lossRed, fontFamily: 'monospace' }}>
                {sovThreats.data.summary.total_kills.toLocaleString()}
              </div>
              <div style={{ fontSize: fontSize.pico, color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase' }}>WH Kills in SOV</div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: fontSize.lg, fontWeight: 700, color: color.warningYellow, fontFamily: 'monospace' }}>
                {formatISKCompact(sovThreats.data.summary.total_isk_destroyed)}
              </div>
              <div style={{ fontSize: fontSize.pico, color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase' }}>ISK Destroyed</div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: fontSize.lg, fontWeight: 700, color: color.pureRed, fontFamily: 'monospace' }}>
                {sovThreats.data.summary.threat_breakdown.critical}
              </div>
              <div style={{ fontSize: fontSize.pico, color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase' }}>CRITICAL WHs</div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: fontSize.lg, fontWeight: 700, color: color.brightOrange, fontFamily: 'monospace' }}>
                {sovThreats.data.summary.threat_breakdown.high}
              </div>
              <div style={{ fontSize: fontSize.pico, color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase' }}>HIGH WHs</div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: fontSize.lg, fontWeight: 700, color: color.warningYellow, fontFamily: 'monospace' }}>
                {sovThreats.data.summary.threat_breakdown.moderate}
              </div>
              <div style={{ fontSize: fontSize.pico, color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase' }}>MODERATE WHs</div>
            </div>
          </div>

          {/* SOV Threats Content - 3 columns */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: spacing.base, padding: spacing.base }}>
            {/* Top Attackers */}
            <div style={{
              background: 'rgba(255,255,255,0.02)',
              borderRadius: '4px',
              padding: spacing.md,
            }}>
              <div style={{ fontSize: fontSize.micro, fontWeight: 700, color: color.lossRed, textTransform: 'uppercase', marginBottom: spacing.md }}>
                🎯 Top WH Attackers
              </div>
              {sovThreats.data.top_attackers.slice(0, 5).map((attacker) => (
                <div key={attacker.alliance_id} style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: spacing.sm,
                  padding: spacing.xs,
                  marginBottom: '0.2rem',
                  background: 'rgba(248,81,73,0.08)',
                  borderRadius: '3px',
                }}>
                  <img
                    src={`https://images.evetech.net/alliances/${attacker.alliance_id}/logo?size=32`}
                    alt=""
                    style={{ width: 18, height: 18, borderRadius: '2px' }}
                    onError={(e) => { e.currentTarget.style.display = 'none'; }}
                  />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: fontSize.micro, color: '#fff', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {attacker.alliance_name}
                    </div>
                    <div style={{ fontSize: fontSize.pico, color: 'rgba(255,255,255,0.4)' }}>
                      {attacker.wh_systems} WH systems
                    </div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: fontSize.nano, fontWeight: 600, color: color.lossRed, fontFamily: 'monospace' }}>
                      {attacker.kills.toLocaleString()}
                    </div>
                    <div style={{ fontSize: fontSize.pico, color: 'rgba(255,255,255,0.4)' }}>kills</div>
                  </div>
                </div>
              ))}
            </div>

            {/* Top Regions Hit */}
            <div style={{
              background: 'rgba(255,255,255,0.02)',
              borderRadius: '4px',
              padding: spacing.md,
            }}>
              <div style={{ fontSize: fontSize.micro, fontWeight: 700, color: color.accentPurple, textTransform: 'uppercase', marginBottom: spacing.md }}>
                🗺️ Regions Hit
              </div>
              {sovThreats.data.top_regions.slice(0, 5).map((region, idx) => (
                <div key={region.region} style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: spacing.sm,
                  padding: spacing.xs,
                  marginBottom: '0.2rem',
                  background: 'rgba(168,85,247,0.08)',
                  borderRadius: '3px',
                }}>
                  <span style={{
                    fontSize: fontSize.nano,
                    fontWeight: 700,
                    color: color.accentPurple,
                    width: '16px',
                  }}>
                    #{idx + 1}
                  </span>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: fontSize.micro, color: '#fff', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {region.region}
                    </div>
                    <div style={{ fontSize: fontSize.pico, color: 'rgba(255,255,255,0.4)' }}>
                      {region.systems_hit} systems
                    </div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: fontSize.nano, fontWeight: 600, color: color.accentPurple, fontFamily: 'monospace' }}>
                      {region.kills.toLocaleString()}
                    </div>
                    <div style={{ fontSize: fontSize.pico, color: 'rgba(255,255,255,0.4)' }}>kills</div>
                  </div>
                </div>
              ))}
            </div>

            {/* Timezone + Doctrines */}
            <div style={{
              background: 'rgba(255,255,255,0.02)',
              borderRadius: '4px',
              padding: spacing.md,
              display: 'flex',
              flexDirection: 'column',
              gap: spacing.base,
            }}>
              {/* Timezone Distribution */}
              <div>
                <div style={{ fontSize: fontSize.micro, fontWeight: 700, color: color.linkBlue, textTransform: 'uppercase', marginBottom: spacing.sm }}>
                  🕐 Attack Timezones
                </div>
                <div style={{ display: 'flex', height: '20px', borderRadius: '3px', overflow: 'hidden', background: 'rgba(0,0,0,0.3)' }}>
                  <div style={{ width: `${sovThreats.data.timezone_distribution.us_prime_pct}%`, background: color.linkBlue, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    {sovThreats.data.timezone_distribution.us_prime_pct >= 15 && (
                      <span style={{ fontSize: fontSize.pico, fontWeight: 600, color: '#fff' }}>US {sovThreats.data.timezone_distribution.us_prime_pct.toFixed(0)}%</span>
                    )}
                  </div>
                  <div style={{ width: `${sovThreats.data.timezone_distribution.eu_prime_pct}%`, background: color.killGreen, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    {sovThreats.data.timezone_distribution.eu_prime_pct >= 15 && (
                      <span style={{ fontSize: fontSize.pico, fontWeight: 600, color: '#fff' }}>EU {sovThreats.data.timezone_distribution.eu_prime_pct.toFixed(0)}%</span>
                    )}
                  </div>
                  <div style={{ width: `${sovThreats.data.timezone_distribution.au_prime_pct}%`, background: color.warningYellow, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    {sovThreats.data.timezone_distribution.au_prime_pct >= 15 && (
                      <span style={{ fontSize: fontSize.pico, fontWeight: 600, color: '#000' }}>AU {sovThreats.data.timezone_distribution.au_prime_pct.toFixed(0)}%</span>
                    )}
                  </div>
                </div>
              </div>

              {/* Top Doctrines Used */}
              <div>
                <div style={{ fontSize: fontSize.micro, fontWeight: 700, color: color.brightOrange, textTransform: 'uppercase', marginBottom: spacing.sm }}>
                  ⚔️ Attacker Doctrines
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.2rem' }}>
                  {sovThreats.data.attacker_doctrines.slice(0, 6).map((doctrine) => (
                    <span key={doctrine.ship_class} style={{
                      fontSize: fontSize.pico,
                      padding: '2px 5px',
                      background: 'rgba(255,102,0,0.15)',
                      borderRadius: '2px',
                      color: color.brightOrange,
                    }}>
                      {doctrine.ship_class} ({doctrine.uses.toLocaleString()})
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Top Threatening WH Systems */}
          {sovThreats.data.top_wh_systems.length > 0 && (
            <div style={{ padding: spacing.base, borderTop: '1px solid rgba(255,255,255,0.05)' }}>
              <div style={{ fontSize: fontSize.micro, fontWeight: 700, color: color.lossRed, textTransform: 'uppercase', marginBottom: spacing.md }}>
                🔴 Most Dangerous WH Systems (by kills in your SOV)
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: spacing.xs }}>
                {sovThreats.data.top_wh_systems.slice(0, 8).map((sys) => (
                  <div key={sys.system_id} style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: spacing.sm,
                    padding: '0.3rem 0.4rem',
                    background: 'rgba(248,81,73,0.08)',
                    borderRadius: '3px',
                    borderLeft: '2px solid #f85149',
                  }}>
                    <span style={{ fontSize: fontSize.tiny, fontWeight: 600, color: '#fff' }}>
                      {sys.system_name}
                    </span>
                    <span style={{ flex: 1 }} />
                    <span style={{ fontSize: fontSize.nano, color: 'rgba(255,255,255,0.4)' }}>
                      {sys.sov_systems_hit} systems hit
                    </span>
                    <span style={{ fontSize: fontSize.nano, fontWeight: 600, color: color.lossRed, fontFamily: 'monospace' }}>
                      {sys.kills.toLocaleString()} kills
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
