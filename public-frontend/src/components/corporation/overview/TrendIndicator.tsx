/**
 * TrendIndicator Component
 *
 * Displays trend direction with icon and color coding.
 */

interface TrendIndicatorProps {
  trend: 'increasing' | 'decreasing' | 'stable' | 'expanding' | 'contracting' | 'escalating' | 'declining' | 'steady';
  size?: 'small' | 'medium' | 'large';
}

export function TrendIndicator({ trend, size = 'medium' }: TrendIndicatorProps) {
  const sizeMap = {
    small: '0.75rem',
    medium: '1rem',
    large: '1.25rem',
  };

  const trendConfig = {
    increasing: { icon: '⬆️', color: '#3fb950', label: 'Increasing' },
    escalating: { icon: '⬆️', color: '#3fb950', label: 'Escalating' },
    expanding: { icon: '⬆️', color: '#3fb950', label: 'Expanding' },
    decreasing: { icon: '⬇️', color: '#f85149', label: 'Decreasing' },
    declining: { icon: '⬇️', color: '#f85149', label: 'Declining' },
    contracting: { icon: '⬇️', color: '#f85149', label: 'Contracting' },
    stable: { icon: '→', color: '#58a6ff', label: 'Stable' },
    steady: { icon: '→', color: '#58a6ff', label: 'Steady' },
  };

  const config = trendConfig[trend];

  return (
    <span
      style={{
        color: config.color,
        fontSize: sizeMap[size],
        fontWeight: 600,
        display: 'inline-flex',
        alignItems: 'center',
        gap: '0.25rem',
      }}
      title={config.label}
    >
      {config.icon}
    </span>
  );
}
