import { useState, useEffect } from 'react';
import type { FittingItem } from '../../types/fittings';
import { getTypeIconUrl } from '../../types/fittings';
import { resolveTypeNames } from '../../services/api/fittings';

interface SlotPanelProps {
  label: string;
  items: FittingItem[];
  total: number;
  color: string;
}

export function SlotPanel({ label, items, total, color }: SlotPanelProps) {
  const [typeNames, setTypeNames] = useState<Map<number, string>>(new Map());
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const typeIds = [...new Set(items.map(i => i.type_id))];
    if (typeIds.length === 0) {
      setLoading(false);
      return;
    }

    resolveTypeNames(typeIds)
      .then(setTypeNames)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [items]);

  // Group items by type_id
  const groupedItems = items.reduce((acc, item) => {
    const existing = acc.find(g => g.type_id === item.type_id);
    if (existing) {
      existing.quantity += item.quantity;
    } else {
      acc.push({ type_id: item.type_id, quantity: item.quantity });
    }
    return acc;
  }, [] as { type_id: number; quantity: number }[]);

  const filledSlots = items.length;
  const emptySlots = Math.max(0, total - filledSlots);

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
          width: '8px',
          height: '8px',
          borderRadius: '50%',
          background: color,
        }} />
        <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-primary)' }}>
          {label}
        </span>
        <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', marginLeft: 'auto' }}>
          {filledSlots}/{total}
        </span>
      </div>

      {/* Module List */}
      {loading ? (
        <div style={{ padding: '0.5rem', color: 'var(--text-secondary)', fontSize: '0.75rem' }}>
          Loading modules...
        </div>
      ) : (
        <>
          {groupedItems.map(({ type_id, quantity }) => (
            <div
              key={type_id}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                padding: '0.35rem 0',
                borderBottom: '1px solid rgba(255,255,255,0.05)',
              }}
            >
              <img
                src={getTypeIconUrl(type_id, 32)}
                alt=""
                style={{ width: 32, height: 32, borderRadius: 4 }}
              />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{
                  fontSize: '0.75rem',
                  color: 'var(--text-primary)',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}>
                  {typeNames.get(type_id) || `Type #${type_id}`}
                </div>
              </div>
              {quantity > 1 && (
                <span style={{
                  fontSize: '0.7rem',
                  color: 'var(--text-secondary)',
                  padding: '2px 6px',
                  background: 'rgba(255,255,255,0.05)',
                  borderRadius: '4px',
                }}>
                  x{quantity}
                </span>
              )}
            </div>
          ))}

          {/* Empty Slots */}
          {emptySlots > 0 && (
            <div style={{
              padding: '0.35rem 0',
              color: 'var(--text-tertiary)',
              fontSize: '0.7rem',
              fontStyle: 'italic',
              borderLeft: `2px dashed ${color}33`,
              paddingLeft: '0.5rem',
              marginTop: '0.25rem',
            }}>
              {emptySlots} empty slot{emptySlots !== 1 ? 's' : ''}
            </div>
          )}
        </>
      )}
    </div>
  );
}
