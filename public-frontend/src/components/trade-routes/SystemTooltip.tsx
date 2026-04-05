import { forwardRef } from 'react';
import { getSecurityColor } from '../../utils/security';
import type { SystemTooltipData } from './types';
import { TIME_PERIODS, getDangerLevel } from './types';

interface SystemTooltipProps {
  tooltip: SystemTooltipData;
  selectedMinutes: number;
}

export const SystemTooltip = forwardRef<HTMLDivElement, SystemTooltipProps>(
  ({ tooltip, selectedMinutes }, ref) => {
    return (
      <div
        ref={ref}
        style={{
          position: 'fixed',
          left: tooltip.x,
          top: tooltip.y,
          transform: 'translate(-50%, -100%)',
          zIndex: 1000,
          padding: '0.75rem 1rem',
          background: 'linear-gradient(135deg, rgba(20,25,35,0.98) 0%, rgba(15,20,30,0.98) 100%)',
          borderRadius: '8px',
          border: `1px solid ${tooltip.system.is_gate_camp ? 'rgba(255, 136, 0, 0.5)' : 'rgba(0, 212, 255, 0.3)'}`,
          boxShadow: '0 4px 20px rgba(0,0,0,0.5)',
          pointerEvents: 'none',
          minWidth: '180px'
        }}
      >
        {/* Arrow */}
        <div style={{
          position: 'absolute',
          bottom: '-6px',
          left: '50%',
          transform: 'translateX(-50%)',
          width: 0,
          height: 0,
          borderLeft: '6px solid transparent',
          borderRight: '6px solid transparent',
          borderTop: `6px solid ${tooltip.system.is_gate_camp ? 'rgba(255, 136, 0, 0.5)' : 'rgba(0, 212, 255, 0.3)'}`
        }} />

        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
          {tooltip.system.is_gate_camp && <span>🚧</span>}
          <span style={{ fontWeight: 700, color: '#fff', fontSize: '0.9rem' }}>
            {tooltip.system.system_name}
          </span>
          <span style={{
            padding: '0.15rem 0.4rem',
            borderRadius: '3px',
            fontSize: '0.7rem',
            fontWeight: 700,
            background: `${getSecurityColor(tooltip.system.security_status)}22`,
            color: getSecurityColor(tooltip.system.security_status)
          }}>
            {tooltip.system.security_status.toFixed(1)}
          </span>
        </div>

        {/* Gate Camp Warning */}
        {tooltip.system.is_gate_camp && (
          <div style={{
            padding: '0.35rem 0.5rem',
            background: 'rgba(255, 136, 0, 0.2)',
            borderRadius: '4px',
            marginBottom: '0.5rem',
            fontSize: '0.7rem',
            color: '#ff8800',
            fontWeight: 600,
            textAlign: 'center'
          }}>
            Warning: ACTIVE GATE CAMP
          </div>
        )}

        {/* Stats Grid */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: '0.5rem',
          fontSize: '0.75rem'
        }}>
          <div>
            <div style={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.65rem', marginBottom: '0.1rem' }}>KILLS ({TIME_PERIODS.find(p => p.value === selectedMinutes)?.label.toUpperCase() || '24H'})</div>
            <div style={{ color: '#ff4444', fontWeight: 700, fontFamily: 'monospace' }}>
              {tooltip.system.kills_24h}
            </div>
          </div>
          <div>
            <div style={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.65rem', marginBottom: '0.1rem' }}>ISK DESTROYED</div>
            <div style={{ color: '#ffcc00', fontWeight: 700, fontFamily: 'monospace' }}>
              {(tooltip.system.isk_destroyed_24h / 1_000_000_000).toFixed(2)}B
            </div>
          </div>
          <div style={{ gridColumn: '1 / -1' }}>
            <div style={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.65rem', marginBottom: '0.1rem' }}>DANGER LEVEL</div>
            <div style={{
              color: getDangerLevel(tooltip.system.danger_score).color,
              fontWeight: 700
            }}>
              {getDangerLevel(tooltip.system.danger_score).label}
              <span style={{ opacity: 0.6, marginLeft: '0.5rem', fontSize: '0.7rem' }}>
                ({tooltip.system.danger_score.toFixed(1)}/10)
              </span>
            </div>
          </div>
          {/* Click hint for battles */}
          {tooltip.system.battle_id && (
            <div style={{
              gridColumn: '1 / -1',
              marginTop: '0.5rem',
              padding: '0.4rem',
              background: 'rgba(0, 212, 255, 0.15)',
              borderRadius: '4px',
              textAlign: 'center',
              fontSize: '0.7rem',
              color: '#00d4ff',
              fontWeight: 600
            }}>
              Click to view battle details
            </div>
          )}
        </div>
      </div>
    );
  }
);

SystemTooltip.displayName = 'SystemTooltip';
