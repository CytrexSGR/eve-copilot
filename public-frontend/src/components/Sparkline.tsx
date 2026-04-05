import { useMemo } from 'react';

interface SparklineProps {
  data: number[];
  width?: number;
  height?: number;
  color?: string;
  fillColor?: string;
  strokeWidth?: number;
  showArea?: boolean;
}

export function Sparkline({
  data,
  width = 100,
  height = 30,
  color = 'var(--success)',
  fillColor,
  strokeWidth = 1.5,
  showArea = true
}: SparklineProps) {
  const pathData = useMemo(() => {
    if (!data || data.length < 2) return { line: '', area: '' };

    const min = Math.min(...data);
    const max = Math.max(...data);
    const range = max - min || 1;

    const padding = 2;
    const effectiveWidth = width - padding * 2;
    const effectiveHeight = height - padding * 2;

    const points = data.map((value, index) => {
      const x = padding + (index / (data.length - 1)) * effectiveWidth;
      const y = padding + effectiveHeight - ((value - min) / range) * effectiveHeight;
      return { x, y };
    });

    // Create line path
    const line = points
      .map((p, i) => (i === 0 ? `M ${p.x} ${p.y}` : `L ${p.x} ${p.y}`))
      .join(' ');

    // Create area path (for gradient fill)
    const area = `${line} L ${points[points.length - 1].x} ${height - padding} L ${padding} ${height - padding} Z`;

    return { line, area };
  }, [data, width, height]);

  if (!data || data.length < 2) {
    return (
      <div style={{ width, height, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <span style={{ fontSize: '0.6rem', color: 'var(--text-tertiary)' }}>No data</span>
      </div>
    );
  }

  // Determine trend color based on first vs last value
  const trend = data[data.length - 1] - data[0];
  const trendColor = trend > 0 ? 'var(--success)' : trend < 0 ? 'var(--danger)' : 'var(--text-tertiary)';
  const effectiveColor = color === 'auto' ? trendColor : color;
  const effectiveFillColor = fillColor || effectiveColor;

  // Unique ID for gradient
  const gradientId = useMemo(() => `sparkline-gradient-${Math.random().toString(36).substr(2, 9)}`, []);

  return (
    <svg width={width} height={height} style={{ display: 'block' }}>
      <defs>
        <linearGradient id={gradientId} x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor={effectiveFillColor} stopOpacity="0.3" />
          <stop offset="100%" stopColor={effectiveFillColor} stopOpacity="0" />
        </linearGradient>
      </defs>

      {showArea && pathData.area && (
        <path
          d={pathData.area}
          fill={`url(#${gradientId})`}
        />
      )}

      <path
        d={pathData.line}
        fill="none"
        stroke={effectiveColor}
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeLinejoin="round"
      />

      {/* End point dot */}
      {data.length >= 2 && (
        <circle
          cx={width - 2}
          cy={2 + (height - 4) - ((data[data.length - 1] - Math.min(...data)) / (Math.max(...data) - Math.min(...data) || 1)) * (height - 4)}
          r={2}
          fill={effectiveColor}
        />
      )}
    </svg>
  );
}

// Helper component for isotope trend visualization
interface IsotopeSparklineProps {
  snapshots: Array<{ delta_percent: number; timestamp: string }>;
  width?: number;
  height?: number;
}

export function IsotopeSparkline({ snapshots, width = 120, height = 32 }: IsotopeSparklineProps) {
  // Reverse to show oldest → newest (left to right)
  const data = useMemo(() => {
    return [...snapshots]
      .reverse()
      .slice(-24) // Last 24 data points
      .map(s => s.delta_percent);
  }, [snapshots]);

  // Determine color based on current value
  const currentValue = data[data.length - 1] || 0;
  const color = currentValue >= 10 ? 'var(--danger)' :
                currentValue >= 5 ? 'var(--warning)' :
                'var(--success)';

  return (
    <div style={{
      background: 'var(--bg-elevated)',
      borderRadius: '4px',
      padding: '4px',
      display: 'inline-block'
    }}>
      <Sparkline
        data={data}
        width={width}
        height={height}
        color={color}
        showArea={true}
      />
    </div>
  );
}
