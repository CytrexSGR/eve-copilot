import { useState, useEffect } from 'react';
import { resolveTypeNames } from '../../services/api/fittings';
import { getTypeIconUrl, SLOT_RANGES, SLOT_COLORS } from '../../types/fittings';
import type { ShipDetail, FittingItem, SlotType, FittingChargeMap, ModuleState } from '../../types/fittings';

interface SlotEditorProps {
  shipDetail: ShipDetail;
  items: FittingItem[];
  charges: FittingChargeMap;
  activeSlot?: { type: SlotType; flag: number } | null;
  onSlotClick: (type: SlotType, flag: number) => void;
  onRemoveModule: (flag: number) => void;
  onChargeClick: (flag: number, weaponTypeId: number) => void;
  isWeapon: (typeId: number) => boolean;
  moduleStates: Record<number, ModuleState>;
  onModuleStateChange: (flag: number, state: ModuleState) => void;
}

export function SlotEditor({
  shipDetail, items, charges, activeSlot,
  onSlotClick, onRemoveModule, onChargeClick, isWeapon,
  moduleStates, onModuleStateChange,
}: SlotEditorProps) {
  const [moduleNames, setModuleNames] = useState<Map<number, string>>(new Map());
  const [chargeNames, setChargeNames] = useState<Map<number, string>>(new Map());

  // Resolve module names
  useEffect(() => {
    const typeIds = items.map(i => i.type_id);
    if (typeIds.length === 0) return;
    resolveTypeNames(typeIds).then(setModuleNames);
  }, [items]);

  // Resolve charge names
  useEffect(() => {
    const chargeTypeIds = Object.values(charges);
    if (chargeTypeIds.length === 0) return;
    resolveTypeNames(chargeTypeIds).then(setChargeNames);
  }, [charges]);

  const STATE_COLORS: Record<string, string> = {
    active: '#3fb950',      // green
    overheated: '#f85149',  // red
    online: '#d29922',      // yellow
    offline: '#8b949e',     // gray
  };

  const STATE_CYCLE: Record<string, string> = {
    active: 'overheated',
    overheated: 'offline',
    offline: 'active',
    online: 'active',
  };

  const cycleModuleState = (flag: number, e: React.MouseEvent) => {
    e.stopPropagation();
    const current = moduleStates[flag] || 'active';
    onModuleStateChange(flag, STATE_CYCLE[current] as ModuleState);
  };

  const slotConfigs = [
    { type: 'high' as SlotType, count: shipDetail.hi_slots, label: 'High Slots' },
    { type: 'mid' as SlotType, count: shipDetail.med_slots, label: 'Mid Slots' },
    { type: 'low' as SlotType, count: shipDetail.low_slots, label: 'Low Slots' },
    { type: 'rig' as SlotType, count: shipDetail.rig_slots, label: 'Rig Slots' },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
      {slotConfigs.map(({ type, count, label }) => {
        if (count === 0) return null;
        const range = SLOT_RANGES[type];
        const flags = Array.from({ length: count }, (_, i) => range.start + i);
        const itemMap = new Map(
          items.filter(i => i.flag >= range.start && i.flag <= range.end).map(i => [i.flag, i])
        );
        const filledCount = itemMap.size;
        const slotColor = SLOT_COLORS[type];

        return (
          <div key={type} style={{
            background: 'var(--bg-secondary)',
            border: '1px solid var(--border-color)',
            borderRadius: '8px',
            padding: '0.75rem',
          }}>
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
                background: slotColor,
              }} />
              <div style={{ flex: 1, fontWeight: 600, fontSize: '0.85rem' }}>{label}</div>
              {type === 'high' && (shipDetail.turret_hardpoints > 0 || shipDetail.launcher_hardpoints > 0) && (
                <div style={{ display: 'flex', gap: '4px', marginRight: '0.5rem' }}>
                  {shipDetail.turret_hardpoints > 0 && (
                    <span style={{
                      fontSize: '0.6rem', fontWeight: 700, padding: '1px 4px', borderRadius: '3px',
                      background: 'rgba(248, 81, 73, 0.15)', color: '#f85149', fontFamily: 'monospace',
                    }}>
                      {shipDetail.turret_hardpoints}T
                    </span>
                  )}
                  {shipDetail.launcher_hardpoints > 0 && (
                    <span style={{
                      fontSize: '0.6rem', fontWeight: 700, padding: '1px 4px', borderRadius: '3px',
                      background: 'rgba(0, 212, 255, 0.15)', color: '#00d4ff', fontFamily: 'monospace',
                    }}>
                      {shipDetail.launcher_hardpoints}L
                    </span>
                  )}
                </div>
              )}
              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontFamily: 'monospace' }}>
                {filledCount}/{count}
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
              {flags.map(flag => {
                const item = itemMap.get(flag);
                const isActive = activeSlot?.type === type && activeSlot?.flag === flag;

                if (item) {
                  const moduleName = moduleNames.get(item.type_id) || `Type #${item.type_id}`;
                  const hasCharge = charges[flag] !== undefined;
                  const chargeTypeId = charges[flag];
                  const chargeName = hasCharge ? (chargeNames.get(chargeTypeId) || `Type #${chargeTypeId}`) : null;
                  const moduleIsWeapon = isWeapon(item.type_id);

                  return (
                    <div
                      key={flag}
                      style={{
                        background: 'var(--bg-elevated)',
                        borderRadius: '4px',
                        border: '1px solid var(--border-color)',
                        overflow: 'hidden',
                        opacity: (moduleStates[item.flag] === 'offline') ? 0.4 : 1,
                        boxShadow: (moduleStates[item.flag] === 'overheated') ? 'inset 0 0 8px rgba(248, 81, 73, 0.3)' : undefined,
                      }}
                    >
                      {/* Module row */}
                      <div
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '0.5rem',
                          padding: '0.35rem',
                          cursor: 'pointer',
                        }}
                        onClick={() => onSlotClick(type, flag)}
                        onContextMenu={(e) => { e.preventDefault(); cycleModuleState(item.flag, e); }}
                      >
                        <div
                          onClick={(e) => cycleModuleState(item.flag, e)}
                          title={moduleStates[item.flag] || 'active'}
                          style={{
                            width: 8,
                            height: 8,
                            borderRadius: '50%',
                            backgroundColor: STATE_COLORS[moduleStates[item.flag] || 'active'],
                            border: '1px solid rgba(255,255,255,0.2)',
                            cursor: 'pointer',
                            flexShrink: 0,
                            marginRight: 4,
                            transition: 'background-color 0.15s',
                          }}
                        />
                        <img
                          src={getTypeIconUrl(item.type_id, 32)}
                          alt={moduleName}
                          style={{ width: 28, height: 28, borderRadius: 4 }}
                        />
                        <div style={{ flex: 1, fontSize: '0.8rem', fontWeight: 500 }}>{moduleName}</div>
                        <button
                          onClick={e => { e.stopPropagation(); onRemoveModule(flag); }}
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

                      {/* Charge row (only for weapons) */}
                      {moduleIsWeapon && (
                        <div
                          onClick={() => onChargeClick(flag, item.type_id)}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.5rem',
                            padding: '0.2rem 0.35rem 0.3rem 0.35rem',
                            paddingLeft: '2.1rem',
                            cursor: 'pointer',
                            borderTop: '1px solid rgba(255,255,255,0.04)',
                            background: 'rgba(0,0,0,0.15)',
                          }}
                        >
                          {hasCharge ? (
                            <>
                              <img
                                src={getTypeIconUrl(chargeTypeId, 32)}
                                alt={chargeName || ''}
                                style={{ width: 18, height: 18, borderRadius: 2 }}
                              />
                              <span style={{ fontSize: '0.7rem', color: '#00d4ff' }}>{chargeName}</span>
                            </>
                          ) : (
                            <span style={{ fontSize: '0.7rem', color: 'var(--text-tertiary)', fontStyle: 'italic' }}>
                              No ammo loaded
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                  );
                } else {
                  return (
                    <div
                      key={flag}
                      onClick={() => onSlotClick(type, flag)}
                      style={{
                        padding: '0.35rem',
                        border: isActive ? `2px solid ${slotColor}` : '2px dashed var(--border-color)',
                        borderRadius: '4px',
                        textAlign: 'center',
                        cursor: 'pointer',
                        color: 'var(--text-tertiary)',
                        fontSize: '0.75rem',
                        background: isActive ? `${slotColor}11` : 'transparent',
                      }}
                    >
                      +
                    </div>
                  );
                }
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}
