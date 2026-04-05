import React from 'react';

interface CardProps {
  children: React.ReactNode;
  variant?: 'default' | 'danger' | 'accent' | 'warning';
  className?: string;
  style?: React.CSSProperties;
  padding?: 'none' | 'sm' | 'md' | 'lg';
  withNoise?: boolean;
}

const VARIANT_STYLES: Record<string, { border: string; accent?: string }> = {
  default: { border: 'rgba(100, 150, 255, 0.15)' },
  danger: { border: 'rgba(255, 68, 68, 0.2)', accent: '#ff4444' },
  accent: { border: 'rgba(0, 212, 255, 0.15)', accent: '#00d4ff' },
  warning: { border: 'rgba(255, 136, 0, 0.15)', accent: '#ff8800' },
};

const PADDING_VALUES = {
  none: '0',
  sm: '0.75rem',
  md: '1.5rem',
  lg: '2rem',
};

// SVG noise texture as data URI
const NOISE_SVG = "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E\")";

export function Card({
  children,
  variant = 'default',
  className,
  style,
  padding = 'md',
  withNoise = true,
}: CardProps) {
  const variantStyle = VARIANT_STYLES[variant];

  return (
    <div
      className={className}
      style={{
        background: 'linear-gradient(135deg, rgba(15,20,30,0.95) 0%, rgba(20,25,35,0.9) 100%)',
        borderRadius: '12px',
        border: `1px solid ${variantStyle.border}`,
        padding: PADDING_VALUES[padding],
        position: 'relative',
        overflow: 'hidden',
        ...style,
      }}
    >
      {withNoise && (
        <div
          style={{
            position: 'absolute',
            inset: 0,
            backgroundImage: NOISE_SVG,
            opacity: 0.04,
            pointerEvents: 'none',
            borderRadius: 'inherit',
          }}
        />
      )}
      <div style={{ position: 'relative' }}>{children}</div>
    </div>
  );
}

interface CardHeaderProps {
  icon?: string;
  title: string;
  subtitle?: string;
  action?: React.ReactNode;
  titleColor?: string;
}

export function CardHeader({ icon, title, subtitle, action, titleColor = '#fff' }: CardHeaderProps) {
  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
        marginBottom: '1rem',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
        {icon && <span style={{ fontSize: '1.5rem' }}>{icon}</span>}
        <div>
          <h2
            style={{
              margin: 0,
              fontSize: '1.1rem',
              fontWeight: 700,
              color: titleColor,
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
            }}
          >
            {title}
          </h2>
          {subtitle && (
            <p style={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.75rem', margin: 0 }}>
              {subtitle}
            </p>
          )}
        </div>
      </div>
      {action}
    </div>
  );
}

export function CardLink({ to, children }: { to: string; children: React.ReactNode }) {
  return (
    <a
      href={to}
      style={{
        padding: '0.4rem 0.75rem',
        background: 'rgba(0, 212, 255, 0.15)',
        color: '#00d4ff',
        borderRadius: '6px',
        textDecoration: 'none',
        fontSize: '0.7rem',
        fontWeight: 600,
        border: '1px solid rgba(0, 212, 255, 0.3)',
        textTransform: 'uppercase',
      }}
    >
      {children}
    </a>
  );
}
