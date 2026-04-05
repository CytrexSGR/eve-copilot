import { STATUS_LEVELS, COLOR_MODES, ACTIVITY_OPTIONS, type StatusLevel, type ColorMode } from '../../constants';

interface StatusFilters {
  gank: boolean;
  brawl: boolean;
  battle: boolean;
  hellcamp: boolean;
}

interface StatusCounts {
  gank: number;
  brawl: number;
  battle: number;
  hellcamp: number;
}

interface StatusFilterBarProps {
  statusFilters: StatusFilters;
  onStatusFilterChange: (key: StatusLevel) => void;
  statusCounts: StatusCounts;
  colorMode: ColorMode;
  onColorModeChange: (mode: ColorMode) => void;
  activityMinutes: number;
  onActivityMinutesChange: (minutes: number) => void;
  externalLink?: string;
}

export function StatusFilterBar({
  statusFilters,
  onStatusFilterChange,
  statusCounts,
  colorMode,
  onColorModeChange,
  activityMinutes,
  onActivityMinutesChange,
  externalLink,
}: StatusFilterBarProps) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem' }}>
      {/* Status Level Filters */}
      {(Object.entries(STATUS_LEVELS) as [StatusLevel, typeof STATUS_LEVELS[StatusLevel]][]).map(
        ([key, { label, color }]) => (
          <button
            key={key}
            onClick={() => onStatusFilterChange(key)}
            style={{
              padding: '0.3rem 0.6rem',
              fontSize: '0.7rem',
              fontWeight: 700,
              borderRadius: '4px',
              border: statusFilters[key]
                ? `1px solid ${color}`
                : '1px solid rgba(255,255,255,0.1)',
              cursor: 'pointer',
              transition: 'all 0.2s',
              backgroundColor: statusFilters[key] ? `${color}22` : 'rgba(0,0,0,0.3)',
              color: statusFilters[key] ? color : 'rgba(255,255,255,0.4)',
              textTransform: 'uppercase',
              letterSpacing: '0.02em',
            }}
          >
            {label} <span style={{ opacity: 0.7 }}>({statusCounts[key]})</span>
          </button>
        )
      )}

      <Divider />

      {/* Color Mode Filters */}
      {(Object.entries(COLOR_MODES) as [ColorMode, typeof COLOR_MODES[ColorMode]][]).map(
        ([key, { label }]) => (
          <button
            key={key}
            onClick={() => onColorModeChange(key)}
            style={{
              padding: '0.3rem 0.5rem',
              fontSize: '0.7rem',
              fontWeight: 600,
              borderRadius: '4px',
              border:
                colorMode === key
                  ? '1px solid #00d4ff'
                  : '1px solid rgba(255,255,255,0.1)',
              cursor: 'pointer',
              transition: 'all 0.2s',
              backgroundColor:
                colorMode === key ? 'rgba(0, 212, 255, 0.2)' : 'rgba(0,0,0,0.3)',
              color: colorMode === key ? '#00d4ff' : 'rgba(255,255,255,0.4)',
              textTransform: 'uppercase',
            }}
          >
            {label}
          </button>
        )
      )}

      <Divider />

      {/* Time Selector */}
      <select
        id="activity-minutes"
        name="activity-minutes"
        value={activityMinutes}
        onChange={(e) => onActivityMinutesChange(parseInt(e.target.value))}
        style={{
          padding: '0.3rem 0.5rem',
          fontSize: '0.7rem',
          borderRadius: '4px',
          backgroundColor: 'rgba(0,0,0,0.3)',
          color: 'rgba(255,255,255,0.7)',
          border: '1px solid rgba(255,255,255,0.1)',
          cursor: 'pointer',
        }}
      >
        {ACTIVITY_OPTIONS.map((opt) => (
          <option
            key={opt.value}
            value={opt.value}
            style={{
              backgroundColor: 'rgba(0,0,0,0.95)',
              color: 'rgba(255,255,255,0.9)',
            }}
          >
            {opt.label}
          </option>
        ))}
      </select>

      {externalLink && (
        <a
          href={externalLink}
          target="_blank"
          rel="noopener noreferrer"
          style={{
            padding: '0.3rem 0.6rem',
            background: 'rgba(0, 212, 255, 0.2)',
            color: '#00d4ff',
            borderRadius: '4px',
            textDecoration: 'none',
            fontSize: '0.7rem',
            fontWeight: 600,
            border: '1px solid rgba(0, 212, 255, 0.3)',
          }}
        >
          ↗
        </a>
      )}
    </div>
  );
}

function Divider() {
  return (
    <div
      style={{
        width: '1px',
        height: '20px',
        backgroundColor: 'rgba(255,255,255,0.1)',
        margin: '0 0.25rem',
      }}
    />
  );
}

export type { StatusFilters, StatusCounts };
