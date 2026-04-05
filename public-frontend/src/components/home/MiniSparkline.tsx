import { useMemo, memo } from 'react';

interface MiniSparklineProps {
  data: number[];
  width?: number;
  height?: number;
  color?: string;
  showTrend?: boolean;
}

export const MiniSparkline = memo(function MiniSparkline({
  data,
  width = 60,
  height = 20,
  color,
  showTrend = true,
}: MiniSparklineProps) {
  const gradientId = useMemo(
    () => `mini-spark-${Math.random().toString(36).substring(2, 11)}`,
    []
  );

  if (!data || data.length < 2) {
    return <div style={{ width, height, background: 'rgba(255,255,255,0.03)', borderRadius: '3px' }} />;
  }

  const max = Math.max(...data) || 1;
  const min = Math.min(...data);
  const range = max - min || 1;

  // Determine trend color
  const trend = data[data.length - 1] - data[0];
  const trendColor = trend > 0 ? '#00ff88' : trend < 0 ? '#ff4444' : '#888888';
  const effectiveColor = color || (showTrend ? trendColor : '#00d4ff');

  const points = data.map((v, i) => {
    const x = (i / (data.length - 1)) * width;
    const y = height - ((v - min) / range) * (height - 4) - 2;
    return `${x},${y}`;
  }).join(' ');

  return (
    <svg width={width} height={height} style={{ display: 'block' }}>
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={effectiveColor} stopOpacity="0.3" />
          <stop offset="100%" stopColor={effectiveColor} stopOpacity="0" />
        </linearGradient>
      </defs>
      <polygon
        points={`0,${height} ${points} ${width},${height}`}
        fill={`url(#${gradientId})`}
      />
      <polyline
        points={points}
        fill="none"
        stroke={effectiveColor}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
});
