interface ConfidenceBadgeProps {
  score: number;
}

export function ConfidenceBadge({ score }: ConfidenceBadgeProps) {
  const color = score >= 70 ? 'var(--success)' :
                score >= 40 ? 'var(--warning)' : 'var(--text-tertiary)';
  const label = score >= 70 ? 'HIGH' : score >= 40 ? 'MED' : 'LOW';

  return (
    <span style={{
      padding: '0.2rem 0.4rem',
      background: color,
      color: 'white',
      borderRadius: '4px',
      fontSize: '0.6rem',
      fontWeight: 700,
      marginLeft: '0.5rem'
    }}>
      {label} {score}%
    </span>
  );
}
