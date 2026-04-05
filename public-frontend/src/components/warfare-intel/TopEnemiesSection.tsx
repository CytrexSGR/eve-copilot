// src/components/warfare-intel/TopEnemiesSection.tsx
import type { FastEnemy } from '../../types/intelligence';

interface TopEnemy extends FastEnemy {
  efficiency_vs_them?: number;
}

interface TopEnemiesSectionProps {
  enemies: TopEnemy[];
  timeframeLabel: string;
  loading?: boolean;
}

function formatIsk(value: number | string): string {
  const num = typeof value === 'string' ? parseFloat(value) : value;
  if (num >= 1e9) return `${(num / 1e9).toFixed(1)}B`;
  if (num >= 1e6) return `${(num / 1e6).toFixed(0)}M`;
  if (num >= 1e3) return `${(num / 1e3).toFixed(0)}K`;
  return num.toString();
}

export function TopEnemiesSection({ enemies, timeframeLabel, loading }: TopEnemiesSectionProps) {
  const sectionStyle = {
    background: 'linear-gradient(135deg, rgba(15,20,30,0.95) 0%, rgba(20,25,35,0.9) 100%)',
    borderRadius: '12px',
    border: '1px solid rgba(100, 150, 255, 0.1)',
    padding: '1.5rem',
    marginBottom: '1.5rem'
  };

  if (loading) {
    return (
      <div style={sectionStyle}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
          <span style={{ fontSize: '1.25rem' }}>🎯</span>
          <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: '#ff8800' }}>
            Top Enemies
          </h3>
        </div>
        <div style={{ color: 'rgba(255,255,255,0.4)', padding: '2rem', textAlign: 'center' }}>
          Loading enemies...
        </div>
      </div>
    );
  }

  const top3 = enemies.slice(0, 3);
  const rest = enemies.slice(3);

  return (
    <div style={sectionStyle}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{ fontSize: '1.25rem' }}>🎯</span>
          <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: '#ff8800' }}>
            Top Enemies
          </h3>
        </div>
        <span style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.4)' }}>
          {timeframeLabel}
        </span>
      </div>

      {/* Top 3 Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginBottom: '1rem' }}>
        {top3.length === 0 ? (
          <div style={{ color: 'rgba(255,255,255,0.4)', padding: '1rem', textAlign: 'center', gridColumn: '1 / -1' }}>
            No enemy activity in selected timeframe
          </div>
        ) : (
          top3.map(enemy => {
            const efficiency: number = Number.isFinite(enemy.efficiency_vs_them) ? enemy.efficiency_vs_them! : 50;
            const efficiencyColor = efficiency >= 60 ? '#00ff88' : efficiency >= 40 ? '#ffcc00' : '#ff4444';
            return (
              <div
                key={enemy.alliance_id}
                style={{
                  padding: '1rem',
                  background: 'rgba(0,0,0,0.3)',
                  borderRadius: '10px',
                  border: '1px solid rgba(255,255,255,0.05)'
                }}
              >
                <div style={{ marginBottom: '0.75rem' }}>
                  <div style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    [{enemy.ticker || '???'}]
                  </div>
                  <div style={{ fontSize: '0.95rem', fontWeight: 600, color: '#fff', lineHeight: 1.3 }}>
                    {enemy.alliance_name}
                  </div>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                  <span style={{ fontSize: '0.8rem', color: 'rgba(255,255,255,0.5)' }}>{enemy.kills} kills</span>
                  <span style={{ fontSize: '0.8rem', color: '#00d4ff' }}>{formatIsk(enemy.isk_destroyed)}</span>
                </div>
                {/* Efficiency Bar */}
                <div style={{ marginTop: '0.5rem' }}>
                  <div style={{
                    height: '4px',
                    background: 'rgba(255,255,255,0.1)',
                    borderRadius: '2px',
                    overflow: 'hidden'
                  }}>
                    <div style={{
                      width: `${efficiency}%`,
                      height: '100%',
                      background: efficiencyColor,
                      borderRadius: '2px'
                    }} />
                  </div>
                  <div style={{ fontSize: '0.7rem', color: efficiencyColor, marginTop: '0.25rem' }}>
                    {efficiency.toFixed(0)}% efficiency
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* More enemies link */}
      {rest.length > 0 && (
        <div style={{ fontSize: '0.8rem', color: 'rgba(255,255,255,0.4)', textAlign: 'center' }}>
          + {rest.length} more alliance{rest.length !== 1 ? 's' : ''} engaged
        </div>
      )}
    </div>
  );
}
