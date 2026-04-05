import { StatusFilterBar, type StatusFilters, type StatusCounts } from './StatusFilterBar';
import { ISK_BILLION, type ColorMode, type StatusLevel } from '../../constants';

interface BattleMapSectionProps {
  activityMinutes: number;
  mapIskDestroyed: number;
  statusFilters: StatusFilters;
  statusCounts: StatusCounts;
  colorMode: ColorMode;
  mapUrl: string;
  onStatusFilterChange: (key: StatusLevel) => void;
  onColorModeChange: (mode: ColorMode) => void;
  onActivityMinutesChange: (minutes: number) => void;
}

export function BattleMapSection({
  activityMinutes,
  mapIskDestroyed,
  statusFilters,
  statusCounts,
  colorMode,
  mapUrl,
  onStatusFilterChange,
  onColorModeChange,
  onActivityMinutesChange,
}: BattleMapSectionProps) {
  const timeLabel = activityMinutes < 60 ? `${activityMinutes}m` : `${activityMinutes / 60}h`;

  return (
    <div
      style={{
        marginBottom: '1.5rem',
        padding: 0,
        overflow: 'hidden',
        background:
          'linear-gradient(135deg, rgba(15,20,30,0.95) 0%, rgba(20,25,35,0.9) 100%)',
        borderRadius: '12px',
        border: '1px solid rgba(255, 68, 68, 0.2)',
      }}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '0.875rem 1.5rem',
          borderBottom: '1px solid rgba(255,255,255,0.05)',
          flexWrap: 'wrap',
          gap: '0.75rem',
          background: 'rgba(0,0,0,0.2)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ fontSize: '1.1rem' }}>🗺️</span>
            <h2
              style={{
                margin: 0,
                fontSize: '1rem',
                fontWeight: 700,
                color: '#ff4444',
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
              }}
            >
              Live Battle Map
            </h2>
          </div>
          <IskDisplay value={mapIskDestroyed} timeLabel={timeLabel} />
        </div>

        <StatusFilterBar
          statusFilters={statusFilters}
          onStatusFilterChange={onStatusFilterChange}
          statusCounts={statusCounts}
          colorMode={colorMode}
          onColorModeChange={onColorModeChange}
          activityMinutes={activityMinutes}
          onActivityMinutesChange={onActivityMinutesChange}
          externalLink="/ectmap"
        />
      </div>

      {/* Map iframe */}
      <iframe
        src={mapUrl}
        loading="lazy"
        style={{
          width: '100%',
          height: '480px',
          border: 'none',
          background: '#0a0a0a',
        }}
        title="EVE Online Battle Map"
      />
    </div>
  );
}

function IskDisplay({ value, timeLabel }: { value: number; timeLabel: string }) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '0.5rem',
        padding: '0.375rem 0.75rem',
        background: 'rgba(255, 68, 68, 0.15)',
        borderRadius: '6px',
        border: '1px solid rgba(255, 68, 68, 0.3)',
      }}
    >
      <span style={{ fontSize: '0.8rem' }}>💰</span>
      <span
        style={{
          fontSize: '1rem',
          fontWeight: 700,
          color: '#ff4444',
          fontFamily: 'monospace',
        }}
      >
        {(value / ISK_BILLION).toFixed(1)}B
      </span>
      <span style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)' }}>
        ({timeLabel})
      </span>
    </div>
  );
}
