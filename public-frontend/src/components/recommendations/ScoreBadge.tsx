export function ScoreBadge({ score }: { score: number }) {
  const color = score >= 70 ? '#3fb950' : score >= 40 ? '#ffcc00' : '#f85149';
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
      width: 26, height: 26, borderRadius: '50%',
      background: `${color}15`, border: `1px solid ${color}33`,
      color, fontWeight: 800, fontSize: '0.6rem', fontFamily: 'monospace',
    }}>
      {score}
    </span>
  );
}
