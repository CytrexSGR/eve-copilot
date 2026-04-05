import { useState, useEffect } from 'react';
import { buybackApi } from '../../services/api/finance';
import type { BuybackAppraisal, BuybackRequest, BuybackConfig } from '../../types/finance';
import { formatIsk } from '../../types/finance';
import { useAuth } from '../../hooks/useAuth';

const STATUS_COLORS: Record<string, string> = {
  pending_review: '#d29922',
  approved: '#3fb950',
  rejected: '#f85149',
  paid: '#00d4ff',
};

const STATUS_LABELS: Record<string, string> = {
  pending_review: 'Pending Review',
  approved: 'Approved',
  rejected: 'Rejected',
  paid: 'Paid',
};

export function BuybackTab({ corpId }: { corpId: number }) {
  const { account } = useAuth();

  const [rawText, setRawText] = useState('');
  const [configs, setConfigs] = useState<BuybackConfig[]>([]);
  const [selectedConfigId, setSelectedConfigId] = useState<number | undefined>(undefined);
  const [appraisal, setAppraisal] = useState<BuybackAppraisal | null>(null);
  const [requests, setRequests] = useState<BuybackRequest[]>([]);
  const [appraising, setAppraising] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    buybackApi.getConfigs(corpId).then(res => {
      setConfigs(res.configs);
      if (res.configs.length > 0) {
        setSelectedConfigId(res.configs[0].id);
      }
    }).catch(() => setConfigs([]));
  }, [corpId]);

  useEffect(() => {
    loadRequests();
  }, [corpId]);

  async function loadRequests() {
    try {
      const res = await buybackApi.getRequests({ corporation_id: corpId });
      setRequests(res.requests);
    } catch {
      setRequests([]);
    }
  }

  async function handleAppraise() {
    if (!rawText.trim()) return;
    setAppraising(true);
    setError(null);
    setAppraisal(null);
    try {
      const result = await buybackApi.appraise(rawText, selectedConfigId);
      setAppraisal(result);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Appraisal failed';
      setError(msg);
    } finally {
      setAppraising(false);
    }
  }

  async function handleSubmit() {
    if (!appraisal || !selectedConfigId || !account) return;
    setSubmitting(true);
    setError(null);
    try {
      await buybackApi.submit(
        rawText,
        selectedConfigId,
        account.primary_character_id,
        account.primary_character_name,
        corpId,
      );
      setAppraisal(null);
      setRawText('');
      await loadRequests();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Submit failed';
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* Appraisal Input Section */}
      <div style={cardStyle}>
        <h3 style={sectionTitle}>Buyback Appraisal</h3>

        <textarea
          value={rawText}
          onChange={e => setRawText(e.target.value)}
          placeholder="Paste items from inventory (Tab-separated: Name  Quantity)"
          style={textareaStyle}
          rows={8}
        />

        <div style={{ display: 'flex', gap: '12px', alignItems: 'center', marginTop: '10px' }}>
          <select
            value={selectedConfigId ?? ''}
            onChange={e => setSelectedConfigId(Number(e.target.value) || undefined)}
            style={selectStyle}
          >
            {configs.length === 0 && <option value="">No configs available</option>}
            {configs.map(c => (
              <option key={c.id} value={c.id}>
                {c.name} ({(c.base_discount * 100).toFixed(0)}% discount)
              </option>
            ))}
          </select>

          <button
            onClick={handleAppraise}
            disabled={appraising || !rawText.trim()}
            style={{
              ...buttonStyle,
              opacity: appraising || !rawText.trim() ? 0.5 : 1,
              cursor: appraising || !rawText.trim() ? 'not-allowed' : 'pointer',
            }}
          >
            {appraising ? 'Appraising...' : 'Appraise'}
          </button>
        </div>

        {error && (
          <div style={{ color: '#f85149', fontSize: '0.85rem', marginTop: '8px' }}>
            {error}
          </div>
        )}
      </div>

      {/* Appraisal Results */}
      {appraisal && (
        <div style={cardStyle}>
          <h3 style={sectionTitle}>Appraisal Results</h3>

          {/* Summary Bar */}
          <div style={summaryBarStyle}>
            <div style={summaryItemStyle}>
              <span style={summaryLabel}>Items</span>
              <span style={summaryValue}>{appraisal.summary.item_count}</span>
            </div>
            <div style={summaryItemStyle}>
              <span style={summaryLabel}>Jita Sell</span>
              <span style={{ ...summaryValue, fontFamily: 'monospace' }}>
                {formatIsk(appraisal.summary.total_jita_sell)}
              </span>
            </div>
            <div style={summaryItemStyle}>
              <span style={summaryLabel}>Jita Buy</span>
              <span style={{ ...summaryValue, fontFamily: 'monospace' }}>
                {formatIsk(appraisal.summary.total_jita_buy)}
              </span>
            </div>
            <div style={summaryItemStyle}>
              <span style={summaryLabel}>Volume</span>
              <span style={summaryValue}>
                {appraisal.summary.total_volume.toLocaleString(undefined, { maximumFractionDigits: 1 })} m\u00B3
              </span>
            </div>
          </div>

          {/* Buyback Offer Card */}
          <div style={offerCardStyle}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <div style={{ fontSize: '0.75rem', color: '#8b949e', marginBottom: '4px' }}>
                  Total Buyback Payout
                </div>
                <div style={{
                  fontSize: '1.6rem',
                  fontFamily: 'monospace',
                  fontWeight: 700,
                  color: '#ff8800',
                }}>
                  {formatIsk(appraisal.buyback.total_payout)}
                </div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: '0.75rem', color: '#8b949e', marginBottom: '4px' }}>
                  Discount Applied
                </div>
                <div style={{
                  fontSize: '1.1rem',
                  fontFamily: 'monospace',
                  color: '#d29922',
                }}>
                  {(appraisal.buyback.discount_applied * 100).toFixed(1)}%
                </div>
              </div>
            </div>
            <div style={{ fontSize: '0.75rem', color: '#8b949e', marginTop: '6px' }}>
              Config: {appraisal.config.name} (Base: {(appraisal.config.base_discount * 100).toFixed(0)}%
              {appraisal.config.ore_modifier !== 1 ? `, Ore: ${(appraisal.config.ore_modifier * 100).toFixed(0)}%` : ''})
            </div>
          </div>

          {/* Items Table */}
          <div style={{ overflowX: 'auto', marginTop: '12px' }}>
            <table style={tableStyle}>
              <thead>
                <tr>
                  <th style={thStyle}></th>
                  <th style={{ ...thStyle, textAlign: 'left' }}>Name</th>
                  <th style={thStyleRight}>Qty</th>
                  <th style={thStyleRight}>Jita Sell</th>
                  <th style={thStyleRight}>Jita Buy</th>
                  <th style={thStyleRight}>Buyback Price</th>
                  <th style={thStyleRight}>Buyback Total</th>
                </tr>
              </thead>
              <tbody>
                {appraisal.items.map((item, idx) => (
                  <tr key={idx} style={{ borderBottom: '1px solid var(--border-color)' }}>
                    <td style={tdStyle}>
                      <img
                        src={`https://images.evetech.net/types/${item.type_id}/icon?size=32`}
                        alt=""
                        width={32}
                        height={32}
                        style={{ borderRadius: '4px', display: 'block' }}
                        loading="lazy"
                      />
                    </td>
                    <td style={{ ...tdStyle, textAlign: 'left', fontSize: '0.85rem' }}>
                      {item.type_name}
                    </td>
                    <td style={tdStyleMono}>
                      {item.quantity.toLocaleString()}
                    </td>
                    <td style={tdStyleMono}>
                      {formatIsk(item.jita_sell)}
                    </td>
                    <td style={tdStyleMono}>
                      {formatIsk(item.jita_buy)}
                    </td>
                    <td style={tdStyleMono}>
                      {formatIsk(item.buyback_price)}
                    </td>
                    <td style={{ ...tdStyleMono, color: '#ff8800' }}>
                      {formatIsk(item.buyback_total)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Submit Button */}
          <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '12px' }}>
            <button
              onClick={handleSubmit}
              disabled={submitting || !account}
              style={{
                ...submitButtonStyle,
                opacity: submitting || !account ? 0.5 : 1,
                cursor: submitting || !account ? 'not-allowed' : 'pointer',
              }}
            >
              {submitting ? 'Submitting...' : 'Submit Buyback'}
            </button>
          </div>
        </div>
      )}

      {/* Request History */}
      <div style={cardStyle}>
        <h3 style={sectionTitle}>Request History</h3>

        {requests.length === 0 ? (
          <div style={{ color: '#8b949e', fontSize: '0.85rem', padding: '16px 0' }}>
            No buyback requests yet.
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={tableStyle}>
              <thead>
                <tr>
                  <th style={thStyle}>ID</th>
                  <th style={thStyle}>Status</th>
                  <th style={thStyleRight}>Total Payout</th>
                  <th style={thStyle}>Submitted</th>
                </tr>
              </thead>
              <tbody>
                {requests.map(req => (
                  <tr key={req.id} style={{ borderBottom: '1px solid var(--border-color)' }}>
                    <td style={{ ...tdStyle, fontFamily: 'monospace', fontSize: '0.85rem' }}>
                      #{req.id}
                    </td>
                    <td style={tdStyle}>
                      <span style={{
                        display: 'inline-block',
                        padding: '2px 8px',
                        borderRadius: '4px',
                        fontSize: '0.75rem',
                        fontWeight: 600,
                        color: '#0d1117',
                        backgroundColor: STATUS_COLORS[req.status] ?? '#8b949e',
                      }}>
                        {STATUS_LABELS[req.status] ?? req.status}
                      </span>
                    </td>
                    <td style={{ ...tdStyleMono, color: '#ff8800' }}>
                      {formatIsk(req.total_payout)}
                    </td>
                    <td style={{ ...tdStyle, fontSize: '0.85rem', color: '#8b949e' }}>
                      {new Date(req.submitted_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

/* ── Styles ──────────────────────────────────────────────────────── */

const cardStyle: React.CSSProperties = {
  background: 'var(--bg-secondary)',
  border: '1px solid var(--border-color)',
  borderRadius: '8px',
  padding: '16px',
};

const sectionTitle: React.CSSProperties = {
  margin: '0 0 12px 0',
  fontSize: '0.95rem',
  fontWeight: 600,
  color: '#e6edf3',
};

const textareaStyle: React.CSSProperties = {
  width: '100%',
  minHeight: '150px',
  fontFamily: 'monospace',
  fontSize: '0.85rem',
  background: 'var(--bg-primary)',
  color: '#e6edf3',
  border: '1px solid var(--border-color)',
  borderRadius: '6px',
  padding: '10px',
  resize: 'vertical',
  boxSizing: 'border-box',
};

const selectStyle: React.CSSProperties = {
  flex: 1,
  padding: '8px 12px',
  fontSize: '0.85rem',
  background: 'var(--bg-primary)',
  color: '#e6edf3',
  border: '1px solid var(--border-color)',
  borderRadius: '6px',
  cursor: 'pointer',
};

const buttonStyle: React.CSSProperties = {
  padding: '8px 20px',
  fontSize: '0.85rem',
  fontWeight: 600,
  color: '#0d1117',
  background: '#ff8800',
  border: 'none',
  borderRadius: '6px',
  whiteSpace: 'nowrap',
};

const submitButtonStyle: React.CSSProperties = {
  padding: '10px 24px',
  fontSize: '0.9rem',
  fontWeight: 600,
  color: '#0d1117',
  background: '#3fb950',
  border: 'none',
  borderRadius: '6px',
};

const summaryBarStyle: React.CSSProperties = {
  display: 'flex',
  gap: '16px',
  flexWrap: 'wrap',
  padding: '10px 14px',
  background: 'var(--bg-primary)',
  borderRadius: '6px',
  border: '1px solid var(--border-color)',
};

const summaryItemStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: '2px',
  flex: '1 1 120px',
};

const summaryLabel: React.CSSProperties = {
  fontSize: '0.7rem',
  color: '#8b949e',
  textTransform: 'uppercase',
  letterSpacing: '0.04em',
};

const summaryValue: React.CSSProperties = {
  fontSize: '0.95rem',
  fontWeight: 600,
  color: '#e6edf3',
};

const offerCardStyle: React.CSSProperties = {
  marginTop: '12px',
  padding: '14px 16px',
  background: 'var(--bg-primary)',
  borderRadius: '6px',
  border: '1px solid #ff880044',
};

const tableStyle: React.CSSProperties = {
  width: '100%',
  borderCollapse: 'collapse',
  fontSize: '0.85rem',
};

const thStyle: React.CSSProperties = {
  padding: '8px 10px',
  textAlign: 'left',
  fontSize: '0.75rem',
  fontWeight: 600,
  color: '#8b949e',
  textTransform: 'uppercase',
  letterSpacing: '0.04em',
  borderBottom: '1px solid var(--border-color)',
};

const thStyleRight: React.CSSProperties = {
  ...thStyle,
  textAlign: 'right',
};

const tdStyle: React.CSSProperties = {
  padding: '8px 10px',
  verticalAlign: 'middle',
};

const tdStyleMono: React.CSSProperties = {
  ...tdStyle,
  fontFamily: 'monospace',
  fontSize: '0.85rem',
  textAlign: 'right',
  color: '#e6edf3',
};
