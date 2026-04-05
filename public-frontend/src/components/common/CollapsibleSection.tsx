/**
 * CollapsibleSection - Expandable/collapsible panel with refresh indicator
 *
 * Used in the Geography tab for DOTLAN sections that can be expanded or collapsed.
 */

import { useState, type ReactNode } from 'react';

interface CollapsibleSectionProps {
  /** Section title (displayed in uppercase) */
  title: string;
  /** Optional icon emoji to display before title */
  icon?: string;
  /** Refresh rate text to display (e.g., "10min", "1h") */
  refreshRate?: string;
  /** Optional badge text (e.g., "ALERT") */
  badge?: string;
  /** Badge color variant */
  badgeColor?: 'danger' | 'warning' | 'success' | 'info';
  /** Whether section is open by default */
  defaultOpen?: boolean;
  /** Callback when section is opened (useful for lazy loading) */
  onOpen?: () => void;
  /** Section content */
  children: ReactNode;
}

const badgeColors = {
  danger: 'var(--danger, #f85149)',
  warning: 'var(--warning, #d29922)',
  success: 'var(--success, #3fb950)',
  info: 'var(--accent-blue, #58a6ff)',
};

export function CollapsibleSection({
  title,
  icon,
  refreshRate,
  badge,
  badgeColor = 'warning',
  defaultOpen = false,
  onOpen,
  children,
}: CollapsibleSectionProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  const handleToggle = () => {
    const newState = !isOpen;
    setIsOpen(newState);
    if (newState && onOpen) {
      onOpen();
    }
  };

  return (
    <div
      style={{
        background: 'rgba(0,0,0,0.3)',
        borderRadius: '8px',
        border: '1px solid var(--border-color, rgba(255,255,255,0.1))',
        overflow: 'hidden',
      }}
    >
      {/* Header / Toggle Button */}
      <button
        onClick={handleToggle}
        style={{
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
          padding: '0.75rem 1rem',
          background: 'transparent',
          border: 'none',
          cursor: 'pointer',
          color: 'var(--text-primary, #c9d1d9)',
          textAlign: 'left',
        }}
      >
        {/* Arrow indicator */}
        <span
          style={{
            transform: isOpen ? 'rotate(90deg)' : 'none',
            transition: 'transform 0.2s ease',
            fontSize: '0.7rem',
            color: 'var(--text-tertiary, #8b949e)',
          }}
        >
          ▶
        </span>

        {/* Icon */}
        {icon && <span style={{ fontSize: '1rem' }}>{icon}</span>}

        {/* Title */}
        <span
          style={{
            fontWeight: 600,
            textTransform: 'uppercase',
            fontSize: '0.75rem',
            letterSpacing: '0.5px',
          }}
        >
          {title}
        </span>

        {/* Spacer */}
        <span style={{ flex: 1 }} />

        {/* Refresh rate indicator */}
        {refreshRate && (
          <span
            style={{
              fontSize: '0.65rem',
              color: 'var(--text-tertiary, #8b949e)',
              display: 'flex',
              alignItems: 'center',
              gap: '0.25rem',
            }}
          >
            <span style={{ opacity: 0.7 }}>↻</span>
            {refreshRate}
          </span>
        )}

        {/* Badge */}
        {badge && (
          <span
            style={{
              padding: '0.15rem 0.5rem',
              borderRadius: '4px',
              fontSize: '0.6rem',
              fontWeight: 700,
              background: badgeColors[badgeColor],
              color: badgeColor === 'warning' ? '#000' : '#fff',
              textTransform: 'uppercase',
              letterSpacing: '0.5px',
              animation: badgeColor === 'danger' ? 'pulse 2s infinite' : 'none',
            }}
          >
            {badge}
          </span>
        )}
      </button>

      {/* Content */}
      {isOpen && (
        <div
          style={{
            padding: '0.75rem 1rem',
            borderTop: '1px solid var(--border-color, rgba(255,255,255,0.1))',
          }}
        >
          {children}
        </div>
      )}
    </div>
  );
}

export default CollapsibleSection;
