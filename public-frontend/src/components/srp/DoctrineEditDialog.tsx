import { useState } from 'react';
import { doctrineApi } from '../../services/api/srp';
import type { Doctrine, DoctrineCategory } from '../../types/srp';
import { DOCTRINE_CATEGORIES, CATEGORY_LABELS } from '../../types/srp';

interface DoctrineEditDialogProps {
  doctrine: Doctrine;
  onClose: () => void;
  onSaved: () => void;
}

export default function DoctrineEditDialog({ doctrine, onClose, onSaved }: DoctrineEditDialogProps) {
  const [name, setName] = useState(doctrine.name);
  const [category, setCategory] = useState<DoctrineCategory>(doctrine.category || 'general');
  const [basePayout, setBasePayout] = useState(doctrine.base_payout?.toString() || '');
  const [isActive, setIsActive] = useState(doctrine.is_active);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSave = async () => {
    if (!name.trim()) {
      setError('Name is required');
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await doctrineApi.update(doctrine.id, {
        name: name.trim(),
        category,
        base_payout: basePayout ? Number(basePayout) : null,
        is_active: isActive,
      });
      onSaved();
      onClose();
    } catch (err) {
      console.error('Failed to update doctrine:', err);
      setError('Failed to save changes');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: 'rgba(0,0,0,0.7)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
      }}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{
          background: '#16213e',
          border: '1px solid #0f3460',
          borderRadius: '12px',
          padding: '1.5rem',
          width: '420px',
          maxWidth: '90vw',
          boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
        }}
      >
        <div style={{
          fontSize: '1rem',
          fontWeight: 700,
          color: '#fff',
          marginBottom: '1.25rem',
          borderBottom: '1px solid #0f3460',
          paddingBottom: '0.75rem',
        }}>
          Edit Doctrine
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {/* Name */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
            <label style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', fontWeight: 700 }}>
              Name
            </label>
            <input
              type="text"
              value={name}
              onChange={e => setName(e.target.value)}
              style={{
                background: 'rgba(0,0,0,0.3)',
                border: '1px solid #0f3460',
                borderRadius: '4px',
                color: '#fff',
                padding: '0.5rem 0.6rem',
                fontSize: '0.85rem',
                outline: 'none',
              }}
            />
          </div>

          {/* Category */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
            <label style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', fontWeight: 700 }}>
              Category
            </label>
            <select
              value={category}
              onChange={e => setCategory(e.target.value as DoctrineCategory)}
              style={{
                background: 'rgba(0,0,0,0.3)',
                border: '1px solid #0f3460',
                borderRadius: '4px',
                color: '#fff',
                padding: '0.5rem 0.6rem',
                fontSize: '0.85rem',
                outline: 'none',
                cursor: 'pointer',
              }}
            >
              {DOCTRINE_CATEGORIES.map(cat => (
                <option key={cat} value={cat}>{CATEGORY_LABELS[cat]}</option>
              ))}
            </select>
          </div>

          {/* Base Payout */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
            <label style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', fontWeight: 700 }}>
              Base Payout (ISK)
            </label>
            <input
              type="number"
              value={basePayout}
              onChange={e => setBasePayout(e.target.value)}
              placeholder="Optional"
              style={{
                background: 'rgba(0,0,0,0.3)',
                border: '1px solid #0f3460',
                borderRadius: '4px',
                color: '#fff',
                padding: '0.5rem 0.6rem',
                fontSize: '0.85rem',
                fontFamily: 'monospace',
                outline: 'none',
              }}
            />
          </div>

          {/* Active Toggle */}
          <label style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            fontSize: '0.85rem',
            color: 'rgba(255,255,255,0.7)',
            cursor: 'pointer',
          }}>
            <input
              type="checkbox"
              checked={isActive}
              onChange={e => setIsActive(e.target.checked)}
              style={{ accentColor: '#00d4ff' }}
            />
            Active
          </label>
        </div>

        {/* Error */}
        {error && (
          <div style={{
            marginTop: '0.75rem',
            padding: '0.4rem 0.6rem',
            background: 'rgba(248,81,73,0.1)',
            border: '1px solid rgba(248,81,73,0.3)',
            borderRadius: '4px',
            color: '#f85149',
            fontSize: '0.8rem',
          }}>
            {error}
          </div>
        )}

        {/* Actions */}
        <div style={{
          display: 'flex',
          justifyContent: 'flex-end',
          gap: '0.5rem',
          marginTop: '1.25rem',
          paddingTop: '0.75rem',
          borderTop: '1px solid #0f3460',
        }}>
          <button
            onClick={onClose}
            style={{
              background: 'rgba(255,255,255,0.05)',
              border: '1px solid rgba(255,255,255,0.15)',
              borderRadius: '6px',
              color: 'rgba(255,255,255,0.6)',
              padding: '0.45rem 1rem',
              fontSize: '0.8rem',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving || !name.trim()}
            style={{
              background: 'rgba(0,212,255,0.15)',
              border: '1px solid rgba(0,212,255,0.3)',
              borderRadius: '6px',
              color: '#00d4ff',
              padding: '0.45rem 1rem',
              fontSize: '0.8rem',
              fontWeight: 600,
              cursor: saving || !name.trim() ? 'not-allowed' : 'pointer',
              opacity: saving || !name.trim() ? 0.5 : 1,
            }}
          >
            {saving ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>
    </div>
  );
}
