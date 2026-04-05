import { memo } from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

interface TrendIndicatorProps {
  change: number; // percentage change, e.g. 23 for +23%
  label?: string;
}

export const TrendIndicator = memo(function TrendIndicator({
  change,
  label = '7d'
}: TrendIndicatorProps) {
  const isRising = change > 5;
  const isDecline = change < -5;

  const color = isRising ? '#00ff88' : isDecline ? '#ff4444' : '#ffcc00';
  const Icon = isRising ? TrendingUp : isDecline ? TrendingDown : Minus;
  const statusText = isRising ? 'Rising' : isDecline ? 'Declining' : 'Stable';

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
      <Icon size={14} color={color} />
      <span style={{
        fontSize: '0.75rem',
        fontFamily: 'monospace',
        fontWeight: 700,
        color
      }}>
        {change > 0 ? '+' : ''}{change}%
      </span>
      <span style={{
        fontSize: '0.6rem',
        color: 'rgba(255,255,255,0.4)'
      }}>
        ({label})
      </span>
      <span style={{
        fontSize: '0.6rem',
        padding: '0.15rem 0.4rem',
        background: `${color}22`,
        color,
        borderRadius: '4px',
        fontWeight: 600
      }}>
        {statusText}
      </span>
    </div>
  );
});
