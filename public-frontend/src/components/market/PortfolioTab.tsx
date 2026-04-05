import { useState, useEffect } from 'react';
import { useAuth } from '../../hooks/useAuth';
import { ordersApi, tradingApi, portfolioApi } from '../../services/api/market';
import type { AggregatedOrdersResponse, TradingPnLReport, PortfolioSnapshot } from '../../types/market';
import { formatISK, formatISKCompact } from '../../utils/format';

import { fontSize, color, spacing } from '../../styles/theme';

type SubTab = 'orders' | 'pnl' | 'snapshot';

const SUB_TAB_CONFIG: { id: SubTab; label: string; color: string }[] = [
  { id: 'orders', label: 'Orders', color: color.accentCyan },
  { id: 'pnl', label: 'P&L', color: color.killGreen },
  { id: 'snapshot', label: 'Portfolio', color: color.warningYellow },
];

export function PortfolioTab() {
  const { account, isLoggedIn, login } = useAuth();
  const [subTab, setSubTab] = useState<SubTab>('orders');

  // Orders state
  const [ordersData, setOrdersData] = useState<AggregatedOrdersResponse | null>(null);
  const [ordersLoading, setOrdersLoading] = useState(false);
  const [orderFilter, setOrderFilter] = useState<'all' | 'sell' | 'buy'>('all');

  // P&L state
  const [pnlData, setPnlData] = useState<TradingPnLReport | null>(null);
  const [pnlLoading, setPnlLoading] = useState(false);
  const [pnlDays, setPnlDays] = useState(30);

  // Portfolio state
  const [snapshots, setSnapshots] = useState<PortfolioSnapshot[]>([]);
  const [snapshotLoading, setSnapshotLoading] = useState(false);

  const primaryCharId = account?.primary_character_id;

  // Load orders
  useEffect(() => {
    if (subTab !== 'orders' || !primaryCharId) return;
    setOrdersLoading(true);
    ordersApi.getAggregated(undefined, orderFilter === 'all' ? undefined : orderFilter)
      .then(setOrdersData)
      .catch(() => setOrdersData(null))
      .finally(() => setOrdersLoading(false));
  }, [subTab, primaryCharId, orderFilter]);

  // Load P&L
  useEffect(() => {
    if (subTab !== 'pnl' || !primaryCharId) return;
    setPnlLoading(true);
    tradingApi.getPnL(primaryCharId, pnlDays)
      .then(setPnlData)
      .catch(() => setPnlData(null))
      .finally(() => setPnlLoading(false));
  }, [subTab, primaryCharId, pnlDays]);

  // Load snapshots
  useEffect(() => {
    if (subTab !== 'snapshot' || !primaryCharId) return;
    setSnapshotLoading(true);
    portfolioApi.getSummaryAll()
      .then(data => setSnapshots(data.snapshots || []))
      .catch(() => setSnapshots([]))
      .finally(() => setSnapshotLoading(false));
  }, [subTab, primaryCharId]);

  if (!isLoggedIn) {
    return (
      <div style={{ textAlign: 'center', padding: '3rem 1rem' }}>
        <p style={{ color: 'rgba(255,255,255,0.4)', marginBottom: '1.25rem', fontSize: fontSize.base, letterSpacing: '0.02em' }}>
          Login to view your portfolio
        </p>
        <button onClick={login} style={{
          background: 'linear-gradient(135deg, #0a2a3f 0%, #1a4a6f 50%, #0d3050 100%)',
          border: '1px solid rgba(0,212,255,0.4)',
          color: color.accentCyan,
          padding: '12px 32px',
          borderRadius: 6,
          fontSize: fontSize.base,
          fontWeight: 700,
          cursor: 'pointer',
          textTransform: 'uppercase',
          letterSpacing: '0.06em',
          boxShadow: '0 0 20px rgba(0,212,255,0.15), inset 0 1px 0 rgba(255,255,255,0.05)',
          transition: 'all 0.2s',
        }}>Login with EVE SSO</button>
      </div>
    );
  }

  return (
    <div>
      {/* Sub-tabs - Battle Report style */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: spacing.xs,
        padding: '0.35rem 0.5rem',
        background: 'rgba(0,0,0,0.3)',
        borderRadius: '6px',
        border: '1px solid rgba(255,255,255,0.05)',
        height: '42px',
        boxSizing: 'border-box',
        marginBottom: spacing.lg,
      }}>
        {SUB_TAB_CONFIG.map(t => {
          const isActive = subTab === t.id;
          return (
            <button key={t.id} onClick={() => setSubTab(t.id)} style={{
              padding: '0.35rem 0.6rem',
              fontSize: fontSize.xs,
              fontWeight: 700,
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              transition: 'all 0.2s',
              background: isActive ? `${t.color}22` : 'transparent',
              color: isActive ? t.color : 'rgba(255,255,255,0.4)',
              borderBottom: isActive ? `2px solid ${t.color}` : '2px solid transparent',
              textTransform: 'uppercase',
              letterSpacing: '0.03em',
              display: 'flex',
              alignItems: 'center',
              gap: spacing.sm,
            }}>
              {t.label}
              {isActive && (
                <span style={{
                  width: '6px',
                  height: '6px',
                  borderRadius: '50%',
                  background: t.color,
                  boxShadow: `0 0 8px ${t.color}`,
                }} />
              )}
            </button>
          );
        })}
      </div>

      {/* Orders View */}
      {subTab === 'orders' && (
        <div>
          {/* Order filter pills */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: spacing.xs,
            padding: '0.35rem 0.5rem',
            background: 'rgba(0,0,0,0.3)',
            borderRadius: '6px',
            border: '1px solid rgba(255,255,255,0.05)',
            height: '36px',
            boxSizing: 'border-box',
            marginBottom: spacing.lg,
          }}>
            {(['all', 'sell', 'buy'] as const).map(f => {
              const isActive = orderFilter === f;
              const filterColor = f === 'sell' ? '#f85149' : f === 'buy' ? '#3fb950' : '#00d4ff';
              return (
                <button key={f} onClick={() => setOrderFilter(f)} style={{
                  padding: '0.25rem 0.55rem',
                  fontSize: fontSize.xxs,
                  fontWeight: 700,
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                  background: isActive ? `${filterColor}22` : 'transparent',
                  color: isActive ? filterColor : 'rgba(255,255,255,0.4)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.03em',
                }}>
                  {f}
                </button>
              );
            })}
          </div>

          {ordersLoading ? <div className="skeleton" style={{ height: 300 }} /> : ordersData ? (
            <div>
              {/* Summary badges - CombatSummaryBar style */}
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: spacing.xs,
                background: 'rgba(0,0,0,0.3)',
                borderRadius: '6px',
                border: '1px solid rgba(255,255,255,0.05)',
                padding: '0.35rem 0.5rem',
                height: '42px',
                boxSizing: 'border-box',
                marginBottom: spacing.lg,
              }}>
                {/* Sell Orders */}
                <div style={{ padding: '0.35rem 0.6rem', background: 'rgba(248,81,73,0.1)', borderRadius: '4px', display: 'flex', alignItems: 'center', gap: spacing.sm }}>
                  <span style={{ fontSize: fontSize.xs, fontWeight: 700, color: color.lossRed, fontFamily: 'monospace' }}>
                    {ordersData.summary.total_sell_orders}
                  </span>
                  <span style={{ fontSize: fontSize.tiny, fontWeight: 700, color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', letterSpacing: '0.03em' }}>Sell</span>
                  <span style={{ fontSize: fontSize.tiny, fontWeight: 600, color: 'rgba(248,81,73,0.6)', fontFamily: 'monospace' }}>
                    {formatISKCompact(ordersData.summary.total_isk_in_sell_orders)}
                  </span>
                </div>

                {/* Buy Orders */}
                <div style={{ padding: '0.35rem 0.6rem', background: 'rgba(63,185,80,0.1)', borderRadius: '4px', display: 'flex', alignItems: 'center', gap: spacing.sm }}>
                  <span style={{ fontSize: fontSize.xs, fontWeight: 700, color: color.killGreen, fontFamily: 'monospace' }}>
                    {ordersData.summary.total_buy_orders}
                  </span>
                  <span style={{ fontSize: fontSize.tiny, fontWeight: 700, color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', letterSpacing: '0.03em' }}>Buy</span>
                  <span style={{ fontSize: fontSize.tiny, fontWeight: 600, color: 'rgba(63,185,80,0.6)', fontFamily: 'monospace' }}>
                    {formatISKCompact(ordersData.summary.total_isk_in_buy_orders)}
                  </span>
                </div>

                {/* Outbid */}
                <div style={{
                  padding: '0.35rem 0.6rem',
                  background: ordersData.summary.outbid_count > 0 ? 'rgba(248,81,73,0.15)' : 'rgba(63,185,80,0.1)',
                  borderRadius: '4px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: spacing.sm,
                }}>
                  <span style={{
                    fontSize: fontSize.xs,
                    fontWeight: 700,
                    color: ordersData.summary.outbid_count > 0 ? '#f85149' : '#3fb950',
                    fontFamily: 'monospace',
                  }}>
                    {ordersData.summary.outbid_count}
                  </span>
                  <span style={{ fontSize: fontSize.tiny, fontWeight: 700, color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', letterSpacing: '0.03em' }}>Outbid</span>
                </div>

                {/* Characters */}
                <div style={{ padding: '0.35rem 0.6rem', background: 'rgba(0,212,255,0.1)', borderRadius: '4px', display: 'flex', alignItems: 'center', gap: spacing.sm }}>
                  <span style={{ fontSize: fontSize.xs, fontWeight: 700, color: color.accentCyan, fontFamily: 'monospace' }}>
                    {ordersData.summary.total_characters}
                  </span>
                  <span style={{ fontSize: fontSize.tiny, fontWeight: 700, color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', letterSpacing: '0.03em' }}>Chars</span>
                </div>
              </div>

              {/* Order Table */}
              <div style={{ background: 'rgba(0,0,0,0.2)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: 8, overflow: 'hidden' }}>
                <div style={{
                  display: 'grid', gridTemplateColumns: '2fr 1fr 0.8fr 0.8fr 0.5fr',
                  padding: '0.5rem 0.75rem', fontSize: fontSize.tiny, fontWeight: 700,
                  color: 'rgba(255,255,255,0.35)', borderBottom: '1px solid rgba(255,255,255,0.06)',
                  textTransform: 'uppercase', letterSpacing: '0.04em',
                }}>
                  <span>Item</span><span style={{ textAlign: 'right' }}>Price</span>
                  <span style={{ textAlign: 'right' }}>Volume</span><span style={{ textAlign: 'right' }}>Location</span>
                  <span style={{ textAlign: 'center' }}>Status</span>
                </div>
                {ordersData.orders.slice(0, 50).map(order => (
                  <div key={order.order_id} style={{
                    display: 'grid', gridTemplateColumns: '2fr 1fr 0.8fr 0.8fr 0.5fr',
                    padding: '0.35rem 0.75rem', fontSize: fontSize.sm,
                    borderBottom: '1px solid rgba(255,255,255,0.03)',
                    alignItems: 'center',
                  }}>
                    <div>
                      <div style={{ fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: 'rgba(255,255,255,0.85)' }}>{order.type_name}</div>
                      <div style={{ fontSize: fontSize.micro, color: 'rgba(255,255,255,0.3)' }}>{order.character_name}</div>
                    </div>
                    <span style={{ textAlign: 'right', fontFamily: 'monospace', fontWeight: 600, color: order.is_buy_order ? '#3fb950' : '#f85149' }}>
                      {formatISKCompact(order.price)}
                    </span>
                    <span style={{ textAlign: 'right', fontFamily: 'monospace', color: 'rgba(255,255,255,0.45)' }}>
                      {order.volume_remain}/{order.volume_total}
                    </span>
                    <span style={{ textAlign: 'right', fontSize: fontSize.xxs, color: 'rgba(255,255,255,0.3)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {order.region_name}
                    </span>
                    <div style={{ textAlign: 'center' }}>
                      {order.market_status.is_outbid ? (
                        <span style={{
                          fontSize: fontSize.micro, padding: '2px 8px', borderRadius: 3,
                          background: 'rgba(248,81,73,0.2)', color: color.lossRed, fontWeight: 700,
                          border: '1px solid rgba(248,81,73,0.3)',
                          textTransform: 'uppercase', letterSpacing: '0.04em',
                        }}>OUTBID</span>
                      ) : (
                        <span style={{
                          fontSize: fontSize.micro, padding: '2px 8px', borderRadius: 3,
                          background: 'rgba(63,185,80,0.15)', color: color.killGreen, fontWeight: 700,
                          border: '1px solid rgba(63,185,80,0.2)',
                          textTransform: 'uppercase', letterSpacing: '0.04em',
                        }}>BEST</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div style={{ textAlign: 'center', padding: spacing["3xl"], color: 'rgba(255,255,255,0.3)', fontSize: fontSize.base }}>No order data available</div>
          )}
        </div>
      )}

      {/* P&L View */}
      {subTab === 'pnl' && (
        <div>
          {/* Period filter - TimeFilter style */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: spacing.xs,
            padding: '0.35rem 0.5rem',
            background: 'rgba(0,0,0,0.3)',
            borderRadius: '6px',
            border: '1px solid rgba(255,255,255,0.05)',
            height: '36px',
            boxSizing: 'border-box',
            marginBottom: spacing.lg,
          }}>
            {[7, 14, 30, 90].map(d => {
              const isActive = pnlDays === d;
              const periodColor = '#3fb950';
              return (
                <button key={d} onClick={() => setPnlDays(d)} style={{
                  padding: '0.25rem 0.55rem',
                  fontSize: fontSize.xxs,
                  fontWeight: 700,
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                  background: isActive ? `${periodColor}22` : 'transparent',
                  color: isActive ? periodColor : 'rgba(255,255,255,0.4)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.03em',
                  display: 'flex',
                  alignItems: 'center',
                  gap: spacing.sm,
                }}>
                  {d}D
                  {isActive && (
                    <span style={{
                      width: '5px',
                      height: '5px',
                      borderRadius: '50%',
                      background: periodColor,
                      boxShadow: `0 0 6px ${periodColor}`,
                    }} />
                  )}
                </button>
              );
            })}
          </div>

          {pnlLoading ? <div className="skeleton" style={{ height: 300 }} /> : pnlData ? (
            <div>
              {/* P&L summary badges - inline row */}
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: spacing.xs,
                background: 'rgba(0,0,0,0.3)',
                borderRadius: '6px',
                border: '1px solid rgba(255,255,255,0.05)',
                padding: '0.35rem 0.5rem',
                height: '42px',
                boxSizing: 'border-box',
                marginBottom: spacing.lg,
              }}>
                {/* Realized */}
                <div style={{
                  padding: '0.35rem 0.6rem',
                  background: (pnlData.realized_pnl ?? pnlData.total_realized_pnl ?? 0) >= 0 ? 'rgba(63,185,80,0.1)' : 'rgba(248,81,73,0.1)',
                  borderRadius: '4px', display: 'flex', alignItems: 'center', gap: spacing.sm,
                }}>
                  <span style={{
                    fontSize: fontSize.xs, fontWeight: 700, fontFamily: 'monospace',
                    color: (pnlData.realized_pnl ?? pnlData.total_realized_pnl ?? 0) >= 0 ? '#3fb950' : '#f85149',
                  }}>
                    {formatISK(pnlData.realized_pnl ?? pnlData.total_realized_pnl ?? 0)}
                  </span>
                  <span style={{ fontSize: fontSize.tiny, fontWeight: 700, color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', letterSpacing: '0.03em' }}>Realized</span>
                </div>

                {/* Unrealized */}
                <div style={{
                  padding: '0.35rem 0.6rem',
                  background: (pnlData.unrealized_pnl ?? pnlData.total_unrealized_pnl ?? 0) >= 0 ? 'rgba(63,185,80,0.1)' : 'rgba(248,81,73,0.1)',
                  borderRadius: '4px', display: 'flex', alignItems: 'center', gap: spacing.sm,
                }}>
                  <span style={{
                    fontSize: fontSize.xs, fontWeight: 700, fontFamily: 'monospace',
                    color: (pnlData.unrealized_pnl ?? pnlData.total_unrealized_pnl ?? 0) >= 0 ? '#3fb950' : '#f85149',
                  }}>
                    {formatISK(pnlData.unrealized_pnl ?? pnlData.total_unrealized_pnl ?? 0)}
                  </span>
                  <span style={{ fontSize: fontSize.tiny, fontWeight: 700, color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', letterSpacing: '0.03em' }}>Unrealized</span>
                </div>

                {/* Total */}
                <div style={{
                  padding: '0.35rem 0.6rem',
                  background: (pnlData.total_pnl ?? 0) >= 0 ? 'rgba(255,204,0,0.1)' : 'rgba(248,81,73,0.15)',
                  borderRadius: '4px', display: 'flex', alignItems: 'center', gap: spacing.sm,
                }}>
                  <span style={{
                    fontSize: fontSize.xs, fontWeight: 700, fontFamily: 'monospace',
                    color: (pnlData.total_pnl ?? 0) >= 0 ? '#ffcc00' : '#f85149',
                  }}>
                    {formatISK(pnlData.total_pnl ?? 0)}
                  </span>
                  <span style={{ fontSize: fontSize.tiny, fontWeight: 700, color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', letterSpacing: '0.03em' }}>Total</span>
                </div>

                {/* Trades */}
                {pnlData.total_trades != null && (
                <div style={{ padding: '0.35rem 0.6rem', background: 'rgba(0,212,255,0.1)', borderRadius: '4px', display: 'flex', alignItems: 'center', gap: spacing.sm }}>
                  <span style={{ fontSize: fontSize.xs, fontWeight: 700, color: color.accentCyan, fontFamily: 'monospace' }}>
                    {pnlData.total_trades.toLocaleString()}
                  </span>
                  <span style={{ fontSize: fontSize.tiny, fontWeight: 700, color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', letterSpacing: '0.03em' }}>Trades</span>
                </div>
                )}
              </div>

              {/* Top Winners/Losers - side-by-side panels */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: spacing.base }}>
                {/* Winners */}
                <div style={{
                  background: 'rgba(0,0,0,0.2)',
                  border: '1px solid rgba(63,185,80,0.15)',
                  borderRadius: 8,
                  overflow: 'hidden',
                }}>
                  <div style={{
                    padding: '0.5rem 0.75rem',
                    borderBottom: '1px solid rgba(63,185,80,0.1)',
                    display: 'flex', alignItems: 'center', gap: spacing.md,
                  }}>
                    <span style={{
                      width: '6px', height: '6px', borderRadius: '50%',
                      background: color.killGreen, boxShadow: '0 0 8px #3fb950',
                    }} />
                    <span style={{ fontSize: fontSize.xxs, fontWeight: 700, color: color.killGreen, textTransform: 'uppercase', letterSpacing: '0.04em' }}>Top Winners</span>
                  </div>
                  {(pnlData.top_winners ?? []).slice(0, 5).map((item, i) => (
                    <div key={i} style={{
                      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                      padding: '0.3rem 0.75rem',
                      borderBottom: '1px solid rgba(255,255,255,0.03)',
                    }}>
                      <span style={{ fontSize: fontSize.sm, color: 'rgba(255,255,255,0.75)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '60%' }}>
                        {item.type_name}
                      </span>
                      <span style={{ fontFamily: 'monospace', fontSize: fontSize.sm, color: color.killGreen, fontWeight: 700 }}>
                        +{formatISKCompact(item.total)}
                      </span>
                    </div>
                  ))}
                </div>

                {/* Losers */}
                <div style={{
                  background: 'rgba(0,0,0,0.2)',
                  border: '1px solid rgba(248,81,73,0.15)',
                  borderRadius: 8,
                  overflow: 'hidden',
                }}>
                  <div style={{
                    padding: '0.5rem 0.75rem',
                    borderBottom: '1px solid rgba(248,81,73,0.1)',
                    display: 'flex', alignItems: 'center', gap: spacing.md,
                  }}>
                    <span style={{
                      width: '6px', height: '6px', borderRadius: '50%',
                      background: color.lossRed, boxShadow: '0 0 8px #f85149',
                    }} />
                    <span style={{ fontSize: fontSize.xxs, fontWeight: 700, color: color.lossRed, textTransform: 'uppercase', letterSpacing: '0.04em' }}>Top Losers</span>
                  </div>
                  {(pnlData.top_losers ?? []).slice(0, 5).map((item, i) => (
                    <div key={i} style={{
                      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                      padding: '0.3rem 0.75rem',
                      borderBottom: '1px solid rgba(255,255,255,0.03)',
                    }}>
                      <span style={{ fontSize: fontSize.sm, color: 'rgba(255,255,255,0.75)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '60%' }}>
                        {item.type_name}
                      </span>
                      <span style={{ fontFamily: 'monospace', fontSize: fontSize.sm, color: color.lossRed, fontWeight: 700 }}>
                        {formatISKCompact(item.total)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div style={{ textAlign: 'center', padding: spacing["3xl"], color: 'rgba(255,255,255,0.3)', fontSize: fontSize.base }}>No P&L data available</div>
          )}
        </div>
      )}

      {/* Portfolio Snapshot View */}
      {subTab === 'snapshot' && (
        <div>
          {snapshotLoading ? <div className="skeleton" style={{ height: 200 }} /> : snapshots.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: spacing.md }}>
              {snapshots.map(snap => (
                <div key={snap.character_id} style={{
                  padding: '0.5rem 0.75rem',
                  background: 'rgba(0,0,0,0.2)',
                  border: '1px solid rgba(255,255,255,0.06)',
                  borderRadius: 8,
                  display: 'flex',
                  alignItems: 'center',
                  gap: spacing.lg,
                  flexWrap: 'wrap',
                }}>
                  {/* Character info */}
                  <div style={{ minWidth: '120px', flex: '1 1 120px' }}>
                    <div style={{ fontWeight: 700, fontSize: fontSize.base, color: 'rgba(255,255,255,0.85)' }}>Character {snap.character_id}</div>
                    <div style={{ fontSize: fontSize.micro, color: 'rgba(255,255,255,0.3)', letterSpacing: '0.02em' }}>{snap.snapshot_date}</div>
                  </div>

                  {/* Wallet badge */}
                  <div style={{ padding: '0.3rem 0.5rem', background: 'rgba(0,212,255,0.1)', borderRadius: '4px', display: 'flex', alignItems: 'center', gap: spacing.xs }}>
                    <span style={{ fontSize: fontSize.micro, fontWeight: 700, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', letterSpacing: '0.03em' }}>Wallet</span>
                    <span style={{ fontFamily: 'monospace', fontSize: fontSize.sm, fontWeight: 700, color: color.accentCyan }}>{formatISKCompact(snap.wallet_balance)}</span>
                  </div>

                  {/* Sell Orders badge */}
                  <div style={{ padding: '0.3rem 0.5rem', background: 'rgba(248,81,73,0.1)', borderRadius: '4px', display: 'flex', alignItems: 'center', gap: spacing.xs }}>
                    <span style={{ fontSize: fontSize.micro, fontWeight: 700, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', letterSpacing: '0.03em' }}>Sell</span>
                    <span style={{ fontFamily: 'monospace', fontSize: fontSize.sm, fontWeight: 600, color: color.lossRed }}>{formatISKCompact(snap.sell_order_value)}</span>
                  </div>

                  {/* Buy Escrow badge */}
                  <div style={{ padding: '0.3rem 0.5rem', background: 'rgba(63,185,80,0.1)', borderRadius: '4px', display: 'flex', alignItems: 'center', gap: spacing.xs }}>
                    <span style={{ fontSize: fontSize.micro, fontWeight: 700, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', letterSpacing: '0.03em' }}>Escrow</span>
                    <span style={{ fontFamily: 'monospace', fontSize: fontSize.sm, fontWeight: 600, color: color.killGreen }}>{formatISKCompact(snap.buy_order_escrow)}</span>
                  </div>

                  {/* Total Liquid badge */}
                  <div style={{ padding: '0.3rem 0.5rem', background: 'rgba(255,204,0,0.1)', borderRadius: '4px', display: 'flex', alignItems: 'center', gap: spacing.xs }}>
                    <span style={{ fontSize: fontSize.micro, fontWeight: 700, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', letterSpacing: '0.03em' }}>Liquid</span>
                    <span style={{ fontFamily: 'monospace', fontSize: fontSize.base, fontWeight: 700, color: color.warningYellow }}>{formatISKCompact(snap.total_liquid)}</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div style={{ textAlign: 'center', padding: spacing["3xl"], color: 'rgba(255,255,255,0.3)', fontSize: fontSize.base }}>
              No portfolio snapshots yet. Snapshots are taken automatically.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
