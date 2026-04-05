import { useState, useEffect } from 'react';
import { marketApi } from '../../services/api/market';
import type { ItemSearchResult, RegionalComparison } from '../../types/market';
import { formatISK } from '../../utils/format';

interface Props {
  selectedItem: ItemSearchResult;
}

interface OrderEntry {
  price: number;
  volume_remain: number;
  is_buy_order: boolean;
  location_name?: string;
  issued?: string;
}

const SELL_COLOR = '#f85149';
const BUY_COLOR = '#3fb950';

const thStyle: React.CSSProperties = {
  fontSize: '0.65rem',
  fontWeight: 700,
  textTransform: 'uppercase',
  color: 'var(--text-secondary)',
  padding: '0.4rem 0.6rem',
  textAlign: 'left',
  letterSpacing: '0.04em',
  borderBottom: '1px solid rgba(255,255,255,0.06)',
};

const tdStyle: React.CSSProperties = {
  padding: '0.35rem 0.6rem',
  fontSize: '0.78rem',
  fontFamily: 'monospace',
  borderBottom: '1px solid rgba(255,255,255,0.03)',
};

function Badge({ label, color }: { label: string; color: string }) {
  return (
    <span style={{
      fontSize: '0.55rem',
      fontWeight: 700,
      color,
      background: `${color}22`,
      border: `1px solid ${color}44`,
      padding: '1px 5px',
      borderRadius: 3,
      textTransform: 'uppercase',
      letterSpacing: '0.03em',
      whiteSpace: 'nowrap',
    }}>
      {label}
    </span>
  );
}

export function HistoryTab({ selectedItem }: Props) {
  const [comparison, setComparison] = useState<RegionalComparison | null>(null);
  const [orders, setOrders] = useState<OrderEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [orderType, setOrderType] = useState<'sell' | 'buy'>('sell');

  useEffect(() => {
    setLoading(true);
    setComparison(null);
    setOrders([]);

    Promise.allSettled([
      marketApi.getRegionalComparison(selectedItem.typeID),
      marketApi.getRawOrders(selectedItem.typeID, 10000002, orderType),
    ]).then(([compResult, ordersResult]) => {
      if (compResult.status === 'fulfilled') setComparison(compResult.value);
      if (ordersResult.status === 'fulfilled') setOrders(ordersResult.value as unknown as OrderEntry[]);
      setLoading(false);
    });
  }, [selectedItem.typeID, orderType]);

  if (loading) return <div className="skeleton" style={{ height: 300 }} />;

  const sortedOrders = [...orders]
    .sort((a, b) => orderType === 'sell' ? a.price - b.price : b.price - a.price)
    .slice(0, 25);

  const maxVolume = sortedOrders.length > 0
    ? Math.max(...sortedOrders.map(o => o.volume_remain), 1)
    : 1;

  return (
    <div>
      {/* Regional Price Comparison — Dense Table */}
      {comparison && (
        <div style={{ marginBottom: '1.5rem' }}>
          <h3 style={{
            fontSize: '0.65rem', fontWeight: 700, color: 'var(--text-secondary)',
            marginBottom: '0.5rem', textTransform: 'uppercase', letterSpacing: '0.04em',
          }}>
            Regional Comparison
          </h3>
          <div style={{
            background: 'var(--bg-secondary)',
            border: '1px solid var(--border-color)',
            borderRadius: 6,
            overflow: 'hidden',
          }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr>
                  <th style={thStyle}>Region</th>
                  <th style={{ ...thStyle, textAlign: 'right' }}>Sell</th>
                  <th style={{ ...thStyle, textAlign: 'right' }}>Buy</th>
                  <th style={{ ...thStyle, textAlign: 'right' }}>Volume</th>
                  <th style={{ ...thStyle, textAlign: 'center', width: '1%' }}></th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(comparison.prices_by_region).map(([region, data]) => {
                  const isBestSell = comparison.best_sell_region === region;
                  const isBestBuy = comparison.best_buy_region === region;
                  return (
                    <tr key={region} style={{
                      background: (isBestSell || isBestBuy) ? 'rgba(63,185,80,0.04)' : 'transparent',
                    }}>
                      <td style={{ ...tdStyle, fontFamily: 'inherit', fontWeight: 600, fontSize: '0.75rem' }}>
                        {region}
                      </td>
                      <td style={{ ...tdStyle, textAlign: 'right', color: SELL_COLOR }}>
                        {formatISK(data.sell_price)}
                      </td>
                      <td style={{ ...tdStyle, textAlign: 'right', color: BUY_COLOR }}>
                        {formatISK(data.buy_price)}
                      </td>
                      <td style={{ ...tdStyle, textAlign: 'right', color: 'var(--text-secondary)' }}>
                        {(data.volume ?? 0).toLocaleString()}
                      </td>
                      <td style={{ ...tdStyle, textAlign: 'center', whiteSpace: 'nowrap' }}>
                        <span style={{ display: 'inline-flex', gap: '0.25rem' }}>
                          {isBestSell && <Badge label="BEST SELL" color={BUY_COLOR} />}
                          {isBestBuy && <Badge label="BEST BUY" color="#00d4ff" />}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Order Book */}
      <div>
        {/* Toggle Bar — Battle Report style */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0.4rem 0.6rem',
          background: 'rgba(0,0,0,0.3)',
          borderRadius: '6px',
          border: '1px solid rgba(255,255,255,0.05)',
          marginBottom: '0.5rem',
        }}>
          <span style={{
            fontSize: '0.65rem', fontWeight: 700, color: 'var(--text-secondary)',
            textTransform: 'uppercase', letterSpacing: '0.04em',
          }}>
            Jita Order Book
          </span>
          <div style={{ display: 'flex', gap: '0.25rem' }}>
            {(['sell', 'buy'] as const).map(t => {
              const isActive = orderType === t;
              const color = t === 'sell' ? SELL_COLOR : BUY_COLOR;
              return (
                <button
                  key={t}
                  onClick={() => setOrderType(t)}
                  style={{
                    padding: '0.3rem 0.65rem',
                    fontSize: '0.72rem',
                    fontWeight: 700,
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer',
                    transition: 'all 0.2s',
                    background: isActive ? `${color}22` : 'transparent',
                    color: isActive ? color : 'rgba(255,255,255,0.4)',
                    borderBottom: isActive ? `2px solid ${color}` : '2px solid transparent',
                    textTransform: 'uppercase',
                    letterSpacing: '0.03em',
                  }}
                >
                  {t === 'sell' ? 'Sell Orders' : 'Buy Orders'}
                  {isActive && (
                    <span style={{
                      display: 'inline-block',
                      width: '5px',
                      height: '5px',
                      borderRadius: '50%',
                      background: color,
                      boxShadow: `0 0 6px ${color}`,
                      marginLeft: '0.35rem',
                      verticalAlign: 'middle',
                    }} />
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* Order Table with Depth Bars */}
        <div style={{
          background: 'var(--bg-secondary)',
          border: '1px solid var(--border-color)',
          borderRadius: 6,
          overflow: 'hidden',
        }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                <th style={thStyle}>Price</th>
                <th style={{ ...thStyle, textAlign: 'right' }}>Volume</th>
              </tr>
            </thead>
            <tbody>
              {sortedOrders.length === 0 ? (
                <tr>
                  <td colSpan={2} style={{
                    padding: '1.5rem', textAlign: 'center',
                    color: 'var(--text-secondary)', fontSize: '0.8rem',
                  }}>
                    No orders found
                  </td>
                </tr>
              ) : (
                sortedOrders.map((order, i) => {
                  const pct = (order.volume_remain / maxVolume) * 100;
                  const barColor = orderType === 'sell' ? SELL_COLOR : BUY_COLOR;
                  const barGradient = orderType === 'sell'
                    ? `linear-gradient(to right, ${barColor}18 0%, ${barColor}08 ${pct}%, transparent ${pct}%)`
                    : `linear-gradient(to left, ${barColor}18 0%, ${barColor}08 ${pct}%, transparent ${pct}%)`;

                  return (
                    <tr key={i} style={{ background: barGradient }}>
                      <td style={{
                        ...tdStyle,
                        color: orderType === 'sell' ? SELL_COLOR : BUY_COLOR,
                      }}>
                        {formatISK(order.price)}
                      </td>
                      <td style={{
                        ...tdStyle,
                        textAlign: 'right',
                        color: 'var(--text-secondary)',
                      }}>
                        {order.volume_remain.toLocaleString()}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
