import { memo } from 'react';

interface TimeOption {
  label: string;
  minutes: number;
}

interface TimeFilterProps {
  value: number;
  onChange: (minutes: number) => void;
  options?: TimeOption[];
}

const DEFAULT_OPTIONS: TimeOption[] = [
  { label: '10m', minutes: 10 },
  { label: '1h', minutes: 60 },
  { label: '12h', minutes: 720 },
  { label: '24h', minutes: 1440 },
  { label: '7d', minutes: 10080 },
];

export const TimeFilter = memo(function TimeFilter({
  value,
  onChange,
  options = DEFAULT_OPTIONS
}: TimeFilterProps) {
  const accentColor = '#00d4ff';

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: '0.25rem',
      padding: '0.35rem 0.5rem',
      background: 'rgba(0,0,0,0.3)',
      borderRadius: '6px',
      border: '1px solid rgba(255,255,255,0.05)',
      height: '42px',
      boxSizing: 'border-box',
    }}>
      {options.map(option => {
        const isActive = value === option.minutes;
        return (
          <button
            key={option.minutes}
            onClick={() => onChange(option.minutes)}
            style={{
              padding: '0.35rem 0.6rem',
              fontSize: '0.75rem',
              fontWeight: 700,
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              transition: 'all 0.2s',
              textTransform: 'uppercase',
              letterSpacing: '0.03em',
              background: isActive ? `${accentColor}22` : 'rgba(0,212,255,0.08)',
              color: isActive ? accentColor : 'rgba(255,255,255,0.5)',
              borderBottom: isActive ? `2px solid ${accentColor}` : '2px solid transparent',
              display: 'flex',
              alignItems: 'center',
              gap: '0.3rem'
            }}
          >
            {option.label}
            {isActive && (
              <span style={{
                width: '6px',
                height: '6px',
                borderRadius: '50%',
                background: accentColor,
                boxShadow: `0 0 8px ${accentColor}`
              }} />
            )}
          </button>
        );
      })}
    </div>
  );
});
