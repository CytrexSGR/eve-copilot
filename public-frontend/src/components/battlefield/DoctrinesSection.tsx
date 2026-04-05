import { useState, useEffect } from 'react';

interface DoctrineUsage {
  doctrine_name: string;
  ship_type: string;
  count: number;
  percentage: number;
  avg_fleet_size: number;
}

interface DoctrineMatchup {
  doctrine_a: string;
  doctrine_b: string;
  alliance_a_ticker: string;
  alliance_b_ticker: string;
  wins_a: number;
  wins_b: number;
  total_fights: number;
}

interface DoctrinesSectionProps {
  timeframeMinutes?: number;
}

function getTimeframeLabel(minutes: number): string {
  if (minutes <= 10) return '10m';
  if (minutes <= 60) return '1h';
  if (minutes <= 720) return '12h';
  if (minutes <= 1440) return '24h';
  return '7d';
}

export function DoctrinesSection({ timeframeMinutes = 1440 }: DoctrinesSectionProps) {
  const [doctrines, setDoctrines] = useState<DoctrineUsage[]>([]);
  const [matchups, setMatchups] = useState<DoctrineMatchup[]>([]);
  const [loading, setLoading] = useState(true);

  const timeframeLabel = getTimeframeLabel(timeframeMinutes);

  useEffect(() => {
    // Static data — backend endpoint not yet implemented
    setDoctrines([
      { doctrine_name: 'Muninn Fleet', ship_type: 'Muninn', count: 156, percentage: 34, avg_fleet_size: 45 },
      { doctrine_name: 'Eagle Fleet', ship_type: 'Eagle', count: 98, percentage: 21, avg_fleet_size: 38 },
      { doctrine_name: 'Cerberus Fleet', ship_type: 'Cerberus', count: 67, percentage: 15, avg_fleet_size: 52 },
      { doctrine_name: 'Jackdaw Fleet', ship_type: 'Jackdaw', count: 54, percentage: 12, avg_fleet_size: 65 },
      { doctrine_name: 'Ferox Fleet', ship_type: 'Ferox', count: 43, percentage: 9, avg_fleet_size: 42 },
      { doctrine_name: 'Nightmare Fleet', ship_type: 'Nightmare', count: 38, percentage: 8, avg_fleet_size: 28 },
    ]);
    setMatchups([
      { doctrine_a: 'Muninn', doctrine_b: 'Cerberus', alliance_a_ticker: 'INIT', alliance_b_ticker: 'HORDE', wins_a: 12, wins_b: 5, total_fights: 17 },
      { doctrine_a: 'Eagle', doctrine_b: 'Muninn', alliance_a_ticker: 'GSF', alliance_b_ticker: 'FRT', wins_a: 8, wins_b: 11, total_fights: 19 },
      { doctrine_a: 'Cerberus', doctrine_b: 'Jackdaw', alliance_a_ticker: 'HORDE', alliance_b_ticker: 'BRAVE', wins_a: 6, wins_b: 2, total_fights: 8 },
    ]);
    setLoading(false);
  }, [timeframeMinutes]);

  const totalFleets = doctrines.reduce((sum, d) => sum + d.count, 0);

  return (
    <div style={{
      background: 'rgba(0,0,0,0.3)',
      borderRadius: '8px',
      border: '1px solid rgba(255,255,255,0.08)',
      overflow: 'hidden',
      height: '480px',
      display: 'flex',
      flexDirection: 'column',
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
          <span style={{ fontSize: '0.65rem' }}>📊</span>
          <span style={{ fontSize: '0.7rem', fontWeight: 700, color: '#a855f7', textTransform: 'uppercase' }}>
            Fleet Doctrines
          </span>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', fontSize: '0.55rem' }}>
          <span style={{ color: '#a855f7', fontWeight: 700, fontFamily: 'monospace' }}>{totalFleets}</span>
          <span style={{ color: 'rgba(255,255,255,0.4)' }}>fleets tracked</span>
          <span style={{ color: '#a855f7' }}>({timeframeLabel})</span>
        </div>
      </div>

      {/* Content */}
      <div style={{
        padding: '0.25rem',
        flex: 1,
        overflowY: 'auto',
        overflowX: 'hidden',
      }}>
        {loading ? (
          <div style={{ padding: '0.5rem' }}>
            {[1, 2, 3, 4].map(i => (
              <div key={i} className="skeleton" style={{ height: '40px', borderRadius: '4px', marginBottom: '0.2rem' }} />
            ))}
          </div>
        ) : (
          <>
            {/* Top Doctrines */}
            <div style={{ marginBottom: '0.5rem' }}>
              <div style={{
                fontSize: '0.55rem',
                color: 'rgba(255,255,255,0.35)',
                textTransform: 'uppercase',
                padding: '0.25rem 0.4rem',
                letterSpacing: '0.05em'
              }}>
                Most Used
              </div>
              {doctrines.slice(0, 6).map((doctrine, idx) => (
                <DoctrineBar key={doctrine.doctrine_name} doctrine={doctrine} rank={idx + 1} />
              ))}
            </div>

            {/* Recent Matchups */}
            {matchups.length > 0 && (
              <div>
                <div style={{
                  fontSize: '0.55rem',
                  color: 'rgba(255,255,255,0.35)',
                  textTransform: 'uppercase',
                  padding: '0.25rem 0.4rem',
                  letterSpacing: '0.05em',
                  marginTop: '0.3rem'
                }}>
                  Recent Matchups
                </div>
                {matchups.slice(0, 4).map((matchup, idx) => (
                  <MatchupCard key={idx} matchup={matchup} />
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

function DoctrineBar({ doctrine, rank }: { doctrine: DoctrineUsage; rank: number }) {
  // Color gradient based on rank
  const colors = ['#a855f7', '#8b5cf6', '#7c3aed', '#6d28d9', '#5b21b6', '#4c1d95'];
  const color = colors[Math.min(rank - 1, colors.length - 1)];

  return (
    <div style={{
      padding: '0.35rem 0.4rem',
      marginBottom: '0.15rem',
      background: `${color}15`,
      borderRadius: '4px',
      borderLeft: `2px solid ${color}`,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
        {/* Rank */}
        <span style={{
          fontSize: '0.6rem',
          fontWeight: 800,
          color: 'rgba(255,255,255,0.25)',
          width: '14px',
          textAlign: 'center'
        }}>
          #{rank}
        </span>

        {/* Name + Bar */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.15rem' }}>
            <span style={{ fontSize: '0.7rem', fontWeight: 700, color: '#fff' }}>
              {doctrine.doctrine_name}
            </span>
            <span style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.5)', fontFamily: 'monospace' }}>
              {doctrine.count} <span style={{ color: 'rgba(255,255,255,0.3)' }}>({doctrine.percentage}%)</span>
            </span>
          </div>
          <div style={{ height: '3px', background: 'rgba(255,255,255,0.1)', borderRadius: '2px', overflow: 'hidden' }}>
            <div style={{ width: `${doctrine.percentage}%`, height: '100%', background: color, borderRadius: '2px' }} />
          </div>
        </div>
      </div>
    </div>
  );
}

function MatchupCard({ matchup }: { matchup: DoctrineMatchup }) {
  const winrateA = matchup.total_fights > 0 ? (matchup.wins_a / matchup.total_fights) * 100 : 50;
  const winnerColor = winrateA >= 50 ? '#00d4ff' : '#ff8800';

  return (
    <div style={{
      padding: '0.35rem 0.4rem',
      marginBottom: '0.15rem',
      background: `${winnerColor}10`,
      borderRadius: '4px',
      borderLeft: `2px solid ${winnerColor}`,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        {/* Matchup Names */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', fontSize: '0.7rem' }}>
          <span style={{ color: '#00d4ff', fontWeight: 700 }}>{matchup.doctrine_a}</span>
          <span style={{ color: 'rgba(255,255,255,0.25)', fontSize: '0.55rem' }}>vs</span>
          <span style={{ color: '#ff8800', fontWeight: 700 }}>{matchup.doctrine_b}</span>
        </div>

        {/* W/L Record */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', fontSize: '0.65rem' }}>
          <span style={{ color: '#00d4ff', fontFamily: 'monospace', fontWeight: 700 }}>{matchup.wins_a}</span>
          <span style={{ color: 'rgba(255,255,255,0.2)' }}>-</span>
          <span style={{ color: '#ff8800', fontFamily: 'monospace', fontWeight: 700 }}>{matchup.wins_b}</span>
        </div>
      </div>

      {/* Efficiency Bar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', marginTop: '0.2rem' }}>
        <span style={{ fontSize: '0.55rem', color: '#00d4ff' }}>[{matchup.alliance_a_ticker}]</span>
        <div style={{ flex: 1, display: 'flex', height: '3px', borderRadius: '2px', overflow: 'hidden', background: 'rgba(255,255,255,0.1)' }}>
          <div style={{ width: `${winrateA}%`, background: '#00d4ff' }} />
          <div style={{ width: `${100 - winrateA}%`, background: '#ff8800' }} />
        </div>
        <span style={{ fontSize: '0.55rem', color: '#ff8800' }}>[{matchup.alliance_b_ticker}]</span>
      </div>
    </div>
  );
}
