import { useState, useEffect, useRef, useCallback } from 'react';
import { fleetApi, syncApi } from '../../services/api/fleet';
import type { FleetOperationSummary, FleetRegisterRequest, FleetParticipation } from '../../types/fleet';
import { formatDuration } from '../../types/fleet';

const formatDate = (iso: string): string => {
  const d = new Date(iso);
  return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, '0')}-${String(d.getUTCDate()).padStart(2, '0')} ${String(d.getUTCHours()).padStart(2, '0')}:${String(d.getUTCMinutes()).padStart(2, '0')}`;
};

interface SyncStatus {
  is_syncing: boolean;
  last_sync?: string;
  error?: string;
  esi_fleet_id?: number;
  fc_character_id?: number;
}

export function OperationsTab({ corpId: _corpId }: { corpId: number }) {
  const [active, setActive] = useState<FleetOperationSummary[]>([]);
  const [history, setHistory] = useState<FleetOperationSummary[]>([]);
  const [loadingActive, setLoadingActive] = useState(true);
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [papData, setPapData] = useState<FleetParticipation | null>(null);
  const [loadingPap, setLoadingPap] = useState(false);
  const [form, setForm] = useState<FleetRegisterRequest>({ fleetName: '' });

  // Sync state
  const [syncStatuses, setSyncStatuses] = useState<Record<number, SyncStatus>>({});
  const [syncForms, setSyncForms] = useState<Record<number, { esiFleetId: string; fcCharId: string }>>({});
  const [showSyncForm, setShowSyncForm] = useState<Record<number, boolean>>({});
  const [syncLoading, setSyncLoading] = useState<Record<number, boolean>>({});
  const syncIntervalRef = useRef<Record<number, ReturnType<typeof setInterval>>>({});

  const loadData = async () => {
    setLoadingActive(true);
    setLoadingHistory(true);
    fleetApi.getActive()
      .then(setActive)
      .catch(err => console.error('Failed to load active fleets:', err))
      .finally(() => setLoadingActive(false));
    fleetApi.getHistory({ limit: 30 })
      .then(setHistory)
      .catch(err => console.error('Failed to load fleet history:', err))
      .finally(() => setLoadingHistory(false));
  };

  const fetchSyncStatus = useCallback(async (opId: number) => {
    try {
      const { data } = await syncApi.status(opId);
      setSyncStatuses(prev => ({ ...prev, [opId]: data }));
    } catch {
      // Sync endpoint may not exist yet — ignore errors silently
    }
  }, []);

  // Fetch sync status for all active fleets
  useEffect(() => {
    if (active.length > 0) {
      active.forEach(op => fetchSyncStatus(op.id));
    }
  }, [active, fetchSyncStatus]);

  // Auto-refresh sync status every 30s for syncing fleets
  useEffect(() => {
    const intervals = syncIntervalRef.current;
    // Clear old intervals
    Object.values(intervals).forEach(clearInterval);
    syncIntervalRef.current = {};

    // Set up new intervals for syncing fleets
    Object.entries(syncStatuses).forEach(([opIdStr, status]) => {
      if (status.is_syncing) {
        const opId = Number(opIdStr);
        syncIntervalRef.current[opId] = setInterval(() => {
          fetchSyncStatus(opId);
        }, 30000);
      }
    });

    return () => {
      Object.values(syncIntervalRef.current).forEach(clearInterval);
    };
  }, [syncStatuses, fetchSyncStatus]);

  useEffect(() => { loadData(); }, []);

  const handleCreate = async () => {
    if (!form.fleetName.trim()) return;
    setCreating(true);
    try {
      await fleetApi.register(form);
      setForm({ fleetName: '' });
      setShowCreate(false);
      await loadData();
    } catch (err) {
      console.error('Failed to create fleet:', err);
    } finally {
      setCreating(false);
    }
  };

  const handleClose = async (opId: number) => {
    try {
      await fleetApi.close(opId);
      await loadData();
    } catch (err) {
      console.error('Failed to close fleet:', err);
    }
  };

  const handleExpand = async (opId: number) => {
    if (expandedId === opId) {
      setExpandedId(null);
      setPapData(null);
      return;
    }
    setExpandedId(opId);
    setLoadingPap(true);
    try {
      const data = await fleetApi.getParticipation(opId);
      setPapData(data);
    } catch (err) {
      console.error('Failed to load PAP data:', err);
      setPapData(null);
    } finally {
      setLoadingPap(false);
    }
  };

  const handleSyncStart = async (opId: number) => {
    const formData = syncForms[opId];
    if (!formData?.esiFleetId || !formData?.fcCharId) return;
    const esiFleetId = Number(formData.esiFleetId);
    const fcCharId = Number(formData.fcCharId);
    if (isNaN(esiFleetId) || isNaN(fcCharId)) return;

    setSyncLoading(prev => ({ ...prev, [opId]: true }));
    try {
      await syncApi.start(opId, esiFleetId, fcCharId);
      setShowSyncForm(prev => ({ ...prev, [opId]: false }));
      setSyncForms(prev => ({ ...prev, [opId]: { esiFleetId: '', fcCharId: '' } }));
      await fetchSyncStatus(opId);
    } catch (err: any) {
      const msg = err?.response?.data?.error || err?.message || 'Sync start failed';
      setSyncStatuses(prev => ({
        ...prev,
        [opId]: { ...prev[opId], is_syncing: false, error: msg },
      }));
    } finally {
      setSyncLoading(prev => ({ ...prev, [opId]: false }));
    }
  };

  const handleSyncStop = async (opId: number) => {
    setSyncLoading(prev => ({ ...prev, [opId]: true }));
    try {
      await syncApi.stop(opId);
      await fetchSyncStatus(opId);
    } catch (err: any) {
      const msg = err?.response?.data?.error || err?.message || 'Sync stop failed';
      setSyncStatuses(prev => ({
        ...prev,
        [opId]: { ...prev[opId], error: msg },
      }));
    } finally {
      setSyncLoading(prev => ({ ...prev, [opId]: false }));
    }
  };

  const inputStyle = {
    background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-color)',
    borderRadius: '4px', color: '#fff', padding: '0.4rem 0.6rem', fontSize: '0.8rem', outline: 'none',
  };

  const renderSyncControls = (op: FleetOperationSummary) => {
    const status = syncStatuses[op.id];
    const isSyncing = status?.is_syncing ?? false;
    const isLoading = syncLoading[op.id] ?? false;
    const showForm = showSyncForm[op.id] ?? false;
    const formData = syncForms[op.id] ?? { esiFleetId: '', fcCharId: '' };

    return (
      <div style={{
        marginTop: '0.5rem',
        paddingTop: '0.5rem',
        borderTop: '1px solid rgba(255,255,255,0.06)',
      }}>
        {/* Sync status row */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
          {isSyncing ? (
            <>
              <span style={{
                padding: '3px 8px', borderRadius: '3px', fontSize: '0.7rem', fontWeight: 700,
                background: 'rgba(63,185,80,0.15)', color: '#3fb950',
                animation: 'pulse 2s infinite',
              }}>SYNCING</span>
              {status?.last_sync && (
                <span style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)' }}>
                  Last sync: {formatDate(status.last_sync)}
                </span>
              )}
              {status?.esi_fleet_id && (
                <span style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.35)', fontFamily: 'monospace' }}>
                  ESI: {status.esi_fleet_id}
                </span>
              )}
              <button
                onClick={() => handleSyncStop(op.id)}
                disabled={isLoading}
                style={{
                  background: 'rgba(248,81,73,0.1)', border: '1px solid rgba(248,81,73,0.3)',
                  borderRadius: '4px', color: '#f85149', padding: '2px 8px', fontSize: '0.7rem',
                  fontWeight: 600, cursor: isLoading ? 'not-allowed' : 'pointer',
                  marginLeft: 'auto',
                }}
              >
                {isLoading ? 'Stopping...' : 'Stop Sync'}
              </button>
            </>
          ) : (
            <>
              <span style={{
                padding: '3px 8px', borderRadius: '3px', fontSize: '0.7rem', fontWeight: 600,
                background: 'rgba(255,255,255,0.05)', color: 'rgba(255,255,255,0.35)',
              }}>NO SYNC</span>
              <button
                onClick={() => setShowSyncForm(prev => ({ ...prev, [op.id]: !prev[op.id] }))}
                disabled={isLoading}
                style={{
                  background: 'rgba(88,166,255,0.1)', border: '1px solid rgba(88,166,255,0.3)',
                  borderRadius: '4px', color: '#58a6ff', padding: '2px 8px', fontSize: '0.7rem',
                  fontWeight: 600, cursor: 'pointer',
                  marginLeft: 'auto',
                }}
              >
                {showForm ? 'Cancel' : 'Start Sync'}
              </button>
            </>
          )}
        </div>

        {/* Sync error */}
        {status?.error && (
          <div style={{
            marginTop: '0.35rem', fontSize: '0.7rem', color: '#f85149',
            background: 'rgba(248,81,73,0.08)', padding: '0.25rem 0.5rem',
            borderRadius: '4px', border: '1px solid rgba(248,81,73,0.15)',
          }}>
            Sync Error: {status.error}
          </div>
        )}

        {/* Sync start form */}
        {showForm && !isSyncing && (
          <div style={{
            marginTop: '0.5rem', display: 'flex', gap: '0.5rem', alignItems: 'flex-end', flexWrap: 'wrap',
          }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
              <label style={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase' }}>
                ESI Fleet ID
              </label>
              <input
                type="number"
                value={formData.esiFleetId}
                onChange={e => setSyncForms(prev => ({
                  ...prev, [op.id]: { ...formData, esiFleetId: e.target.value }
                }))}
                style={{ ...inputStyle, width: '140px' }}
                placeholder="e.g. 1234567890"
              />
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
              <label style={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase' }}>
                FC Character ID
              </label>
              <input
                type="number"
                value={formData.fcCharId}
                onChange={e => setSyncForms(prev => ({
                  ...prev, [op.id]: { ...formData, fcCharId: e.target.value }
                }))}
                style={{ ...inputStyle, width: '140px' }}
                placeholder="e.g. 93812345"
              />
            </div>
            <button
              onClick={() => handleSyncStart(op.id)}
              disabled={isLoading || !formData.esiFleetId || !formData.fcCharId}
              style={{
                background: 'rgba(63,185,80,0.15)', border: '1px solid rgba(63,185,80,0.3)',
                borderRadius: '4px', color: '#3fb950', padding: '0.4rem 0.75rem',
                fontSize: '0.75rem', fontWeight: 600,
                cursor: (isLoading || !formData.esiFleetId || !formData.fcCharId) ? 'not-allowed' : 'pointer',
              }}
            >
              {isLoading ? 'Starting...' : 'Connect'}
            </button>
          </div>
        )}
      </div>
    );
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Active Fleets */}
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
          <div style={{ fontSize: '0.9rem', fontWeight: 600 }}>Active Operations ({active.length})</div>
          <button onClick={() => setShowCreate(!showCreate)} style={{
            background: showCreate ? 'rgba(255,255,255,0.05)' : 'rgba(63,185,80,0.15)',
            border: '1px solid rgba(63,185,80,0.3)', borderRadius: '6px',
            color: '#3fb950', padding: '0.4rem 1rem', fontSize: '0.8rem', fontWeight: 600, cursor: 'pointer',
          }}>
            {showCreate ? 'Cancel' : 'New Operation'}
          </button>
        </div>

        {/* Create form */}
        {showCreate && (
          <div style={{
            background: 'var(--bg-secondary)', border: '1px solid var(--border-color)',
            borderRadius: '8px', padding: '1rem', marginBottom: '0.75rem',
            display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: '0.75rem',
          }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
              <label style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase' }}>Fleet Name</label>
              <input value={form.fleetName} onChange={e => setForm({ ...form, fleetName: e.target.value })} style={inputStyle} placeholder="e.g. Stratop - K-6K16" />
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
              <label style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase' }}>FC Name</label>
              <input value={form.fcName || ''} onChange={e => setForm({ ...form, fcName: e.target.value })} style={inputStyle} />
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
              <label style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase' }}>Notes</label>
              <input value={form.notes || ''} onChange={e => setForm({ ...form, notes: e.target.value })} style={inputStyle} />
            </div>
            <div style={{ display: 'flex', alignItems: 'flex-end' }}>
              <button onClick={handleCreate} disabled={creating || !form.fleetName.trim()} style={{
                background: 'rgba(63,185,80,0.15)', border: '1px solid rgba(63,185,80,0.3)',
                borderRadius: '6px', color: '#3fb950', padding: '0.4rem 1.25rem',
                fontSize: '0.8rem', fontWeight: 600,
                cursor: creating || !form.fleetName.trim() ? 'not-allowed' : 'pointer',
              }}>
                {creating ? 'Creating...' : 'Create'}
              </button>
            </div>
          </div>
        )}

        {/* Active fleet cards */}
        {loadingActive ? (
          <div style={{ padding: '1rem', color: 'rgba(255,255,255,0.3)', fontSize: '0.85rem' }}>Loading...</div>
        ) : active.length === 0 ? (
          <div style={{
            background: 'var(--bg-secondary)', border: '1px solid var(--border-color)',
            borderRadius: '8px', padding: '1.5rem', textAlign: 'center', color: 'rgba(255,255,255,0.3)',
            fontSize: '0.85rem',
          }}>No active operations</div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {active.map(op => (
              <div key={op.id} style={{
                background: 'var(--bg-secondary)', border: '1px solid rgba(248,81,73,0.3)',
                borderRadius: '8px', padding: '0.75rem 1rem',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: '0.9rem' }}>{op.fleetName}</div>
                    <div style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.5)', display: 'flex', gap: '1rem', marginTop: '0.25rem' }}>
                      {op.fcName && <span>FC: {op.fcName}</span>}
                      <span>Started: {formatDate(op.startTime)}</span>
                      <span>Members: {op.memberCount}</span>
                      <span>Snapshots: {op.snapshotCount}</span>
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <span style={{
                      padding: '3px 8px', borderRadius: '3px', fontSize: '0.7rem', fontWeight: 700,
                      background: 'rgba(63,185,80,0.15)', color: '#3fb950',
                    }}>ACTIVE</span>
                    <button onClick={() => handleClose(op.id)} style={{
                      background: 'rgba(248,81,73,0.1)', border: '1px solid rgba(248,81,73,0.3)',
                      borderRadius: '4px', color: '#f85149', padding: '3px 8px', fontSize: '0.75rem',
                      fontWeight: 600, cursor: 'pointer',
                    }}>Close</button>
                  </div>
                </div>
                {/* Sync Controls */}
                {renderSyncControls(op)}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Fleet History */}
      <div>
        <div style={{ fontSize: '0.9rem', fontWeight: 600, marginBottom: '0.75rem' }}>Fleet History ({history.length})</div>

        <div style={{
          background: 'var(--bg-secondary)', border: '1px solid var(--border-color)',
          borderRadius: '8px', overflow: 'hidden',
        }}>
          <div style={{
            display: 'grid', gridTemplateColumns: '1.5fr 1fr 120px 80px 80px 80px 80px',
            gap: '0.5rem', padding: '0.6rem 1rem', borderBottom: '1px solid var(--border-color)',
            fontSize: '0.7rem', fontWeight: 700, textTransform: 'uppercase', color: 'rgba(255,255,255,0.45)',
          }}>
            <span>Fleet</span><span>FC</span><span>Start</span>
            <span style={{ textAlign: 'right' }}>Duration</span>
            <span style={{ textAlign: 'right' }}>Pilots</span>
            <span style={{ textAlign: 'right' }}>Snaps</span>
            <span></span>
          </div>

          {loadingHistory ? (
            <div style={{ padding: '2rem', textAlign: 'center', color: 'rgba(255,255,255,0.3)', fontSize: '0.85rem' }}>Loading...</div>
          ) : history.length === 0 ? (
            <div style={{ padding: '2rem', textAlign: 'center', color: 'rgba(255,255,255,0.3)', fontSize: '0.85rem' }}>No fleet history</div>
          ) : (
            <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
              {history.map((op, idx) => (
                <div key={op.id}>
                  <div
                    onClick={() => handleExpand(op.id)}
                    style={{
                      display: 'grid', gridTemplateColumns: '1.5fr 1fr 120px 80px 80px 80px 80px',
                      gap: '0.5rem', padding: '0.5rem 1rem', fontSize: '0.8rem', cursor: 'pointer',
                      background: expandedId === op.id ? 'rgba(255,255,255,0.04)' : idx % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.02)',
                      borderBottom: '1px solid rgba(255,255,255,0.03)', alignItems: 'center',
                    }}
                  >
                    <span style={{ fontWeight: 600 }}>{op.fleetName}</span>
                    <span style={{ color: 'rgba(255,255,255,0.6)' }}>{op.fcName || '—'}</span>
                    <span style={{ fontFamily: 'monospace', fontSize: '0.75rem', color: 'rgba(255,255,255,0.5)' }}>
                      {formatDate(op.startTime)}
                    </span>
                    <span style={{ textAlign: 'right', fontFamily: 'monospace', color: 'rgba(255,255,255,0.6)' }}>
                      {op.durationMinutes != null ? formatDuration(op.durationMinutes) : '—'}
                    </span>
                    <span style={{ textAlign: 'right', fontFamily: 'monospace', color: 'rgba(255,255,255,0.6)' }}>
                      {op.totalParticipants ?? op.memberCount ?? 0}
                    </span>
                    <span style={{ textAlign: 'right', fontFamily: 'monospace', color: 'rgba(255,255,255,0.4)' }}>
                      {op.totalSnapshots ?? op.snapshotCount ?? 0}
                    </span>
                    <span style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.3)', textAlign: 'center' }}>
                      {expandedId === op.id ? 'Hide' : 'PAP'}
                    </span>
                  </div>

                  {/* Expanded PAP */}
                  {expandedId === op.id && (
                    <div style={{
                      padding: '0.75rem 1rem', background: 'rgba(0,0,0,0.15)',
                      borderBottom: '1px solid var(--border-color)',
                    }}>
                      {loadingPap ? (
                        <div style={{ color: 'rgba(255,255,255,0.3)', fontSize: '0.8rem' }}>Loading PAP data...</div>
                      ) : !papData ? (
                        <div style={{ color: 'rgba(255,255,255,0.3)', fontSize: '0.8rem' }}>No PAP data available</div>
                      ) : (
                        <div>
                          <div style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', marginBottom: '0.5rem' }}>
                            Participation ({papData.totalParticipants} pilots, {papData.totalSnapshots} snapshots)
                          </div>
                          <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr 80px 60px', gap: '0.3rem', fontSize: '0.78rem' }}>
                            <span style={{ fontWeight: 700, color: 'rgba(255,255,255,0.45)', fontSize: '0.7rem' }}>PILOT</span>
                            <span style={{ fontWeight: 700, color: 'rgba(255,255,255,0.45)', fontSize: '0.7rem' }}>SHIP</span>
                            <span style={{ fontWeight: 700, color: 'rgba(255,255,255,0.45)', fontSize: '0.7rem', textAlign: 'right' }}>SNAPS</span>
                            <span style={{ fontWeight: 700, color: 'rgba(255,255,255,0.45)', fontSize: '0.7rem', textAlign: 'right' }}>PAP%</span>
                          </div>
                          <div style={{ maxHeight: '200px', overflowY: 'auto' }}>
                            {papData.participants.map(p => (
                              <div key={p.characterId} style={{
                                display: 'grid', gridTemplateColumns: '1.2fr 1fr 80px 60px',
                                gap: '0.3rem', padding: '0.2rem 0', fontSize: '0.78rem',
                                borderBottom: '1px solid rgba(255,255,255,0.02)',
                              }}>
                                <span>{p.characterName || `ID ${p.characterId}`}</span>
                                <span style={{ color: 'rgba(255,255,255,0.5)' }}>{p.shipTypeName || p.shipName || '—'}</span>
                                <span style={{ textAlign: 'right', fontFamily: 'monospace' }}>{p.snapshotCount}</span>
                                <span style={{
                                  textAlign: 'right', fontFamily: 'monospace', fontWeight: 700,
                                  color: (p.participationPct ?? 0) >= 80 ? '#3fb950' : (p.participationPct ?? 0) >= 50 ? '#d29922' : '#f85149',
                                }}>
                                  {p.participationPct != null ? `${p.participationPct.toFixed(0)}%` : '—'}
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
