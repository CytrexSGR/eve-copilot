interface ShipClassData {
  battle_id?: number;
  system_id?: number;
  hours?: number;
  total_kills: number;
  group_by: string;
  breakdown: {
    [key: string]: number;
  };
}

interface BattleShipClassesProps {
  shipClasses: ShipClassData | null;
}

function getShipClassColor(cls: string): string {
  const lowerCls = cls.toLowerCase();
  if (lowerCls.includes('capital') || lowerCls.includes('titan') || lowerCls.includes('supercarrier')) return '#ff4444';
  if (lowerCls.includes('battleship')) return '#ff6b00';
  if (lowerCls.includes('battlecruiser')) return '#ff9500';
  if (lowerCls.includes('cruiser')) return '#00d4ff';
  if (lowerCls.includes('destroyer')) return '#a855f7';
  if (lowerCls.includes('frigate')) return '#00ff88';
  if (lowerCls.includes('logistics')) return '#22d3ee';
  if (lowerCls.includes('stealth') || lowerCls.includes('bomber')) return '#dc2626';
  if (lowerCls.includes('industrial') || lowerCls.includes('hauler')) return '#8b949e';
  if (lowerCls.includes('mining')) return '#fb923c';
  if (lowerCls.includes('capsule') || lowerCls.includes('pod')) return '#6b7280';
  return '#888';
}

function getShipClassLabel(cls: string): string {
  if (cls.includes(':')) {
    const [category, role] = cls.split(':');
    const categoryLabel = category.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    const roleLabel = role.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    return `${categoryLabel} (${roleLabel})`;
  }
  return cls.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}

export function BattleShipClasses({ shipClasses }: BattleShipClassesProps) {
  const entries = shipClasses
    ? Object.entries(shipClasses.breakdown)
        .filter(([, count]) => count > 0)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 10)
    : [];
  const maxCount = entries.length > 0 ? Math.max(...entries.map(([, c]) => c)) : 1;

  return (
    <div style={{
      background: 'rgba(0,0,0,0.3)',
      borderRadius: '8px',
      border: '1px solid rgba(255,255,255,0.08)',
      overflow: 'hidden',
      marginBottom: '1rem',
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
            background: '#ff6b00',
          }} />
          <span style={{
            fontSize: '0.75rem',
            fontWeight: 700,
            color: '#ff6b00',
            textTransform: 'uppercase'
          }}>
            Ship Classes Destroyed
          </span>
        </div>

        {/* Summary Stats */}
        {shipClasses && (
          <div style={{ display: 'flex', gap: '1rem', fontSize: '0.65rem' }}>
            <span>
              <span style={{ color: '#ff6b00', fontWeight: 700, fontFamily: 'monospace' }}>
                {shipClasses.total_kills}
              </span>
              <span style={{ color: 'rgba(255,255,255,0.4)', marginLeft: '0.25rem' }}>ships</span>
            </span>
            <span>
              <span style={{ color: '#00d4ff', fontWeight: 700, fontFamily: 'monospace' }}>
                {entries.length}
              </span>
              <span style={{ color: 'rgba(255,255,255,0.4)', marginLeft: '0.25rem' }}>classes</span>
            </span>
          </div>
        )}
      </div>

      {/* Content */}
      <div style={{ padding: '0.4rem' }}>
        {entries.length > 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.15rem' }}>
            {entries.map(([shipClass, count], idx) => {
              const percentage = (count / maxCount) * 100;
              const color = getShipClassColor(shipClass);
              const isTop = idx === 0;

              return (
                <div
                  key={shipClass}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.35rem',
                    padding: '0.25rem 0.4rem',
                    background: isTop ? `${color}15` : 'rgba(0,0,0,0.2)',
                    borderRadius: '4px',
                    borderLeft: `2px solid ${color}`,
                  }}
                >
                  {/* Rank */}
                  <span style={{
                    fontSize: '0.6rem',
                    fontWeight: 700,
                    color: isTop ? color : 'rgba(255,255,255,0.4)',
                    width: '18px',
                    textAlign: 'center',
                  }}>
                    #{idx + 1}
                  </span>

                  {/* Class Name */}
                  <div style={{
                    width: '110px',
                    fontSize: '0.7rem',
                    fontWeight: isTop ? 700 : 500,
                    color: isTop ? '#fff' : 'rgba(255,255,255,0.7)',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                  }}>
                    {getShipClassLabel(shipClass)}
                  </div>

                  {/* Bar */}
                  <div style={{
                    flex: 1,
                    height: '10px',
                    background: 'rgba(255,255,255,0.05)',
                    borderRadius: '2px',
                    overflow: 'hidden',
                  }}>
                    <div style={{
                      height: '100%',
                      width: `${percentage}%`,
                      background: `linear-gradient(90deg, ${color}80, ${color})`,
                      borderRadius: '2px',
                      transition: 'width 0.3s ease',
                    }} />
                  </div>

                  {/* Count */}
                  <div style={{
                    width: '28px',
                    textAlign: 'right',
                    fontWeight: 700,
                    fontSize: '0.7rem',
                    fontFamily: 'monospace',
                    color: isTop ? color : '#fff',
                  }}>
                    {count}
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div style={{
            padding: '1.5rem',
            textAlign: 'center',
            color: 'rgba(255,255,255,0.3)',
            fontSize: '0.75rem',
          }}>
            No ship class data available
          </div>
        )}
      </div>
    </div>
  );
}
