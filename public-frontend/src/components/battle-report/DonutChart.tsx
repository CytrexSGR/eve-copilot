interface DonutChartData {
  label: string;
  value: number;
  color: string;
}

interface DonutChartProps {
  data: DonutChartData[];
  size?: number;
}

export function DonutChart({ data, size = 120 }: DonutChartProps) {
  const total = data.reduce((sum, d) => sum + d.value, 0);
  if (total === 0) return null;

  const strokeWidth = 20;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;

  let currentOffset = 0;

  return (
    <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
      {data.map((item, idx) => {
        const percentage = item.value / total;
        const strokeDasharray = `${percentage * circumference} ${circumference}`;
        const strokeDashoffset = -currentOffset * circumference;
        currentOffset += percentage;

        return (
          <circle
            key={idx}
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={item.color}
            strokeWidth={strokeWidth}
            strokeDasharray={strokeDasharray}
            strokeDashoffset={strokeDashoffset}
            style={{ transition: 'all 0.3s ease' }}
          />
        );
      })}
      <circle cx={size / 2} cy={size / 2} r={radius - strokeWidth / 2} fill="rgba(15,20,30,0.95)" />
    </svg>
  );
}
