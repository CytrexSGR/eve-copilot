import { useState, useEffect } from 'react';
import { miningApi, invoiceApi } from '../../services/api/finance';
import type { MiningTaxSummary, MiningConfig, TaxInvoice } from '../../types/finance';
import { formatIsk } from '../../types/finance';

const STATUS_COLORS: Record<string, string> = {
  pending: '#d29922', partial: '#ff8800', paid: '#3fb950', overdue: '#f85149',
};
const DAYS_OPTIONS = [7, 14, 30, 60, 90];
const PRICING_MODES = ['jita_buy', 'jita_sell', 'jita_split'];
const STATUS_FILTERS = ['all', 'pending', 'partial', 'paid', 'overdue'];

const card: React.CSSProperties = {
  background: 'var(--bg-secondary)', border: '1px solid var(--border-color)',
  borderRadius: 8, padding: 16, marginBottom: 16,
};
const tbl: React.CSSProperties = { width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' };
const th: React.CSSProperties = {
  textAlign: 'left', padding: '8px 10px', borderBottom: '1px solid var(--border-color)',
  color: 'var(--text-secondary)', fontWeight: 600, fontSize: '0.8rem',
  textTransform: 'uppercase', letterSpacing: '0.5px',
};
const td: React.CSSProperties = { padding: '8px 10px', borderBottom: '1px solid var(--border-color)' };
const mono: React.CSSProperties = { fontFamily: 'monospace', whiteSpace: 'nowrap' };
const btn: React.CSSProperties = {
  padding: '6px 14px', borderRadius: 6, border: '1px solid var(--border-color)',
  background: 'var(--bg-secondary)', color: 'var(--text-primary)', cursor: 'pointer',
  fontSize: '0.82rem', fontWeight: 500,
};
const btnG: React.CSSProperties = { ...btn, background: '#238636', borderColor: '#238636', color: '#fff' };
const inp: React.CSSProperties = {
  padding: '5px 8px', borderRadius: 4, border: '1px solid var(--border-color)',
  background: 'var(--bg-primary)', color: 'var(--text-primary)', fontSize: '0.85rem', width: 90,
};

const pill = (active: boolean): React.CSSProperties => ({
  ...btn, padding: '4px 10px', fontSize: '0.78rem',
  background: active ? 'var(--text-accent, #58a6ff)' : 'var(--bg-secondary)',
  color: active ? '#fff' : 'var(--text-primary)',
  borderColor: active ? 'var(--text-accent, #58a6ff)' : 'var(--border-color)',
});

export function MiningTaxTab({ corpId }: { corpId: number }) {
  const [config, setConfig] = useState<MiningConfig | null>(null);
  const [configOpen, setConfigOpen] = useState(false);
  const [editing, setEditing] = useState(false);
  const [editConfig, setEditConfig] = useState<Partial<MiningConfig>>({});
  const [configSaving, setConfigSaving] = useState(false);

  const [days, setDays] = useState(30);
  const [summary, setSummary] = useState<MiningTaxSummary[]>([]);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [expandedRow, setExpandedRow] = useState<number | null>(null);

  const [invoices, setInvoices] = useState<TaxInvoice[]>([]);
  const [invoicesLoading, setInvoicesLoading] = useState(false);
  const [statusFilter, setStatusFilter] = useState('all');
  const [showGenerate, setShowGenerate] = useState(false);
  const [genStart, setGenStart] = useState('');
  const [genEnd, setGenEnd] = useState('');
  const [genRate, setGenRate] = useState(10);
  const [generating, setGenerating] = useState(false);
  const [matching, setMatching] = useState(false);

  useEffect(() => {
    miningApi.getConfig(corpId).then(setConfig).catch(() => setConfig(null));
  }, [corpId]);

  useEffect(() => {
    setSummaryLoading(true);
    miningApi.getTaxSummary(corpId, days)
      .then((d) => setSummary([...d].sort((a, b) => b.total_tax - a.total_tax)))
      .catch(() => setSummary([]))
      .finally(() => setSummaryLoading(false));
  }, [corpId, days]);

  useEffect(() => {
    setInvoicesLoading(true);
    invoiceApi.getInvoices({ corporation_id: corpId })
      .then(setInvoices).catch(() => setInvoices([]))
      .finally(() => setInvoicesLoading(false));
  }, [corpId]);

  const startEditing = () => {
    if (config) setEditConfig({ tax_rate: config.tax_rate, reprocessing_yield: config.reprocessing_yield, pricing_mode: config.pricing_mode });
    setEditing(true);
  };

  const saveConfig = async () => {
    setConfigSaving(true);
    try { const u = await miningApi.updateConfig(corpId, editConfig); setConfig(u); setEditing(false); }
    catch { /* keep editing */ }
    finally { setConfigSaving(false); }
  };

  const handleGenerate = async () => {
    if (!genStart || !genEnd) return;
    setGenerating(true);
    try {
      await invoiceApi.generate(corpId, genStart, genEnd, genRate);
      setInvoices(await invoiceApi.getInvoices({ corporation_id: corpId }));
      setShowGenerate(false);
    } catch { /* silent */ }
    finally { setGenerating(false); }
  };

  const handleMatchPayments = async () => {
    setMatching(true);
    try {
      await invoiceApi.matchPayments(corpId);
      setInvoices(await invoiceApi.getInvoices({ corporation_id: corpId }));
    } catch { /* silent */ }
    finally { setMatching(false); }
  };

  const filtered = statusFilter === 'all' ? invoices : invoices.filter((i) => i.status === statusFilter);
  const totalMined = summary.reduce((s, r) => s + r.total_isk_value, 0);
  const totalTax = summary.reduce((s, r) => s + r.total_tax, 0);

  return (
    <div>
      {/* ==================== SECTION 1: TAX CONFIGURATION ==================== */}
      <div style={card}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', cursor: 'pointer' }}
          onClick={() => setConfigOpen(!configOpen)}>
          <h3 style={{ margin: 0, fontSize: '0.95rem' }}>
            {configOpen ? '\u25BC' : '\u25B6'} Tax Configuration
          </h3>
          {config && !configOpen && (
            <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              Rate: {config.tax_rate}% &middot; Yield: {config.reprocessing_yield}% &middot; {config.pricing_mode}
            </span>
          )}
        </div>
        {configOpen && config && (
          <div style={{ marginTop: 14 }}>
            {!editing ? (
              <div style={{ display: 'flex', gap: 24, alignItems: 'center', flexWrap: 'wrap' }}>
                <div>
                  <span style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>Tax Rate</span>
                  <div style={{ fontFamily: 'monospace', fontSize: '0.95rem' }}>{config.tax_rate}%</div>
                </div>
                <div>
                  <span style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>Reprocessing Yield</span>
                  <div style={{ fontFamily: 'monospace', fontSize: '0.95rem' }}>{config.reprocessing_yield}%</div>
                </div>
                <div>
                  <span style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>Pricing Mode</span>
                  <div style={{ fontSize: '0.95rem' }}>{config.pricing_mode}</div>
                </div>
                <button style={btn} onClick={(e) => { e.stopPropagation(); startEditing(); }}>Edit</button>
              </div>
            ) : (
              <div style={{ display: 'flex', gap: 16, alignItems: 'flex-end', flexWrap: 'wrap' }}>
                <label style={{ fontSize: '0.8rem' }}>
                  Tax Rate (%)<br />
                  <input type="number" min={0} max={100} step={0.5} value={editConfig.tax_rate ?? 0}
                    onChange={(e) => setEditConfig({ ...editConfig, tax_rate: Number(e.target.value) })} style={inp} />
                </label>
                <label style={{ fontSize: '0.8rem' }}>
                  Reprocessing Yield (%)<br />
                  <input type="number" min={0} max={100} step={0.5} value={editConfig.reprocessing_yield ?? 0}
                    onChange={(e) => setEditConfig({ ...editConfig, reprocessing_yield: Number(e.target.value) })} style={inp} />
                </label>
                <label style={{ fontSize: '0.8rem' }}>
                  Pricing Mode<br />
                  <select value={editConfig.pricing_mode ?? 'jita_sell'}
                    onChange={(e) => setEditConfig({ ...editConfig, pricing_mode: e.target.value })}
                    style={{ ...inp, width: 130 }}>
                    {PRICING_MODES.map((m) => <option key={m} value={m}>{m}</option>)}
                  </select>
                </label>
                <div style={{ display: 'flex', gap: 8 }}>
                  <button style={btnG} onClick={saveConfig} disabled={configSaving}>
                    {configSaving ? 'Saving...' : 'Save'}
                  </button>
                  <button style={btn} onClick={() => setEditing(false)}>Cancel</button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* ==================== SECTION 2: TAX SUMMARY ==================== */}
      <div style={card}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
          <h3 style={{ margin: 0, fontSize: '0.95rem' }}>Tax Summary per Member</h3>
          <div style={{ display: 'flex', gap: 4 }}>
            {DAYS_OPTIONS.map((d) => (
              <button key={d} onClick={() => setDays(d)} style={pill(d === days)}>{d}d</button>
            ))}
          </div>
        </div>
        {summaryLoading ? (
          <div style={{ textAlign: 'center', padding: 24, color: 'var(--text-secondary)' }}>Loading...</div>
        ) : summary.length === 0 ? (
          <div style={{ textAlign: 'center', padding: 24, color: 'var(--text-secondary)' }}>No mining data for the selected period</div>
        ) : (
          <table style={tbl}>
            <thead>
              <tr>
                <th style={th}>Character Name</th>
                <th style={{ ...th, textAlign: 'right' }}>Total Mined (ISK)</th>
                <th style={{ ...th, textAlign: 'right' }}>Tax Owed (ISK)</th>
                <th style={th}>Ore Types</th>
              </tr>
            </thead>
            <tbody>
              {summary.flatMap((row) => {
                const expanded = expandedRow === row.character_id;
                const rows = [
                  <tr key={row.character_id}
                    onClick={() => setExpandedRow(expanded ? null : row.character_id)}
                    style={{ cursor: 'pointer' }}
                    onMouseEnter={(e) => { (e.currentTarget as HTMLTableRowElement).style.background = 'rgba(255,255,255,0.03)'; }}
                    onMouseLeave={(e) => { (e.currentTarget as HTMLTableRowElement).style.background = 'transparent'; }}>
                    <td style={td}>
                      <span style={{ marginRight: 6, fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
                        {expanded ? '\u25BC' : '\u25B6'}
                      </span>
                      {row.character_name}
                    </td>
                    <td style={{ ...td, textAlign: 'right', ...mono }}>{formatIsk(row.total_isk_value)}</td>
                    <td style={{ ...td, textAlign: 'right', ...mono, color: '#d29922' }}>{formatIsk(row.total_tax)}</td>
                    <td style={{ ...td, fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                      {row.ore_breakdown.length} type{row.ore_breakdown.length !== 1 ? 's' : ''}
                    </td>
                  </tr>,
                ];
                if (expanded) {
                  rows.push(
                    <tr key={`${row.character_id}-detail`}>
                      <td colSpan={4} style={{ padding: '4px 10px 12px 32px', borderBottom: '1px solid var(--border-color)' }}>
                        <table style={{ ...tbl, fontSize: '0.8rem' }}>
                          <thead>
                            <tr>
                              <th style={{ ...th, padding: '4px 8px' }}>Ore</th>
                              <th style={{ ...th, padding: '4px 8px', textAlign: 'right' }}>Quantity</th>
                              <th style={{ ...th, padding: '4px 8px', textAlign: 'right' }}>ISK Value</th>
                            </tr>
                          </thead>
                          <tbody>
                            {row.ore_breakdown.map((ore) => (
                              <tr key={ore.ore}>
                                <td style={{ ...td, padding: '4px 8px' }}>{ore.ore}</td>
                                <td style={{ ...td, padding: '4px 8px', textAlign: 'right', ...mono }}>{ore.quantity.toLocaleString()}</td>
                                <td style={{ ...td, padding: '4px 8px', textAlign: 'right', ...mono }}>{formatIsk(ore.isk_value)}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </td>
                    </tr>
                  );
                }
                return rows;
              })}
              <tr style={{ fontWeight: 600 }}>
                <td style={{ ...td, borderBottom: 'none' }}>Total ({summary.length} member{summary.length !== 1 ? 's' : ''})</td>
                <td style={{ ...td, textAlign: 'right', borderBottom: 'none', ...mono }}>{formatIsk(totalMined)}</td>
                <td style={{ ...td, textAlign: 'right', borderBottom: 'none', ...mono, color: '#d29922' }}>{formatIsk(totalTax)}</td>
                <td style={{ ...td, borderBottom: 'none' }} />
              </tr>
            </tbody>
          </table>
        )}
      </div>

      {/* ==================== SECTION 3: INVOICES ==================== */}
      <div style={card}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12, flexWrap: 'wrap', gap: 8 }}>
          <h3 style={{ margin: 0, fontSize: '0.95rem' }}>Invoices</h3>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {STATUS_FILTERS.map((s) => (
              <button key={s} onClick={() => setStatusFilter(s)}
                style={{ ...pill(s === statusFilter), textTransform: 'capitalize' }}>{s}</button>
            ))}
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
          <button style={btnG} onClick={() => setShowGenerate(!showGenerate)}>
            {showGenerate ? 'Cancel' : 'Generate Invoices'}
          </button>
          <button style={btn} onClick={handleMatchPayments} disabled={matching}>
            {matching ? 'Matching...' : 'Match Payments'}
          </button>
        </div>
        {showGenerate && (
          <div style={{ display: 'flex', gap: 12, alignItems: 'flex-end', flexWrap: 'wrap',
            padding: 12, marginBottom: 12, borderRadius: 6,
            background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-color)' }}>
            <label style={{ fontSize: '0.8rem' }}>
              Period Start<br />
              <input type="date" value={genStart} onChange={(e) => setGenStart(e.target.value)} style={{ ...inp, width: 140 }} />
            </label>
            <label style={{ fontSize: '0.8rem' }}>
              Period End<br />
              <input type="date" value={genEnd} onChange={(e) => setGenEnd(e.target.value)} style={{ ...inp, width: 140 }} />
            </label>
            <label style={{ fontSize: '0.8rem' }}>
              Tax Rate (%)<br />
              <input type="number" min={0} max={100} step={0.5} value={genRate}
                onChange={(e) => setGenRate(Number(e.target.value))} style={inp} />
            </label>
            <button style={btnG} onClick={handleGenerate} disabled={generating || !genStart || !genEnd}>
              {generating ? 'Generating...' : 'Generate'}
            </button>
          </div>
        )}
        {invoicesLoading ? (
          <div style={{ textAlign: 'center', padding: 24, color: 'var(--text-secondary)' }}>Loading...</div>
        ) : filtered.length === 0 ? (
          <div style={{ textAlign: 'center', padding: 24, color: 'var(--text-secondary)' }}>
            No invoices{statusFilter !== 'all' ? ` with status "${statusFilter}"` : ''}
          </div>
        ) : (
          <table style={tbl}>
            <thead>
              <tr>
                <th style={th}>Character</th>
                <th style={th}>Period</th>
                <th style={{ ...th, textAlign: 'right' }}>Amount Due</th>
                <th style={{ ...th, textAlign: 'right' }}>Amount Paid</th>
                <th style={{ ...th, textAlign: 'right' }}>Remaining</th>
                <th style={{ ...th, textAlign: 'center' }}>Status</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((inv) => (
                <tr key={inv.id}>
                  <td style={td}>{inv.character_id}</td>
                  <td style={{ ...td, fontSize: '0.8rem', whiteSpace: 'nowrap' }}>
                    {inv.period_start.slice(0, 10)} &ndash; {inv.period_end.slice(0, 10)}
                  </td>
                  <td style={{ ...td, textAlign: 'right', ...mono }}>{formatIsk(inv.amount_due)}</td>
                  <td style={{ ...td, textAlign: 'right', ...mono, color: '#3fb950' }}>{formatIsk(inv.amount_paid)}</td>
                  <td style={{ ...td, textAlign: 'right', ...mono, color: inv.remaining_balance > 0 ? '#f85149' : '#3fb950' }}>
                    {formatIsk(inv.remaining_balance)}
                  </td>
                  <td style={{ ...td, textAlign: 'center' }}>
                    <span style={{
                      display: 'inline-block', padding: '2px 8px', borderRadius: 10,
                      fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase',
                      letterSpacing: '0.3px', color: '#fff',
                      background: STATUS_COLORS[inv.status] ?? '#8b949e',
                    }}>{inv.status}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
