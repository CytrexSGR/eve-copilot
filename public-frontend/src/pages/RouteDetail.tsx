import { useState, useEffect, useMemo, useRef } from 'react';
import { useParams, useSearchParams, useNavigate } from 'react-router-dom';
import { reportsApi } from '../services/api';
import { getEctmapBaseUrl } from '../utils/format';

interface RouteSystem {
  system_id: number;
  system_name: string;
  security_status: number;
  danger_score: number;
  kills_24h: number;
  isk_destroyed_24h: number;
  is_gate_camp: boolean;
  battle_id?: number;
}

interface TradeRoute {
  origin_system: string;
  destination_system: string;
  jumps: number;
  danger_score: number;
  total_kills: number;
  total_isk_destroyed: number;
  systems: RouteSystem[];
}

// Threat config matching ActiveCombatZones style
const THREAT_CONFIG = {
  critical: { color: '#ff0000', bg: 'rgba(255,0,0,0.15)', pulse: true, label: 'CRITICAL' },
  danger: { color: '#ff4444', bg: 'rgba(255,68,68,0.12)', pulse: true, label: 'DANGER' },
  caution: { color: '#ffaa00', bg: 'rgba(255,170,0,0.1)', pulse: false, label: 'CAUTION' },
  clear: { color: '#00ff88', bg: 'rgba(0,255,136,0.08)', pulse: false, label: 'CLEAR' },
};

function formatISK(value: number): string {
  if (value >= 1e12) return `${(value / 1e12).toFixed(1)}T`;
  if (value >= 1e9) return `${(value / 1e9).toFixed(1)}B`;
  if (value >= 1e6) return `${(value / 1e6).toFixed(0)}M`;
  return value.toLocaleString();
}

function getSecurityColor(sec: number): string {
  if (sec >= 0.5) return '#00ff88';
  if (sec > 0) return '#ffcc00';
  return '#ff4444';
}

function calculateRouteDanger(route: TradeRoute): number {
  const maxSystemDanger = Math.max(...(route.systems?.map(s => s.danger_score) || [0]));
  const killsPerJump = route.total_kills / Math.max(1, route.jumps);
  const gateCamps = route.systems?.filter(s => s.is_gate_camp).length || 0;
  const killScore = Math.min(100, killsPerJump * 10);
  const gateCampBonus = gateCamps * 15;
  return Math.min(100, (maxSystemDanger * 0.4) + (killScore * 0.4) + gateCampBonus);
}

function getThreatLevel(score: number): keyof typeof THREAT_CONFIG {
  if (score >= 60) return 'critical';
  if (score >= 40) return 'danger';
  if (score >= 20) return 'caution';
  return 'clear';
}

function getSystemThreat(sys: RouteSystem): keyof typeof THREAT_CONFIG {
  if (sys.is_gate_camp) return 'critical';
  if (sys.kills_24h >= 10 || sys.danger_score >= 30) return 'danger';
  if (sys.kills_24h >= 3 || sys.danger_score >= 10) return 'caution';
  return 'clear';
}

export function RouteDetail() {
  const { origin, destination } = useParams<{ origin: string; destination: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const minutes = parseInt(searchParams.get('minutes') || '1440', 10);

  const [route, setRoute] = useState<TradeRoute | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedSystem, setSelectedSystem] = useState<RouteSystem | null>(null);
  const mapIframeRef = useRef<HTMLIFrameElement>(null);

  useEffect(() => {
    const fetchRoute = async () => {
      try {
        setLoading(true);
        const data = await reportsApi.getTradeRoutes(minutes);
        const found = data.routes?.find(
          r => r.origin_system.toUpperCase() === origin?.toUpperCase() &&
               r.destination_system.toUpperCase() === destination?.toUpperCase()
        );
        setRoute(found || null);
      } catch (err) {
        console.error('Failed to fetch route:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchRoute();
  }, [origin, destination, minutes]);

  // Send message to map iframe when a system is selected
  useEffect(() => {
    if (selectedSystem && mapIframeRef.current?.contentWindow) {
      mapIframeRef.current.contentWindow.postMessage(
        { type: 'ectmap-focus-system', systemId: selectedSystem.system_id },
        '*'
      );
    }
  }, [selectedSystem]);

  const threatInfo = useMemo(() => {
    if (!route) return THREAT_CONFIG.clear;
    return THREAT_CONFIG[getThreatLevel(calculateRouteDanger(route))];
  }, [route]);

  const gateCamps = route?.systems?.filter(s => s.is_gate_camp) || [];
  const hotspots = route?.systems?.filter(s => s.kills_24h >= 5) || [];
  const battlesOnRoute = route?.systems?.filter(s => s.battle_id) || [];
  const timeLabel = minutes >= 1440 ? `${Math.round(minutes / 1440)}d` : `${Math.round(minutes / 60)}h`;

  if (loading) {
    return (
      <div style={{ padding: '1rem' }}>
        <div className="skeleton" style={{ height: '60px', borderRadius: '8px', marginBottom: '1rem' }} />
        <div className="skeleton" style={{ height: '250px', borderRadius: '8px', marginBottom: '1rem' }} />
        <div className="skeleton" style={{ height: '300px', borderRadius: '8px' }} />
      </div>
    );
  }

  if (!route) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center' }}>
        <div style={{
          background: 'rgba(0,0,0,0.3)',
          borderRadius: '8px',
          border: '1px solid rgba(255,255,255,0.08)',
          padding: '2rem',
          maxWidth: '400px',
          margin: '0 auto',
        }}>
          <div style={{ fontSize: '0.7rem', fontWeight: 700, color: '#ff4444', textTransform: 'uppercase', marginBottom: '0.5rem' }}>
            Route Not Found
          </div>
          <div style={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.8rem', marginBottom: '1rem' }}>
            {origin} → {destination}
          </div>
          <button
            onClick={() => navigate(-1)}
            style={{
              padding: '0.35rem 0.8rem',
              background: 'rgba(0,212,255,0.15)',
              border: '1px solid rgba(0,212,255,0.3)',
              borderRadius: '4px',
              color: '#00d4ff',
              cursor: 'pointer',
              fontSize: '0.7rem',
              fontWeight: 600,
            }}
          >
            ← Go Back
          </button>
        </div>
      </div>
    );
  }

  const dangerScore = calculateRouteDanger(route);

  return (
    <div style={{ padding: '1rem', maxWidth: '1200px', margin: '0 auto' }}>
      {/* CSS for animations */}
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.5; transform: scale(1.2); }
        }
        @keyframes glow {
          0%, 100% { box-shadow: 0 0 5px rgba(255,68,68,0.3); }
          50% { box-shadow: 0 0 15px rgba(255,68,68,0.5); }
        }
      `}</style>

      {/* Header Card - Compact Battlefield Style */}
      <div style={{
        background: 'rgba(0,0,0,0.3)',
        borderRadius: '8px',
        border: '1px solid rgba(255,255,255,0.08)',
        marginBottom: '1rem',
        overflow: 'hidden',
      }}>
        {/* Header Row */}
        <div style={{
          padding: '0.4rem 0.5rem',
          borderBottom: '1px solid rgba(255,255,255,0.08)',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
        }}>
          <button
            onClick={() => navigate(-1)}
            style={{
              padding: '0.2rem 0.5rem',
              background: 'rgba(255,255,255,0.05)',
              border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: '3px',
              color: 'rgba(255,255,255,0.5)',
              cursor: 'pointer',
              fontSize: '0.6rem',
            }}
          >
            ←
          </button>

          {threatInfo.pulse && (
            <span style={{
              width: '6px',
              height: '6px',
              borderRadius: '50%',
              background: threatInfo.color,
              animation: 'pulse 1.5s infinite',
            }} />
          )}

          <span style={{ fontSize: '0.7rem', fontWeight: 700, color: threatInfo.color, textTransform: 'uppercase' }}>
            {threatInfo.label}
          </span>

          <span style={{ fontSize: '0.8rem', fontWeight: 700, color: '#fff' }}>
            {route.origin_system}
          </span>
          <span style={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.3)' }}>→</span>
          <span style={{ fontSize: '0.8rem', fontWeight: 700, color: '#fff' }}>
            {route.destination_system}
          </span>

          <span style={{
            marginLeft: 'auto',
            padding: '0.15rem 0.4rem',
            background: 'rgba(0,212,255,0.15)',
            color: '#00d4ff',
            borderRadius: '3px',
            fontSize: '0.6rem',
            fontWeight: 600,
          }}>
            {timeLabel}
          </span>
        </div>

        {/* Stats Row - Compact inline */}
        <div style={{
          padding: '0.4rem 0.5rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.75rem',
          fontSize: '0.7rem',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
            <span style={{ fontWeight: 700, color: '#00d4ff', fontFamily: 'monospace' }}>{route.jumps}</span>
            <span style={{ color: 'rgba(255,255,255,0.4)' }}>jumps</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
            <span style={{ fontWeight: 700, color: '#ff4444', fontFamily: 'monospace' }}>{route.total_kills}</span>
            <span style={{ color: 'rgba(255,255,255,0.4)' }}>kills</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
            <span style={{ fontWeight: 700, color: '#ffcc00', fontFamily: 'monospace' }}>{formatISK(route.total_isk_destroyed)}</span>
            <span style={{ color: 'rgba(255,255,255,0.4)' }}>lost</span>
          </div>
          {gateCamps.length > 0 && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
              <span style={{ fontWeight: 700, color: '#ff0000', fontFamily: 'monospace' }}>{gateCamps.length}</span>
              <span style={{ color: '#ff6666' }}>gate camps</span>
            </div>
          )}
          {battlesOnRoute.length > 0 && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
              <span style={{ fontWeight: 700, color: '#00d4ff', fontFamily: 'monospace' }}>{battlesOnRoute.length}</span>
              <span style={{ color: 'rgba(0,212,255,0.7)' }}>battles</span>
            </div>
          )}

          {/* Danger bar */}
          <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <span style={{ fontSize: '0.55rem', color: 'rgba(255,255,255,0.3)' }}>DANGER</span>
            <div style={{
              width: '60px',
              height: '4px',
              background: 'rgba(255,255,255,0.1)',
              borderRadius: '2px',
              overflow: 'hidden',
            }}>
              <div style={{
                width: `${Math.min(100, dangerScore)}%`,
                height: '100%',
                background: threatInfo.color,
                borderRadius: '2px',
                transition: 'width 0.3s ease',
              }} />
            </div>
            <span style={{ fontSize: '0.6rem', color: threatInfo.color, fontFamily: 'monospace', fontWeight: 700 }}>
              {Math.round(dangerScore)}
            </span>
          </div>
        </div>
      </div>

      {/* Two Column Layout */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>

        {/* Left: Map */}
        <div style={{
          background: 'rgba(0,0,0,0.3)',
          borderRadius: '8px',
          border: '1px solid rgba(255,255,255,0.08)',
          overflow: 'hidden',
        }}>
          <div style={{
            padding: '0.4rem 0.5rem',
            borderBottom: '1px solid rgba(255,255,255,0.08)',
            display: 'flex',
            alignItems: 'center',
            gap: '0.35rem',
          }}>
            <span style={{ fontSize: '0.65rem' }}>🗺️</span>
            <span style={{ fontSize: '0.7rem', fontWeight: 700, color: '#00d4ff', textTransform: 'uppercase' }}>
              Route Map
            </span>
          </div>
          <iframe
            ref={mapIframeRef}
            src={`${getEctmapBaseUrl()}?snapshot=true&colorMode=security&showKills=true&killsMinutes=${minutes}`}
            style={{
              width: '100%',
              height: '280px',
              border: 'none',
            }}
            title="Route Map"
          />
        </div>

        {/* Right: Route Path List - ActiveCombatZones Style */}
        <div style={{
          background: 'rgba(0,0,0,0.3)',
          borderRadius: '8px',
          border: '1px solid rgba(255,255,255,0.08)',
          overflow: 'hidden',
        }}>
          {/* Header */}
          <div style={{
            padding: '0.4rem 0.5rem',
            borderBottom: '1px solid rgba(255,255,255,0.08)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              <span style={{ fontSize: '0.65rem' }}>🛤️</span>
              <span style={{ fontSize: '0.7rem', fontWeight: 700, color: '#ffcc00', textTransform: 'uppercase' }}>
                Route Path
              </span>
            </div>
            <div style={{ display: 'flex', gap: '0.5rem', fontSize: '0.55rem' }}>
              {hotspots.length > 0 && (
                <span style={{ color: '#ff4444' }}>{hotspots.length} hot</span>
              )}
              {gateCamps.length > 0 && (
                <span style={{ color: '#ff0000' }}>{gateCamps.length} gc</span>
              )}
              <span style={{ color: 'rgba(255,255,255,0.4)' }}>{route.systems?.length || 0} sys</span>
            </div>
          </div>

          {/* Systems List */}
          <div style={{
            padding: '0.25rem',
            maxHeight: '280px',
            overflowY: 'auto',
            overflowX: 'hidden',
          }}>
            {route.systems?.map((sys, idx) => {
              const threat = getSystemThreat(sys);
              const config = THREAT_CONFIG[threat];
              const isSelected = selectedSystem?.system_id === sys.system_id;
              const isFirst = idx === 0;
              const isLast = idx === (route.systems?.length || 0) - 1;

              return (
                <div
                  key={sys.system_id}
                  onClick={() => setSelectedSystem(isSelected ? null : sys)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.4rem',
                    padding: '0.35rem 0.4rem',
                    marginBottom: idx < (route.systems?.length || 0) - 1 ? '0.2rem' : 0,
                    background: isSelected ? 'rgba(255,255,255,0.1)' : config.bg,
                    borderRadius: '4px',
                    borderLeft: `2px solid ${isSelected ? '#fff' : config.color}`,
                    cursor: 'pointer',
                    transition: 'all 0.15s ease',
                  }}
                  onMouseEnter={(e) => { if (!isSelected) e.currentTarget.style.background = 'rgba(255,255,255,0.08)'; }}
                  onMouseLeave={(e) => { if (!isSelected) e.currentTarget.style.background = config.bg; }}
                >
                  {/* Index */}
                  <span style={{
                    fontSize: '0.5rem',
                    color: 'rgba(255,255,255,0.25)',
                    fontFamily: 'monospace',
                    minWidth: '16px',
                  }}>
                    {String(idx + 1).padStart(2, '0')}
                  </span>

                  {/* Security Badge */}
                  <div style={{
                    width: 20,
                    height: 20,
                    borderRadius: '2px',
                    background: getSecurityColor(sys.security_status),
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '0.5rem',
                    fontWeight: 700,
                    color: sys.security_status >= 0.5 ? '#000' : '#fff',
                  }}>
                    {sys.security_status.toFixed(1)}
                  </div>

                  {/* System Name */}
                  <div style={{ flex: 1, minWidth: 0, display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                    <span style={{
                      fontWeight: 700,
                      fontSize: '0.75rem',
                      color: (isFirst || isLast) ? '#00d4ff' : '#fff',
                    }}>
                      {sys.system_name}
                    </span>
                    {(isFirst || isLast) && (
                      <span style={{ fontSize: '0.5rem', color: '#00d4ff', fontWeight: 600 }}>
                        {isFirst ? 'START' : 'END'}
                      </span>
                    )}
                  </div>

                  {/* Indicators */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                    {/* Kills */}
                    {sys.kills_24h > 0 && (
                      <span style={{
                        fontSize: '0.7rem',
                        fontWeight: 700,
                        fontFamily: 'monospace',
                        color: sys.kills_24h >= 5 ? '#ff4444' : 'rgba(255,255,255,0.5)',
                      }}>
                        {sys.kills_24h}
                      </span>
                    )}

                    {/* Gate Camp */}
                    {sys.is_gate_camp && (
                      <span style={{
                        fontSize: '0.5rem',
                        padding: '1px 4px',
                        borderRadius: '2px',
                        background: 'rgba(255,0,0,0.3)',
                        color: '#ff6666',
                        fontWeight: 700,
                        animation: 'pulse 1.5s infinite',
                      }}>
                        GC
                      </span>
                    )}

                    {/* Battle */}
                    {sys.battle_id && (
                      <span style={{
                        fontSize: '0.5rem',
                        padding: '1px 4px',
                        borderRadius: '2px',
                        background: 'rgba(0,212,255,0.3)',
                        color: '#00d4ff',
                        fontWeight: 700,
                      }}>
                        BATTLE
                      </span>
                    )}

                    {/* ISK */}
                    {sys.isk_destroyed_24h > 1e6 && (
                      <span style={{
                        fontSize: '0.55rem',
                        color: '#ffcc00',
                        fontFamily: 'monospace',
                      }}>
                        {formatISK(sys.isk_destroyed_24h)}
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* System Detail Panel - Shows when system selected */}
      {selectedSystem && (
        <div style={{
          marginTop: '1rem',
          background: 'rgba(0,0,0,0.3)',
          borderRadius: '8px',
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
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <div style={{
                width: 24,
                height: 24,
                borderRadius: '3px',
                background: getSecurityColor(selectedSystem.security_status),
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '0.6rem',
                fontWeight: 700,
                color: selectedSystem.security_status >= 0.5 ? '#000' : '#fff',
              }}>
                {selectedSystem.security_status.toFixed(1)}
              </div>
              <span style={{ fontSize: '0.85rem', fontWeight: 700, color: '#fff' }}>
                {selectedSystem.system_name}
              </span>
              {selectedSystem.is_gate_camp && (
                <span style={{
                  fontSize: '0.55rem',
                  padding: '2px 6px',
                  borderRadius: '3px',
                  background: 'rgba(255,0,0,0.2)',
                  color: '#ff4444',
                  fontWeight: 700,
                }}>
                  GATE CAMP
                </span>
              )}
              {selectedSystem.battle_id && (
                <span style={{
                  fontSize: '0.55rem',
                  padding: '2px 6px',
                  borderRadius: '3px',
                  background: 'rgba(0,212,255,0.2)',
                  color: '#00d4ff',
                  fontWeight: 700,
                }}>
                  ACTIVE BATTLE
                </span>
              )}
            </div>
            <button
              onClick={() => setSelectedSystem(null)}
              style={{
                padding: '0.15rem 0.4rem',
                background: 'transparent',
                border: '1px solid rgba(255,255,255,0.15)',
                borderRadius: '3px',
                color: 'rgba(255,255,255,0.4)',
                cursor: 'pointer',
                fontSize: '0.6rem',
              }}
            >
              ✕
            </button>
          </div>

          <div style={{ padding: '0.5rem', display: 'flex', gap: '1rem', alignItems: 'center' }}>
            {/* Stats */}
            <div style={{ display: 'flex', gap: '1.5rem' }}>
              <div>
                <div style={{ fontSize: '0.55rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase' }}>
                  Kills ({timeLabel})
                </div>
                <div style={{ fontSize: '1.2rem', fontWeight: 700, color: '#ff4444', fontFamily: 'monospace' }}>
                  {selectedSystem.kills_24h}
                </div>
              </div>
              <div>
                <div style={{ fontSize: '0.55rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase' }}>
                  ISK Lost
                </div>
                <div style={{ fontSize: '1.2rem', fontWeight: 700, color: '#ffcc00', fontFamily: 'monospace' }}>
                  {formatISK(selectedSystem.isk_destroyed_24h)}
                </div>
              </div>
              <div>
                <div style={{ fontSize: '0.55rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase' }}>
                  Danger
                </div>
                <div style={{
                  fontSize: '1.2rem',
                  fontWeight: 700,
                  color: THREAT_CONFIG[getSystemThreat(selectedSystem)].color,
                  fontFamily: 'monospace'
                }}>
                  {selectedSystem.danger_score}
                </div>
              </div>
            </div>

            {/* Actions */}
            <div style={{ marginLeft: 'auto', display: 'flex', gap: '0.5rem' }}>
              <button
                onClick={() => navigate(`/system/${selectedSystem.system_id}?minutes=${minutes}`)}
                style={{
                  padding: '0.35rem 0.7rem',
                  background: 'rgba(0,212,255,0.15)',
                  border: '1px solid rgba(0,212,255,0.3)',
                  borderRadius: '4px',
                  color: '#00d4ff',
                  cursor: 'pointer',
                  fontSize: '0.65rem',
                  fontWeight: 600,
                }}
              >
                System Details
              </button>
              {selectedSystem.battle_id && (
                <button
                  onClick={() => navigate(`/battle/${selectedSystem.battle_id}`)}
                  style={{
                    padding: '0.35rem 0.7rem',
                    background: 'rgba(255,68,68,0.15)',
                    border: '1px solid rgba(255,68,68,0.3)',
                    borderRadius: '4px',
                    color: '#ff4444',
                    cursor: 'pointer',
                    fontSize: '0.65rem',
                    fontWeight: 600,
                  }}
                >
                  View Battle
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Recommendations - Compact */}
      <div style={{
        marginTop: '1rem',
        background: 'rgba(0,0,0,0.3)',
        borderRadius: '8px',
        border: '1px solid rgba(255,255,255,0.08)',
        overflow: 'hidden',
      }}>
        <div style={{
          padding: '0.4rem 0.5rem',
          borderBottom: '1px solid rgba(255,255,255,0.08)',
          display: 'flex',
          alignItems: 'center',
          gap: '0.35rem',
        }}>
          <span style={{ fontSize: '0.65rem' }}>⚠️</span>
          <span style={{ fontSize: '0.7rem', fontWeight: 700, color: threatInfo.color, textTransform: 'uppercase' }}>
            Intel Summary
          </span>
        </div>
        <div style={{ padding: '0.5rem', fontSize: '0.7rem', color: 'rgba(255,255,255,0.7)', lineHeight: 1.8 }}>
          {dangerScore >= 40 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
              <span style={{ color: '#ff4444' }}>⛔ High risk route - use heavily tanked haulers or escort fleet</span>
              <span style={{ color: '#ff4444' }}>👁️ Scout ahead with alt character</span>
              <span>💰 Avoid high-value cargo on this route</span>
            </div>
          ) : dangerScore >= 20 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
              <span style={{ color: '#ffaa00' }}>⚠️ Moderate risk - standard precautions advised</span>
              <span>🛡️ Fit appropriate tank modules</span>
              <span>📡 Monitor intel channels</span>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
              <span style={{ color: '#00ff88' }}>✅ Route appears relatively safe</span>
              <span>🔒 Standard precautions still recommended</span>
            </div>
          )}
          {gateCamps.length > 0 && (
            <div style={{ marginTop: '0.5rem', paddingTop: '0.5rem', borderTop: '1px solid rgba(255,255,255,0.05)' }}>
              <span style={{ color: '#ff0000' }}>
                🚨 {gateCamps.length} gate camp{gateCamps.length > 1 ? 's' : ''}: {gateCamps.map(g => g.system_name).join(', ')}
              </span>
            </div>
          )}
          {battlesOnRoute.length > 0 && (
            <div style={{ marginTop: gateCamps.length > 0 ? '0.3rem' : '0.5rem', paddingTop: gateCamps.length > 0 ? 0 : '0.5rem', borderTop: gateCamps.length > 0 ? 'none' : '1px solid rgba(255,255,255,0.05)' }}>
              <span style={{ color: '#00d4ff' }}>
                💥 {battlesOnRoute.length} active battle{battlesOnRoute.length > 1 ? 's' : ''} - expect increased activity
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
