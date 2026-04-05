import { Link } from 'react-router-dom';
import { fontSize, color, spacing } from '../../../styles/theme';

interface SectionCardProps {
  title: string;
  borderColor: string;
  linkTo: string;
  linkLabel?: string;
  loading?: boolean;
  children: React.ReactNode;
}

function SkeletonLines() {
  const lineWidths = ['80%', '60%', '45%'];
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
      {lineWidths.map((width, i) => (
        <div
          key={i}
          style={{
            height: '0.75rem',
            width,
            background: 'rgba(255,255,255,0.06)',
            borderRadius: '3px',
            animation: 'pulse 1.5s ease-in-out infinite',
          }}
        />
      ))}
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 0.4; }
          50% { opacity: 1; }
        }
      `}</style>
    </div>
  );
}

export function SectionCard({
  title,
  borderColor,
  linkTo,
  linkLabel,
  loading,
  children,
}: SectionCardProps) {
  return (
    <div
      style={{
        background: 'rgba(0,0,0,0.3)',
        borderRadius: '8px',
        padding: spacing.base,
        borderLeft: `3px solid ${borderColor}`,
        display: 'flex',
        flexDirection: 'column',
        gap: '0.5rem',
      }}
    >
      {/* Title */}
      <div
        style={{
          fontSize: fontSize.xs,
          color: color.textSecondary,
          textTransform: 'uppercase',
          letterSpacing: '0.5px',
          fontWeight: 600,
        }}
      >
        {title}
      </div>

      {/* Content */}
      <div style={{ flex: 1 }}>
        {loading ? <SkeletonLines /> : children}
      </div>

      {/* Bottom link */}
      <div style={{ textAlign: 'right' }}>
        <Link
          to={linkTo}
          style={{
            fontSize: fontSize.tiny,
            color: borderColor,
            textDecoration: 'none',
            fontWeight: 600,
          }}
        >
          {linkLabel || 'View Details'} &rarr;
        </Link>
      </div>
    </div>
  );
}
