// ---------------------------------------------------------------------------
// Sparkline & DualSparkline — lightweight inline SVG chart components
// ---------------------------------------------------------------------------

interface SparklineProps {
  data: number[];
  width?: number;
  height?: number;
  color?: string;
  fillOpacity?: number;
}

export function Sparkline({ data: rawData, width = 200, height = 40, color = '#3fb950', fillOpacity = 0.2 }: SparklineProps) {
  const data = rawData.map(v => (Number.isFinite(v) ? v : 0));
  if (data.length < 2) return null;
  const max = Math.max(...data, 1);
  const points = data.map((v, i) => {
    const x = (i / (data.length - 1)) * width;
    const y = height - (v / max) * (height - 4);
    return `${x},${y}`;
  }).join(' ');

  const areaPath = `M0,${height} ` +
    data.map((v, i) => {
      const x = (i / (data.length - 1)) * width;
      const y = height - (v / max) * (height - 4);
      return `L${x},${y}`;
    }).join(' ') +
    ` L${width},${height} Z`;

  return (
    <svg width={width} height={height} style={{ display: 'block' }}>
      <path d={areaPath} fill={color} opacity={fillOpacity} />
      <polyline
        points={points}
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        opacity="0.8"
      />
    </svg>
  );
}

// ---------------------------------------------------------------------------
// DualSparkline — overlay two data series (e.g. income + expense)
// ---------------------------------------------------------------------------

interface DualSparklineProps {
  data1: number[];
  data2: number[];
  width?: number;
  height?: number;
  color1?: string;
  color2?: string;
  fillOpacity?: number;
}

export function DualSparkline({ data1: raw1, data2: raw2, width = 200, height = 40, color1 = '#3fb950', color2 = '#f85149', fillOpacity = 0.15 }: DualSparklineProps) {
  const data1 = raw1.map(v => (Number.isFinite(v) ? v : 0));
  const data2 = raw2.map(v => (Number.isFinite(v) ? v : 0));
  const len = Math.max(data1.length, data2.length);
  if (len < 2) return null;

  const allValues = [...data1, ...data2];
  const max = Math.max(...allValues, 1);

  function makePoints(data: number[]) {
    return data.map((v, i) => {
      const x = (i / (len - 1)) * width;
      const y = height - (v / max) * (height - 4);
      return `${x},${y}`;
    }).join(' ');
  }

  function makeAreaPath(data: number[]) {
    return `M0,${height} ` +
      data.map((v, i) => {
        const x = (i / (len - 1)) * width;
        const y = height - (v / max) * (height - 4);
        return `L${x},${y}`;
      }).join(' ') +
      ` L${width},${height} Z`;
  }

  return (
    <svg width={width} height={height} style={{ display: 'block' }}>
      <path d={makeAreaPath(data1)} fill={color1} opacity={fillOpacity} />
      <polyline points={makePoints(data1)} fill="none" stroke={color1} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" opacity="0.8" />
      <path d={makeAreaPath(data2)} fill={color2} opacity={fillOpacity} />
      <polyline points={makePoints(data2)} fill="none" stroke={color2} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" opacity="0.8" />
    </svg>
  );
}
