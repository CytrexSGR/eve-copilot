import type { ReactNode } from 'react';

type Status = 'critical' | 'warning' | 'success' | 'neutral';

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  status?: Status;
  trend?: number;
  trendLabel?: string;
  icon?: string;
  chart?: ReactNode;
  compact?: boolean;
}

const STATUS_COLORS: Record<Status, string> = {
  critical: 'var(--danger)',
  warning: 'var(--warning)',
  success: 'var(--success)',
  neutral: 'var(--text-secondary)'
};

export function StatCard({
  title,
  value,
  subtitle,
  status = 'neutral',
  trend,
  trendLabel,
  icon,
  chart,
  compact = false
}: StatCardProps) {
  const statusColor = STATUS_COLORS[status];
  const trendColor = trend !== undefined
    ? (trend >= 0 ? 'var(--success)' : 'var(--danger)')
    : undefined;

  return (
    <div style={{
      background: 'var(--bg-secondary)',
      border: `1px solid ${status !== 'neutral' ? statusColor : 'var(--border-color)'}`,
      borderRadius: '8px',
      padding: compact ? '0.75rem' : '1rem',
      display: 'flex',
      flexDirection: 'column',
      gap: '0.5rem'
    }}>
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <span style={{
          fontSize: '0.7rem',
          color: 'var(--text-tertiary)',
          textTransform: 'uppercase',
          letterSpacing: '0.5px'
        }}>
          {icon && <span style={{ marginRight: '0.25rem' }}>{icon}</span>}
          {title}
        </span>
        {trend !== undefined && (
          <span style={{
            fontSize: '0.7rem',
            color: trendColor,
            fontWeight: 500
          }}>
            {trend >= 0 ? '▲' : '▼'} {Math.abs(trend).toFixed(1)}%
            {trendLabel && <span style={{ color: 'var(--text-tertiary)', marginLeft: '0.25rem' }}>{trendLabel}</span>}
          </span>
        )}
      </div>

      <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.5rem' }}>
        <span style={{
          fontSize: compact ? '1.25rem' : '1.5rem',
          fontWeight: 'bold',
          color: statusColor
        }}>
          {value}
        </span>
        {subtitle && (
          <span style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)' }}>
            {subtitle}
          </span>
        )}
      </div>

      {chart && (
        <div style={{ marginTop: '0.25rem' }}>
          {chart}
        </div>
      )}
    </div>
  );
}
