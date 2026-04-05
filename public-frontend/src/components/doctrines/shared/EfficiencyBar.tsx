import { memo } from 'react';

interface EfficiencyBarProps {
  value: number; // e.g. 1.87 for 187%
  label?: string;
  showPercent?: boolean;
}

export const EfficiencyBar = memo(function EfficiencyBar({
  value,
  label = 'ISK Eff',
  showPercent = true
}: EfficiencyBarProps) {
  const percent = Math.min(value * 50, 100); // 2.0 = 100%
  const color = value >= 1.0 ? '#00ff88' : '#ff4444';
  const displayValue = showPercent ? `${Math.round(value * 100)}%` : value.toFixed(2);

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
      <span style={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.5)', minWidth: '45px' }}>
        {label}
      </span>
      <div style={{
        flex: 1,
        height: '6px',
        background: 'rgba(255,255,255,0.1)',
        borderRadius: '3px',
        overflow: 'hidden'
      }}>
        <div style={{
          width: `${percent}%`,
          height: '100%',
          background: color,
          borderRadius: '3px'
        }} />
      </div>
      <span style={{
        fontSize: '0.75rem',
        fontFamily: 'monospace',
        fontWeight: 700,
        color,
        minWidth: '40px',
        textAlign: 'right'
      }}>
        {displayValue}
      </span>
    </div>
  );
});
