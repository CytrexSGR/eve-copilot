import { useState, useEffect } from 'react';
import { applicationApi } from '../../services/api/hr';
import type { HrApplication } from '../../types/hr';
import { STATUS_COLORS, getRiskColor, getRiskLabel } from '../../types/hr';

type StatusFilter = 'all' | 'pending' | 'reviewing' | 'approved' | 'rejected';

const formatDate = (iso: string): string => {
  const d = new Date(iso);
  return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, '0')}-${String(d.getUTCDate()).padStart(2, '0')}`;
};

export function ApplicationsTab({ corpId }: { corpId: number }) {
  const [filter, setFilter] = useState<StatusFilter>('all');
  const [apps, setApps] = useState<HrApplication[]>([]);
  const [count, setCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [actionLoading, setActionLoading] = useState<number | null>(null);

  const loadApps = async () => {
    setLoading(true);
    try {
      const params: { corporation_id: number; status?: string; limit: number } = { corporation_id: corpId, limit: 50 };
      if (filter !== 'all') params.status = filter;
      const res = await applicationApi.getApplications(params);
      setApps(res.applications);
      setCount(res.count);
    } catch (err) {
      console.error('Failed to load applications:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadApps(); }, [corpId, filter]);

  const handleReview = async (id: number, status: 'approved' | 'rejected') => {
    setActionLoading(id);
    try {
      await applicationApi.reviewApplication(id, { recruiter_id: 0, status });
      await loadApps();
      setExpandedId(null);
    } catch (err) {
      console.error('Failed to review:', err);
    } finally {
      setActionLoading(null);
    }
  };

  const handleVet = async (id: number) => {
    setActionLoading(id);
    try {
      await applicationApi.vetApplication(id);
      await loadApps();
    } catch (err) {
      console.error('Failed to vet:', err);
    } finally {
      setActionLoading(null);
    }
  };

  const filters: StatusFilter[] = ['all', 'pending', 'reviewing', 'approved', 'rejected'];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      {/* Filter tabs */}
      <div style={{ display: 'flex', gap: '0.5rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.5rem' }}>
        {filters.map(f => (
          <button key={f} onClick={() => setFilter(f)} style={{
            background: filter === f ? 'rgba(255,255,255,0.08)' : 'transparent',
            border: filter === f ? '1px solid var(--border-color)' : '1px solid transparent',
            color: filter === f ? '#fff' : 'var(--text-secondary)',
            padding: '0.4rem 0.75rem', borderRadius: '6px', cursor: 'pointer',
            fontSize: '0.8rem', fontWeight: filter === f ? 600 : 400, textTransform: 'capitalize',
          }}>
            {f} {f === 'all' ? `(${count})` : ''}
          </button>
        ))}
      </div>

      {/* Table */}
      <div style={{
        background: 'var(--bg-secondary)', border: '1px solid var(--border-color)',
        borderRadius: '8px', overflow: 'hidden',
      }}>
        <div style={{
          display: 'grid', gridTemplateColumns: '1.2fr 90px 2fr 70px 90px 80px',
          gap: '0.5rem', padding: '0.6rem 1rem', borderBottom: '1px solid var(--border-color)',
          fontSize: '0.7rem', fontWeight: 700, textTransform: 'uppercase', color: 'rgba(255,255,255,0.45)',
        }}>
          <span>Character</span><span>Status</span><span>Motivation</span>
          <span style={{ textAlign: 'center' }}>Risk</span><span>Submitted</span><span></span>
        </div>

        {loading ? (
          <div style={{ padding: '2rem', textAlign: 'center', color: 'rgba(255,255,255,0.3)', fontSize: '0.85rem' }}>Loading...</div>
        ) : apps.length === 0 ? (
          <div style={{ padding: '2rem', textAlign: 'center', color: 'rgba(255,255,255,0.3)', fontSize: '0.85rem' }}>No applications found</div>
        ) : (
          <div style={{ maxHeight: '520px', overflowY: 'auto' }}>
            {apps.map((app, idx) => {
              const isExpanded = expandedId === app.id;
              const statusColor = STATUS_COLORS[app.status] || '#8b949e';
              return (
                <div key={app.id}>
                  <div
                    onClick={() => setExpandedId(isExpanded ? null : app.id)}
                    style={{
                      display: 'grid', gridTemplateColumns: '1.2fr 90px 2fr 70px 90px 80px',
                      gap: '0.5rem', padding: '0.5rem 1rem', fontSize: '0.8rem', cursor: 'pointer',
                      background: isExpanded ? 'rgba(255,255,255,0.04)' : idx % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.02)',
                      borderBottom: '1px solid rgba(255,255,255,0.03)', alignItems: 'center',
                    }}
                  >
                    <span style={{ fontWeight: 600 }}>{app.character_name}</span>
                    <span style={{
                      padding: '2px 6px', borderRadius: '3px', fontSize: '0.7rem', fontWeight: 600,
                      background: `${statusColor}22`, color: statusColor, textTransform: 'capitalize',
                      textAlign: 'center',
                    }}>{app.status}</span>
                    <span style={{ color: 'rgba(255,255,255,0.5)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {app.motivation}
                    </span>
                    <span style={{ textAlign: 'center' }}>
                      {app.risk_score != null ? (
                        <span style={{ fontFamily: 'monospace', fontWeight: 700, color: getRiskColor(app.risk_score) }}>
                          {app.risk_score}
                        </span>
                      ) : (
                        <span style={{ color: 'rgba(255,255,255,0.2)', fontSize: '0.75rem' }}>N/A</span>
                      )}
                    </span>
                    <span style={{ fontFamily: 'monospace', fontSize: '0.75rem', color: 'rgba(255,255,255,0.45)' }}>
                      {formatDate(app.submitted_at)}
                    </span>
                    <span style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.3)', textAlign: 'center' }}>
                      {isExpanded ? 'Collapse' : 'Expand'}
                    </span>
                  </div>

                  {/* Expanded Detail */}
                  {isExpanded && (
                    <div style={{
                      padding: '1rem', background: 'rgba(0,0,0,0.15)',
                      borderBottom: '1px solid var(--border-color)',
                    }}>
                      <div style={{ marginBottom: '0.75rem' }}>
                        <div style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', marginBottom: '0.25rem', textTransform: 'uppercase' }}>Motivation</div>
                        <div style={{
                          padding: '0.75rem', background: 'rgba(0,0,0,0.2)', borderRadius: '4px',
                          fontSize: '0.85rem', lineHeight: 1.5, whiteSpace: 'pre-wrap',
                        }}>
                          {app.motivation}
                        </div>
                      </div>

                      {/* Risk + Flags */}
                      {app.risk_score != null && (
                        <div style={{ marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                          <span style={{
                            fontFamily: 'monospace', fontSize: '1.5rem', fontWeight: 700,
                            color: getRiskColor(app.risk_score),
                          }}>
                            {app.risk_score}
                          </span>
                          <span style={{ color: 'rgba(255,255,255,0.5)' }}>{getRiskLabel(app.risk_score)}</span>
                        </div>
                      )}

                      {app.vetting_flags && (
                        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '0.75rem' }}>
                          {Object.entries(app.vetting_flags).filter(([, v]) => v).map(([key]) => (
                            <span key={key} style={{
                              padding: '3px 8px', borderRadius: '3px', fontSize: '0.7rem', fontWeight: 700,
                              background: 'rgba(248,81,73,0.15)', color: '#f85149',
                              border: '1px solid rgba(248,81,73,0.3)',
                            }}>
                              {key.replace(/_/g, ' ')}
                            </span>
                          ))}
                        </div>
                      )}

                      {/* Actions */}
                      {(app.status === 'pending' || app.status === 'reviewing') && (
                        <div style={{ display: 'flex', gap: '0.75rem', paddingTop: '0.5rem', borderTop: '1px solid var(--border-color)' }}>
                          <button onClick={() => handleVet(app.id)} disabled={actionLoading === app.id}
                            style={{
                              background: 'rgba(0,212,255,0.1)', border: '1px solid rgba(0,212,255,0.3)',
                              borderRadius: '6px', color: '#00d4ff', padding: '0.4rem 1rem',
                              fontSize: '0.8rem', fontWeight: 600, cursor: actionLoading === app.id ? 'not-allowed' : 'pointer',
                              opacity: actionLoading === app.id ? 0.5 : 1,
                            }}>
                            {actionLoading === app.id ? 'Vetting...' : 'Run Vetting'}
                          </button>
                          <button onClick={() => handleReview(app.id, 'approved')} disabled={actionLoading === app.id}
                            style={{
                              background: 'rgba(63,185,80,0.1)', border: '1px solid rgba(63,185,80,0.3)',
                              borderRadius: '6px', color: '#3fb950', padding: '0.4rem 1rem',
                              fontSize: '0.8rem', fontWeight: 600, cursor: actionLoading === app.id ? 'not-allowed' : 'pointer',
                              opacity: actionLoading === app.id ? 0.5 : 1,
                            }}>Approve</button>
                          <button onClick={() => handleReview(app.id, 'rejected')} disabled={actionLoading === app.id}
                            style={{
                              background: 'rgba(248,81,73,0.1)', border: '1px solid rgba(248,81,73,0.3)',
                              borderRadius: '6px', color: '#f85149', padding: '0.4rem 1rem',
                              fontSize: '0.8rem', fontWeight: 600, cursor: actionLoading === app.id ? 'not-allowed' : 'pointer',
                              opacity: actionLoading === app.id ? 0.5 : 1,
                            }}>Reject</button>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
