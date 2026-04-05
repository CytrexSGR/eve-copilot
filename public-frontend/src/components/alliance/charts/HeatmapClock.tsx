// src/components/alliance/charts/HeatmapClock.tsx
interface HeatmapClockProps {
  hourlyData: number[]; // 24 values (0-23 hours)
  size?: number;
  color?: string;
  dangerColor?: string;
}

export function HeatmapClock({
  hourlyData,
  size = 120,
  color = 'var(--success)',
  dangerColor = 'var(--danger)'
}: HeatmapClockProps) {
  if (hourlyData.length !== 24) return null;

  const maxValue = Math.max(...hourlyData) || 1;
  const center = size / 2;
  const innerRadius = size * 0.25;
  const outerRadius = size * 0.45;

  const peakHour = hourlyData.indexOf(Math.max(...hourlyData));
  const safeHour = hourlyData.indexOf(Math.min(...hourlyData));

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.5rem' }}>
      <svg width={size} height={size}>
        {/* Hour segments */}
        {hourlyData.map((value, hour) => {
          const intensity = value / maxValue;
          const angleStart = (hour - 6) * 15 * (Math.PI / 180); // Start at 6 o'clock position
          const angleEnd = (hour - 5) * 15 * (Math.PI / 180);

          const x1 = center + innerRadius * Math.cos(angleStart);
          const y1 = center + innerRadius * Math.sin(angleStart);
          const x2 = center + outerRadius * Math.cos(angleStart);
          const y2 = center + outerRadius * Math.sin(angleStart);
          const x3 = center + outerRadius * Math.cos(angleEnd);
          const y3 = center + outerRadius * Math.sin(angleEnd);
          const x4 = center + innerRadius * Math.cos(angleEnd);
          const y4 = center + innerRadius * Math.sin(angleEnd);

          const segmentColor = intensity > 0.7 ? dangerColor : color;

          return (
            <path
              key={hour}
              d={`M ${x1} ${y1} L ${x2} ${y2} A ${outerRadius} ${outerRadius} 0 0 1 ${x3} ${y3} L ${x4} ${y4} A ${innerRadius} ${innerRadius} 0 0 0 ${x1} ${y1}`}
              fill={segmentColor}
              opacity={0.2 + intensity * 0.8}
              stroke="var(--bg-primary)"
              strokeWidth={1}
            />
          );
        })}
        {/* Center text */}
        <text x={center} y={center - 5} textAnchor="middle" fill="var(--text-secondary)" fontSize={8}>
          UTC
        </text>
        <text x={center} y={center + 8} textAnchor="middle" fill="var(--text-primary)" fontSize={10} fontWeight="bold">
          24H
        </text>
        {/* Hour markers */}
        {[0, 6, 12, 18].map(hour => {
          const angle = (hour - 6) * 15 * (Math.PI / 180);
          const x = center + (outerRadius + 8) * Math.cos(angle);
          const y = center + (outerRadius + 8) * Math.sin(angle);
          return (
            <text key={hour} x={x} y={y} textAnchor="middle" dominantBaseline="middle" fill="var(--text-tertiary)" fontSize={8}>
              {hour}
            </text>
          );
        })}
      </svg>
      <div style={{ display: 'flex', gap: '1rem', fontSize: '0.7rem' }}>
        <span style={{ color: dangerColor }}>Peak: {peakHour}:00</span>
        <span style={{ color }}>Safe: {safeHour}:00</span>
      </div>
    </div>
  );
}
