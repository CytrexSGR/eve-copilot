import React from 'react';
import { COLORS } from '../../constants';

interface StatBoxProps {
  label: string;
  value: string | number;
  color?: string;
  size?: 'sm' | 'md';
}

export function StatBox({ label, value, color = COLORS.accentBlue, size = 'md' }: StatBoxProps) {
  const isSmall = size === 'sm';

  return (
    <div
      style={{
        padding: isSmall ? '0.375rem 0.5rem' : '0.5rem 0.75rem',
        background: `${color}1a`, // 10% opacity
        borderRadius: '6px',
        border: `1px solid ${color}33`, // 20% opacity
      }}
    >
      <span
        style={{
          fontSize: isSmall ? '0.6rem' : '0.65rem',
          color: 'rgba(255,255,255,0.5)',
          textTransform: 'uppercase',
          display: 'block',
        }}
      >
        {label}
      </span>
      <div
        style={{
          fontSize: isSmall ? '0.85rem' : '1rem',
          fontWeight: 700,
          color,
          fontFamily: 'monospace',
        }}
      >
        {value}
      </div>
    </div>
  );
}

interface StatRowProps {
  children: React.ReactNode;
  gap?: string;
}

export function StatRow({ children, gap = '1rem' }: StatRowProps) {
  return (
    <div
      style={{
        display: 'flex',
        gap,
        flexWrap: 'wrap',
      }}
    >
      {children}
    </div>
  );
}

interface InlineStatProps {
  icon?: string;
  value: string | number;
  color?: string;
  label?: string;
}

export function InlineStat({ icon, value, color = 'rgba(255,255,255,0.6)', label }: InlineStatProps) {
  return (
    <span style={{ color: 'rgba(255,255,255,0.6)', fontSize: '0.7rem' }}>
      {icon && <span>{icon} </span>}
      <span style={{ color, fontWeight: 600, fontFamily: 'monospace' }}>{value}</span>
      {label && <span> {label}</span>}
    </span>
  );
}
