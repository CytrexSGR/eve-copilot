interface Segment {
  label: string;
  value: number;
  color: string;
}

interface DonutChartProps {
  segments: Segment[];
  size?: number;
  strokeWidth?: number;
  showLegend?: boolean;
}

export function DonutChart({
  segments,
  size = 80,
  strokeWidth = 12,
  showLegend = true
}: DonutChartProps) {
  const total = segments.reduce((sum, s) => sum + s.value, 0);
  if (total === 0) return null;

  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const center = size / 2;

  let cumulativePercent = 0;

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
      <svg width={size} height={size}>
        {segments.map((segment, i) => {
          const percent = segment.value / total;
          const strokeDasharray = `${percent * circumference} ${circumference}`;
          const rotation = cumulativePercent * 360 - 90;
          cumulativePercent += percent;

          return (
            <circle
              key={i}
              cx={center}
              cy={center}
              r={radius}
              fill="none"
              stroke={segment.color}
              strokeWidth={strokeWidth}
              strokeDasharray={strokeDasharray}
              transform={`rotate(${rotation} ${center} ${center})`}
              style={{ transition: 'stroke-dasharray 0.3s ease' }}
            />
          );
        })}
        <text
          x={center}
          y={center}
          textAnchor="middle"
          dominantBaseline="middle"
          fill="var(--text-primary)"
          fontSize={12}
          fontWeight="bold"
        >
          {total.toLocaleString()}
        </text>
      </svg>
      {showLegend && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
          {segments.map((s, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.75rem' }}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: s.color }} />
              <span style={{ color: 'var(--text-secondary)' }}>{s.label}</span>
              <span style={{ color: 'var(--text-primary)', fontWeight: 500 }}>
                {((s.value / total) * 100).toFixed(1)}%
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
