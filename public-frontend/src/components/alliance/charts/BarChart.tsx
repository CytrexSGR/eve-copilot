export interface BarItem {
  label: string;
  value: number;
  secondaryValue?: number;
  color?: string;
}

interface BarChartProps {
  items: BarItem[];
  maxItems?: number;
  showValues?: boolean;
  formatValue?: (v: number) => string;
  formatSecondary?: (v: number) => string;
  color?: string;
}

export function BarChart({
  items,
  maxItems = 10,
  showValues = true,
  formatValue = (v) => v.toLocaleString(),
  formatSecondary,
  color = 'var(--accent-blue)'
}: BarChartProps) {
  const displayItems = items.slice(0, maxItems);
  const maxValue = Math.max(...displayItems.map(i => i.value)) || 1;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
      {displayItems.map((item, i) => {
        const percentage = (item.value / maxValue) * 100;
        const barColor = item.color || color;

        return (
          <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{
              width: '80px',
              fontSize: '0.75rem',
              color: 'var(--text-secondary)',
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis'
            }}>
              {item.label}
            </span>
            <div style={{
              flex: 1,
              height: '16px',
              background: 'var(--bg-elevated)',
              borderRadius: '2px',
              overflow: 'hidden',
              position: 'relative'
            }}>
              <div style={{
                height: '100%',
                width: `${percentage}%`,
                background: barColor,
                borderRadius: '2px',
                transition: 'width 0.3s ease'
              }} />
            </div>
            {showValues && (
              <div style={{
                display: 'flex',
                gap: '0.5rem',
                fontSize: '0.75rem',
                minWidth: '80px',
                justifyContent: 'flex-end'
              }}>
                <span style={{ color: 'var(--text-primary)', fontWeight: 500 }}>
                  {formatValue(item.value)}
                </span>
                {item.secondaryValue !== undefined && formatSecondary && (
                  <span style={{ color: 'var(--text-tertiary)' }}>
                    {formatSecondary(item.secondaryValue)}
                  </span>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
