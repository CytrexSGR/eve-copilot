/**
 * StatCard Component
 *
 * Displays a labeled statistic with optional icon, color, and formatting.
 */

import type { ReactNode } from 'react';

interface StatCardProps {
  label: string;
  value: string | number;
  icon?: ReactNode;
  color?: string;
  size?: 'small' | 'medium' | 'large';
  suffix?: string;
}

export function StatCard({
  label,
  value,
  icon,
  color = '#58a6ff',
  size = 'medium',
  suffix,
}: StatCardProps) {
  const sizeConfig = {
    small: {
      labelSize: '0.65rem',
      valueSize: '0.9rem',
      gap: '0.15rem',
    },
    medium: {
      labelSize: '0.7rem',
      valueSize: '1.25rem',
      gap: '0.2rem',
    },
    large: {
      labelSize: '0.75rem',
      valueSize: '1.75rem',
      gap: '0.25rem',
    },
  };

  const config = sizeConfig[size];

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: config.gap,
      }}
    >
      {/* Label */}
      <div
        style={{
          fontSize: config.labelSize,
          color: '#8b949e',
          textTransform: 'uppercase',
          letterSpacing: '0.05em',
          fontWeight: 500,
        }}
      >
        {label}
      </div>

      {/* Value with optional icon */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.3rem',
        }}
      >
        {icon && (
          <span style={{ fontSize: config.valueSize, lineHeight: 1 }}>
            {icon}
          </span>
        )}
        <span
          style={{
            fontSize: config.valueSize,
            fontWeight: 700,
            color: color,
            lineHeight: 1,
            fontFamily: 'monospace',
          }}
        >
          {value}
        </span>
        {suffix && (
          <span
            style={{
              fontSize: `calc(${config.valueSize} * 0.7)`,
              color: '#8b949e',
              fontWeight: 500,
            }}
          >
            {suffix}
          </span>
        )}
      </div>
    </div>
  );
}
