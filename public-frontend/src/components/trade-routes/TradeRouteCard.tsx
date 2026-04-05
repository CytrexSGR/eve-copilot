import { getSecurityColor } from '../../utils/security';
import type { RouteSystem } from './types';
import { TIME_PERIODS, getDangerLevel } from './types';

interface Route {
  origin_system: string;
  destination_system: string;
  jumps: number;
  total_kills: number;
  total_isk_destroyed: number;
  danger_score: number;
  systems: RouteSystem[];
}

interface TradeRouteCardProps {
  route: Route;
  isExpanded: boolean;
  onToggle: () => void;
  onSystemHover: (e: React.MouseEvent, system: RouteSystem) => void;
  onSystemLeave: () => void;
  onBattleClick: (battleId: number) => void;
  selectedMinutes: number;
}

export function TradeRouteCard({
  route,
  isExpanded,
  onToggle,
  onSystemHover,
  onSystemLeave,
  onBattleClick,
  selectedMinutes
}: TradeRouteCardProps) {
  const danger = getDangerLevel(route.danger_score);
  const dangerPct = Math.min((route.danger_score / 10) * 100, 100);
  const iskB = (route.total_isk_destroyed || 0) / 1_000_000_000;
  const gateCampSystems = route.systems?.filter(s => s.is_gate_camp) || [];

  return (
    <div
      style={{
        background: 'linear-gradient(135deg, rgba(15,20,30,0.95) 0%, rgba(20,25,35,0.9) 100%)',
        borderRadius: '12px',
        border: `1px solid ${danger.color}33`,
        overflow: 'hidden'
      }}
    >
      {/* Danger bar */}
      <div style={{
        height: '4px',
        background: 'rgba(255,255,255,0.05)'
      }}>
        <div style={{
          height: '100%',
          width: `${dangerPct}%`,
          background: `linear-gradient(90deg, ${danger.color}88, ${danger.color})`,
          transition: 'width 0.3s'
        }} />
      </div>

      {/* Route Header - Clickable */}
      <div
        onClick={onToggle}
        style={{
          padding: '1.25rem 1.5rem',
          cursor: 'pointer',
          transition: 'background 0.2s'
        }}
        onMouseOver={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.02)'; }}
        onMouseOut={(e) => { e.currentTarget.style.background = 'transparent'; }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div style={{ flex: 1 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '0.5rem' }}>
              <h2 style={{
                margin: 0,
                fontSize: '1.25rem',
                fontWeight: 700,
                color: '#fff'
              }}>
                {route.origin_system}
                <span style={{ color: 'rgba(255,255,255,0.3)', margin: '0 0.75rem' }}>-&gt;</span>
                {route.destination_system}
              </h2>
              <span style={{
                padding: '0.25rem 0.75rem',
                background: `${danger.color}22`,
                border: `1px solid ${danger.color}44`,
                borderRadius: '4px',
                fontWeight: 700,
                fontSize: '0.7rem',
                color: danger.color,
                textTransform: 'uppercase'
              }}>
                {danger.label}
              </span>
            </div>

            {/* Quick Stats */}
            <div style={{ display: 'flex', gap: '1.5rem', fontSize: '0.8rem' }}>
              <span style={{ color: 'rgba(255,255,255,0.5)' }}>
                <span style={{ color: '#00d4ff', fontWeight: 600 }}>{route.jumps}</span> jumps
              </span>
              <span style={{ color: 'rgba(255,255,255,0.5)' }}>
                <span style={{ color: '#ff4444', fontWeight: 600 }}>{route.total_kills}</span> kills
              </span>
              <span style={{ color: 'rgba(255,255,255,0.5)' }}>
                <span style={{ color: '#ffcc00', fontWeight: 600 }}>{iskB.toFixed(1)}B</span> destroyed
              </span>
              {gateCampSystems.length > 0 && (
                <span style={{ color: 'rgba(255,255,255,0.5)' }}>
                  <span style={{ color: '#ff8800', fontWeight: 600 }}>{gateCampSystems.length}</span> gate camp{gateCampSystems.length > 1 ? 's' : ''}
                </span>
              )}
            </div>
          </div>

          {/* Expand indicator */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            color: 'rgba(255,255,255,0.4)',
            fontSize: '0.75rem'
          }}>
            <span>{isExpanded ? 'Hide Details' : 'Show Details'}</span>
            <span style={{
              transform: isExpanded ? 'rotate(180deg)' : 'rotate(0deg)',
              transition: 'transform 0.2s'
            }}>&#x25BC;</span>
          </div>
        </div>

        {/* Gate Camp Warning */}
        {gateCampSystems.length > 0 && (
          <div style={{
            marginTop: '0.75rem',
            padding: '0.5rem 0.75rem',
            background: 'rgba(255, 136, 0, 0.15)',
            borderRadius: '6px',
            border: '1px solid rgba(255, 136, 0, 0.25)',
            fontSize: '0.8rem'
          }}>
            <span style={{ color: '#ff8800', fontWeight: 600 }}>Warning: Active Gate Camp{gateCampSystems.length > 1 ? 's' : ''}:</span>
            <span style={{ color: 'rgba(255,255,255,0.8)', marginLeft: '0.5rem' }}>
              {gateCampSystems.map(s => s.system_name).join(', ')}
            </span>
          </div>
        )}
      </div>

      {/* Expanded Content */}
      {isExpanded && (
        <div style={{
          padding: '0 1.5rem 1.5rem',
          borderTop: '1px solid rgba(255,255,255,0.05)'
        }}>
          {/* System Chain - Horizontal */}
          <div style={{ marginTop: '1rem' }}>
            <h3 style={{
              fontSize: '0.8rem',
              fontWeight: 700,
              color: 'rgba(255,255,255,0.5)',
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              marginBottom: '0.75rem'
            }}>
              Route Path
            </h3>

            <div style={{
              display: 'flex',
              flexWrap: 'wrap',
              alignItems: 'center',
              gap: '0.25rem',
              padding: '0.75rem',
              background: 'rgba(0,0,0,0.3)',
              borderRadius: '8px'
            }}>
              {route.systems.map((system, idx) => {
                const isHot = system.kills_24h > 5 || system.is_gate_camp;
                const hasBattle = !!system.battle_id;

                return (
                  <div key={system.system_id} style={{ display: 'flex', alignItems: 'center' }}>
                    {/* System chip */}
                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.35rem',
                        padding: '0.35rem 0.6rem',
                        background: system.is_gate_camp
                          ? 'rgba(255, 136, 0, 0.2)'
                          : isHot
                            ? 'rgba(255, 68, 68, 0.15)'
                            : 'rgba(255,255,255,0.05)',
                        borderRadius: '4px',
                        border: hasBattle
                          ? '1px solid rgba(0, 212, 255, 0.5)'
                          : system.is_gate_camp
                            ? '1px solid rgba(255, 136, 0, 0.4)'
                            : isHot
                              ? '1px solid rgba(255, 68, 68, 0.3)'
                              : '1px solid rgba(255,255,255,0.1)',
                        cursor: hasBattle ? 'pointer' : 'default',
                        transition: 'all 0.15s',
                        boxShadow: hasBattle ? '0 0 8px rgba(0, 212, 255, 0.3)' : 'none'
                      }}
                      onMouseEnter={(e) => onSystemHover(e, system)}
                      onMouseLeave={onSystemLeave}
                      onClick={() => {
                        if (hasBattle && system.battle_id) {
                          onBattleClick(system.battle_id);
                        }
                      }}
                    >
                      {/* Battle indicator */}
                      {hasBattle && (
                        <span style={{ fontSize: '0.65rem', color: '#00d4ff' }}>Battle</span>
                      )}
                      {/* Gate camp icon */}
                      {system.is_gate_camp && !hasBattle && (
                        <span style={{ fontSize: '0.7rem' }}>Camp</span>
                      )}
                      {/* System name */}
                      <span style={{
                        fontSize: '0.75rem',
                        fontWeight: system.is_gate_camp || isHot || hasBattle ? 600 : 400,
                        color: hasBattle
                          ? '#00d4ff'
                          : system.is_gate_camp
                            ? '#ff8800'
                            : isHot
                              ? '#ff4444'
                              : '#fff'
                      }}>
                        {system.system_name}
                      </span>
                      {/* Security badge */}
                      <span style={{
                        fontSize: '0.6rem',
                        fontWeight: 700,
                        color: getSecurityColor(system.security_status),
                        opacity: 0.8
                      }}>
                        {system.security_status.toFixed(1)}
                      </span>
                      {/* Kill count if notable */}
                      {system.kills_24h > 0 && (
                        <span style={{
                          fontSize: '0.6rem',
                          color: hasBattle ? '#00d4ff' : '#ff4444',
                          fontFamily: 'monospace'
                        }}>
                          {system.kills_24h}
                        </span>
                      )}
                    </div>
                    {/* Arrow between systems */}
                    {idx < route.systems.length - 1 && (
                      <span style={{
                        color: 'rgba(255,255,255,0.2)',
                        fontSize: '0.7rem',
                        margin: '0 0.15rem'
                      }}>-&gt;</span>
                    )}
                  </div>
                );
              })}
            </div>

            {/* Legend */}
            <div style={{
              display: 'flex',
              gap: '1.5rem',
              marginTop: '0.5rem',
              fontSize: '0.65rem',
              color: 'rgba(255,255,255,0.4)'
            }}>
              <span>
                <span style={{
                  display: 'inline-block',
                  width: '8px',
                  height: '8px',
                  background: 'rgba(255, 136, 0, 0.4)',
                  borderRadius: '2px',
                  marginRight: '0.3rem'
                }} />
                Gate Camp
              </span>
              <span>
                <span style={{
                  display: 'inline-block',
                  width: '8px',
                  height: '8px',
                  background: 'rgba(255, 68, 68, 0.3)',
                  borderRadius: '2px',
                  marginRight: '0.3rem'
                }} />
                Hot (5+ kills)
              </span>
              <span>
                <span style={{
                  display: 'inline-block',
                  width: '8px',
                  height: '8px',
                  background: 'rgba(0, 212, 255, 0.5)',
                  borderRadius: '2px',
                  marginRight: '0.3rem',
                  boxShadow: '0 0 4px rgba(0, 212, 255, 0.5)'
                }} />
                Battle (click for details)
              </span>
              <span>Numbers = kills ({TIME_PERIODS.find(p => p.value === selectedMinutes)?.label || '24h'})</span>
            </div>
          </div>

          {/* Recommendations */}
          <div style={{
            marginTop: '1rem',
            padding: '1rem',
            background: `${danger.color}11`,
            borderRadius: '8px',
            border: `1px solid ${danger.color}22`
          }}>
            <h4 style={{
              fontSize: '0.75rem',
              fontWeight: 700,
              color: danger.color,
              textTransform: 'uppercase',
              marginBottom: '0.5rem'
            }}>
              Recommendations
            </h4>
            {route.danger_score >= 7 ? (
              <div style={{ fontSize: '0.8rem', color: 'rgba(255,255,255,0.7)', lineHeight: 1.6 }}>
                <p style={{ marginBottom: '0.5rem' }}>
                  <strong>EXTREME DANGER</strong> - This route is extremely hazardous:
                </p>
                <ul style={{ marginLeft: '1.25rem', marginBottom: 0 }}>
                  <li>Use Deep Space Transport or tanked hauler</li>
                  <li>Scout ahead with an alt</li>
                  <li>Avoid carrying high-value cargo</li>
                  <li>Consider escort fleet</li>
                </ul>
              </div>
            ) : route.danger_score >= 4 ? (
              <div style={{ fontSize: '0.8rem', color: 'rgba(255,255,255,0.7)', lineHeight: 1.6 }}>
                <p style={{ marginBottom: '0.5rem' }}>
                  <strong>HIGH RISK</strong> - Exercise caution:
                </p>
                <ul style={{ marginLeft: '1.25rem', marginBottom: 0 }}>
                  <li>Avoid fragile ships with valuable cargo</li>
                  <li>Monitor local and intel channels</li>
                  <li>Consider alternative routes</li>
                </ul>
              </div>
            ) : route.danger_score >= 2 ? (
              <div style={{ fontSize: '0.8rem', color: 'rgba(255,255,255,0.7)', lineHeight: 1.6 }}>
                <p>
                  <strong>MODERATE ACTIVITY</strong> - Standard precautions apply. Watch for unusual activity spikes.
                </p>
              </div>
            ) : (
              <div style={{ fontSize: '0.8rem', color: 'rgba(255,255,255,0.7)', lineHeight: 1.6 }}>
                <p>
                  <strong>RELATIVELY SAFE</strong> - Low combat activity detected. Standard autopilot precautions apply.
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
