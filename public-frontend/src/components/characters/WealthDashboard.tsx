import { useState, useEffect } from 'react';
import { usePilotIntel } from '../../hooks/usePilotIntel';
import { portfolioApi, tradingApi, ordersApi } from '../../services/api/market';
import { formatISK } from '../../utils/format';
import type { PortfolioHistory, TradingPnLReport, AggregatedOrdersResponse } from '../../types/market';

interface Props {
  characterId: number;
}

export function WealthDashboard({ characterId }: Props) {
  const { derived, profile } = usePilotIntel();
  const [portfolioHistory, setPortfolioHistory] = useState<PortfolioHistory | null>(null);
  const [pnl, setPnl] = useState<TradingPnLReport | null>(null);
  const [ordersData, setOrdersData] = useState<AggregatedOrdersResponse | null>(null);

  useEffect(() => {
    if (!characterId) return;
    portfolioApi.getHistory(characterId, 30).then(setPortfolioHistory).catch(() => {});
    tradingApi.getPnL(characterId, 30).then(setPnl).catch(() => {});
    ordersApi.getAggregated([characterId]).then(setOrdersData).catch(() => {});
  }, [characterId]);

  // Per-character data from PilotIntel
  const charProfile = profile.characters.find(c => c.character_id === characterId);
  const walletBalance = charProfile?.wallet?.balance ?? 0;

  // Per-character order data
  const charOrders = ordersData?.by_character?.find(c => c.character_id === characterId);
  const sellOrderValue = charOrders?.isk_in_sell_orders ?? 0;
  const buyEscrow = charOrders?.isk_in_escrow ?? 0;
  const buyOrders = charOrders?.buy_orders ?? 0;
  const sellOrders = charOrders?.sell_orders ?? 0;
  const netWorth = walletBalance + sellOrderValue + buyEscrow;

  // Active orders for this character
  const myOrders = ordersData?.orders?.filter(o => o.character_id === characterId) ?? [];
  const outbidOrders = myOrders.filter(o => o.market_status?.is_outbid);

  // Industry jobs for this character
  const activeJobs = (charProfile?.industry?.jobs ?? []).filter(j => j.status === 'active');

  const breakdown = [
    { label: 'Wallet', value: walletBalance, color: '#3fb950' },
    { label: 'Sell Orders', value: sellOrderValue, color: '#00d4ff' },
    { label: 'Buy Escrow', value: buyEscrow, color: '#ff8800' },
  ].filter(b => b.value > 0);

  const realizedPnl = pnl?.realized_pnl ?? pnl?.total_realized_pnl ?? 0;
  const unrealizedPnl = pnl?.unrealized_pnl ?? pnl?.total_unrealized_pnl ?? 0;
  const hasPnlData = realizedPnl !== 0 || unrealizedPnl !== 0 || (pnl?.total_trades ?? 0) > 0;

  const sectionStyle = {
    background: 'rgba(0,0,0,0.2)',
    border: '1px solid rgba(255,255,255,0.06)',
    borderRadius: '8px',
    padding: '0.75rem',
    marginBottom: '0.75rem',
  };

  const labelStyle = {
    fontSize: '0.65rem',
    color: 'rgba(255,255,255,0.4)',
    textTransform: 'uppercase' as const,
    fontWeight: 700,
    marginBottom: '0.5rem',
  };

  return (
    <div style={{ maxWidth: 900 }}>
      {/* Net Worth Header */}
      <div style={{
        background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.06)',
        borderRadius: '8px', padding: '1rem', marginBottom: '0.75rem', textAlign: 'center',
      }}>
        <div style={labelStyle}>Net Worth</div>
        <div style={{ fontSize: '1.8rem', fontFamily: 'monospace', fontWeight: 800, color: '#3fb950' }}>
          {formatISK(netWorth)} ISK
        </div>
        {portfolioHistory && portfolioHistory.growth_absolute !== 0 && (
          <div style={{
            fontSize: '0.75rem', fontFamily: 'monospace',
            color: portfolioHistory.growth_absolute > 0 ? '#3fb950' : '#f85149',
          }}>
            {portfolioHistory.growth_absolute > 0 ? '+' : ''}{formatISK(portfolioHistory.growth_absolute)}
            {' '}({(portfolioHistory.growth_percent ?? 0).toFixed(1)}%) in 30d
          </div>
        )}
      </div>

      {/* Breakdown bars */}
      {breakdown.length > 0 && (
        <div style={sectionStyle}>
          {breakdown.map(b => {
            const pct = netWorth > 0 ? (b.value / netWorth) * 100 : 0;
            return (
              <div key={b.label} style={{ marginBottom: '0.5rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.2rem' }}>
                  <span style={{ fontSize: '0.7rem', color: b.color }}>{b.label}</span>
                  <span style={{ fontSize: '0.7rem', fontFamily: 'monospace', color: b.color }}>
                    {formatISK(b.value)} ({pct.toFixed(0)}%)
                  </span>
                </div>
                <div style={{ height: '4px', background: 'rgba(255,255,255,0.05)', borderRadius: '2px' }}>
                  <div style={{ width: `${pct}%`, height: '100%', background: b.color, borderRadius: '2px' }} />
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Active Orders */}
      {myOrders.length > 0 && (
        <div style={sectionStyle}>
          <div style={labelStyle}>Active Market Orders</div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.5rem', marginBottom: '0.75rem' }}>
            <div style={{ background: 'rgba(0,212,255,0.08)', borderRadius: '4px', padding: '0.5rem', textAlign: 'center' }}>
              <div style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.4)' }}>Sell Orders</div>
              <div style={{ fontSize: '1rem', fontFamily: 'monospace', fontWeight: 700, color: '#00d4ff' }}>{sellOrders}</div>
            </div>
            <div style={{ background: 'rgba(255,136,0,0.08)', borderRadius: '4px', padding: '0.5rem', textAlign: 'center' }}>
              <div style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.4)' }}>Buy Orders</div>
              <div style={{ fontSize: '1rem', fontFamily: 'monospace', fontWeight: 700, color: '#ff8800' }}>{buyOrders}</div>
            </div>
            <div style={{ background: 'rgba(248,81,73,0.08)', borderRadius: '4px', padding: '0.5rem', textAlign: 'center' }}>
              <div style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.4)' }}>Outbid</div>
              <div style={{ fontSize: '1rem', fontFamily: 'monospace', fontWeight: 700, color: outbidOrders.length > 0 ? '#f85149' : '#3fb950' }}>
                {outbidOrders.length}
              </div>
            </div>
          </div>

          {/* Order list */}
          {myOrders
            .sort((a, b) => (b.price * b.volume_remain) - (a.price * a.volume_remain))
            .map(order => (
            <div key={order.order_id} style={{
              display: 'flex', alignItems: 'center', gap: '0.5rem',
              padding: '4px 0', borderBottom: '1px solid rgba(255,255,255,0.03)',
            }}>
              <img
                src={`https://images.evetech.net/types/${order.type_id}/icon?size=32`}
                alt="" style={{ width: 24, height: 24, borderRadius: 3, flexShrink: 0 }}
              />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: '0.78rem', fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {order.type_name}
                  <span style={{ color: 'var(--text-secondary)', marginLeft: 4 }}>
                    x{order.volume_remain}
                  </span>
                </div>
                <div style={{ fontSize: '0.6rem', color: 'var(--text-secondary)' }}>
                  {order.location_name} · {order.region_name}
                </div>
              </div>
              <span style={{
                fontSize: '0.55rem', padding: '1px 5px', borderRadius: 3, fontWeight: 700,
                background: order.is_buy_order ? 'rgba(255,136,0,0.15)' : 'rgba(0,212,255,0.15)',
                color: order.is_buy_order ? '#ff8800' : '#00d4ff',
              }}>
                {order.is_buy_order ? 'BUY' : 'SELL'}
              </span>
              {order.market_status?.is_outbid && (
                <span style={{
                  fontSize: '0.55rem', padding: '1px 5px', borderRadius: 3, fontWeight: 700,
                  background: 'rgba(248,81,73,0.15)', color: '#f85149',
                }}>
                  OUTBID
                </span>
              )}
              <span style={{
                fontSize: '0.75rem', fontFamily: 'monospace', fontWeight: 600, minWidth: 75, textAlign: 'right',
                color: order.is_buy_order ? '#ff8800' : '#3fb950',
              }}>
                {formatISK(order.price * order.volume_remain)}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Active Industry Jobs */}
      {activeJobs.length > 0 && (
        <div style={sectionStyle}>
          <div style={labelStyle}>Active Industry Jobs</div>
          {activeJobs.map(job => {
            const progress = job.end_date && job.start_date
              ? Math.min(100, Math.max(0, (Date.now() - new Date(job.start_date).getTime()) / (new Date(job.end_date).getTime() - new Date(job.start_date).getTime()) * 100))
              : 0;
            return (
              <div key={job.job_id} style={{
                display: 'flex', alignItems: 'center', gap: '0.5rem',
                padding: '4px 0', borderBottom: '1px solid rgba(255,255,255,0.03)',
              }}>
                <div style={{ flex: 1, fontSize: '0.78rem' }}>
                  {job.product_type_name || job.blueprint_type_name}
                  {job.runs > 1 && <span style={{ color: 'var(--text-secondary)', marginLeft: 4 }}>x{job.runs}</span>}
                </div>
                <div style={{ width: 60, height: 4, background: 'rgba(255,255,255,0.05)', borderRadius: 2, overflow: 'hidden' }}>
                  <div style={{ width: `${isFinite(progress) ? progress : 0}%`, height: '100%', background: '#d29922', borderRadius: 2 }} />
                </div>
                <span style={{ fontSize: '0.7rem', fontFamily: 'monospace', color: 'var(--text-secondary)', minWidth: 50, textAlign: 'right' }}>
                  {isFinite(progress) ? progress.toFixed(0) : 0}%
                </span>
              </div>
            );
          })}
        </div>
      )}

      {/* Trading P&L — only show if there's actual data */}
      {hasPnlData && (
        <div style={sectionStyle}>
          <div style={labelStyle}>Trading P&L (30d)</div>
          <div style={{ display: 'flex', gap: '1.5rem' }}>
            <div>
              <div style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.4)' }}>Realized</div>
              <div style={{ fontSize: '0.9rem', fontFamily: 'monospace', fontWeight: 700, color: realizedPnl >= 0 ? '#3fb950' : '#f85149' }}>
                {realizedPnl >= 0 ? '+' : ''}{formatISK(realizedPnl)}
              </div>
            </div>
            <div>
              <div style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.4)' }}>Unrealized</div>
              <div style={{ fontSize: '0.9rem', fontFamily: 'monospace', fontWeight: 700, color: unrealizedPnl >= 0 ? '#3fb950' : '#f85149' }}>
                {unrealizedPnl >= 0 ? '+' : ''}{formatISK(unrealizedPnl)}
              </div>
            </div>
            <div>
              <div style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.4)' }}>Trades</div>
              <div style={{ fontSize: '0.9rem', fontFamily: 'monospace', fontWeight: 700 }}>{pnl?.total_trades ?? 0}</div>
            </div>
          </div>
        </div>
      )}

      {/* Account-wide summary at bottom */}
      <div style={{
        ...sectionStyle,
        background: 'rgba(0,0,0,0.15)',
        border: '1px solid rgba(255,255,255,0.03)',
      }}>
        <div style={labelStyle}>Account Total (all characters)</div>
        <div style={{ display: 'flex', gap: '1.5rem' }}>
          <div>
            <div style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.4)' }}>Net Worth</div>
            <div style={{ fontSize: '0.9rem', fontFamily: 'monospace', fontWeight: 700, color: '#3fb950' }}>
              {formatISK(derived.totalNetWorth)}
            </div>
          </div>
          <div>
            <div style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.4)' }}>Wallet</div>
            <div style={{ fontSize: '0.9rem', fontFamily: 'monospace', fontWeight: 700 }}>
              {formatISK(derived.totalWallet)}
            </div>
          </div>
          <div>
            <div style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.4)' }}>Sell Orders</div>
            <div style={{ fontSize: '0.9rem', fontFamily: 'monospace', fontWeight: 700, color: '#00d4ff' }}>
              {formatISK(derived.totalSellOrderValue)}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
