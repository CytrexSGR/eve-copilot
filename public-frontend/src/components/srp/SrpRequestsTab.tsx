import { useState, useEffect } from 'react';
import { srpApi } from '../../services/api/srp';
import type { SrpRequest, SrpReviewRequest } from '../../types/srp';
import { SRP_STATUS_COLORS, getMatchScoreColor, formatIsk } from '../../types/srp';

type StatusFilter = 'all' | 'pending' | 'approved' | 'rejected' | 'paid';

const formatDate = (iso: string): string => {
  const d = new Date(iso);
  return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, '0')}-${String(d.getUTCDate()).padStart(2, '0')}`;
};

export function SrpRequestsTab({ corpId }: { corpId: number }) {
  const [filter, setFilter] = useState<StatusFilter>('all');
  const [requests, setRequests] = useState<SrpRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [actionLoading, setActionLoading] = useState<number | null>(null);
  const [payoutText, setPayoutText] = useState<string | null>(null);

  const loadRequests = async () => {
    setLoading(true);
    try {
      const params: { status?: string; limit: number } = { limit: 100 };
      if (filter !== 'all') params.status = filter;
      const data = await srpApi.getRequests(corpId, params);
      setRequests(data);
    } catch (err) {
      console.error('Failed to load SRP requests:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadRequests(); }, [corpId, filter]);

  const handleReview = async (id: number, status: 'approved' | 'rejected') => {
    setActionLoading(id);
    try {
      const review: SrpReviewRequest = { status, reviewed_by: 0 };
      await srpApi.review(id, review);
      await loadRequests();
      setExpandedId(null);
    } catch (err) {
      console.error('Failed to review:', err);
    } finally {
      setActionLoading(null);
    }
  };

  const handleBatchPaid = async () => {
    const approvedIds = requests.filter(r => r.status === 'approved').map(r => r.id);
    if (approvedIds.length === 0) return;
    try {
      await srpApi.batchPaid(approvedIds);
      await loadRequests();
    } catch (err) {
      console.error('Failed to mark as paid:', err);
    }
  };

  const handleExportPayout = async () => {
    try {
      const text = await srpApi.getPayoutList(corpId, 'approved');
      setPayoutText(text);
    } catch (err) {
      console.error('Failed to export payout list:', err);
    }
  };

  const filters: StatusFilter[] = ['all', 'pending', 'approved', 'rejected', 'paid'];
  const approvedCount = requests.filter(r => r.status === 'approved').length;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      {/* Filter tabs + actions */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem' }}>
        <div style={{ display: 'flex', gap: '0.5rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.5rem' }}>
          {filters.map(f => (
            <button key={f} onClick={() => setFilter(f)} style={{
              background: filter === f ? 'rgba(255,255,255,0.08)' : 'transparent',
              border: filter === f ? '1px solid var(--border-color)' : '1px solid transparent',
              color: filter === f ? '#fff' : 'var(--text-secondary)',
              padding: '0.4rem 0.75rem', borderRadius: '6px', cursor: 'pointer',
              fontSize: '0.8rem', fontWeight: filter === f ? 600 : 400, textTransform: 'capitalize',
            }}>
              {f}
            </button>
          ))}
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          {approvedCount > 0 && (
            <>
              <button onClick={handleExportPayout} style={{
                background: 'rgba(0,212,255,0.1)', border: '1px solid rgba(0,212,255,0.3)',
                borderRadius: '6px', color: '#00d4ff', padding: '0.4rem 0.75rem',
                fontSize: '0.75rem', fontWeight: 600, cursor: 'pointer',
              }}>Export Payout</button>
              <button onClick={handleBatchPaid} style={{
                background: 'rgba(63,185,80,0.1)', border: '1px solid rgba(63,185,80,0.3)',
                borderRadius: '6px', color: '#3fb950', padding: '0.4rem 0.75rem',
                fontSize: '0.75rem', fontWeight: 600, cursor: 'pointer',
              }}>Mark All Paid ({approvedCount})</button>
            </>
          )}
        </div>
      </div>

      {/* Payout text */}
      {payoutText && (
        <div style={{
          background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-color)',
          borderRadius: '6px', padding: '0.75rem', position: 'relative',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
            <span style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase' }}>Payout List (TSV)</span>
            <button onClick={() => { navigator.clipboard.writeText(payoutText); }} style={{
              background: 'rgba(0,212,255,0.1)', border: '1px solid rgba(0,212,255,0.3)',
              borderRadius: '4px', color: '#00d4ff', padding: '2px 8px', fontSize: '0.7rem', cursor: 'pointer',
            }}>Copy</button>
          </div>
          <pre style={{
            margin: 0, fontSize: '0.75rem', fontFamily: 'monospace', color: 'rgba(255,255,255,0.7)',
            maxHeight: '150px', overflowY: 'auto', whiteSpace: 'pre-wrap',
          }}>{payoutText}</pre>
        </div>
      )}

      {/* Table */}
      <div style={{
        background: 'var(--bg-secondary)', border: '1px solid var(--border-color)',
        borderRadius: '8px', overflow: 'hidden',
      }}>
        <div style={{
          display: 'grid', gridTemplateColumns: '1.2fr 1fr 90px 90px 80px 90px 80px',
          gap: '0.5rem', padding: '0.6rem 1rem', borderBottom: '1px solid var(--border-color)',
          fontSize: '0.7rem', fontWeight: 700, textTransform: 'uppercase', color: 'rgba(255,255,255,0.45)',
        }}>
          <span>Character</span><span>Ship</span><span>Status</span>
          <span style={{ textAlign: 'right' }}>Payout</span>
          <span style={{ textAlign: 'center' }}>Match</span>
          <span>Submitted</span><span></span>
        </div>

        {loading ? (
          <div style={{ padding: '2rem', textAlign: 'center', color: 'rgba(255,255,255,0.3)', fontSize: '0.85rem' }}>Loading...</div>
        ) : requests.length === 0 ? (
          <div style={{ padding: '2rem', textAlign: 'center', color: 'rgba(255,255,255,0.3)', fontSize: '0.85rem' }}>No SRP requests found</div>
        ) : (
          <div style={{ maxHeight: '520px', overflowY: 'auto' }}>
            {requests.map((req, idx) => {
              const isExpanded = expandedId === req.id;
              const statusColor = SRP_STATUS_COLORS[req.status] || '#8b949e';
              return (
                <div key={req.id}>
                  <div
                    onClick={() => setExpandedId(isExpanded ? null : req.id)}
                    style={{
                      display: 'grid', gridTemplateColumns: '1.2fr 1fr 90px 90px 80px 90px 80px',
                      gap: '0.5rem', padding: '0.5rem 1rem', fontSize: '0.8rem', cursor: 'pointer',
                      background: isExpanded ? 'rgba(255,255,255,0.04)' : idx % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.02)',
                      borderBottom: '1px solid rgba(255,255,255,0.03)', alignItems: 'center',
                    }}
                  >
                    <span style={{ fontWeight: 600 }}>{req.character_name || `ID ${req.character_id}`}</span>
                    <span style={{ color: 'rgba(255,255,255,0.6)' }}>{req.ship_name || `Type ${req.ship_type_id}`}</span>
                    <span style={{
                      padding: '2px 6px', borderRadius: '3px', fontSize: '0.7rem', fontWeight: 600,
                      background: `${statusColor}22`, color: statusColor, textTransform: 'capitalize',
                      textAlign: 'center',
                    }}>{req.status}</span>
                    <span style={{ textAlign: 'right', fontFamily: 'monospace', color: '#3fb950', fontSize: '0.78rem' }}>
                      {formatIsk(req.payout_amount)}
                    </span>
                    <span style={{ textAlign: 'center' }}>
                      <span style={{
                        fontFamily: 'monospace', fontWeight: 700, fontSize: '0.78rem',
                        color: getMatchScoreColor(req.match_score),
                      }}>
                        {(req.match_score * 100).toFixed(0)}%
                      </span>
                    </span>
                    <span style={{ fontFamily: 'monospace', fontSize: '0.75rem', color: 'rgba(255,255,255,0.45)' }}>
                      {formatDate(req.submitted_at)}
                    </span>
                    <span style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.3)', textAlign: 'center' }}>
                      {isExpanded ? 'Collapse' : 'Expand'}
                    </span>
                  </div>

                  {/* Expanded detail */}
                  {isExpanded && (
                    <div style={{
                      padding: '1rem', background: 'rgba(0,0,0,0.15)',
                      borderBottom: '1px solid var(--border-color)',
                    }}>
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '1rem', marginBottom: '0.75rem' }}>
                        <div>
                          <div style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', marginBottom: '0.25rem' }}>Doctrine</div>
                          <div style={{ fontSize: '0.85rem' }}>{req.doctrine_name || 'No doctrine match'}</div>
                        </div>
                        <div>
                          <div style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', marginBottom: '0.25rem' }}>Fitting Value</div>
                          <div style={{ fontSize: '0.85rem', fontFamily: 'monospace' }}>{formatIsk(req.fitting_value)}</div>
                        </div>
                        <div>
                          <div style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', marginBottom: '0.25rem' }}>Insurance</div>
                          <div style={{ fontSize: '0.85rem', fontFamily: 'monospace' }}>{formatIsk(req.insurance_payout)}</div>
                        </div>
                      </div>

                      {/* Match result */}
                      {req.match_result && (
                        <div style={{ marginBottom: '0.75rem' }}>
                          <div style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', marginBottom: '0.25rem' }}>Match Details</div>
                          <div style={{ display: 'flex', gap: '1rem', fontSize: '0.8rem' }}>
                            <span>Score: <span style={{ fontWeight: 700, color: getMatchScoreColor(req.match_result.match_score) }}>
                              {(req.match_result.match_score * 100).toFixed(0)}%
                            </span></span>
                            {req.match_result.missing_items.length > 0 && (
                              <span style={{ color: '#d29922' }}>Missing: {req.match_result.missing_items.length}</span>
                            )}
                            {req.match_result.extra_items.length > 0 && (
                              <span style={{ color: 'rgba(255,255,255,0.5)' }}>Extra: {req.match_result.extra_items.length}</span>
                            )}
                            {req.match_result.review_required && (
                              <span style={{ color: '#f85149', fontWeight: 600 }}>Review Required</span>
                            )}
                          </div>
                        </div>
                      )}

                      {/* Review note */}
                      {req.review_note && (
                        <div style={{ marginBottom: '0.75rem' }}>
                          <div style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', marginBottom: '0.25rem' }}>Review Note</div>
                          <div style={{ fontSize: '0.85rem', color: 'rgba(255,255,255,0.7)', fontStyle: 'italic' }}>{req.review_note}</div>
                        </div>
                      )}

                      {/* Actions */}
                      {req.status === 'pending' && (
                        <div style={{ display: 'flex', gap: '0.75rem', paddingTop: '0.5rem', borderTop: '1px solid var(--border-color)' }}>
                          <button onClick={() => handleReview(req.id, 'approved')} disabled={actionLoading === req.id}
                            style={{
                              background: 'rgba(63,185,80,0.1)', border: '1px solid rgba(63,185,80,0.3)',
                              borderRadius: '6px', color: '#3fb950', padding: '0.4rem 1rem',
                              fontSize: '0.8rem', fontWeight: 600, cursor: actionLoading === req.id ? 'not-allowed' : 'pointer',
                              opacity: actionLoading === req.id ? 0.5 : 1,
                            }}>Approve</button>
                          <button onClick={() => handleReview(req.id, 'rejected')} disabled={actionLoading === req.id}
                            style={{
                              background: 'rgba(248,81,73,0.1)', border: '1px solid rgba(248,81,73,0.3)',
                              borderRadius: '6px', color: '#f85149', padding: '0.4rem 1rem',
                              fontSize: '0.8rem', fontWeight: 600, cursor: actionLoading === req.id ? 'not-allowed' : 'pointer',
                              opacity: actionLoading === req.id ? 0.5 : 1,
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
