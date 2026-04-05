import { useState, useEffect } from 'react';
import { resolveTypeNames } from '../../services/api/fittings';
import { getTypeIconUrl } from '../../types/fittings';
import type { DroneEntry } from '../../types/fittings';

interface DronePanelProps {
  drones: DroneEntry[];
  droneBayTotal: number;
  droneBandwidthTotal: number;
  onAddDrone: () => void;
  onRemoveDrone: (typeId: number) => void;
}

export function DronePanel({
  drones, droneBayTotal, droneBandwidthTotal,
  onAddDrone, onRemoveDrone,
}: DronePanelProps) {
  const [droneNames, setDroneNames] = useState<Map<number, string>>(new Map());

  useEffect(() => {
    const typeIds = drones.map(d => d.type_id);
    if (typeIds.length === 0) return;
    resolveTypeNames(typeIds).then(setDroneNames);
  }, [drones]);

  const totalCount = drones.reduce((sum, d) => sum + d.count, 0);

  return (
    <div style={{
      background: 'var(--bg-secondary)',
      border: '1px solid var(--border-color)',
      borderRadius: '8px',
      padding: '0.75rem',
    }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '0.5rem',
        marginBottom: '0.5rem',
        paddingBottom: '0.5rem',
        borderBottom: '1px solid var(--border-color)',
      }}>
        <div style={{
          width: 8,
          height: 8,
          borderRadius: '50%',
          background: '#a855f7',
        }} />
        <div style={{ flex: 1, fontWeight: 600, fontSize: '0.85rem' }}>Drone Bay</div>
        <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontFamily: 'monospace' }}>
          {totalCount} drones
        </div>
      </div>

      {/* Capacity bars (only show if we have bay/bandwidth info) */}
      {(droneBayTotal > 0 || droneBandwidthTotal > 0) && (
        <div style={{ display: 'flex', gap: '1rem', marginBottom: '0.5rem', fontSize: '0.7rem' }}>
          {droneBayTotal > 0 && (
            <div style={{ flex: 1 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '2px', color: 'var(--text-secondary)' }}>
                <span>Bay</span>
                <span style={{ fontFamily: 'monospace' }}>0 / {droneBayTotal} m3</span>
              </div>
              <div style={{ height: 4, background: 'var(--bg-primary)', borderRadius: 2, overflow: 'hidden' }}>
                <div style={{ width: '0%', height: '100%', background: '#a855f7', transition: 'width 0.3s' }} />
              </div>
            </div>
          )}
          {droneBandwidthTotal > 0 && (
            <div style={{ flex: 1 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '2px', color: 'var(--text-secondary)' }}>
                <span>BW</span>
                <span style={{ fontFamily: 'monospace' }}>0 / {droneBandwidthTotal} Mbit/s</span>
              </div>
              <div style={{ height: 4, background: 'var(--bg-primary)', borderRadius: 2, overflow: 'hidden' }}>
                <div style={{ width: '0%', height: '100%', background: '#a855f7', transition: 'width 0.3s' }} />
              </div>
            </div>
          )}
        </div>
      )}

      {/* Drone list */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
        {drones.map(drone => {
          const droneName = droneNames.get(drone.type_id) || `Type #${drone.type_id}`;
          return (
            <div
              key={drone.type_id}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                padding: '0.35rem',
                background: 'var(--bg-elevated)',
                borderRadius: '4px',
                border: '1px solid var(--border-color)',
              }}
            >
              <img
                src={getTypeIconUrl(drone.type_id, 32)}
                alt={droneName}
                style={{ width: 24, height: 24, borderRadius: 4 }}
              />
              <div style={{ flex: 1, fontSize: '0.8rem', fontWeight: 500 }}>
                {droneName}
                <span style={{ color: '#a855f7', marginLeft: '0.35rem', fontFamily: 'monospace', fontSize: '0.75rem' }}>
                  x{drone.count}
                </span>
              </div>
              <button
                onClick={() => onRemoveDrone(drone.type_id)}
                style={{
                  padding: '2px 6px',
                  background: 'transparent',
                  border: '1px solid var(--border-color)',
                  borderRadius: '4px',
                  color: 'var(--text-secondary)',
                  cursor: 'pointer',
                  fontSize: '0.75rem',
                }}
              >
                x
              </button>
            </div>
          );
        })}

        {drones.length === 0 && (
          <div style={{
            padding: '0.35rem',
            textAlign: 'center',
            color: 'var(--text-tertiary)',
            fontSize: '0.75rem',
          }}>
            No drones loaded
          </div>
        )}
      </div>

      {/* Add drone button */}
      <button
        onClick={onAddDrone}
        style={{
          width: '100%',
          marginTop: '0.5rem',
          padding: '0.35rem',
          background: 'transparent',
          border: '2px dashed var(--border-color)',
          borderRadius: '4px',
          color: 'var(--text-tertiary)',
          cursor: 'pointer',
          fontSize: '0.75rem',
        }}
      >
        + Add Drone
      </button>
    </div>
  );
}
