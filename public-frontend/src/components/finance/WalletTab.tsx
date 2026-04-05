import { useState, useEffect } from 'react';
import { walletApi } from '../../services/api/finance';
import type { WalletJournalEntry, WalletBalance, WalletDivision } from '../../types/finance';
import { formatIsk } from '../../types/finance';

const DEFAULT_LIMIT = 50;

export function WalletTab({ corpId }: { corpId: number }) {
  const [divisions, setDivisions] = useState<WalletDivision[]>([]);
  const [divisionId, setDivisionId] = useState<number>(1);
  const [balance, setBalance] = useState<WalletBalance | null>(null);
  const [entries, setEntries] = useState<WalletJournalEntry[]>([]);
  const [refTypeFilter, setRefTypeFilter] = useState('');
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [loadingBalance, setLoadingBalance] = useState(true);
  const [loadingJournal, setLoadingJournal] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);

  // Fetch divisions on mount
  useEffect(() => {
    let cancelled = false;
    walletApi.getDivisions(corpId)
      .then(data => {
        if (!cancelled) setDivisions(data);
      })
      .catch(err => console.error('Failed to fetch wallet divisions:', err));
    return () => { cancelled = true; };
  }, [corpId]);

  // Fetch balance when division changes
  useEffect(() => {
    let cancelled = false;
    setLoadingBalance(true);
    walletApi.getBalance(corpId, divisionId)
      .then(data => {
        if (!cancelled) setBalance(data);
      })
      .catch(err => console.error('Failed to fetch wallet balance:', err))
      .finally(() => { if (!cancelled) setLoadingBalance(false); });
    return () => { cancelled = true; };
  }, [corpId, divisionId]);

  // Fetch journal when division changes (reset)
  useEffect(() => {
    let cancelled = false;
    setLoadingJournal(true);
    setEntries([]);
    setOffset(0);
    setHasMore(true);
    walletApi.getJournal(corpId, { division_id: divisionId, limit: DEFAULT_LIMIT, offset: 0 })
      .then(data => {
        if (!cancelled) {
          const sorted = data.sort((a, b) =>
            new Date(b.date).getTime() - new Date(a.date).getTime()
          );
          setEntries(sorted);
          setHasMore(data.length >= DEFAULT_LIMIT);
          setOffset(DEFAULT_LIMIT);
        }
      })
      .catch(err => console.error('Failed to fetch wallet journal:', err))
      .finally(() => { if (!cancelled) setLoadingJournal(false); });
    return () => { cancelled = true; };
  }, [corpId, divisionId]);

  const handleLoadMore = async () => {
    setLoadingMore(true);
    try {
      const data = await walletApi.getJournal(corpId, {
        division_id: divisionId,
        limit: DEFAULT_LIMIT,
        offset,
      });
      const sorted = data.sort((a, b) =>
        new Date(b.date).getTime() - new Date(a.date).getTime()
      );
      setEntries(prev => [...prev, ...sorted]);
      setHasMore(data.length >= DEFAULT_LIMIT);
      setOffset(prev => prev + DEFAULT_LIMIT);
    } catch (err) {
      console.error('Failed to load more journal entries:', err);
    } finally {
      setLoadingMore(false);
    }
  };

  const filteredEntries = refTypeFilter
    ? entries.filter(e =>
        (e.ref_type_label || e.ref_type || '')
          .toLowerCase()
          .includes(refTypeFilter.toLowerCase())
      )
    : entries;

  const formatDate = (iso: string): string => {
    const d = new Date(iso);
    const yyyy = d.getUTCFullYear();
    const mm = String(d.getUTCMonth() + 1).padStart(2, '0');
    const dd = String(d.getUTCDate()).padStart(2, '0');
    const hh = String(d.getUTCHours()).padStart(2, '0');
    const min = String(d.getUTCMinutes()).padStart(2, '0');
    return `${yyyy}-${mm}-${dd} ${hh}:${min}`;
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      {/* Balance Card */}
      <div style={{
        background: 'var(--bg-secondary)',
        border: '1px solid var(--border-color)',
        borderRadius: '8px',
        padding: '1.25rem 1.5rem',
      }}>
        <div style={{
          fontSize: '0.7rem',
          textTransform: 'uppercase',
          letterSpacing: '0.05em',
          color: 'rgba(255,255,255,0.4)',
          marginBottom: '0.5rem',
        }}>
          Corporation Wallet Balance
        </div>
        {loadingBalance ? (
          <div style={{
            fontSize: '1.8rem',
            fontFamily: 'monospace',
            color: 'rgba(255,255,255,0.2)',
          }}>
            Loading...
          </div>
        ) : balance ? (
          <>
            <div style={{
              fontSize: '2rem',
              fontWeight: 800,
              fontFamily: 'monospace',
              color: '#3fb950',
              lineHeight: 1.2,
            }}>
              {formatIsk(balance.balance)} ISK
            </div>
            {balance.as_of && (
              <div style={{
                fontSize: '0.7rem',
                color: 'rgba(255,255,255,0.3)',
                marginTop: '0.35rem',
              }}>
                as of {formatDate(balance.as_of)}
              </div>
            )}
          </>
        ) : (
          <div style={{
            fontSize: '1rem',
            color: 'rgba(255,255,255,0.3)',
          }}>
            No balance data available
          </div>
        )}
      </div>

      {/* Filter Bar */}
      <div style={{
        background: 'var(--bg-secondary)',
        border: '1px solid var(--border-color)',
        borderRadius: '8px',
        padding: '0.75rem 1rem',
        display: 'flex',
        alignItems: 'center',
        gap: '1rem',
        flexWrap: 'wrap',
      }}>
        {/* Division Dropdown */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <label style={{
            fontSize: '0.75rem',
            color: 'rgba(255,255,255,0.5)',
            whiteSpace: 'nowrap',
          }}>
            Division
          </label>
          <select
            value={divisionId}
            onChange={e => setDivisionId(Number(e.target.value))}
            style={{
              background: 'rgba(0,0,0,0.3)',
              border: '1px solid var(--border-color)',
              borderRadius: '4px',
              color: '#fff',
              padding: '0.35rem 0.5rem',
              fontSize: '0.8rem',
              outline: 'none',
              cursor: 'pointer',
            }}
          >
            {divisions.length > 0 ? (
              divisions.map(div => (
                <option key={div.division_id} value={div.division_id}>
                  {div.name || `Division ${div.division_id}`}
                </option>
              ))
            ) : (
              <option value={1}>Division 1</option>
            )}
          </select>
        </div>

        {/* Ref Type Filter */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flex: 1, minWidth: '180px' }}>
          <label style={{
            fontSize: '0.75rem',
            color: 'rgba(255,255,255,0.5)',
            whiteSpace: 'nowrap',
          }}>
            Type
          </label>
          <input
            type="text"
            value={refTypeFilter}
            onChange={e => setRefTypeFilter(e.target.value)}
            placeholder="Filter by ref type..."
            style={{
              flex: 1,
              background: 'rgba(0,0,0,0.3)',
              border: '1px solid var(--border-color)',
              borderRadius: '4px',
              color: '#fff',
              padding: '0.35rem 0.5rem',
              fontSize: '0.8rem',
              outline: 'none',
            }}
          />
        </div>

        {/* Entry Count */}
        <div style={{
          fontSize: '0.7rem',
          color: 'rgba(255,255,255,0.35)',
          whiteSpace: 'nowrap',
        }}>
          {filteredEntries.length} entries
        </div>
      </div>

      {/* Journal Table */}
      <div style={{
        background: 'var(--bg-secondary)',
        border: '1px solid var(--border-color)',
        borderRadius: '8px',
        overflow: 'hidden',
      }}>
        {/* Table Header */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: '140px 1fr 140px 140px 1.2fr',
          gap: '0.5rem',
          padding: '0.6rem 1rem',
          borderBottom: '1px solid var(--border-color)',
          fontSize: '0.7rem',
          fontWeight: 700,
          textTransform: 'uppercase',
          letterSpacing: '0.04em',
          color: 'rgba(255,255,255,0.45)',
        }}>
          <span>Date</span>
          <span>Type</span>
          <span style={{ textAlign: 'right' }}>Amount</span>
          <span style={{ textAlign: 'right' }}>Balance</span>
          <span>Reason</span>
        </div>

        {/* Table Body */}
        {loadingJournal ? (
          <div style={{
            padding: '2rem',
            textAlign: 'center',
            color: 'rgba(255,255,255,0.3)',
            fontSize: '0.85rem',
          }}>
            Loading journal entries...
          </div>
        ) : filteredEntries.length === 0 ? (
          <div style={{
            padding: '2rem',
            textAlign: 'center',
            color: 'rgba(255,255,255,0.3)',
            fontSize: '0.85rem',
          }}>
            {refTypeFilter
              ? 'No entries match the current filter'
              : 'No journal entries found'}
          </div>
        ) : (
          <div style={{ maxHeight: '520px', overflowY: 'auto' }}>
            {filteredEntries.map((entry, idx) => {
              const isPositive = entry.amount >= 0;
              const rowBg = idx % 2 === 0
                ? 'transparent'
                : 'rgba(255,255,255,0.02)';

              return (
                <div
                  key={entry.transaction_id ?? `${entry.date}-${idx}`}
                  style={{
                    display: 'grid',
                    gridTemplateColumns: '140px 1fr 140px 140px 1.2fr',
                    gap: '0.5rem',
                    padding: '0.5rem 1rem',
                    fontSize: '0.85rem',
                    background: rowBg,
                    borderBottom: '1px solid rgba(255,255,255,0.03)',
                    alignItems: 'center',
                  }}
                >
                  {/* Date */}
                  <span style={{
                    fontFamily: 'monospace',
                    fontSize: '0.78rem',
                    color: 'rgba(255,255,255,0.55)',
                    whiteSpace: 'nowrap',
                  }}>
                    {formatDate(entry.date)}
                  </span>

                  {/* Type */}
                  <span style={{
                    fontSize: '0.8rem',
                    color: 'rgba(255,255,255,0.7)',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                  }}>
                    {entry.ref_type_label || entry.ref_type || '—'}
                  </span>

                  {/* Amount */}
                  <span style={{
                    fontFamily: 'monospace',
                    fontWeight: 700,
                    fontSize: '0.85rem',
                    textAlign: 'right',
                    color: isPositive ? '#3fb950' : '#f85149',
                    whiteSpace: 'nowrap',
                  }}>
                    {isPositive ? '+' : ''}{formatIsk(entry.amount)}
                  </span>

                  {/* Balance */}
                  <span style={{
                    fontFamily: 'monospace',
                    fontSize: '0.8rem',
                    textAlign: 'right',
                    color: 'rgba(255,255,255,0.6)',
                    whiteSpace: 'nowrap',
                  }}>
                    {entry.balance != null ? formatIsk(entry.balance) : '—'}
                  </span>

                  {/* Reason */}
                  <span style={{
                    fontSize: '0.78rem',
                    color: 'rgba(255,255,255,0.45)',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                  }}
                    title={entry.reason || undefined}
                  >
                    {entry.reason || '—'}
                  </span>
                </div>
              );
            })}
          </div>
        )}

        {/* Load More */}
        {!loadingJournal && hasMore && filteredEntries.length > 0 && (
          <div style={{
            padding: '0.75rem 1rem',
            borderTop: '1px solid var(--border-color)',
            display: 'flex',
            justifyContent: 'center',
          }}>
            <button
              onClick={handleLoadMore}
              disabled={loadingMore}
              style={{
                background: loadingMore ? 'rgba(255,255,255,0.05)' : 'rgba(63,185,80,0.12)',
                border: '1px solid rgba(63,185,80,0.3)',
                borderRadius: '6px',
                color: loadingMore ? 'rgba(255,255,255,0.3)' : '#3fb950',
                padding: '0.45rem 1.5rem',
                fontSize: '0.8rem',
                fontWeight: 600,
                cursor: loadingMore ? 'not-allowed' : 'pointer',
                transition: 'background 0.15s',
              }}
            >
              {loadingMore ? 'Loading...' : 'Load More'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
