import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { reportsApi } from '../../services/api';
import type { TimePeriodValue } from '../trade-routes';
import type { TradeRoutes } from '../../types/reports';

interface RoutesTabProps {
  selectedMinutes: TimePeriodValue;
  onTimeChange: (minutes: TimePeriodValue) => void;
}

type TradeRoute = TradeRoutes['routes'][0];

const DANGER_CONFIG = {
  critical: { color: '#ff4444', bg: 'rgba(255,68,68,0.15)', label: 'CRITICAL' },
  high: { color: '#ff8800', bg: 'rgba(255,136,0,0.12)', label: 'HIGH' },
  moderate: { color: '#ffcc00', bg: 'rgba(255,204,0,0.1)', label: 'MODERATE' },
  safe: { color: '#00ff88', bg: 'rgba(0,255,136,0.08)', label: 'SAFE' },
};

function getDangerLevel(score: number): keyof typeof DANGER_CONFIG {
  if (score >= 7) return 'critical';
  if (score >= 4) return 'high';
  if (score >= 2) return 'moderate';
  return 'safe';
}

function formatISK(value: number): string {
  if (value >= 1e12) return `${(value / 1e12).toFixed(1)}T`;
  if (value >= 1e9) return `${(value / 1e9).toFixed(1)}B`;
  if (value >= 1e6) return `${(value / 1e6).toFixed(0)}M`;
  return value.toLocaleString();
}

export function RoutesTab({ selectedMinutes, onTimeChange: _onTimeChange }: RoutesTabProps) {
  const navigate = useNavigate();
  const [expandedRoute, setExpandedRoute] = useState<string | null>(null);

  const { data: report, isLoading } = useQuery({
    queryKey: ['tradeRoutes', selectedMinutes],
    queryFn: () => reportsApi.getTradeRoutes(selectedMinutes),
    staleTime: 60000,
    refetchInterval: 60000
  });

  const routes = report?.routes || [];

  const handleRouteClick = (route: TradeRoute) => {
    const key = `${route.origin_system}-${route.destination_system}`;
    setExpandedRoute(expandedRoute === key ? null : key);
  };

  const handleSystemClick = (system: TradeRoute['systems'][0]) => {
    if (system.battle_id) {
      navigate(`/battle/${system.battle_id}`);
    } else {
      navigate(`/system/${system.system_id}?minutes=${selectedMinutes}`);
    }
  };

  return (
    <>
      {/* TRADE ROUTE INTELLIGENCE */}
      <div style={{
        background: 'rgba(0,0,0,0.3)',
        borderRadius: '8px',
        border: '1px solid rgba(255,255,255,0.08)',
        marginBottom: '0.75rem'
      }}>
        {/* Header with inline stats */}
        <div style={{
          padding: '0.4rem 0.5rem',
          borderBottom: '1px solid rgba(255,255,255,0.08)',
          display: 'flex',
          alignItems: 'center',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ fontSize: '0.65rem' }}>🛣️</span>
            <span style={{ fontSize: '0.7rem', fontWeight: 700, color: '#00d4ff', textTransform: 'uppercase' }}>
              Trade Routes
            </span>
            {/* Inline Stats */}
            {report && (
              <div style={{ display: 'flex', gap: '0.75rem', marginLeft: '0.5rem', fontSize: '0.6rem' }}>
                <span><span style={{ color: '#00d4ff', fontWeight: 700 }}>{report.global.total_routes}</span> <span style={{ color: 'rgba(255,255,255,0.4)' }}>routes</span></span>
                <span><span style={{ color: '#ff4444', fontWeight: 700 }}>{report.global.dangerous_routes}</span> <span style={{ color: 'rgba(255,255,255,0.4)' }}>danger</span></span>
                <span><span style={{ color: '#ff8800', fontWeight: 700 }}>{report.global.gate_camps_detected}</span> <span style={{ color: 'rgba(255,255,255,0.4)' }}>camps</span></span>
                <span><span style={{ color: '#ffcc00', fontWeight: 700 }}>{report.global.avg_danger_score.toFixed(1)}</span> <span style={{ color: 'rgba(255,255,255,0.4)' }}>avg</span></span>
              </div>
            )}
          </div>
        </div>

        {/* Routes List */}
        <div style={{ padding: '0.4rem' }}>
          {isLoading ? (
            <div style={{ padding: '0.75rem', textAlign: 'center', color: 'rgba(255,255,255,0.3)', fontSize: '0.7rem' }}>
              Loading routes...
            </div>
          ) : routes.length === 0 ? (
            <div style={{ padding: '0.75rem', textAlign: 'center', color: 'rgba(255,255,255,0.3)', fontSize: '0.7rem' }}>
              No trade route data available
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
              {routes.map((route, idx) => {
                const level = getDangerLevel(route.danger_score);
                const config = DANGER_CONFIG[level];
                const gateCamps = route.systems?.filter(s => s.is_gate_camp).length || 0;
                const routeKey = `${route.origin_system}-${route.destination_system}`;
                const isExpanded = expandedRoute === routeKey;

                return (
                  <div key={idx}>
                    {/* Route Row */}
                    <div
                      onClick={() => handleRouteClick(route)}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.5rem',
                        padding: '0.4rem 0.5rem',
                        background: config.bg,
                        borderRadius: '4px',
                        borderLeft: `2px solid ${config.color}`,
                        cursor: 'pointer',
                        transition: 'all 0.15s ease',
                      }}
                      onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.08)'; }}
                      onMouseLeave={(e) => { e.currentTarget.style.background = config.bg; }}
                    >
                      {/* Danger Badge */}
                      <div style={{ display: 'flex', alignItems: 'center', gap: '3px', minWidth: '70px' }}>
                        <span style={{ width: '5px', height: '5px', borderRadius: '50%', background: config.color }} />
                        <span style={{ fontSize: '0.6rem', fontWeight: 700, color: config.color }}>
                          {config.label}
                        </span>
                      </div>

                      {/* Route */}
                      <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: '0.35rem', minWidth: 0 }}>
                        <span style={{ fontWeight: 700, fontSize: '0.7rem', color: '#fff' }}>{route.origin_system}</span>
                        <span style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.35)' }}>→</span>
                        <span style={{ fontWeight: 700, fontSize: '0.7rem', color: '#fff' }}>{route.destination_system}</span>
                        <span style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.35)' }}>{route.jumps}j</span>
                      </div>

                      {/* Stats */}
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <span style={{ fontSize: '0.85rem', fontWeight: 700, fontFamily: 'monospace', color: config.color }}>
                          {route.total_kills}
                        </span>
                        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', lineHeight: 1.1 }}>
                          <span style={{ fontSize: '0.6rem', color: '#ffcc00', fontFamily: 'monospace' }}>
                            {formatISK(route.total_isk_destroyed)}
                          </span>
                          {gateCamps > 0 && (
                            <span style={{ fontSize: '0.5rem', color: '#ff8800', fontWeight: 600 }}>
                              {gateCamps} camp{gateCamps > 1 ? 's' : ''}
                            </span>
                          )}
                        </div>
                        {/* Danger bar */}
                        <div style={{ width: '30px', height: '4px', background: 'rgba(255,255,255,0.1)', borderRadius: '2px', overflow: 'hidden' }}>
                          <div style={{ width: `${Math.min(100, route.danger_score * 10)}%`, height: '100%', background: config.color, borderRadius: '2px' }} />
                        </div>
                        {/* Expand indicator */}
                        <span style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.4)', transform: isExpanded ? 'rotate(180deg)' : 'none', transition: 'transform 0.15s' }}>▼</span>
                      </div>
                    </div>

                    {/* Expanded: System Chain */}
                    {isExpanded && (
                      <div style={{
                        margin: '0.25rem 0 0.25rem 0.5rem',
                        padding: '0.5rem',
                        background: 'rgba(0,0,0,0.3)',
                        borderRadius: '4px',
                        borderLeft: `2px solid ${config.color}44`,
                      }}>
                        <div style={{ fontSize: '0.55rem', color: 'rgba(255,255,255,0.4)', marginBottom: '0.35rem', textTransform: 'uppercase' }}>
                          Route Path
                        </div>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.2rem', alignItems: 'center' }}>
                          {route.systems.map((system, sIdx) => {
                            const isHot = system.kills_24h > 5 || system.is_gate_camp;
                            const hasBattle = !!system.battle_id;
                            return (
                              <div key={system.system_id} style={{ display: 'flex', alignItems: 'center' }}>
                                <div
                                  onClick={(e) => { e.stopPropagation(); handleSystemClick(system); }}
                                  style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '0.2rem',
                                    padding: '0.2rem 0.35rem',
                                    background: system.is_gate_camp ? 'rgba(255,136,0,0.2)' : isHot ? 'rgba(255,68,68,0.15)' : 'rgba(255,255,255,0.05)',
                                    borderRadius: '3px',
                                    border: hasBattle ? '1px solid rgba(0,212,255,0.5)' : system.is_gate_camp ? '1px solid rgba(255,136,0,0.4)' : '1px solid rgba(255,255,255,0.1)',
                                    cursor: 'pointer',
                                    fontSize: '0.6rem',
                                  }}
                                >
                                  {hasBattle && <span style={{ color: '#00d4ff', fontSize: '0.5rem' }}>⚔</span>}
                                  {system.is_gate_camp && !hasBattle && <span style={{ color: '#ff8800', fontSize: '0.5rem' }}>⚠</span>}
                                  <span style={{
                                    fontWeight: isHot || hasBattle ? 600 : 400,
                                    color: hasBattle ? '#00d4ff' : system.is_gate_camp ? '#ff8800' : isHot ? '#ff4444' : '#fff'
                                  }}>
                                    {system.system_name}
                                  </span>
                                  <span style={{ color: getSecurityColor(system.security_status), fontSize: '0.5rem', fontWeight: 700 }}>
                                    {system.security_status.toFixed(1)}
                                  </span>
                                  {system.kills_24h > 0 && (
                                    <span style={{ color: hasBattle ? '#00d4ff' : '#ff4444', fontFamily: 'monospace', fontSize: '0.5rem' }}>
                                      {system.kills_24h}
                                    </span>
                                  )}
                                </div>
                                {sIdx < route.systems.length - 1 && (
                                  <span style={{ color: 'rgba(255,255,255,0.2)', fontSize: '0.5rem', margin: '0 0.1rem' }}>→</span>
                                )}
                              </div>
                            );
                          })}
                        </div>
                        {/* Legend */}
                        <div style={{ display: 'flex', gap: '1rem', marginTop: '0.35rem', fontSize: '0.5rem', color: 'rgba(255,255,255,0.35)' }}>
                          <span><span style={{ display: 'inline-block', width: '6px', height: '6px', background: 'rgba(255,136,0,0.4)', borderRadius: '2px', marginRight: '0.2rem' }} />Camp</span>
                          <span><span style={{ display: 'inline-block', width: '6px', height: '6px', background: 'rgba(255,68,68,0.3)', borderRadius: '2px', marginRight: '0.2rem' }} />Hot</span>
                          <span><span style={{ display: 'inline-block', width: '6px', height: '6px', background: 'rgba(0,212,255,0.5)', borderRadius: '2px', marginRight: '0.2rem' }} />Battle</span>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

    </>
  );
}

function getSecurityColor(sec: number): string {
  if (sec >= 0.5) return '#00ff00';
  if (sec > 0) return '#ffff00';
  return '#ff4444';
}
