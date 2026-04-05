interface DataPoint {
  label: string;
  value: number;
}

interface LineChartProps {
  data: DataPoint[];
  width?: number;
  height?: number;
  color?: string;
  showArea?: boolean;
  showDots?: boolean;
  formatValue?: (v: number) => string;
}

export function LineChart({
  data,
  width = 200,
  height = 60,
  color = 'var(--accent-blue)',
  showArea = true,
  showDots = false,
  formatValue = (v) => v.toString()
}: LineChartProps) {
  if (!data.length) return null;

  const padding = { top: 5, right: 5, bottom: 5, left: 5 };
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;

  const values = data.map(d => d.value);
  const minValue = Math.min(...values);
  const maxValue = Math.max(...values);
  const range = maxValue - minValue || 1;

  const points = data.map((d, i) => {
    const x = padding.left + (i / (data.length - 1)) * chartWidth;
    const y = padding.top + chartHeight - ((d.value - minValue) / range) * chartHeight;
    return { x, y, ...d };
  });

  const linePath = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ');
  const areaPath = `${linePath} L ${points[points.length - 1].x} ${height - padding.bottom} L ${padding.left} ${height - padding.bottom} Z`;

  const trend = values[values.length - 1] - values[0];
  const trendColor = trend >= 0 ? 'var(--success)' : 'var(--danger)';

  return (
    <svg width={width} height={height} style={{ overflow: 'visible' }}>
      {showArea && (
        <path d={areaPath} fill={color} opacity={0.15} />
      )}
      <path d={linePath} fill="none" stroke={color} strokeWidth={2} />
      {showDots && points.map((p, i) => (
        <circle key={i} cx={p.x} cy={p.y} r={3} fill={color} />
      ))}
      {/* Trend indicator */}
      <text
        x={width - 5}
        y={12}
        textAnchor="end"
        fill={trendColor}
        fontSize={10}
        fontWeight="bold"
      >
        {trend >= 0 ? '▲' : '▼'} {formatValue(Math.abs(trend))}
      </text>
    </svg>
  );
}
