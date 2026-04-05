/**
 * MiniChart Component
 *
 * Displays a small SVG sparkline chart for timeline data.
 */

interface MiniChartProps {
  data: number[];
  height?: number;
  color?: string;
  showArea?: boolean;
  showLine?: boolean;
}

export function MiniChart({
  data,
  height = 40,
  color = '#58a6ff',
  showArea = true,
  showLine = true,
}: MiniChartProps) {
  if (!data || data.length === 0) {
    return (
      <div style={{ height: `${height}px`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <span style={{ color: '#8b949e', fontSize: '0.65rem' }}>No data</span>
      </div>
    );
  }

  const maxValue = Math.max(...data, 1);
  const width = 100; // percentage
  const numPoints = data.length;
  const xStep = width / (numPoints - 1);

  // Generate SVG path for area chart
  const generateAreaPath = (): string => {
    if (numPoints === 0) return '';

    let path = `M 0,${height}`;

    // Draw top edge (data points)
    data.forEach((value, i) => {
      const x = i * xStep;
      const y = height - (value / maxValue) * height;
      path += ` L ${x},${y}`;
    });

    // Return to baseline
    path += ` L ${width},${height} Z`;

    return path;
  };

  // Generate SVG path for line chart
  const generateLinePath = (): string => {
    if (numPoints === 0) return '';

    let path = '';

    data.forEach((value, i) => {
      const x = i * xStep;
      const y = height - (value / maxValue) * height;
      path += `${i === 0 ? 'M' : ' L'} ${x},${y}`;
    });

    return path;
  };

  return (
    <div style={{ width: '100%', height: `${height}px` }}>
      <svg
        viewBox={`0 0 ${width} ${height}`}
        preserveAspectRatio="none"
        style={{ width: '100%', height: '100%', display: 'block' }}
      >
        {/* Area fill */}
        {showArea && (
          <path
            d={generateAreaPath()}
            fill={color}
            opacity={0.3}
          />
        )}

        {/* Line stroke */}
        {showLine && (
          <path
            d={generateLinePath()}
            fill="none"
            stroke={color}
            strokeWidth={2}
            opacity={0.8}
          />
        )}
      </svg>
    </div>
  );
}
