import { useState, useEffect } from 'react';
import { marketApi } from '../../services/api/market';
import { TRADE_HUBS } from '../../types/market';
import type { MarketPrice, MarketStats, ItemSearchResult, ItemDetail } from '../../types/market';
import { formatISK, formatISKCompact } from '../../utils/format';

interface Props {
  selectedItem: ItemSearchResult;
  itemDetail: ItemDetail | null;
}

export function PricesTab({ selectedItem, itemDetail }: Props) {
  const [prices, setPrices] = useState<Record<number, MarketPrice>>({});
  const [stats, setStats] = useState<MarketStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [descExpanded, setDescExpanded] = useState(false);

  useEffect(() => {
    setLoading(true);
    setPrices({});
    setStats(null);

    const pricePromises = TRADE_HUBS.map(hub =>
      marketApi.getPrice(selectedItem.typeID, hub.regionId)
        .then(p => ({ regionId: hub.regionId, price: p }))
    );

    const statsPromise = marketApi.getStats(selectedItem.typeID).catch(() => null);

    Promise.allSettled([...pricePromises, statsPromise]).then(results => {
      const priceMap: Record<number, MarketPrice> = {};
      for (let i = 0; i < TRADE_HUBS.length; i++) {
        const r = results[i];
        if (r.status === 'fulfilled' && r.value && typeof r.value === 'object' && 'regionId' in r.value) {
          priceMap[(r.value as { regionId: number; price: MarketPrice }).regionId] =
            (r.value as { regionId: number; price: MarketPrice }).price;
        }
      }
      const statsResult = results[TRADE_HUBS.length];
      if (statsResult.status === 'fulfilled' && statsResult.value) {
        setStats(statsResult.value as MarketStats);
      }
      setPrices(priceMap);
      setLoading(false);
    });
  }, [selectedItem.typeID]);

  // Derived values
  const priceEntries = Object.values(prices);
  const sellPrices = priceEntries.map(p => p.sell_price).filter(p => p > 0);
  const lowestSell = sellPrices.length > 0 ? Math.min(...sellPrices) : null;
  const jitaPrice = prices[10000002];
  const jitaSpread = jitaPrice && jitaPrice.sell_price > 0
    ? ((jitaPrice.sell_price - jitaPrice.buy_price) / jitaPrice.sell_price * 100)
    : null;

  if (loading) return <div className="skeleton" style={{ height: 200 }} />;

  // -- Inline badge style helper --
  const badge = (
    value: string,
    label: string,
    color: string,
    bgAlpha = 0.1,
  ) => (
    <div style={{
      padding: '0.35rem 0.6rem',
      background: `${color}${Math.round(bgAlpha * 255).toString(16).padStart(2, '0')}`,
      borderRadius: 4,
      display: 'flex',
      alignItems: 'center',
      gap: '0.3rem',
      whiteSpace: 'nowrap' as const,
    }}>
      <span style={{ fontSize: '0.75rem', fontWeight: 700, color, fontFamily: 'monospace' }}>
        {value}
      </span>
      <span style={{
        fontSize: '0.65rem',
        fontWeight: 700,
        color: 'rgba(255,255,255,0.4)',
        textTransform: 'uppercase' as const,
        letterSpacing: '0.03em',
      }}>
        {label}
      </span>
    </div>
  );

  return (
    <div>
      {/* ── Quick Stats Bar (CombatSummaryBar-style) ── */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '0.25rem',
        flexWrap: 'wrap',
        background: 'rgba(0,0,0,0.3)',
        borderRadius: 6,
        border: '1px solid rgba(255,255,255,0.05)',
        padding: '0.35rem 0.5rem',
        minHeight: 42,
        boxSizing: 'border-box',
        marginBottom: '0.75rem',
      }}>
        {/* Sell (Jita) */}
        {badge(
          jitaPrice ? formatISKCompact(jitaPrice.sell_price) : '\u2014',
          'Sell',
          '#f85149',
        )}
        {/* Buy (Jita) */}
        {badge(
          jitaPrice ? formatISKCompact(jitaPrice.buy_price) : '\u2014',
          'Buy',
          '#3fb950',
        )}
        {/* Spread */}
        {badge(
          jitaSpread != null && isFinite(jitaSpread) ? `${jitaSpread.toFixed(1)}%` : '\u2014',
          'Spread',
          '#ffcc00',
        )}
        {/* Volume */}
        {stats?.avg_daily_volume != null
          ? badge(stats.avg_daily_volume.toLocaleString(), 'Vol/d', '#00d4ff')
          : badge('\u2014', 'Vol/d', '#00d4ff')
        }
        {/* 7D Trend */}
        {stats?.trend_7d != null
          ? badge(
              `${stats.trend_7d > 0 ? '+' : ''}${(stats.trend_7d * 100).toFixed(1)}%`,
              '7D',
              stats.trend_7d >= 0 ? '#3fb950' : '#f85149',
            )
          : badge('\u2014', '7D', '#8b949e')
        }
        {/* Risk Score */}
        {stats?.risk_score != null
          ? badge(
              stats.risk_score.toFixed(2),
              'Risk',
              stats.risk_score < 0.3 ? '#3fb950' : stats.risk_score < 0.6 ? '#ffcc00' : '#f85149',
            )
          : badge('\u2014', 'Risk', '#8b949e')
        }
      </div>

      {/* ── Trade Hub Comparison Table ── */}
      <div style={{
        background: 'var(--bg-secondary)',
        border: '1px solid var(--border-color)',
        borderRadius: 6,
        overflow: 'hidden',
        marginBottom: '0.75rem',
      }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.78rem' }}>
          <thead>
            <tr style={{ background: 'rgba(0,0,0,0.2)' }}>
              {['Hub', 'Sell Price', 'Buy Price', 'Spread', ''].map((h, i) => (
                <th key={i} style={{
                  padding: '0.45rem 0.6rem',
                  textAlign: i === 0 ? 'left' : 'right',
                  fontWeight: 700,
                  fontSize: '0.65rem',
                  color: 'rgba(255,255,255,0.45)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.04em',
                  borderBottom: '1px solid rgba(255,255,255,0.06)',
                }}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {TRADE_HUBS.map(hub => {
              const price = prices[hub.regionId];
              const hasSell = price && price.sell_price > 0;
              const isBest = hasSell && isFinite(lowestSell ?? NaN) && price.sell_price === lowestSell;
              const spread = hasSell
                ? ((price.sell_price - price.buy_price) / price.sell_price * 100)
                : null;

              return (
                <tr
                  key={hub.regionId}
                  style={{
                    borderBottom: '1px solid rgba(255,255,255,0.04)',
                    background: isBest ? 'rgba(63,185,80,0.04)' : 'transparent',
                  }}
                >
                  {/* Hub name */}
                  <td style={{
                    padding: '0.5rem 0.6rem',
                    fontWeight: 600,
                    color: isBest ? '#3fb950' : 'var(--text-primary)',
                  }}>
                    {hub.name}
                  </td>

                  {/* Sell price */}
                  <td style={{
                    padding: '0.5rem 0.6rem',
                    textAlign: 'right',
                    fontFamily: 'monospace',
                    fontWeight: 600,
                    color: hasSell ? '#f85149' : 'var(--text-tertiary)',
                  }}>
                    {hasSell ? formatISK(price.sell_price) : '\u2014'}
                  </td>

                  {/* Buy price */}
                  <td style={{
                    padding: '0.5rem 0.6rem',
                    textAlign: 'right',
                    fontFamily: 'monospace',
                    fontWeight: 600,
                    color: price && price.buy_price > 0 ? '#3fb950' : 'var(--text-tertiary)',
                  }}>
                    {price && price.buy_price > 0 ? formatISK(price.buy_price) : '\u2014'}
                  </td>

                  {/* Spread */}
                  <td style={{
                    padding: '0.5rem 0.6rem',
                    textAlign: 'right',
                    fontFamily: 'monospace',
                    fontSize: '0.72rem',
                    color: spread != null && isFinite(spread)
                      ? (spread < 5 ? '#3fb950' : spread < 15 ? '#ffcc00' : '#f85149')
                      : 'var(--text-tertiary)',
                  }}>
                    {spread != null && isFinite(spread) ? `${spread.toFixed(1)}%` : '\u2014'}
                  </td>

                  {/* BEST badge */}
                  <td style={{ padding: '0.5rem 0.6rem', textAlign: 'right', width: 50 }}>
                    {isBest && (
                      <span style={{
                        fontSize: '0.58rem',
                        padding: '2px 6px',
                        background: 'rgba(63,185,80,0.15)',
                        border: '1px solid rgba(63,185,80,0.4)',
                        borderRadius: 3,
                        color: '#3fb950',
                        fontWeight: 700,
                        letterSpacing: '0.04em',
                      }}>
                        BEST
                      </span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* ── Extended Market Stats (dense inline row) ── */}
      {stats && (
        <div style={{
          display: 'flex',
          gap: '0.5rem',
          flexWrap: 'wrap',
          marginBottom: '0.75rem',
        }}>
          {[
            {
              label: 'Volatility',
              value: stats.price_volatility != null ? `${(stats.price_volatility * 100).toFixed(1)}%` : '\u2014',
              color: '#00d4ff',
            },
            {
              label: 'Days to Sell 100',
              value: stats.days_to_sell_100 != null ? stats.days_to_sell_100.toFixed(1) : '\u2014',
              color: stats.days_to_sell_100 != null
                ? (stats.days_to_sell_100 < 1 ? '#3fb950' : stats.days_to_sell_100 < 7 ? '#ffcc00' : '#f85149')
                : '#8b949e',
            },
            {
              label: 'Sell Vol',
              value: stats.sell_volume?.toLocaleString() ?? '\u2014',
              color: '#f85149',
            },
            {
              label: 'Buy Vol',
              value: stats.buy_volume?.toLocaleString() ?? '\u2014',
              color: '#3fb950',
            },
          ].map(s => (
            <div key={s.label} style={{
              padding: '0.4rem 0.65rem',
              background: 'var(--bg-secondary)',
              border: '1px solid var(--border-color)',
              borderRadius: 5,
              display: 'flex',
              alignItems: 'center',
              gap: '0.35rem',
            }}>
              <span style={{
                fontSize: '0.65rem',
                color: 'rgba(255,255,255,0.4)',
                textTransform: 'uppercase',
                fontWeight: 700,
                letterSpacing: '0.03em',
              }}>
                {s.label}
              </span>
              <span style={{
                fontSize: '0.78rem',
                fontWeight: 600,
                fontFamily: 'monospace',
                color: s.color,
              }}>
                {s.value}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* ── Item Description (collapsed by default) ── */}
      {itemDetail?.description && (
        <div
          onClick={() => setDescExpanded(prev => !prev)}
          style={{
            padding: '0.5rem 0.7rem',
            background: 'rgba(0,0,0,0.15)',
            border: '1px solid rgba(255,255,255,0.04)',
            borderRadius: 5,
            cursor: 'pointer',
            userSelect: 'none',
          }}
        >
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}>
            <span style={{
              fontSize: '0.65rem',
              fontWeight: 700,
              color: 'rgba(255,255,255,0.35)',
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
            }}>
              Description
            </span>
            <span style={{
              fontSize: '0.6rem',
              color: 'rgba(255,255,255,0.25)',
              transform: descExpanded ? 'rotate(180deg)' : 'rotate(0deg)',
              transition: 'transform 0.2s',
            }}>
              &#9660;
            </span>
          </div>
          {descExpanded && (
            <div style={{
              fontSize: '0.75rem',
              color: 'var(--text-secondary)',
              lineHeight: 1.5,
              marginTop: '0.4rem',
            }}>
              {itemDetail.description.replace(/<[^>]+>/g, '')}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
