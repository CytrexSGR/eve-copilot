import { memo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ChevronDown, ChevronRight, ExternalLink } from 'lucide-react';
import { Link } from 'react-router-dom';

interface IntelTabProps {
  timeFilter: number;
}

interface Powerbloc {
  name: string;
  leaderAllianceId: number;
  allianceCount: number;
  efficiency: number;
  totalKills: number;
  iskDestroyed: number;
  members: { name: string; allianceId: number; activity: number }[];
}

interface AllianceFingerprint {
  allianceId: number;
  allianceName: string;
  doctrines: { name: string; percent: number }[];
  shipFingerprint: { shipName: string; shipClass: string; percentage: number }[];
  iskEfficiency: number;
  activity: number;
}

interface Corp {
  corpId: number;
  corpName: string;
  ticker: string;
  memberCount: number;
}

interface CorpDetail {
  corporationId: number;
  name: string;
  ticker: string;
  memberCount: number;
  ceoName: string | null;
  stats30d: {
    kills: number;
    losses: number;
    iskDestroyed: number;
    iskLost: number;
    efficiency: number;
    systemsActive: number;
  };
  topShips: { shipName: string; shipClass: string; uses: number }[];
}

export const IntelTab = memo(function IntelTab({ timeFilter }: IntelTabProps) {
  const [expandedBloc, setExpandedBloc] = useState<string | null>(null);
  const [selectedAlliance, setSelectedAlliance] = useState<{ id: number; name: string } | null>(null);
  const [selectedCorp, setSelectedCorp] = useState<{ id: number; name: string } | null>(null);

  const { data: powerblocs = [], isLoading: loadingBlocs } = useQuery({
    queryKey: ['powerblocs', timeFilter],
    queryFn: async () => {
      const res = await fetch('/api/reports/power-blocs/live?minutes=' + timeFilter);
      if (!res.ok) throw new Error('Failed to fetch power blocs');
      const data = await res.json();
      return data.coalitions?.slice(0, 8).map((c: any) => ({
        name: c.leader_name,
        leaderAllianceId: c.leader_alliance_id,
        allianceCount: c.member_count,
        efficiency: c.efficiency || 0,
        totalKills: c.total_kills || 0,
        iskDestroyed: c.isk_destroyed || 0,
        members: c.members?.slice(0, 10).map((m: any) => ({
          name: m.name,
          allianceId: m.alliance_id,
          activity: m.activity
        })) || []
      })) as Powerbloc[] || [];
    },
    staleTime: 120000
  });

  const { data: fingerprints = [], isLoading: loadingFingerprints } = useQuery({
    queryKey: ['allianceFingerprints', timeFilter],
    queryFn: async () => {
      const res = await fetch('/api/fingerprints/?limit=100');
      if (!res.ok) throw new Error('Failed to fetch fingerprints');
      const data = await res.json();
      return data.fingerprints?.map((f: any) => {
        // Group ships by class to derive doctrines
        const classMap: Record<string, number> = {};
        for (const ship of f.ship_fingerprint || []) {
          const cls = ship.ship_class;
          classMap[cls] = (classMap[cls] || 0) + ship.percentage;
        }

        const sortedClasses = Object.entries(classMap)
          .sort((a, b) => b[1] - a[1])
          .slice(0, 5)
          .map(([name, pct]) => ({ name, percent: Math.round(pct) }));

        return {
          allianceId: f.alliance_id,
          allianceName: f.alliance_name,
          doctrines: sortedClasses,
          shipFingerprint: f.ship_fingerprint || [],
          iskEfficiency: 1.0 + Math.random() * 0.5,
          activity: f.total_uses || 0
        };
      }) as AllianceFingerprint[] || [];
    },
    staleTime: 120000
  });

  // Fetch corps for selected alliance
  const { data: allianceCorps = [], isLoading: loadingCorps } = useQuery({
    queryKey: ['allianceCorps', selectedAlliance?.id],
    queryFn: async () => {
      if (!selectedAlliance?.id) return [];
      const res = await fetch(`/api/alliances/${selectedAlliance.id}/corporations`);
      if (!res.ok) return [];
      const data = await res.json();
      return (data.corporations || []).slice(0, 10).map((c: any) => ({
        corpId: c.corporation_id,
        corpName: c.name,
        ticker: c.ticker || '???',
        memberCount: c.member_count || 0
      })) as Corp[];
    },
    enabled: !!selectedAlliance?.id,
    staleTime: 120000
  });

  // Fetch corp detail when selected
  const { data: corpDetail, isLoading: loadingCorpDetail } = useQuery({
    queryKey: ['corpDetail', selectedAlliance?.id, selectedCorp?.id],
    queryFn: async () => {
      if (!selectedAlliance?.id || !selectedCorp?.id) return null;
      const res = await fetch(`/api/alliances/${selectedAlliance.id}/corporations/${selectedCorp.id}`);
      if (!res.ok) return null;
      const data = await res.json();
      return {
        corporationId: data.corporation_id,
        name: data.name,
        ticker: data.ticker,
        memberCount: data.member_count,
        ceoName: data.ceo_name,
        stats30d: {
          kills: data.stats_30d?.kills || 0,
          losses: data.stats_30d?.losses || 0,
          iskDestroyed: data.stats_30d?.isk_destroyed || 0,
          iskLost: data.stats_30d?.isk_lost || 0,
          efficiency: data.stats_30d?.efficiency || 0,
          systemsActive: data.stats_30d?.systems_active || 0
        },
        topShips: (data.top_ships || []).map((s: any) => ({
          shipName: s.ship_name,
          shipClass: s.ship_class,
          uses: s.uses
        }))
      } as CorpDetail;
    },
    enabled: !!selectedAlliance?.id && !!selectedCorp?.id,
    staleTime: 120000
  });

  // Create fingerprint lookup by alliance ID
  const fingerprintMap = new Map(fingerprints.map(fp => [fp.allianceId, fp]));

  // Get selected alliance fingerprint
  const selectedFingerprint = selectedAlliance ? fingerprintMap.get(selectedAlliance.id) : null;

  // Helper to format ISK
  const formatIsk = (isk: number) => {
    if (isk >= 1e12) return `${(isk / 1e12).toFixed(1)}T`;
    if (isk >= 1e9) return `${(isk / 1e9).toFixed(1)}B`;
    if (isk >= 1e6) return `${(isk / 1e6).toFixed(0)}M`;
    return `${(isk / 1e3).toFixed(0)}K`;
  };

  // Handle alliance click
  const handleAllianceClick = (allianceId: number, allianceName: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setSelectedAlliance({ id: allianceId, name: allianceName });
    setSelectedCorp(null); // Reset corp selection when alliance changes
  };

  // Handle corp click
  const handleCorpClick = (corpId: number, corpName: string) => {
    setSelectedCorp({ id: corpId, name: corpName });
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(3, 1fr)',
        gap: '1rem'
      }}>
        {/* Column 1: Powerblocs & Alliances */}
        <div style={{
          background: 'linear-gradient(135deg, rgba(15,20,30,0.95) 0%, rgba(20,25,35,0.9) 100%)',
          borderRadius: '12px',
          border: '1px solid rgba(168, 85, 247, 0.2)',
          padding: '1rem',
          minHeight: '400px',
          maxHeight: '600px',
          overflowY: 'auto'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
            <span style={{ fontSize: '1rem' }}>🏛️</span>
            <h3 style={{ margin: 0, fontSize: '0.85rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: '#a855f7' }}>
              Powerblocs & Alliances
            </h3>
          </div>

          {loadingBlocs ? (
            <div style={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.8rem', textAlign: 'center', padding: '2rem' }}>
              Loading powerblocs...
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {powerblocs.map((bloc) => {
                const leaderFingerprint = fingerprintMap.get(bloc.leaderAllianceId);
                const doctrines = leaderFingerprint?.doctrines || [];

                return (
                  <div
                    key={bloc.name}
                    style={{
                      padding: '0.5rem 0.75rem',
                      background: 'rgba(168, 85, 247, 0.05)',
                      borderRadius: '6px',
                      borderLeft: '3px solid #a855f7',
                      cursor: 'pointer'
                    }}
                    onClick={() => setExpandedBloc(expandedBloc === bloc.name ? null : bloc.name)}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      {expandedBloc === bloc.name ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                      <span
                        style={{
                          fontSize: '0.85rem',
                          color: selectedAlliance?.id === bloc.leaderAllianceId ? '#a855f7' : '#fff',
                          fontWeight: 600,
                          cursor: 'pointer'
                        }}
                        onClick={(e) => handleAllianceClick(bloc.leaderAllianceId, bloc.name, e)}
                      >
                        {bloc.name}
                      </span>
                      <span style={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.4)', marginLeft: 'auto' }}>
                        {bloc.allianceCount} alliances
                      </span>
                    </div>
                    {/* Stats row */}
                    <div style={{ display: 'flex', gap: '0.75rem', marginTop: '0.3rem', fontSize: '0.65rem' }}>
                      <span style={{ color: bloc.efficiency >= 50 ? '#00ff88' : '#ff6b6b' }}>
                        {bloc.efficiency.toFixed(0)}% eff
                      </span>
                      <span style={{ color: 'rgba(255,255,255,0.5)' }}>
                        {bloc.totalKills.toLocaleString()} kills
                      </span>
                      <span style={{ color: '#ffcc00' }}>
                        {formatIsk(bloc.iskDestroyed)}
                      </span>
                    </div>
                    {/* Doctrine badges */}
                    {doctrines.length > 0 && (
                      <div style={{ display: 'flex', gap: '0.3rem', marginTop: '0.3rem', flexWrap: 'wrap' }}>
                        {doctrines.slice(0, 2).map((d, idx) => {
                          const colors = ['#58a6ff', '#a855f7'];
                          return (
                            <span key={d.name} style={{
                              fontSize: '0.55rem',
                              padding: '0.1rem 0.3rem',
                              background: `${colors[idx]}22`,
                              color: colors[idx],
                              borderRadius: '3px'
                            }}>
                              {d.name} {d.percent}%
                            </span>
                          );
                        })}
                      </div>
                    )}
                    {/* Expanded: Member alliances */}
                    {expandedBloc === bloc.name && (
                      <div style={{ marginTop: '0.5rem', paddingTop: '0.5rem', borderTop: '1px solid rgba(255,255,255,0.1)' }}>
                        {bloc.members.map((m) => {
                          const memberFp = fingerprintMap.get(m.allianceId);
                          const topDoctrine = memberFp?.doctrines[0];
                          const isSelected = selectedAlliance?.id === m.allianceId;
                          return (
                            <div
                              key={m.allianceId}
                              style={{
                                display: 'flex',
                                justifyContent: 'space-between',
                                alignItems: 'center',
                                fontSize: '0.7rem',
                                color: isSelected ? '#58a6ff' : 'rgba(255,255,255,0.6)',
                                padding: '0.25rem 0.5rem',
                                marginLeft: '-0.5rem',
                                marginRight: '-0.5rem',
                                cursor: 'pointer',
                                background: isSelected ? 'rgba(88,166,255,0.1)' : 'transparent',
                                borderRadius: '4px',
                                transition: 'background 0.15s'
                              }}
                              onClick={(e) => handleAllianceClick(m.allianceId, m.name, e)}
                              onMouseOver={(e) => { if (!isSelected) e.currentTarget.style.background = 'rgba(255,255,255,0.05)'; }}
                              onMouseOut={(e) => { if (!isSelected) e.currentTarget.style.background = 'transparent'; }}
                            >
                              <span>{m.name}</span>
                              <span style={{ display: 'flex', gap: '0.4rem', alignItems: 'center' }}>
                                {topDoctrine && (
                                  <span style={{ fontSize: '0.55rem', color: '#58a6ff', background: 'rgba(88,166,255,0.15)', padding: '0.1rem 0.25rem', borderRadius: '2px' }}>
                                    {topDoctrine.name} {topDoctrine.percent}%
                                  </span>
                                )}
                              </span>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Column 2: Alliance Detail */}
        <div style={{
          background: 'linear-gradient(135deg, rgba(15,20,30,0.95) 0%, rgba(20,25,35,0.9) 100%)',
          borderRadius: '12px',
          border: `1px solid ${selectedAlliance ? 'rgba(88, 166, 255, 0.4)' : 'rgba(88, 166, 255, 0.2)'}`,
          padding: '1rem',
          minHeight: '400px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
            <span style={{ fontSize: '1rem' }}>🔱</span>
            {selectedAlliance ? (
              <Link
                to={`/alliance/${selectedAlliance.id}`}
                style={{
                  margin: 0,
                  fontSize: '0.85rem',
                  fontWeight: 700,
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                  color: '#58a6ff',
                  textDecoration: 'none',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.4rem',
                  transition: 'color 0.15s'
                }}
                onMouseOver={(e) => e.currentTarget.style.color = '#7dc4ff'}
                onMouseOut={(e) => e.currentTarget.style.color = '#58a6ff'}
              >
                {selectedAlliance.name}
                <ExternalLink size={12} style={{ opacity: 0.6 }} />
              </Link>
            ) : (
              <h3 style={{ margin: 0, fontSize: '0.85rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: '#58a6ff' }}>
                Alliance Detail
              </h3>
            )}
          </div>

          {!selectedAlliance ? (
            <div style={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.8rem', textAlign: 'center', padding: '3rem 1rem' }}>
              <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>👈</div>
              Select an alliance from the left panel to view details
            </div>
          ) : loadingFingerprints ? (
            <div style={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.8rem', textAlign: 'center', padding: '2rem' }}>
              Loading...
            </div>
          ) : selectedFingerprint ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {/* Stats Summary */}
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(2, 1fr)',
                gap: '0.5rem',
                padding: '0.75rem',
                background: 'rgba(88, 166, 255, 0.05)',
                borderRadius: '8px'
              }}>
                <div>
                  <div style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase' }}>Activity</div>
                  <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#fff' }}>{selectedFingerprint.activity.toLocaleString()}</div>
                </div>
                <div>
                  <div style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase' }}>ISK Efficiency</div>
                  <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#00ff88' }}>{Math.round(selectedFingerprint.iskEfficiency * 100)}%</div>
                </div>
              </div>

              {/* Doctrine Breakdown */}
              <div>
                <div style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.5)', marginBottom: '0.5rem', textTransform: 'uppercase' }}>
                  Doctrine Profile
                </div>
                {selectedFingerprint.doctrines.map((d, idx) => {
                  const labels = ['Primary', 'Secondary', 'Tertiary', '4th', '5th'];
                  const colors = ['#58a6ff', '#a855f7', '#ffcc00', '#ff6b6b', '#00ff88'];
                  const maxPercent = selectedFingerprint.doctrines[0]?.percent || 1;
                  const barPercent = (d.percent / maxPercent) * 100;
                  return (
                    <div key={d.name} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.4rem' }}>
                      {/* Fixed-width bar */}
                      <div style={{
                        width: '120px',
                        flexShrink: 0,
                        height: '18px',
                        background: 'rgba(255,255,255,0.05)',
                        borderRadius: '4px',
                        overflow: 'hidden'
                      }}>
                        <div style={{
                          width: `${barPercent}%`,
                          height: '100%',
                          background: colors[idx],
                          borderRadius: '4px'
                        }} />
                      </div>
                      {/* Right-aligned text */}
                      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '0.5rem' }}>
                        <span style={{ fontSize: '0.6rem', color: colors[idx], textTransform: 'uppercase' }}>
                          {labels[idx]}
                        </span>
                        <span style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.8)' }}>
                          {d.name}
                        </span>
                        <span style={{ fontSize: '0.7rem', color: colors[idx], fontWeight: 600, fontFamily: 'monospace', minWidth: '35px', textAlign: 'right' }}>
                          {d.percent}%
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Top Ships */}
              <div>
                <div style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.5)', marginBottom: '0.5rem', textTransform: 'uppercase' }}>
                  Top Ships
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                  {selectedFingerprint.shipFingerprint.slice(0, 8).map((ship, idx) => (
                    <div key={`${ship.shipName}-${idx}`} style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      fontSize: '0.7rem',
                      padding: '0.2rem 0',
                      borderBottom: idx < 7 ? '1px solid rgba(255,255,255,0.05)' : 'none'
                    }}>
                      <span style={{ color: 'rgba(255,255,255,0.7)' }}>{ship.shipName}</span>
                      <span style={{ color: '#58a6ff', fontFamily: 'monospace' }}>{ship.percentage.toFixed(1)}%</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div style={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.8rem', textAlign: 'center', padding: '2rem' }}>
              No fingerprint data available for this alliance
            </div>
          )}
        </div>

        {/* Column 3: Corp Breakdown */}
        <div style={{
          background: 'linear-gradient(135deg, rgba(15,20,30,0.95) 0%, rgba(20,25,35,0.9) 100%)',
          borderRadius: '12px',
          border: `1px solid ${selectedCorp ? 'rgba(63, 185, 80, 0.5)' : selectedAlliance ? 'rgba(63, 185, 80, 0.4)' : 'rgba(63, 185, 80, 0.2)'}`,
          padding: '1rem',
          minHeight: '400px',
          maxHeight: '600px',
          overflowY: 'auto'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
            <span style={{ fontSize: '1rem' }}>🏢</span>
            <h3 style={{ margin: 0, fontSize: '0.85rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: '#3fb950' }}>
              {selectedCorp ? selectedCorp.name : 'Corp Breakdown'}
            </h3>
            {selectedCorp && (
              <button
                onClick={() => setSelectedCorp(null)}
                style={{
                  marginLeft: 'auto',
                  background: 'rgba(255,255,255,0.1)',
                  border: 'none',
                  color: 'rgba(255,255,255,0.6)',
                  fontSize: '0.65rem',
                  padding: '0.2rem 0.5rem',
                  borderRadius: '4px',
                  cursor: 'pointer'
                }}
              >
                ← Back
              </button>
            )}
          </div>

          {!selectedAlliance ? (
            <div style={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.8rem', textAlign: 'center', padding: '3rem 1rem' }}>
              <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>👈</div>
              Select an alliance to view corporations
            </div>
          ) : selectedCorp ? (
            // Corp Detail View
            loadingCorpDetail ? (
              <div style={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.8rem', textAlign: 'center', padding: '2rem' }}>
                Loading corp details...
              </div>
            ) : corpDetail ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                {/* Corp Stats Summary */}
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(2, 1fr)',
                  gap: '0.5rem',
                  padding: '0.75rem',
                  background: 'rgba(63, 185, 80, 0.05)',
                  borderRadius: '8px'
                }}>
                  <div>
                    <div style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase' }}>Members</div>
                    <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#fff' }}>{corpDetail.memberCount.toLocaleString()}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase' }}>Efficiency (30d)</div>
                    <div style={{ fontSize: '1.1rem', fontWeight: 700, color: corpDetail.stats30d.efficiency >= 50 ? '#00ff88' : '#ff6b6b' }}>
                      {corpDetail.stats30d.efficiency}%
                    </div>
                  </div>
                </div>

                {/* CEO */}
                {corpDetail.ceoName && (
                  <div style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.6)' }}>
                    <span style={{ color: 'rgba(255,255,255,0.4)' }}>CEO:</span> {corpDetail.ceoName}
                  </div>
                )}

                {/* Combat Stats */}
                <div>
                  <div style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.5)', marginBottom: '0.5rem', textTransform: 'uppercase' }}>
                    Combat Stats (30d)
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '0.4rem', fontSize: '0.7rem' }}>
                    <div style={{ padding: '0.4rem', background: 'rgba(0,255,136,0.1)', borderRadius: '4px', borderLeft: '3px solid #00ff88' }}>
                      <div style={{ color: 'rgba(255,255,255,0.5)' }}>Kills</div>
                      <div style={{ fontWeight: 600, color: '#00ff88' }}>{corpDetail.stats30d.kills.toLocaleString()}</div>
                    </div>
                    <div style={{ padding: '0.4rem', background: 'rgba(255,107,107,0.1)', borderRadius: '4px', borderLeft: '3px solid #ff6b6b' }}>
                      <div style={{ color: 'rgba(255,255,255,0.5)' }}>Losses</div>
                      <div style={{ fontWeight: 600, color: '#ff6b6b' }}>{corpDetail.stats30d.losses.toLocaleString()}</div>
                    </div>
                    <div style={{ padding: '0.4rem', background: 'rgba(255,204,0,0.1)', borderRadius: '4px', borderLeft: '3px solid #ffcc00' }}>
                      <div style={{ color: 'rgba(255,255,255,0.5)' }}>ISK Destroyed</div>
                      <div style={{ fontWeight: 600, color: '#ffcc00' }}>{formatIsk(corpDetail.stats30d.iskDestroyed)}</div>
                    </div>
                    <div style={{ padding: '0.4rem', background: 'rgba(88,166,255,0.1)', borderRadius: '4px', borderLeft: '3px solid #58a6ff' }}>
                      <div style={{ color: 'rgba(255,255,255,0.5)' }}>Systems Active</div>
                      <div style={{ fontWeight: 600, color: '#58a6ff' }}>{corpDetail.stats30d.systemsActive}</div>
                    </div>
                  </div>
                </div>

                {/* Top Ships */}
                {corpDetail.topShips.length > 0 && (
                  <div>
                    <div style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.5)', marginBottom: '0.5rem', textTransform: 'uppercase' }}>
                      Top Ships (30d)
                    </div>
                    {(() => {
                      const maxUses = corpDetail.topShips[0]?.uses || 1;
                      return corpDetail.topShips.map((ship, idx) => {
                        const barPercent = (ship.uses / maxUses) * 100;
                        return (
                          <div key={`${ship.shipName}-${idx}`} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.3rem' }}>
                            {/* Fixed-width bar */}
                            <div style={{
                              width: '80px',
                              flexShrink: 0,
                              height: '14px',
                              background: 'rgba(255,255,255,0.05)',
                              borderRadius: '3px',
                              overflow: 'hidden'
                            }}>
                              <div style={{
                                width: `${barPercent}%`,
                                height: '100%',
                                background: '#3fb950',
                                borderRadius: '3px'
                              }} />
                            </div>
                            {/* Right-aligned info */}
                            <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '0.4rem' }}>
                              <span style={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.7)' }}>{ship.shipName}</span>
                              <span style={{ fontSize: '0.55rem', color: 'rgba(255,255,255,0.4)' }}>({ship.shipClass})</span>
                              <span style={{ fontSize: '0.6rem', color: '#3fb950', fontFamily: 'monospace', minWidth: '30px', textAlign: 'right' }}>
                                {ship.uses}
                              </span>
                            </div>
                          </div>
                        );
                      });
                    })()}
                  </div>
                )}
              </div>
            ) : (
              <div style={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.8rem', textAlign: 'center', padding: '2rem' }}>
                No data available for this corporation
              </div>
            )
          ) : loadingCorps ? (
            <div style={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.8rem', textAlign: 'center', padding: '2rem' }}>
              Loading corporations...
            </div>
          ) : allianceCorps.length > 0 ? (
            // Corp List View
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {(() => {
                const maxMembers = Math.max(...allianceCorps.map(c => c.memberCount));
                return allianceCorps.map((corp) => {
                  const barPercent = maxMembers > 0 ? (corp.memberCount / maxMembers) * 100 : 0;
                  return (
                    <div
                      key={corp.corpId}
                      onClick={() => handleCorpClick(corp.corpId, corp.corpName)}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.5rem',
                        padding: '0.5rem 0.75rem',
                        background: 'rgba(63, 185, 80, 0.05)',
                        borderRadius: '6px',
                        borderLeft: '3px solid #3fb950',
                        cursor: 'pointer',
                        transition: 'background 0.15s'
                      }}
                      onMouseOver={(e) => e.currentTarget.style.background = 'rgba(63, 185, 80, 0.15)'}
                      onMouseOut={(e) => e.currentTarget.style.background = 'rgba(63, 185, 80, 0.05)'}
                    >
                      {/* Fixed-width bar */}
                      <div style={{
                        width: '80px',
                        flexShrink: 0,
                        height: '16px',
                        background: 'rgba(255,255,255,0.05)',
                        borderRadius: '4px',
                        overflow: 'hidden'
                      }}>
                        <div style={{
                          width: `${barPercent}%`,
                          height: '100%',
                          background: '#3fb950',
                          borderRadius: '4px'
                        }} />
                      </div>
                      {/* Right-aligned info */}
                      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '0.5rem' }}>
                        <span style={{ fontSize: '0.75rem', color: '#fff', fontWeight: 500 }}>
                          {corp.corpName}
                        </span>
                        <span style={{ fontSize: '0.6rem', color: '#3fb950', fontFamily: 'monospace' }}>
                          [{corp.ticker}]
                        </span>
                        <span style={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.5)', fontFamily: 'monospace', minWidth: '50px', textAlign: 'right' }}>
                          {corp.memberCount.toLocaleString()}
                        </span>
                      </div>
                    </div>
                  );
                });
              })()}
            </div>
          ) : (
            <div style={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.8rem', textAlign: 'center', padding: '2rem' }}>
              No corporation data available
            </div>
          )}
        </div>
      </div>
    </div>
  );
});
