import { useState, useEffect } from 'react';
import { discordApi } from '../../services/api/corptools';
import type { DiscordRelay, DiscordRelayCreate } from '../../types/corptools';
import { NOTIFY_TYPE_LABELS } from '../../types/corptools';

const formatDate = (iso: string): string => {
  const d = new Date(iso);
  return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, '0')}-${String(d.getUTCDate()).padStart(2, '0')} ${String(d.getUTCHours()).padStart(2, '0')}:${String(d.getUTCMinutes()).padStart(2, '0')}`;
};

const ALL_NOTIFY_TYPES = ['timer_created', 'timer_expiring', 'battle_started', 'structure_attack', 'high_value_kill'];

export function DiscordTab() {
  const [relays, setRelays] = useState<DiscordRelay[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [testingId, setTestingId] = useState<number | null>(null);
  const [testResult, setTestResult] = useState<{ id: number; success: boolean; message: string } | null>(null);
  const [form, setForm] = useState<DiscordRelayCreate>({
    name: '', webhookUrl: '', notifyTypes: ['timer_created', 'battle_started', 'high_value_kill'],
  });

  const loadRelays = async () => {
    setLoading(true);
    try {
      const data = await discordApi.getRelays();
      setRelays(data);
    } catch (err) {
      console.error('Failed to load Discord relays:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadRelays(); }, []);

  const handleCreate = async () => {
    if (!form.name.trim() || !form.webhookUrl.trim()) return;
    setCreating(true);
    try {
      await discordApi.createRelay(form);
      setForm({ name: '', webhookUrl: '', notifyTypes: ['timer_created', 'battle_started', 'high_value_kill'] });
      setShowCreate(false);
      await loadRelays();
    } catch (err) {
      console.error('Failed to create relay:', err);
    } finally {
      setCreating(false);
    }
  };

  const handleToggle = async (relay: DiscordRelay) => {
    try {
      await discordApi.updateRelay(relay.id, { isActive: !relay.isActive });
      await loadRelays();
    } catch (err) {
      console.error('Failed to toggle relay:', err);
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await discordApi.deleteRelay(id);
      await loadRelays();
    } catch (err) {
      console.error('Failed to delete relay:', err);
    }
  };

  const handleTest = async (id: number) => {
    setTestingId(id);
    setTestResult(null);
    try {
      const result = await discordApi.testRelay(id);
      setTestResult({ id, success: result.success, message: result.message });
    } catch (err) {
      setTestResult({ id, success: false, message: 'Test failed' });
    } finally {
      setTestingId(null);
    }
  };

  const toggleNotifyType = (type: string) => {
    const current = form.notifyTypes || [];
    if (current.includes(type)) {
      setForm({ ...form, notifyTypes: current.filter(t => t !== type) });
    } else {
      setForm({ ...form, notifyTypes: [...current, type] });
    }
  };

  const inputStyle = {
    background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-color)',
    borderRadius: '4px', color: '#fff', padding: '0.4rem 0.6rem', fontSize: '0.8rem', outline: 'none',
    width: '100%',
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <div style={{ fontSize: '0.9rem', fontWeight: 600 }}>Discord Webhooks ({relays.length}/10)</div>
          <div style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.4)' }}>
            Send automated notifications to Discord channels
          </div>
        </div>
        <button onClick={() => setShowCreate(!showCreate)} disabled={relays.length >= 10} style={{
          background: showCreate ? 'rgba(255,255,255,0.05)' : 'rgba(168,85,247,0.15)',
          border: '1px solid rgba(168,85,247,0.3)', borderRadius: '6px',
          color: '#a855f7', padding: '0.4rem 1rem', fontSize: '0.8rem', fontWeight: 600,
          cursor: relays.length >= 10 ? 'not-allowed' : 'pointer',
          opacity: relays.length >= 10 ? 0.5 : 1,
        }}>
          {showCreate ? 'Cancel' : 'Add Webhook'}
        </button>
      </div>

      {/* Create form */}
      {showCreate && (
        <div style={{
          background: 'var(--bg-secondary)', border: '1px solid var(--border-color)',
          borderRadius: '8px', padding: '1rem',
          display: 'flex', flexDirection: 'column', gap: '0.75rem',
        }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
              <label style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase' }}>Name</label>
              <input value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} style={inputStyle} placeholder="e.g. Intel Channel" />
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
              <label style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase' }}>Min ISK Threshold</label>
              <input type="number" value={form.minIskThreshold || ''} onChange={e => setForm({ ...form, minIskThreshold: Number(e.target.value) })}
                style={inputStyle} placeholder="0 = all kills" />
            </div>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
            <label style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase' }}>Webhook URL</label>
            <input value={form.webhookUrl} onChange={e => setForm({ ...form, webhookUrl: e.target.value })} style={inputStyle}
              placeholder="https://discord.com/api/webhooks/..." />
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
            <label style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase' }}>Ping Role ID (optional)</label>
            <input value={form.pingRoleId || ''} onChange={e => setForm({ ...form, pingRoleId: e.target.value || undefined })} style={inputStyle}
              placeholder="Discord Role ID for @mentions" />
          </div>
          <div>
            <label style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', display: 'block', marginBottom: '0.5rem' }}>Event Types</label>
            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
              {ALL_NOTIFY_TYPES.map(type => {
                const selected = (form.notifyTypes || []).includes(type);
                return (
                  <button key={type} onClick={() => toggleNotifyType(type)} style={{
                    background: selected ? 'rgba(168,85,247,0.15)' : 'rgba(255,255,255,0.03)',
                    border: selected ? '1px solid rgba(168,85,247,0.4)' : '1px solid rgba(255,255,255,0.1)',
                    borderRadius: '4px', color: selected ? '#a855f7' : 'rgba(255,255,255,0.4)',
                    padding: '0.3rem 0.6rem', fontSize: '0.75rem', cursor: 'pointer',
                  }}>
                    {NOTIFY_TYPE_LABELS[type] || type}
                  </button>
                );
              })}
            </div>
          </div>
          <button onClick={handleCreate} disabled={creating || !form.name.trim() || !form.webhookUrl.trim()} style={{
            background: 'rgba(168,85,247,0.15)', border: '1px solid rgba(168,85,247,0.3)',
            borderRadius: '6px', color: '#a855f7', padding: '0.5rem 1.25rem',
            fontSize: '0.85rem', fontWeight: 600, alignSelf: 'flex-start',
            cursor: creating || !form.name.trim() || !form.webhookUrl.trim() ? 'not-allowed' : 'pointer',
          }}>
            {creating ? 'Creating...' : 'Create Webhook'}
          </button>
        </div>
      )}

      {/* Relays list */}
      {loading ? (
        <div style={{ padding: '2rem', textAlign: 'center', color: 'rgba(255,255,255,0.3)', fontSize: '0.85rem' }}>Loading...</div>
      ) : relays.length === 0 ? (
        <div style={{
          background: 'var(--bg-secondary)', border: '1px solid var(--border-color)',
          borderRadius: '8px', padding: '2rem', textAlign: 'center', color: 'rgba(255,255,255,0.3)',
          fontSize: '0.85rem',
        }}>No Discord webhooks configured</div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          {relays.map(relay => (
            <div key={relay.id} style={{
              background: 'var(--bg-secondary)', border: `1px solid ${relay.isActive ? 'rgba(168,85,247,0.3)' : 'var(--border-color)'}`,
              borderRadius: '8px', padding: '1rem',
              opacity: relay.isActive ? 1 : 0.6,
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.5rem' }}>
                <div>
                  <div style={{ fontWeight: 600, fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    {relay.name}
                    <span style={{
                      padding: '2px 6px', borderRadius: '3px', fontSize: '0.65rem', fontWeight: 700,
                      background: relay.isActive ? 'rgba(63,185,80,0.15)' : 'rgba(255,255,255,0.05)',
                      color: relay.isActive ? '#3fb950' : 'rgba(255,255,255,0.3)',
                    }}>{relay.isActive ? 'ACTIVE' : 'INACTIVE'}</span>
                  </div>
                  <div style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.35)', marginTop: '0.15rem' }}>
                    Created: {formatDate(relay.createdAt)}
                    {relay.minIskThreshold > 0 && ` | Min ISK: ${(relay.minIskThreshold / 1e6).toFixed(0)}M`}
                    {relay.pingRoleId && ` | Ping: ${relay.pingRoleId}`}
                  </div>
                </div>
                <div style={{ display: 'flex', gap: '0.4rem' }}>
                  <button onClick={() => handleTest(relay.id)} disabled={testingId === relay.id} style={{
                    background: 'rgba(0,212,255,0.1)', border: '1px solid rgba(0,212,255,0.3)',
                    borderRadius: '4px', color: '#00d4ff', padding: '3px 8px', fontSize: '0.7rem',
                    fontWeight: 600, cursor: testingId === relay.id ? 'not-allowed' : 'pointer',
                  }}>
                    {testingId === relay.id ? 'Testing...' : 'Test'}
                  </button>
                  <button onClick={() => handleToggle(relay)} style={{
                    background: relay.isActive ? 'rgba(255,255,255,0.05)' : 'rgba(63,185,80,0.1)',
                    border: `1px solid ${relay.isActive ? 'rgba(255,255,255,0.15)' : 'rgba(63,185,80,0.3)'}`,
                    borderRadius: '4px', color: relay.isActive ? 'rgba(255,255,255,0.5)' : '#3fb950',
                    padding: '3px 8px', fontSize: '0.7rem', fontWeight: 600, cursor: 'pointer',
                  }}>
                    {relay.isActive ? 'Disable' : 'Enable'}
                  </button>
                  <button onClick={() => handleDelete(relay.id)} style={{
                    background: 'rgba(248,81,73,0.1)', border: '1px solid rgba(248,81,73,0.3)',
                    borderRadius: '4px', color: '#f85149', padding: '3px 8px', fontSize: '0.7rem',
                    fontWeight: 600, cursor: 'pointer',
                  }}>Delete</button>
                </div>
              </div>

              {/* Event types */}
              <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
                {(relay.notifyTypes || []).map(type => (
                  <span key={type} style={{
                    padding: '2px 6px', borderRadius: '3px', fontSize: '0.65rem', fontWeight: 600,
                    background: 'rgba(168,85,247,0.1)', color: '#a855f7',
                    border: '1px solid rgba(168,85,247,0.2)',
                  }}>
                    {NOTIFY_TYPE_LABELS[type] || type}
                  </span>
                ))}
              </div>

              {/* Filters */}
              {((relay.filterRegions?.length ?? 0) > 0 || (relay.filterAlliances?.length ?? 0) > 0) && (
                <div style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', marginTop: '0.4rem' }}>
                  {(relay.filterRegions?.length ?? 0) > 0 && <span>Regions: {relay.filterRegions.join(', ')} | </span>}
                  {(relay.filterAlliances?.length ?? 0) > 0 && <span>Alliances: {relay.filterAlliances.join(', ')}</span>}
                </div>
              )}

              {/* Test result */}
              {testResult && testResult.id === relay.id && (
                <div style={{
                  marginTop: '0.5rem', padding: '0.4rem 0.6rem', borderRadius: '4px', fontSize: '0.78rem',
                  background: testResult.success ? 'rgba(63,185,80,0.1)' : 'rgba(248,81,73,0.1)',
                  color: testResult.success ? '#3fb950' : '#f85149',
                  border: `1px solid ${testResult.success ? 'rgba(63,185,80,0.3)' : 'rgba(248,81,73,0.3)'}`,
                }}>
                  {testResult.success ? 'Test message sent successfully' : `Test failed: ${testResult.message}`}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
