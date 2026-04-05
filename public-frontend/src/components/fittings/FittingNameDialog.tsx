import { useState, useEffect } from 'react';
import { FITTING_TAGS } from '../../types/fittings';

interface FittingNameDialogProps {
  open: boolean;
  onClose: () => void;
  onSave: (data: { name: string; description: string; tags: string[]; isPublic: boolean; overwrite?: boolean }) => void;
  initialName?: string;
  saving?: boolean;
  editingFittingId?: number | null;
}

export function FittingNameDialog({ open, onClose, onSave, initialName = '', saving = false, editingFittingId }: FittingNameDialogProps) {
  const [name, setName] = useState(initialName);
  const [description, setDescription] = useState('');
  const [tags, setTags] = useState<string[]>([]);
  const [isPublic, setIsPublic] = useState(false);

  // Sync name when dialog opens (useState only captures value on first mount)
  useEffect(() => {
    if (open) {
      setName(initialName);
    }
  }, [open, initialName]);

  if (!open) return null;

  const isEditing = !!editingFittingId;

  const handleSave = (overwrite: boolean) => {
    if (name.trim() === '') return;
    onSave({ name, description, tags, isPublic, overwrite });
  };

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,0.7)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
      }}
      onClick={onClose}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{
          background: 'var(--bg-primary)',
          border: '1px solid var(--border-color)',
          borderRadius: '12px',
          padding: '1.5rem',
          maxWidth: 560,
          width: '90%',
          maxHeight: '80vh',
          overflowY: 'auto',
        }}
      >
        <h2 style={{ margin: '0 0 1rem 0', fontSize: '1.25rem', fontWeight: 700 }}>
          {isEditing ? 'Save Fitting' : 'Save New Fitting'}
        </h2>

        {/* Name */}
        <div style={{ marginBottom: '1rem' }}>
          <label style={{ display: 'block', marginBottom: '0.25rem', fontSize: '0.85rem', fontWeight: 600 }}>
            Name <span style={{ color: '#f85149' }}>*</span>
          </label>
          <input
            type="text"
            value={name}
            onChange={e => setName(e.target.value)}
            placeholder="My Awesome Fitting"
            autoFocus
            style={{
              width: '100%',
              padding: '0.5rem',
              background: 'var(--bg-secondary)',
              border: '1px solid var(--border-color)',
              borderRadius: '6px',
              color: 'var(--text-primary)',
              fontSize: '0.9rem',
              outline: 'none',
              boxSizing: 'border-box',
            }}
          />
        </div>

        {/* Description */}
        <div style={{ marginBottom: '1rem' }}>
          <label style={{ display: 'block', marginBottom: '0.25rem', fontSize: '0.85rem', fontWeight: 600 }}>
            Description
          </label>
          <textarea
            value={description}
            onChange={e => setDescription(e.target.value)}
            placeholder="Optional notes..."
            rows={3}
            style={{
              width: '100%',
              padding: '0.5rem',
              background: 'var(--bg-secondary)',
              border: '1px solid var(--border-color)',
              borderRadius: '6px',
              color: 'var(--text-primary)',
              fontSize: '0.9rem',
              outline: 'none',
              resize: 'vertical',
              fontFamily: 'inherit',
              boxSizing: 'border-box',
            }}
          />
        </div>

        {/* Tags */}
        <div style={{ marginBottom: '1rem' }}>
          <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.85rem', fontWeight: 600 }}>
            Tags
          </label>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
            {FITTING_TAGS.map(tag => (
              <button
                key={tag}
                onClick={() => setTags(prev => prev.includes(tag) ? prev.filter(t => t !== tag) : [...prev, tag])}
                style={{
                  padding: '4px 10px',
                  fontSize: '0.75rem',
                  borderRadius: '12px',
                  cursor: 'pointer',
                  background: tags.includes(tag) ? 'rgba(0,212,255,0.15)' : 'transparent',
                  border: tags.includes(tag) ? '1px solid rgba(0,212,255,0.4)' : '1px solid var(--border-color)',
                  color: tags.includes(tag) ? '#00d4ff' : 'var(--text-secondary)',
                }}
              >
                {tag}
              </button>
            ))}
          </div>
        </div>

        {/* Public toggle */}
        <div style={{ marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <input
            type="checkbox"
            checked={isPublic}
            onChange={e => setIsPublic(e.target.checked)}
            id="public-toggle"
            style={{ width: 16, height: 16, cursor: 'pointer' }}
          />
          <label htmlFor="public-toggle" style={{ fontSize: '0.85rem', cursor: 'pointer' }}>
            Make this fitting public (visible to all users)
          </label>
        </div>

        {/* Footer */}
        <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
          <button
            onClick={onClose}
            disabled={saving}
            style={{
              padding: '0.5rem 1rem',
              background: 'transparent',
              border: '1px solid var(--border-color)',
              borderRadius: '6px',
              color: 'var(--text-secondary)',
              cursor: saving ? 'not-allowed' : 'pointer',
              fontSize: '0.85rem',
              opacity: saving ? 0.5 : 1,
            }}
          >
            Cancel
          </button>
          {isEditing && (
            <button
              onClick={() => handleSave(true)}
              disabled={name.trim() === '' || saving}
              style={{
                padding: '0.5rem 1rem',
                background: name.trim() === '' || saving ? 'var(--bg-secondary)' : 'rgba(210,153,34,0.15)',
                border: `1px solid ${name.trim() === '' || saving ? 'var(--border-color)' : 'rgba(210,153,34,0.4)'}`,
                borderRadius: '6px',
                color: name.trim() === '' || saving ? 'var(--text-tertiary)' : '#d29922',
                cursor: name.trim() === '' || saving ? 'not-allowed' : 'pointer',
                fontSize: '0.85rem',
                fontWeight: 600,
              }}
            >
              {saving ? 'Saving...' : 'Overwrite'}
            </button>
          )}
          <button
            onClick={() => handleSave(false)}
            disabled={name.trim() === '' || saving}
            style={{
              padding: '0.5rem 1rem',
              background: name.trim() === '' || saving ? 'var(--bg-secondary)' : '#00d4ff',
              border: 'none',
              borderRadius: '6px',
              color: name.trim() === '' || saving ? 'var(--text-tertiary)' : '#000',
              cursor: name.trim() === '' || saving ? 'not-allowed' : 'pointer',
              fontSize: '0.85rem',
              fontWeight: 600,
            }}
          >
            {saving ? 'Saving...' : 'Save as New'}
          </button>
        </div>
      </div>
    </div>
  );
}
