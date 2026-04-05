type ThreatLevel = 'critical' | 'high' | 'medium' | 'low' | 'safe';

interface ThreatBadgeProps {
  level: ThreatLevel;
  label?: string;
  showPulse?: boolean;
}

const THREAT_CONFIG: Record<ThreatLevel, { color: string; bg: string; text: string }> = {
  critical: { color: 'var(--danger)', bg: 'rgba(248, 81, 73, 0.2)', text: 'CRITICAL' },
  high: { color: '#ff6b35', bg: 'rgba(255, 107, 53, 0.2)', text: 'HIGH' },
  medium: { color: 'var(--warning)', bg: 'rgba(210, 153, 34, 0.2)', text: 'MEDIUM' },
  low: { color: 'var(--accent-blue)', bg: 'rgba(88, 166, 255, 0.2)', text: 'LOW' },
  safe: { color: 'var(--success)', bg: 'rgba(63, 185, 80, 0.2)', text: 'SAFE' }
};

export function ThreatBadge({ level, label, showPulse = false }: ThreatBadgeProps) {
  const config = THREAT_CONFIG[level];

  return (
    <div style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: '0.5rem',
      padding: '0.25rem 0.75rem',
      background: config.bg,
      border: `1px solid ${config.color}`,
      borderRadius: '4px',
      fontSize: '0.75rem',
      fontWeight: 600
    }}>
      {showPulse && (level === 'critical' || level === 'high') && (
        <span style={{
          width: '6px',
          height: '6px',
          borderRadius: '50%',
          background: config.color,
          animation: 'pulse 1.5s ease-in-out infinite'
        }} />
      )}
      <span style={{ color: 'var(--text-tertiary)' }}>THREAT</span>
      <span style={{ color: config.color }}>{label || config.text}</span>
    </div>
  );
}
