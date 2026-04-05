import { useState, useEffect, useMemo } from 'react';
import { resolveTypeNames } from '../../services/api/fittings';
import { getTypeIconUrl, getShipRenderUrl, SLOT_RANGES, SLOT_COLORS } from '../../types/fittings';
import type { ShipDetail, FittingItem, SlotType, FittingChargeMap, DroneEntry, FittingStats, ModuleState } from '../../types/fittings';

interface ShipDisplayProps {
  shipDetail: ShipDetail | null;
  items: FittingItem[];
  charges: FittingChargeMap;
  drones: DroneEntry[];
  stats: FittingStats | null;
  activeSlot?: { type: SlotType; flag: number } | null;
  onSlotClick: (type: SlotType, flag: number) => void;
  onRemoveModule: (flag: number) => void;
  onChargeClick: (flag: number, weaponTypeId: number) => void;
  isWeapon: (typeId: number) => boolean;
  moduleStates?: Record<number, ModuleState>;
  onModuleStateChange?: (flag: number, state: ModuleState) => void;
  activatableFlags?: Set<number>;
}

const CONTAINER_SIZE = 460;
const SHIP_SIZE = 256;
const SLOT_SIZE = 36;
const SLOT_GAP = 4;

function getSlotPositions(slotCount: number, type: SlotType): { x: number; y: number }[] {
  const centerX = CONTAINER_SIZE / 2;
  const centerY = CONTAINER_SIZE / 2;

  switch (type) {
    case 'high': {
      const totalWidth = slotCount * (SLOT_SIZE + SLOT_GAP) - SLOT_GAP;
      const startX = centerX - totalWidth / 2;
      const y = centerY - SHIP_SIZE / 2 - SLOT_SIZE - 16;
      return Array.from({ length: slotCount }, (_, i) => ({
        x: startX + i * (SLOT_SIZE + SLOT_GAP),
        y,
      }));
    }
    case 'mid': {
      const totalHeight = slotCount * (SLOT_SIZE + SLOT_GAP) - SLOT_GAP;
      const startY = centerY - totalHeight / 2;
      const x = centerX + SHIP_SIZE / 2 + 16;
      return Array.from({ length: slotCount }, (_, i) => ({
        x,
        y: startY + i * (SLOT_SIZE + SLOT_GAP),
      }));
    }
    case 'low': {
      const totalWidth = slotCount * (SLOT_SIZE + SLOT_GAP) - SLOT_GAP;
      const startX = centerX - totalWidth / 2;
      const y = centerY + SHIP_SIZE / 2 + 16;
      return Array.from({ length: slotCount }, (_, i) => ({
        x: startX + i * (SLOT_SIZE + SLOT_GAP),
        y,
      }));
    }
    case 'rig': {
      const totalHeight = slotCount * (SLOT_SIZE + SLOT_GAP) - SLOT_GAP;
      const startY = centerY - totalHeight / 2;
      const x = centerX - SHIP_SIZE / 2 - SLOT_SIZE - 16;
      return Array.from({ length: slotCount }, (_, i) => ({
        x,
        y: startY + i * (SLOT_SIZE + SLOT_GAP),
      }));
    }
  }
}

function barColor(ratio: number): string {
  if (ratio > 1) return '#f85149';
  if (ratio >= 0.8) return '#d29922';
  return '#3fb950';
}

const STATE_COLORS: Record<string, string> = {
  offline: '#555',
  online: '#888',
  active: '#3fb950',
  overheated: '#f85149',
};

const pulseKeyframes = `
@keyframes slotPulse {
  0%, 100% { box-shadow: 0 0 4px currentColor; }
  50% { box-shadow: 0 0 12px currentColor; }
}
`;

export function ShipDisplay({
  shipDetail, items, charges, drones: _drones, stats, activeSlot,
  onSlotClick, onRemoveModule, onChargeClick, isWeapon,
  moduleStates, onModuleStateChange, activatableFlags,
}: ShipDisplayProps) {
  const [moduleNames, setModuleNames] = useState<Map<number, string>>(new Map());
  const [chargeNames, setChargeNames] = useState<Map<number, string>>(new Map());

  useEffect(() => {
    const typeIds = items.map(i => i.type_id);
    if (typeIds.length === 0) return;
    resolveTypeNames(typeIds).then(setModuleNames);
  }, [items]);

  useEffect(() => {
    const chargeTypeIds = Object.values(charges);
    if (chargeTypeIds.length === 0) return;
    resolveTypeNames(chargeTypeIds).then(setChargeNames);
  }, [charges]);

  const itemMap = useMemo(() => new Map(items.map(i => [i.flag, i])), [items]);

  if (!shipDetail) {
    return (
      <div style={{
        display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
        height: CONTAINER_SIZE + 80, color: 'var(--text-tertiary)', gap: '1rem',
      }}>
        <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
          <path d="M12 2L4 8v8l8 6 8-6V8l-8-6z" />
          <circle cx="12" cy="12" r="3" />
        </svg>
        <span style={{ fontSize: '0.9rem' }}>Select a ship to begin fitting</span>
      </div>
    );
  }

  const slotGroups: { type: SlotType; count: number }[] = [
    { type: 'high', count: shipDetail.hi_slots },
    { type: 'mid', count: shipDetail.med_slots },
    { type: 'low', count: shipDetail.low_slots },
    { type: 'rig', count: shipDetail.rig_slots },
  ];

  const res = stats?.resources;
  const cpuUsed = res?.cpu_used ?? 0;
  const cpuTotal = res?.cpu_total ?? shipDetail.cpu_output ?? 0;
  const pgUsed = res?.pg_used ?? 0;
  const pgTotal = res?.pg_total ?? shipDetail.power_output ?? 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
      <style>{pulseKeyframes}</style>

      {/* Radial slot ring + ship render */}
      <div style={{
        position: 'relative',
        width: CONTAINER_SIZE,
        height: CONTAINER_SIZE + 40,
        margin: '0 auto',
      }}>
        {/* Hull name above ship */}
        <div style={{
          position: 'absolute',
          left: 0,
          right: 0,
          top: 4,
          textAlign: 'center',
          fontSize: '0.85rem',
          fontWeight: 600,
          color: 'var(--text-primary)',
          letterSpacing: '0.03em',
          textTransform: 'uppercase',
          pointerEvents: 'none',
        }}>
          {shipDetail.type_name || shipDetail.name}
        </div>

        {/* Ship render centered */}
        <img
          src={getShipRenderUrl(shipDetail.type_id, 256)}
          alt={shipDetail.type_name || shipDetail.name}
          style={{
            position: 'absolute',
            left: (CONTAINER_SIZE - SHIP_SIZE) / 2,
            top: (CONTAINER_SIZE - SHIP_SIZE) / 2,
            width: SHIP_SIZE,
            height: SHIP_SIZE,
            pointerEvents: 'none',
            opacity: 0.85,
          }}
        />

        {/* Hardpoint indicators above high slots */}
        {(() => {
          const turretTotal = res?.turret_hardpoints_total ?? shipDetail.turret_hardpoints ?? 0;
          const turretUsed = res?.turret_hardpoints_used ?? 0;
          const launcherTotal = res?.launcher_hardpoints_total ?? shipDetail.launcher_hardpoints ?? 0;
          const launcherUsed = res?.launcher_hardpoints_used ?? 0;
          if (turretTotal === 0 && launcherTotal === 0) return null;
          const hiCount = shipDetail.hi_slots;
          const totalWidth = hiCount * (SLOT_SIZE + SLOT_GAP) - SLOT_GAP;
          const startX = CONTAINER_SIZE / 2 - totalWidth / 2;
          const y = CONTAINER_SIZE / 2 - SHIP_SIZE / 2 - SLOT_SIZE - 16 - 18;
          return (
            <div style={{
              position: 'absolute', left: startX, top: y,
              width: totalWidth, display: 'flex', justifyContent: 'center', gap: '0.75rem',
              fontSize: '0.65rem', fontFamily: 'monospace',
            }}>
              {turretTotal > 0 && (
                <span style={{ color: turretUsed > turretTotal ? '#f85149' : 'var(--text-secondary)' }}>
                  {turretUsed}/{turretTotal}T
                </span>
              )}
              {launcherTotal > 0 && (
                <span style={{ color: launcherUsed > launcherTotal ? '#f85149' : 'var(--text-secondary)' }}>
                  {launcherUsed}/{launcherTotal}L
                </span>
              )}
            </div>
          );
        })()}

        {/* Slot groups rendered absolutely */}
        {slotGroups.map(({ type, count }) => {
          if (count === 0) return null;
          const positions = getSlotPositions(count, type);
          const range = SLOT_RANGES[type];
          const flags = Array.from({ length: count }, (_, i) => range.start + i);
          const color = SLOT_COLORS[type];

          return flags.map((flag, idx) => {
            const pos = positions[idx];
            const item = itemMap.get(flag);
            const isActive = activeSlot?.type === type && activeSlot?.flag === flag;
            const hasCharge = item && charges[flag] !== undefined;
            const chargeTypeId = charges[flag];
            const modState = (moduleStates?.[flag] || 'active') as ModuleState;
            const isOffline = modState === 'offline';

            return (
              <div
                key={`${type}-${flag}`}
                title={item ? `${moduleNames.get(item.type_id) || `Type #${item.type_id}`} [${modState}]` : `Empty ${type} slot`}
                onClick={() => onSlotClick(type, flag)}
                onContextMenu={e => {
                  e.preventDefault();
                  if (!item) return;
                  if (e.shiftKey) {
                    onRemoveModule(flag);
                  } else if (onModuleStateChange) {
                    const isActivatable = activatableFlags?.has(flag) ?? true;
                    const states: ModuleState[] = isActivatable
                      ? ['active', 'overheated', 'online', 'offline']
                      : ['active', 'offline'];
                    const curIdx = states.indexOf(modState);
                    const next = states[(curIdx + 1) % states.length];
                    onModuleStateChange(flag, next);
                  } else {
                    onRemoveModule(flag);
                  }
                }}
                style={{
                  position: 'absolute',
                  left: pos.x,
                  top: pos.y,
                  width: SLOT_SIZE,
                  height: SLOT_SIZE,
                  borderRadius: 6,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  border: item
                    ? `2px solid ${isActive ? color : 'rgba(255,255,255,0.12)'}`
                    : `2px dashed ${isActive ? color : `${color}44`}`,
                  background: item
                    ? 'rgba(0,0,0,0.65)'
                    : isActive ? `${color}18` : 'rgba(0,0,0,0.35)',
                  boxShadow: isActive
                    ? `0 0 8px ${color}`
                    : item ? `inset 0 0 6px ${color}22` : 'none',
                  animation: isActive ? 'slotPulse 1.5s ease-in-out infinite' : 'none',
                  color,
                  transition: 'border-color 0.15s, background 0.15s, box-shadow 0.15s, opacity 0.15s',
                  opacity: item && isOffline ? 0.4 : 1,
                }}
              >
                {item ? (
                  <>
                    <img
                      src={getTypeIconUrl(item.type_id, 32)}
                      alt=""
                      style={{ width: 32, height: 32, borderRadius: 4 }}
                    />
                    {/* Module state indicator (top-right) */}
                    <div
                      style={{
                        position: 'absolute', top: 2, right: 2,
                        width: 6, height: 6, borderRadius: '50%',
                        background: STATE_COLORS[modState],
                        border: '1px solid rgba(0,0,0,0.5)',
                      }}
                      title={modState}
                    />
                    {/* Charge indicator (bottom-right) */}
                    {hasCharge && (
                      <img
                        src={getTypeIconUrl(chargeTypeId, 32)}
                        alt={chargeNames.get(chargeTypeId) || ''}
                        onClick={e => {
                          e.stopPropagation();
                          onChargeClick(flag, item.type_id);
                        }}
                        style={{
                          position: 'absolute',
                          bottom: -2,
                          right: -2,
                          width: 16,
                          height: 16,
                          borderRadius: 3,
                          border: '1px solid rgba(0,0,0,0.5)',
                        }}
                      />
                    )}
                    {/* Weapon indicator: small dot if weapon has no charge loaded */}
                    {!hasCharge && isWeapon(item.type_id) && (
                      <div
                        onClick={e => {
                          e.stopPropagation();
                          onChargeClick(flag, item.type_id);
                        }}
                        style={{
                          position: 'absolute',
                          bottom: 1,
                          right: 1,
                          width: 8,
                          height: 8,
                          borderRadius: '50%',
                          background: '#d29922',
                          border: '1px solid rgba(0,0,0,0.4)',
                        }}
                      />
                    )}
                  </>
                ) : (
                  <span style={{ fontSize: '1rem', fontWeight: 300, opacity: 0.6 }}>+</span>
                )}
              </div>
            );
          });
        })}
      </div>

      {/* Resource display (EVE client style) */}
      <div style={{
        display: 'flex', gap: '1.5rem', justifyContent: 'center',
        padding: '0.5rem 0.75rem',
        background: 'var(--bg-secondary)',
        border: '1px solid var(--border-color)',
        borderRadius: 8,
      }}>
        <ResourceDisplay label="CPU" used={cpuUsed} total={cpuTotal} unit="tf" />
        <ResourceDisplay label="Power Grid" used={pgUsed} total={pgTotal} unit="MW" />
      </div>
    </div>
  );
}

/* -- Resource display sub-component (EVE client style) -- */

function fmtNum(n: number): string {
  return n.toLocaleString('de-DE', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
}

function ResourceDisplay({ label, used, total, unit }: {
  label: string; used: number; total: number; unit?: string;
}) {
  const ratio = total > 0 ? used / total : 0;
  const color = barColor(ratio);

  return (
    <div style={{ textAlign: 'center', minWidth: 90 }}>
      <div style={{
        fontSize: '0.65rem', fontWeight: 600,
        color: 'var(--text-secondary)',
        marginBottom: 2,
      }}>
        {label}
      </div>
      <div style={{
        fontSize: '0.75rem', fontFamily: 'monospace',
        color,
      }}>
        {fmtNum(used)} / {fmtNum(total)}{unit ? ` ${unit}` : ''}
      </div>
    </div>
  );
}
