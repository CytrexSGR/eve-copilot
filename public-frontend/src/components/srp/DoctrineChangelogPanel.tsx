import { useState, useEffect } from 'react';
import { doctrineApi } from '../../services/api/srp';
import type { DoctrineChangelogEntry } from '../../types/srp';

const ACTION_COLORS: Record<string, string> = {
  created: '#56d364',
  updated: '#58a6ff',
  archived: '#f85149',
  restored: '#56d364',
  cloned: '#bc8cff',
};

function formatTimestamp(iso: string): string {
  const d = new Date(iso);
  const date = `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, '0')}-${String(d.getUTCDate()).padStart(2, '0')}`;
  const time = `${String(d.getUTCHours()).padStart(2, '0')}:${String(d.getUTCMinutes()).padStart(2, '0')}`;
  return `${date} ${time}`;
}

function formatChangeDetails(changes: Record<string, { old?: unknown; new?: unknown }>): string {
  const parts: string[] = [];
  for (const [field, diff] of Object.entries(changes)) {
    if (diff.old !== undefined && diff.new !== undefined) {
      parts.push(`${field}: ${String(diff.old)} -> ${String(diff.new)}`);
    } else if (diff.new !== undefined) {
      parts.push(`${field}: ${String(diff.new)}`);
    } else if (diff.old !== undefined) {
      parts.push(`${field}: removed ${String(diff.old)}`);
    }
  }
  return parts.join(', ') || '\u2014';
}

export function DoctrineChangelogPanel({ doctrineId }: { doctrineId: number }) {
  const [entries, setEntries] = useState<DoctrineChangelogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(false);

    doctrineApi.getChangelog(doctrineId)
      .then((data) => {
        if (!cancelled) setEntries(data);
      })
      .catch(() => {
        if (!cancelled) setError(true);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, [doctrineId]);

  if (loading) {
    return (
      <div style={{
        background: 'rgba(0,0,0,0.15)',
        border: '1px solid var(--border-color)',
        borderRadius: '8px',
        padding: '1rem',
      }}>
        <span style={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.85rem' }}>Loading changelog...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{
        background: 'rgba(0,0,0,0.15)',
        border: '1px solid var(--border-color)',
        borderRadius: '8px',
        padding: '1rem',
      }}>
        <span style={{ color: 'rgba(248,81,73,0.7)', fontSize: '0.85rem' }}>Failed to load changelog</span>
      </div>
    );
  }

  if (entries.length === 0) {
    return (
      <div style={{
        background: 'rgba(0,0,0,0.15)',
        border: '1px solid var(--border-color)',
        borderRadius: '8px',
        padding: '1.5rem',
        textAlign: 'center',
      }}>
        <span style={{ color: 'rgba(255,255,255,0.35)', fontSize: '0.85rem' }}>No changelog entries</span>
      </div>
    );
  }

  return (
    <div style={{
      background: 'rgba(0,0,0,0.15)',
      border: '1px solid var(--border-color)',
      borderRadius: '8px',
      overflow: 'hidden',
    }}>
      <div style={{
        display: 'grid',
        gridTemplateColumns: '130px 80px 120px 1fr',
        gap: '0.5rem',
        padding: '0.5rem 0.75rem',
        borderBottom: '1px solid var(--border-color)',
        fontSize: '0.7rem',
        fontWeight: 700,
        textTransform: 'uppercase',
        color: 'rgba(255,255,255,0.45)',
      }}>
        <span>Time</span>
        <span>Action</span>
        <span>Actor</span>
        <span>Details</span>
      </div>
      <div style={{ maxHeight: '360px', overflowY: 'auto' }}>
        {entries.map((entry, idx) => {
          const actionColor = ACTION_COLORS[entry.action] || 'rgba(255,255,255,0.5)';
          return (
            <div
              key={entry.id}
              style={{
                display: 'grid',
                gridTemplateColumns: '130px 80px 120px 1fr',
                gap: '0.5rem',
                padding: '0.4rem 0.75rem',
                fontSize: '0.8rem',
                background: idx % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.02)',
                borderBottom: '1px solid rgba(255,255,255,0.03)',
                alignItems: 'center',
              }}
            >
              <span style={{
                fontFamily: 'monospace',
                fontSize: '0.73rem',
                color: 'rgba(255,255,255,0.45)',
              }}>
                {formatTimestamp(entry.created_at)}
              </span>
              <span style={{
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                padding: '1px 6px',
                borderRadius: '3px',
                fontSize: '0.68rem',
                fontWeight: 700,
                textTransform: 'uppercase',
                letterSpacing: '0.03em',
                background: `${actionColor}15`,
                border: `1px solid ${actionColor}40`,
                color: actionColor,
                whiteSpace: 'nowrap',
              }}>
                {entry.action}
              </span>
              <span style={{
                color: 'rgba(255,255,255,0.6)',
                fontSize: '0.78rem',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}>
                {entry.actor_name}
              </span>
              <span style={{
                color: 'rgba(255,255,255,0.5)',
                fontSize: '0.75rem',
                fontFamily: 'monospace',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}>
                {formatChangeDetails(entry.changes)}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
