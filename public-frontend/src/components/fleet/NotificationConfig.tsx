import { useState, useEffect, useCallback } from 'react';
import { notificationApi } from '../../services/api/fleet';

/* ── types ───────────────────────────────────────────────── */

interface NotificationConfigEntry {
  id: number;
  webhook_url: string;
  event_types: string[];
  ping_role: string | null;
  is_active: boolean;
  created_at: string;
}

const EVENT_TYPES = [
  { value: 'op_created', label: 'Op Created', color: '#58a6ff' },
  { value: 'op_reminder', label: 'Op Reminder', color: '#d29922' },
  { value: 'fleet_started', label: 'Fleet Started', color: '#3fb950' },
  { value: 'fleet_closed', label: 'Fleet Closed', color: '#f85149' },
] as const;

/* ── helpers ─────────────────────────────────────────────── */

function maskWebhook(url: string): string {
  if (url.length <= 20) return url;
  return url.substring(0, 20) + '...';
}

function eventBadgeColor(evt: string): string {
  return EVENT_TYPES.find(e => e.value === evt)?.color ?? '#8b949e';
}

function eventLabel(evt: string): string {
  return EVENT_TYPES.find(e => e.value === evt)?.label ?? evt;
}

/* ── component ───────────────────────────────────────────── */

export function NotificationConfig() {
  const [configs, setConfigs] = useState<NotificationConfigEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [showForm, setShowForm] = useState(false);
  const [webhookUrl, setWebhookUrl] = useState('');
  const [selectedEvents, setSelectedEvents] = useState<string[]>([]);
  const [pingRole, setPingRole] = useState('');
  const [saving, setSaving] = useState(false);

  // Delete confirmation
  const [deleteId, setDeleteId] = useState<number | null>(null);

  const loadConfigs = useCallback(async () => {
    try {
      setError(null);
      const data = await notificationApi.listConfigs();
      setConfigs(Array.isArray(data) ? data : (data.configs ?? []));
    } catch (err: any) {
      console.error('Failed to load notification configs:', err);
      setError(err?.response?.data?.detail ?? 'Failed to load notification configs');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadConfigs();
  }, [loadConfigs]);

  const handleToggleEvent = (evt: string) => {
    setSelectedEvents(prev =>
      prev.includes(evt)
        ? prev.filter(e => e !== evt)
        : [...prev, evt]
    );
  };

  const handleCreate = async () => {
    if (!webhookUrl.trim() || selectedEvents.length === 0) return;
    setSaving(true);
    try {
      await notificationApi.createConfig({
        webhook_url: webhookUrl.trim(),
        event_types: selectedEvents,
        ping_role: pingRole.trim() || undefined,
      });
      setWebhookUrl('');
      setSelectedEvents([]);
      setPingRole('');
      setShowForm(false);
      await loadConfigs();
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? 'Failed to create config');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await notificationApi.deleteConfig(id);
      setDeleteId(null);
      await loadConfigs();
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? 'Failed to delete config');
    }
  };

  /* ── styles ── */

  const cardStyle: React.CSSProperties = {
    background: 'var(--bg-secondary)',
    border: '1px solid var(--border-color)',
    borderRadius: '8px',
    padding: '1rem',
    marginBottom: '0.75rem',
  };

  const badgeStyle = (color: string): React.CSSProperties => ({
    display: 'inline-block',
    padding: '2px 8px',
    borderRadius: '12px',
    fontSize: '0.75rem',
    fontWeight: 600,
    color,
    background: `${color}18`,
    border: `1px solid ${color}44`,
    marginRight: '0.4rem',
    marginBottom: '0.25rem',
  });

  const btnStyle = (color: string, filled = false): React.CSSProperties => ({
    background: filled ? color : 'transparent',
    border: `1px solid ${color}`,
    color: filled ? '#fff' : color,
    padding: '0.4rem 0.8rem',
    borderRadius: '6px',
    cursor: 'pointer',
    fontSize: '0.8rem',
    fontWeight: 500,
    transition: 'all 0.2s',
  });

  const inputStyle: React.CSSProperties = {
    background: 'var(--bg-primary, #0d1117)',
    border: '1px solid var(--border-color)',
    borderRadius: '6px',
    color: 'var(--text-primary, #e6edf3)',
    padding: '0.5rem 0.75rem',
    fontSize: '0.85rem',
    width: '100%',
    boxSizing: 'border-box' as const,
  };

  /* ── render ── */

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-secondary)' }}>
        Loading notification configs...
      </div>
    );
  }

  return (
    <div>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <div>
          <h3 style={{ margin: 0, fontSize: '1rem', color: 'var(--text-primary, #e6edf3)' }}>
            Discord Notifications
          </h3>
          <p style={{ margin: '0.25rem 0 0', fontSize: '0.8rem', color: 'var(--text-secondary, #8b949e)' }}>
            Configure Discord webhooks for fleet operation notifications
          </p>
        </div>
        {!showForm && (
          <button
            onClick={() => setShowForm(true)}
            style={btnStyle('#58a6ff', true)}
          >
            + Add Webhook
          </button>
        )}
      </div>

      {/* Error */}
      {error && (
        <div style={{
          background: 'rgba(248,81,73,0.1)',
          border: '1px solid rgba(248,81,73,0.4)',
          borderRadius: '6px',
          padding: '0.6rem 1rem',
          marginBottom: '1rem',
          color: '#f85149',
          fontSize: '0.85rem',
        }}>
          {error}
          <button
            onClick={() => setError(null)}
            style={{ float: 'right', background: 'none', border: 'none', color: '#f85149', cursor: 'pointer', fontSize: '0.85rem' }}
          >
            ✕
          </button>
        </div>
      )}

      {/* Create form */}
      {showForm && (
        <div style={{
          ...cardStyle,
          borderColor: 'rgba(88,166,255,0.4)',
          background: 'rgba(88,166,255,0.05)',
        }}>
          <div style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-primary, #e6edf3)', marginBottom: '0.75rem' }}>
            New Webhook Configuration
          </div>

          {/* Webhook URL */}
          <div style={{ marginBottom: '0.75rem' }}>
            <label style={{ display: 'block', fontSize: '0.8rem', color: 'var(--text-secondary, #8b949e)', marginBottom: '0.3rem' }}>
              Webhook URL *
            </label>
            <input
              type="text"
              value={webhookUrl}
              onChange={e => setWebhookUrl(e.target.value)}
              placeholder="https://discord.com/api/webhooks/..."
              style={inputStyle}
            />
          </div>

          {/* Event Types */}
          <div style={{ marginBottom: '0.75rem' }}>
            <label style={{ display: 'block', fontSize: '0.8rem', color: 'var(--text-secondary, #8b949e)', marginBottom: '0.3rem' }}>
              Event Types *
            </label>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
              {EVENT_TYPES.map(evt => (
                <label
                  key={evt.value}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.4rem',
                    padding: '0.35rem 0.7rem',
                    borderRadius: '6px',
                    cursor: 'pointer',
                    fontSize: '0.8rem',
                    border: selectedEvents.includes(evt.value)
                      ? `1px solid ${evt.color}88`
                      : '1px solid var(--border-color)',
                    background: selectedEvents.includes(evt.value)
                      ? `${evt.color}15`
                      : 'transparent',
                    color: selectedEvents.includes(evt.value)
                      ? evt.color
                      : 'var(--text-secondary, #8b949e)',
                    transition: 'all 0.2s',
                  }}
                >
                  <input
                    type="checkbox"
                    checked={selectedEvents.includes(evt.value)}
                    onChange={() => handleToggleEvent(evt.value)}
                    style={{ accentColor: evt.color }}
                  />
                  {evt.label}
                </label>
              ))}
            </div>
          </div>

          {/* Ping Role */}
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', fontSize: '0.8rem', color: 'var(--text-secondary, #8b949e)', marginBottom: '0.3rem' }}>
              Ping Role (optional)
            </label>
            <input
              type="text"
              value={pingRole}
              onChange={e => setPingRole(e.target.value)}
              placeholder="e.g. @fleet-ping or role ID"
              style={{ ...inputStyle, maxWidth: '300px' }}
            />
            <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary, #8b949e)', marginTop: '0.2rem' }}>
              Discord role name or ID to ping with notifications
            </div>
          </div>

          {/* Form Buttons */}
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button
              onClick={handleCreate}
              disabled={saving || !webhookUrl.trim() || selectedEvents.length === 0}
              style={{
                ...btnStyle('#3fb950', true),
                opacity: saving || !webhookUrl.trim() || selectedEvents.length === 0 ? 0.5 : 1,
                cursor: saving || !webhookUrl.trim() || selectedEvents.length === 0 ? 'not-allowed' : 'pointer',
              }}
            >
              {saving ? 'Saving...' : 'Save Config'}
            </button>
            <button
              onClick={() => {
                setShowForm(false);
                setWebhookUrl('');
                setSelectedEvents([]);
                setPingRole('');
              }}
              style={btnStyle('#8b949e')}
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Config List */}
      {configs.length === 0 ? (
        <div style={{
          ...cardStyle,
          textAlign: 'center',
          color: 'var(--text-secondary, #8b949e)',
          padding: '2rem',
        }}>
          No webhook configurations found. Add one to receive Discord notifications for fleet operations.
        </div>
      ) : (
        configs.map(cfg => (
          <div key={cfg.id} style={{
            ...cardStyle,
            opacity: cfg.is_active ? 1 : 0.6,
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div style={{ flex: 1 }}>
                {/* Webhook URL (masked) */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                  <span style={{
                    fontFamily: 'monospace',
                    fontSize: '0.8rem',
                    color: 'var(--text-primary, #e6edf3)',
                    background: 'var(--bg-primary, #0d1117)',
                    padding: '2px 8px',
                    borderRadius: '4px',
                    border: '1px solid var(--border-color)',
                  }}>
                    {maskWebhook(cfg.webhook_url)}
                  </span>
                  <span style={{
                    ...badgeStyle(cfg.is_active ? '#3fb950' : '#8b949e'),
                    marginRight: 0,
                  }}>
                    {cfg.is_active ? 'Active' : 'Inactive'}
                  </span>
                </div>

                {/* Event Type Badges */}
                <div style={{ marginBottom: '0.4rem' }}>
                  {cfg.event_types.map(evt => (
                    <span key={evt} style={badgeStyle(eventBadgeColor(evt))}>
                      {eventLabel(evt)}
                    </span>
                  ))}
                </div>

                {/* Ping Role */}
                {cfg.ping_role && (
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary, #8b949e)' }}>
                    Ping: <span style={{ color: '#d2a8ff' }}>@{cfg.ping_role}</span>
                  </div>
                )}

                {/* Created */}
                <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary, #8b949e)', marginTop: '0.3rem' }}>
                  Created: {new Date(cfg.created_at).toLocaleDateString()}
                </div>
              </div>

              {/* Actions */}
              <div style={{ display: 'flex', gap: '0.4rem', marginLeft: '1rem' }}>
                {deleteId === cfg.id ? (
                  <>
                    <button
                      onClick={() => handleDelete(cfg.id)}
                      style={btnStyle('#f85149', true)}
                    >
                      Confirm
                    </button>
                    <button
                      onClick={() => setDeleteId(null)}
                      style={btnStyle('#8b949e')}
                    >
                      Cancel
                    </button>
                  </>
                ) : (
                  <button
                    onClick={() => setDeleteId(cfg.id)}
                    style={btnStyle('#f85149')}
                  >
                    Delete
                  </button>
                )}
              </div>
            </div>
          </div>
        ))
      )}
    </div>
  );
}
