import { useState, useEffect, useMemo } from 'react';
import { battleApi, reportsApi } from '../services/api';
import type { BattleReshipmentResponse, Coalition } from '../types/reports';
import { formatISKCompact } from '../utils/format';

interface BattleReshipmentsProps {
  battleId: number;
}

// EVE Image Server URLs
const EVE_IMAGE = {
  alliance: (id: number, size = 32) => `https://images.evetech.net/alliances/${id}/logo?size=${size}`,
  corp: (id: number, size = 32) => `https://images.evetech.net/corporations/${id}/logo?size=${size}`,
  character: (id: number, size = 32) => `https://images.evetech.net/characters/${id}/portrait?size=${size}`,
};

export function BattleReshipments({ battleId }: BattleReshipmentsProps) {
  const [data, setData] = useState<BattleReshipmentResponse | null>(null);
  const [coalitions, setCoalitions] = useState<Coalition[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [view, setView] = useState<'hierarchy' | 'pilots'>('hierarchy');
  const [expandedPowerblocs, setExpandedPowerblocs] = useState<Set<string>>(new Set());
  const [expandedAlliances, setExpandedAlliances] = useState<Set<number>>(new Set());

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [reshipData, powerBlocData] = await Promise.all([
          battleApi.getBattleReshipments(battleId),
          reportsApi.getPowerBlocsLive(10080).catch(() => ({ coalitions: [] }))
        ]);
        setData(reshipData);
        setCoalitions(powerBlocData.coalitions || []);
      } catch (err) {
        setError('Failed to load data');
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [battleId]);

  const formatISK = formatISKCompact;

  const getPersistenceColor = (ratio: number): string => {
    if (ratio >= 0.4) return '#3fb950';
    if (ratio >= 0.25) return '#d29922';
    return '#f85149';
  };

  const togglePowerbloc = (name: string) => {
    setExpandedPowerblocs(prev => {
      const next = new Set(prev);
      if (next.has(name)) {
        next.delete(name);
      } else {
        next.add(name);
      }
      return next;
    });
  };

  const toggleAlliance = (allianceId: number) => {
    setExpandedAlliances(prev => {
      const next = new Set(prev);
      if (next.has(allianceId)) {
        next.delete(allianceId);
      } else {
        next.add(allianceId);
      }
      return next;
    });
  };

  // Group alliances by powerbloc
  const groupedAlliances = useMemo(() => {
    if (!data) return { groups: [], unaffiliated: [] };

    // Create alliance -> powerbloc mapping
    const allianceToPowerbloc: Record<number, { name: string; leaderId: number }> = {};
    for (const coalition of coalitions) {
      for (const member of coalition.members) {
        allianceToPowerbloc[member.alliance_id] = {
          name: coalition.leader_name,
          leaderId: coalition.leader_alliance_id
        };
      }
    }

    // Group alliances
    const groups: Record<string, {
      name: string;
      leaderId: number;
      alliances: typeof data.by_alliance;
      totalReshippers: number;
    }> = {};
    const unaffiliated: typeof data.by_alliance = [];

    for (const alliance of data.by_alliance) {
      const powerbloc = allianceToPowerbloc[alliance.alliance_id];
      if (powerbloc) {
        if (!groups[powerbloc.name]) {
          groups[powerbloc.name] = {
            name: powerbloc.name,
            leaderId: powerbloc.leaderId,
            alliances: [],
            totalReshippers: 0
          };
        }
        groups[powerbloc.name].alliances.push(alliance);
        groups[powerbloc.name].totalReshippers += alliance.total_reshippers;
      } else {
        unaffiliated.push(alliance);
      }
    }

    const sortedGroups = Object.values(groups).sort((a, b) => b.totalReshippers - a.totalReshippers);
    for (const group of sortedGroups) {
      group.alliances.sort((a, b) => b.total_reshippers - a.total_reshippers);
    }
    unaffiliated.sort((a, b) => b.total_reshippers - a.total_reshippers);

    return { groups: sortedGroups, unaffiliated };
  }, [data, coalitions]);

  if (loading) {
    return (
      <div style={{
        background: 'rgba(0,0,0,0.3)',
        border: '1px solid rgba(255,255,255,0.08)',
        borderRadius: '8px',
        padding: '1.5rem',
        marginBottom: '1.5rem'
      }}>
        <div className="skeleton" style={{ height: '150px' }} />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div style={{
        background: 'rgba(0,0,0,0.3)',
        border: '1px solid rgba(255,255,255,0.08)',
        borderRadius: '8px',
        padding: '1.5rem',
        marginBottom: '1.5rem',
        textAlign: 'center',
        color: 'rgba(255,255,255,0.5)'
      }}>
        <p>{error || 'No data available'}</p>
      </div>
    );
  }

  const { reshippers, summary } = data;

  return (
    <div style={{
      background: 'rgba(0,0,0,0.3)',
      border: '1px solid rgba(255,255,255,0.08)',
      borderRadius: '8px',
      overflow: 'hidden',
      marginBottom: '1rem'
    }}>
      {/* Header */}
      <div style={{
        padding: '0.5rem 0.75rem',
        borderBottom: '1px solid rgba(255,255,255,0.08)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            background: '#3fb950',
          }} />
          <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#3fb950', textTransform: 'uppercase' }}>
            Combat Persistence
          </span>
        </div>

        <div style={{ display: 'flex', gap: '1rem', fontSize: '0.65rem', alignItems: 'center' }}>
          <span>
            <span style={{ color: '#58a6ff', fontWeight: 700, fontFamily: 'monospace' }}>{summary.total_reshippers}</span>
            <span style={{ color: 'rgba(255,255,255,0.4)', marginLeft: '0.25rem' }}>returned</span>
          </span>
          <span>
            <span style={{ color: '#d29922', fontWeight: 700, fontFamily: 'monospace' }}>{(summary.overall_reship_ratio * 100).toFixed(0)}%</span>
            <span style={{ color: 'rgba(255,255,255,0.4)', marginLeft: '0.25rem' }}>rate</span>
          </span>
          <span>
            <span style={{ color: '#f85149', fontWeight: 700, fontFamily: 'monospace' }}>{summary.max_deaths}x</span>
            <span style={{ color: 'rgba(255,255,255,0.4)', marginLeft: '0.25rem' }}>max</span>
          </span>

          {/* View Toggle */}
          <div style={{ display: 'flex', gap: '0.15rem' }}>
            <button
              onClick={() => setView('hierarchy')}
              style={{
                padding: '2px 8px',
                background: view === 'hierarchy' ? 'rgba(88,166,255,0.2)' : 'transparent',
                color: view === 'hierarchy' ? '#58a6ff' : 'rgba(255,255,255,0.4)',
                border: '1px solid rgba(255,255,255,0.1)',
                borderRadius: '3px',
                cursor: 'pointer',
                fontSize: '0.6rem',
                fontWeight: 600
              }}
            >
              Hierarchy
            </button>
            <button
              onClick={() => setView('pilots')}
              style={{
                padding: '2px 8px',
                background: view === 'pilots' ? 'rgba(88,166,255,0.2)' : 'transparent',
                color: view === 'pilots' ? '#58a6ff' : 'rgba(255,255,255,0.4)',
                border: '1px solid rgba(255,255,255,0.1)',
                borderRadius: '3px',
                cursor: 'pointer',
                fontSize: '0.6rem',
                fontWeight: 600
              }}
            >
              Pilots
            </button>
          </div>
        </div>
      </div>

      {/* Hierarchy View */}
      {view === 'hierarchy' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem', padding: '0.4rem' }}>
          {/* Powerbloc Groups (collapsed by default) */}
          {groupedAlliances.groups.map((group) => {
            const isPowerblocExpanded = expandedPowerblocs.has(group.name);

            return (
              <div key={group.name}>
                {/* Powerbloc Header - Clickable */}
                <div
                  onClick={() => togglePowerbloc(group.name)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                    padding: '0.5rem 0.75rem',
                    background: 'rgba(168,85,247,0.1)',
                    borderRadius: '4px',
                    borderLeft: '3px solid #a855f7',
                    cursor: 'pointer'
                  }}
                >
                  <span style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', width: '12px' }}>
                    {isPowerblocExpanded ? '▼' : '▶'}
                  </span>
                  <img
                    src={EVE_IMAGE.alliance(group.leaderId, 32)}
                    alt=""
                    loading="lazy"
                    decoding="async"
                    style={{ width: '20px', height: '20px', borderRadius: '3px' }}
                    onError={(e) => { e.currentTarget.style.display = 'none'; }}
                  />
                  <span style={{ fontWeight: 600, fontSize: '0.85rem', color: '#a855f7' }}>
                    {group.name} Coalition
                  </span>
                  <span style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', marginLeft: 'auto' }}>
                    {group.alliances.length} alliances • {group.totalReshippers} returned
                  </span>
                </div>

                {/* Alliances in this powerbloc (shown when expanded) */}
                {isPowerblocExpanded && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem', paddingLeft: '1rem', marginTop: '0.3rem' }}>
                    {group.alliances.slice(0, 8).map((alliance) => {
                      const isAllianceExpanded = expandedAlliances.has(alliance.alliance_id);
                      const hasCorps = alliance.corps && alliance.corps.length > 0;

                      return (
                        <div key={alliance.alliance_id}>
                          {/* Alliance Row */}
                          <div
                            onClick={() => hasCorps && toggleAlliance(alliance.alliance_id)}
                            style={{
                              padding: '0.4rem 0.6rem',
                              background: 'rgba(255,255,255,0.03)',
                              borderRadius: '4px',
                              borderLeft: `3px solid ${getPersistenceColor(alliance.reship_ratio)}`,
                              display: 'flex',
                              alignItems: 'center',
                              gap: '0.5rem',
                              cursor: hasCorps ? 'pointer' : 'default'
                            }}
                          >
                            {hasCorps && (
                              <span style={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.4)', width: '10px' }}>
                                {isAllianceExpanded ? '▼' : '▶'}
                              </span>
                            )}
                            <img
                              src={EVE_IMAGE.alliance(alliance.alliance_id, 32)}
                              alt=""
                              loading="lazy"
                              decoding="async"
                              style={{ width: '16px', height: '16px', borderRadius: '2px' }}
                              onError={(e) => { e.currentTarget.style.display = 'none'; }}
                            />
                            <div style={{ flex: 1, minWidth: 0 }}>
                              <div style={{ fontWeight: 500, fontSize: '0.75rem' }}>
                                {alliance.alliance_name}
                              </div>
                            </div>
                            <div style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)' }}>
                              {alliance.total_reshippers} ret
                            </div>
                            <div style={{
                              fontSize: '0.8rem',
                              fontWeight: 'bold',
                              color: getPersistenceColor(alliance.reship_ratio)
                            }}>
                              {(alliance.reship_ratio * 100).toFixed(0)}%
                            </div>
                          </div>

                          {/* Corp Breakdown (expanded) */}
                          {isAllianceExpanded && hasCorps && (
                            <div style={{
                              paddingLeft: '1.25rem',
                              marginTop: '0.2rem',
                              display: 'flex',
                              flexDirection: 'column',
                              gap: '0.15rem'
                            }}>
                              {alliance.corps.slice(0, 5).map((corp) => (
                                <div
                                  key={corp.corp_id}
                                  style={{
                                    padding: '0.3rem 0.5rem',
                                    background: 'rgba(255,255,255,0.02)',
                                    borderRadius: '3px',
                                    borderLeft: `2px solid ${getPersistenceColor(corp.reship_ratio)}`,
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '0.4rem'
                                  }}
                                >
                                  <img
                                    src={EVE_IMAGE.corp(corp.corp_id, 32)}
                                    alt=""
                                    loading="lazy"
                                    decoding="async"
                                    style={{ width: '14px', height: '14px', borderRadius: '2px' }}
                                    onError={(e) => { e.currentTarget.style.display = 'none'; }}
                                  />
                                  <div style={{ flex: 1, fontSize: '0.7rem' }}>
                                    {corp.corp_name}
                                  </div>
                                  <div style={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.4)' }}>
                                    {corp.reshippers}
                                  </div>
                                  <div style={{
                                    fontSize: '0.7rem',
                                    fontWeight: 'bold',
                                    color: getPersistenceColor(corp.reship_ratio)
                                  }}>
                                    {(corp.reship_ratio * 100).toFixed(0)}%
                                  </div>
                                </div>
                              ))}
                              {alliance.corps.length > 5 && (
                                <div style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.3)', paddingLeft: '0.5rem' }}>
                                  +{alliance.corps.length - 5} more
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      );
                    })}
                    {group.alliances.length > 8 && (
                      <div style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.3)', paddingLeft: '0.5rem' }}>
                        +{group.alliances.length - 8} more alliances
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}

          {/* Unaffiliated Alliances - shown directly (no powerbloc) */}
          {groupedAlliances.unaffiliated.slice(0, 8).map((alliance) => {
            const isExpanded = expandedAlliances.has(alliance.alliance_id);
            const hasCorps = alliance.corps && alliance.corps.length > 0;

            return (
              <div key={alliance.alliance_id}>
                <div
                  onClick={() => hasCorps && toggleAlliance(alliance.alliance_id)}
                  style={{
                    padding: '0.5rem 0.75rem',
                    background: 'rgba(255,255,255,0.03)',
                    borderRadius: '4px',
                    borderLeft: `3px solid ${getPersistenceColor(alliance.reship_ratio)}`,
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                    cursor: hasCorps ? 'pointer' : 'default'
                  }}
                >
                  {hasCorps && (
                    <span style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', width: '12px' }}>
                      {isExpanded ? '▼' : '▶'}
                    </span>
                  )}
                  <img
                    src={EVE_IMAGE.alliance(alliance.alliance_id, 32)}
                    alt=""
                    loading="lazy"
                    decoding="async"
                    style={{ width: '18px', height: '18px', borderRadius: '2px' }}
                    onError={(e) => { e.currentTarget.style.display = 'none'; }}
                  />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontWeight: 500, fontSize: '0.8rem' }}>
                      {alliance.alliance_name}
                    </div>
                    <div style={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.4)' }}>
                      {alliance.total_reshippers} returned • {alliance.total_deaths} deaths
                    </div>
                  </div>
                  <div style={{
                    fontSize: '0.85rem',
                    fontWeight: 'bold',
                    color: getPersistenceColor(alliance.reship_ratio)
                  }}>
                    {(alliance.reship_ratio * 100).toFixed(0)}%
                  </div>
                </div>

                {isExpanded && hasCorps && (
                  <div style={{
                    paddingLeft: '1.25rem',
                    marginTop: '0.2rem',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '0.15rem'
                  }}>
                    {alliance.corps.slice(0, 5).map((corp) => (
                      <div
                        key={corp.corp_id}
                        style={{
                          padding: '0.3rem 0.5rem',
                          background: 'rgba(255,255,255,0.02)',
                          borderRadius: '3px',
                          borderLeft: `2px solid ${getPersistenceColor(corp.reship_ratio)}`,
                          display: 'flex',
                          alignItems: 'center',
                          gap: '0.4rem'
                        }}
                      >
                        <img
                          src={EVE_IMAGE.corp(corp.corp_id, 32)}
                          alt=""
                          loading="lazy"
                          decoding="async"
                          style={{ width: '14px', height: '14px', borderRadius: '2px' }}
                          onError={(e) => { e.currentTarget.style.display = 'none'; }}
                        />
                        <div style={{ flex: 1, fontSize: '0.7rem' }}>
                          {corp.corp_name}
                        </div>
                        <div style={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.4)' }}>
                          {corp.reshippers}
                        </div>
                        <div style={{
                          fontSize: '0.7rem',
                          fontWeight: 'bold',
                          color: getPersistenceColor(corp.reship_ratio)
                        }}>
                          {(corp.reship_ratio * 100).toFixed(0)}%
                        </div>
                      </div>
                    ))}
                    {alliance.corps.length > 5 && (
                      <div style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.3)', paddingLeft: '0.5rem' }}>
                        +{alliance.corps.length - 5} more
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
          {groupedAlliances.unaffiliated.length > 8 && (
            <div style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.3)', paddingLeft: '0.5rem' }}>
              +{groupedAlliances.unaffiliated.length - 8} more alliances
            </div>
          )}

          {groupedAlliances.groups.length === 0 && groupedAlliances.unaffiliated.length === 0 && (
            <div style={{ textAlign: 'center', color: 'rgba(255,255,255,0.4)', padding: '1rem', fontSize: '0.8rem' }}>
              No alliance data available
            </div>
          )}
        </div>
      )}

      {/* Pilots View */}
      {view === 'pilots' && reshippers.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem', padding: '0.4rem' }}>
          {reshippers.slice(0, 10).map((pilot) => (
            <div
              key={pilot.character_id}
              style={{
                padding: '0.3rem 0.5rem',
                background: 'rgba(255,255,255,0.03)',
                borderRadius: '4px',
                borderLeft: `2px solid ${pilot.deaths >= 5 ? '#f85149' : pilot.deaths >= 3 ? '#d29922' : '#58a6ff'}`,
                display: 'flex',
                alignItems: 'center',
                gap: '0.4rem'
              }}
            >
              <img
                src={EVE_IMAGE.character(pilot.character_id, 32)}
                alt=""
                loading="lazy"
                decoding="async"
                style={{ width: '20px', height: '20px', borderRadius: '2px', flexShrink: 0 }}
                onError={(e) => { e.currentTarget.style.display = 'none'; }}
              />
              <a
                href={`https://zkillboard.com/character/${pilot.character_id}/`}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  color: '#58a6ff',
                  textDecoration: 'none',
                  fontWeight: 600,
                  fontSize: '0.7rem',
                  flex: 1,
                  minWidth: 0,
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}
              >
                {pilot.character_name}
              </a>
              <span style={{ fontSize: '0.55rem', color: 'rgba(255,255,255,0.3)', flexShrink: 0 }}>
                {pilot.ships_lost.slice(0, 2).join(' → ')}
                {pilot.ships_lost.length > 2 && ` +${pilot.ships_lost.length - 2}`}
              </span>
              <span style={{
                fontSize: '0.65rem',
                fontWeight: 700,
                color: pilot.deaths >= 5 ? '#f85149' : pilot.deaths >= 3 ? '#d29922' : '#58a6ff',
                fontFamily: 'monospace',
                flexShrink: 0,
              }}>
                {pilot.deaths}x
              </span>
              <span style={{ fontSize: '0.6rem', color: '#ff4444', fontFamily: 'monospace', fontWeight: 600, flexShrink: 0 }}>
                {formatISK(pilot.total_isk_lost)}
              </span>
            </div>
          ))}
          {reshippers.length > 10 && (
            <div style={{
              fontSize: '0.7rem',
              color: 'rgba(255,255,255,0.4)',
              textAlign: 'center',
              padding: '0.25rem'
            }}>
              +{reshippers.length - 10} more pilots
            </div>
          )}
        </div>
      )}

      {view === 'pilots' && reshippers.length === 0 && (
        <div style={{ textAlign: 'center', color: 'rgba(255,255,255,0.4)', padding: '1rem', fontSize: '0.8rem' }}>
          No pilots returned to fight after dying
        </div>
      )}
    </div>
  );
}
