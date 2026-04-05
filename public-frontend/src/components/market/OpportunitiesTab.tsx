import { useState, useEffect } from 'react';
import { marketApi } from '../../services/api/market';
import type { HunterOpportunity, TradingOpportunity } from '../../types/market';
import { formatISKCompact } from '../../utils/format';
import { usePersonalizedScore } from '../../hooks/usePersonalizedScore';
import type { OpportunityInput } from '../../hooks/usePersonalizedScore';
import { ScoreBadge, RecommendationBanner } from '../recommendations';
import { useAuth } from '../../hooks/useAuth';

type SubTab = 'manufacturing' | 'trading';

const SUB_TABS = [
  { id: 'manufacturing' as const, label: 'Manufacturing', icon: '\u{1F3ED}', color: '#ff8800' },
  { id: 'trading' as const, label: 'Trading', icon: '\u{1F4CA}', color: '#a855f7' },
];

const DIFF_COLORS: Record<number, string> = {
  1: '#3fb950',
  2: '#58a6ff',
  3: '#ffcc00',
  4: '#ff8800',
  5: '#f85149',
};

const DIFF_LABELS: Record<number, string> = {
  1: 'Easy',
  2: 'Simple',
  3: 'Medium',
  4: 'Hard',
  5: 'Expert',
};

export function OpportunitiesTab() {
  const { score } = usePersonalizedScore();
  const { isLoggedIn } = useAuth();
  const [subTab, setSubTab] = useState<SubTab>('manufacturing');

  // Manufacturing state
  const [mfgResults, setMfgResults] = useState<HunterOpportunity[]>([]);
  const [mfgLoading, setMfgLoading] = useState(false);
  const [mfgSort, setMfgSort] = useState<string>('profit');
  const [mfgMinRoi, setMfgMinRoi] = useState(15);
  const [mfgMaxDiff, setMfgMaxDiff] = useState(3);
  const [mfgSearch, setMfgSearch] = useState('');
  const [hideNoVolume, setHideNoVolume] = useState(false);

  // Trading state
  const [tradResults, setTradResults] = useState<TradingOpportunity[]>([]);
  const [tradLoading, setTradLoading] = useState(false);

  // Load manufacturing
  useEffect(() => {
    if (subTab !== 'manufacturing') return;
    setMfgLoading(true);
    marketApi.scanOpportunities({
      min_roi: mfgMinRoi,
      max_difficulty: mfgMaxDiff,
      min_volume: hideNoVolume ? 1 : 0,
      top: 100,
      search: mfgSearch || undefined,
      sort_by: mfgSort,
    })
      .then(data => setMfgResults(data.results))
      .catch(() => setMfgResults([]))
      .finally(() => setMfgLoading(false));
  }, [subTab, mfgSort, mfgMinRoi, mfgMaxDiff, mfgSearch, hideNoVolume]);

  // Load trading
  useEffect(() => {
    if (subTab !== 'trading') return;
    setTradLoading(true);
    marketApi.getTradingOpportunities({ min_margin: 5 })
      .then(data => setTradResults(data.results || []))
      .catch(() => setTradResults([]))
      .finally(() => setTradLoading(false));
  }, [subTab]);

  const diffColor = (d: number) => DIFF_COLORS[d] || '#f85149';
  const diffLabel = (d: number) => DIFF_LABELS[d] || 'Expert';

  const selectStyle: React.CSSProperties = {
    padding: '0.3rem 0.5rem',
    background: 'var(--bg-elevated)',
    border: '1px solid var(--border-color)',
    borderRadius: 4,
    color: 'var(--text-primary)',
    fontSize: '0.78rem',
  };

  const headerStyle: React.CSSProperties = {
    fontSize: '0.65rem',
    fontWeight: 700,
    color: 'var(--text-secondary)',
    textTransform: 'uppercase',
    letterSpacing: '0.03em',
  };

  return (
    <div>
      {/* Sub-tab toggle - Battle Report style */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '0.25rem',
        padding: '0.35rem 0.5rem',
        background: 'rgba(0,0,0,0.3)',
        borderRadius: 6,
        border: '1px solid rgba(255,255,255,0.05)',
        marginBottom: '1rem',
        height: 42,
        boxSizing: 'border-box',
      }}>
        {SUB_TABS.map(t => {
          const isActive = subTab === t.id;
          return (
            <button
              key={t.id}
              onClick={() => setSubTab(t.id)}
              style={{
                padding: '0.35rem 0.6rem',
                fontSize: '0.75rem',
                fontWeight: 700,
                border: 'none',
                borderRadius: 4,
                cursor: 'pointer',
                transition: 'all 0.2s',
                background: isActive ? `${t.color}22` : 'transparent',
                color: isActive ? t.color : 'rgba(255,255,255,0.4)',
                borderBottom: isActive ? `2px solid ${t.color}` : '2px solid transparent',
                textTransform: 'uppercase',
                letterSpacing: '0.03em',
                display: 'flex',
                alignItems: 'center',
                gap: '0.3rem',
              }}
            >
              <span style={{ opacity: isActive ? 1 : 0.6 }}>{t.icon}</span>
              {t.label}
              {isActive && (
                <span style={{
                  width: 6,
                  height: 6,
                  borderRadius: '50%',
                  background: t.color,
                  boxShadow: `0 0 8px ${t.color}`,
                }} />
              )}
            </button>
          );
        })}
      </div>

      {/* Manufacturing Opportunities */}
      {subTab === 'manufacturing' && (
        <div>
          {/* Filter bar */}
          <div style={{
            display: 'flex',
            flexWrap: 'wrap',
            gap: '0.75rem',
            marginBottom: '0.75rem',
            padding: '0.6rem 0.75rem',
            background: 'rgba(0,0,0,0.3)',
            border: '1px solid rgba(255,255,255,0.05)',
            borderRadius: 8,
            alignItems: 'flex-end',
          }}>
            <div>
              <div style={{ fontSize: '0.6rem', color: 'var(--text-secondary)', marginBottom: '0.2rem' }}>Min ROI</div>
              <select value={mfgMinRoi} onChange={e => setMfgMinRoi(Number(e.target.value))} style={selectStyle}>
                <option value={0}>0%</option>
                <option value={10}>10%</option>
                <option value={15}>15%</option>
                <option value={25}>25%</option>
                <option value={50}>50%</option>
              </select>
            </div>
            <div>
              <div style={{ fontSize: '0.6rem', color: 'var(--text-secondary)', marginBottom: '0.2rem' }}>Max Difficulty</div>
              <select value={mfgMaxDiff} onChange={e => setMfgMaxDiff(Number(e.target.value))} style={selectStyle}>
                {[1, 2, 3, 4, 5].map(d => (
                  <option key={d} value={d}>{d} -- {diffLabel(d)}</option>
                ))}
              </select>
            </div>
            <div>
              <div style={{ fontSize: '0.6rem', color: 'var(--text-secondary)', marginBottom: '0.2rem' }}>Sort By</div>
              <select value={mfgSort} onChange={e => setMfgSort(e.target.value)} style={selectStyle}>
                <option value="profit">Profit</option>
                <option value="roi">ROI</option>
                <option value="volume">Volume</option>
                <option value="sell_price">Sell Price</option>
                <option value="name">Name</option>
              </select>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', paddingBottom: '0.15rem' }}>
              <input
                type="checkbox"
                id="hideNoVol"
                checked={hideNoVolume}
                onChange={e => setHideNoVolume(e.target.checked)}
                style={{ accentColor: '#3fb950' }}
              />
              <label htmlFor="hideNoVol" style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', cursor: 'pointer', whiteSpace: 'nowrap' }}>
                Hide no volume
              </label>
            </div>
            <div style={{ flex: 1, minWidth: 120 }}>
              <div style={{ fontSize: '0.6rem', color: 'var(--text-secondary)', marginBottom: '0.2rem' }}>Search</div>
              <input
                type="text"
                value={mfgSearch}
                onChange={e => setMfgSearch(e.target.value)}
                placeholder="Filter..."
                style={{
                  width: '100%',
                  padding: '0.3rem 0.5rem',
                  background: 'var(--bg-elevated)',
                  border: '1px solid var(--border-color)',
                  borderRadius: 4,
                  color: 'var(--text-primary)',
                  fontSize: '0.78rem',
                  boxSizing: 'border-box',
                }}
              />
            </div>
          </div>

          {mfgLoading ? (
            <div className="skeleton" style={{ height: 300 }} />
          ) : (
            <div style={{
              background: 'var(--bg-secondary)',
              border: '1px solid var(--border-color)',
              borderRadius: 8,
              overflow: 'hidden',
            }}>
              {/* Personalized banner for logged-in users */}
              {isLoggedIn && mfgResults.length > 0 && (() => {
                const topItem = mfgResults[0];
                const topInput: OpportunityInput = {
                  type: 'manufacturing',
                  capitalRequired: topItem.material_cost,
                  estimatedProfit: topItem.profit,
                  blueprintTypeId: topItem.blueprint_id,
                  riskScore: topItem.difficulty * 20,
                };
                return <RecommendationBanner ps={score(topInput)} />;
              })()}
              {/* Table Header */}
              <div style={{
                display: 'grid',
                gridTemplateColumns: isLoggedIn ? '0.3fr 2.5fr 0.6fr 1fr 1fr 1fr 0.6fr' : '2.5fr 0.6fr 1fr 1fr 1fr 0.6fr',
                padding: '0.5rem 0.75rem',
                borderBottom: '1px solid var(--border-color)',
                ...headerStyle,
              }}>
                {isLoggedIn && <span style={{ textAlign: 'center' }}>Fit</span>}
                <span>Product</span>
                <span style={{ textAlign: 'center' }}>Vol</span>
                <span style={{ textAlign: 'right' }}>Cost</span>
                <span style={{ textAlign: 'right' }}>Sell</span>
                <span style={{ textAlign: 'right' }}>Net Profit</span>
                <span style={{ textAlign: 'center' }}>Diff</span>
              </div>

              {mfgResults.length === 0 ? (
                <div style={{
                  padding: '2rem',
                  textAlign: 'center',
                  color: 'var(--text-secondary)',
                  fontSize: '0.85rem',
                }}>
                  No opportunities found
                </div>
              ) : mfgResults.map(item => {
                const mfgInput: OpportunityInput = {
                  type: 'manufacturing',
                  capitalRequired: item.material_cost,
                  estimatedProfit: item.net_profit ?? item.profit,
                  blueprintTypeId: item.blueprint_id,
                  riskScore: (item.avg_daily_volume ?? 0) === 0 ? 90 : (item.risk_score ?? 50),
                };
                const ps = isLoggedIn ? score(mfgInput) : null;
                return (
                <div
                  key={item.product_id}
                  style={{
                    display: 'grid',
                    gridTemplateColumns: isLoggedIn ? '0.3fr 2.5fr 0.6fr 1fr 1fr 1fr 0.6fr' : '2.5fr 0.6fr 1fr 1fr 1fr 0.6fr',
                    padding: '0.4rem 0.75rem',
                    fontSize: '0.8rem',
                    borderBottom: '1px solid rgba(255,255,255,0.03)',
                    alignItems: 'center',
                  }}
                >
                  {/* Personalized score badge */}
                  {isLoggedIn && ps && <div style={{ textAlign: 'center' }}><ScoreBadge score={ps.score} /></div>}
                  {/* Product with icon + name */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', overflow: 'hidden' }}>
                    <img
                      src={`https://images.evetech.net/types/${item.product_id}/icon?size=32`}
                      alt=""
                      style={{ width: 24, height: 24, borderRadius: 3, flexShrink: 0 }}
                      onError={e => { (e.target as HTMLImageElement).style.display = 'none'; }}
                    />
                    <div style={{ overflow: 'hidden' }}>
                      <div style={{
                        fontWeight: 600,
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                        fontSize: '0.8rem',
                      }}>
                        {item.product_name}
                      </div>
                      <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>
                        {item.group_name}
                      </div>
                    </div>
                  </div>

                  {/* Volume indicator */}
                  <div style={{ textAlign: 'center' }}>
                    <span style={{
                      color: (item.avg_daily_volume ?? 0) === 0 ? '#f85149'
                           : (item.avg_daily_volume ?? 0) < 10 ? '#d29922'
                           : '#3fb950',
                      fontFamily: 'monospace',
                      fontSize: '0.7rem',
                      fontWeight: 600,
                    }}>
                      {(item.avg_daily_volume ?? 0) > 0 ? `${item.avg_daily_volume}/d` : 'No Vol'}
                    </span>
                  </div>

                  {/* Cost - red monospace */}
                  <span style={{
                    textAlign: 'right',
                    fontFamily: 'monospace',
                    color: '#f85149',
                  }}>
                    {formatISKCompact(item.material_cost)}
                  </span>

                  {/* Sell - green monospace */}
                  <span style={{
                    textAlign: 'right',
                    fontFamily: 'monospace',
                    color: '#3fb950',
                  }}>
                    {formatISKCompact(item.sell_price)}
                  </span>

                  {/* Net Profit - yellow monospace bold + Net ROI sub-text */}
                  <div style={{ textAlign: 'right' }}>
                    <div style={{
                      fontFamily: 'monospace',
                      color: '#ffcc00',
                      fontWeight: 700,
                    }}>
                      {formatISKCompact(item.net_profit ?? item.profit)}
                    </div>
                    <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>
                      {(item.net_roi ?? item.roi)?.toFixed(0) ?? '0'}% ROI
                    </div>
                  </div>

                  {/* Difficulty badge with graduated color */}
                  <div style={{ textAlign: 'center' }}>
                    <span style={{
                      fontSize: '0.6rem',
                      padding: '2px 6px',
                      borderRadius: 3,
                      background: `${diffColor(item.difficulty)}22`,
                      color: diffColor(item.difficulty),
                      fontWeight: 700,
                    }}>
                      {diffLabel(item.difficulty)}
                    </span>
                  </div>
                </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Trading Opportunities */}
      {subTab === 'trading' && (
        <div>
          {tradLoading ? (
            <div className="skeleton" style={{ height: 300 }} />
          ) : (
            <div style={{
              background: 'var(--bg-secondary)',
              border: '1px solid var(--border-color)',
              borderRadius: 8,
              overflow: 'hidden',
            }}>
              {/* Personalized banner for logged-in users */}
              {isLoggedIn && tradResults.length > 0 && (() => {
                const topTrade = tradResults[0];
                const topInput: OpportunityInput = {
                  type: 'trading',
                  capitalRequired: topTrade.buy_price * topTrade.volume,
                  estimatedProfit: topTrade.profit_per_unit * topTrade.volume,
                  riskScore: topTrade.risk_score * 100,
                };
                return <RecommendationBanner ps={score(topInput)} />;
              })()}
              {/* Table Header */}
              <div style={{
                display: 'grid',
                gridTemplateColumns: isLoggedIn ? '0.3fr 2fr 1fr 1fr 1fr 0.8fr 0.8fr' : '2fr 1fr 1fr 1fr 0.8fr 0.8fr',
                padding: '0.5rem 0.75rem',
                borderBottom: '1px solid var(--border-color)',
                ...headerStyle,
              }}>
                {isLoggedIn && <span style={{ textAlign: 'center' }}>Fit</span>}
                <span>Item</span>
                <span style={{ textAlign: 'right' }}>Buy</span>
                <span style={{ textAlign: 'right' }}>Sell</span>
                <span style={{ textAlign: 'right' }}>Profit</span>
                <span style={{ textAlign: 'right' }}>ROI</span>
                <span style={{ textAlign: 'right' }}>Risk</span>
              </div>

              {tradResults.length === 0 ? (
                <div style={{
                  padding: '2rem',
                  textAlign: 'center',
                  color: 'var(--text-secondary)',
                  fontSize: '0.85rem',
                }}>
                  No trading opportunities found
                </div>
              ) : tradResults.map((item, i) => {
                const tradInput: OpportunityInput = {
                  type: 'trading',
                  capitalRequired: item.buy_price * item.volume,
                  estimatedProfit: item.profit_per_unit * item.volume,
                  riskScore: item.risk_score * 100,
                };
                const tradPs = isLoggedIn ? score(tradInput) : null;
                return (
                <div
                  key={i}
                  style={{
                    display: 'grid',
                    gridTemplateColumns: isLoggedIn ? '0.3fr 2fr 1fr 1fr 1fr 0.8fr 0.8fr' : '2fr 1fr 1fr 1fr 0.8fr 0.8fr',
                    padding: '0.4rem 0.75rem',
                    fontSize: '0.8rem',
                    borderBottom: '1px solid rgba(255,255,255,0.03)',
                    alignItems: 'center',
                  }}
                >
                  {/* Personalized score badge */}
                  {isLoggedIn && tradPs && <div style={{ textAlign: 'center' }}><ScoreBadge score={tradPs.score} /></div>}
                  {/* Item name + hub route */}
                  <div>
                    <div style={{
                      fontWeight: 600,
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}>
                      {item.item_name}
                    </div>
                    <div style={{ fontSize: '0.6rem', color: 'var(--text-secondary)' }}>
                      {item.buy_hub} <span style={{ color: '#58a6ff' }}>{'\u2192'}</span> {item.sell_hub}
                    </div>
                  </div>

                  {/* Buy - red monospace */}
                  <span style={{
                    textAlign: 'right',
                    fontFamily: 'monospace',
                    color: '#f85149',
                  }}>
                    {formatISKCompact(item.buy_price)}
                  </span>

                  {/* Sell - green monospace */}
                  <span style={{
                    textAlign: 'right',
                    fontFamily: 'monospace',
                    color: '#3fb950',
                  }}>
                    {formatISKCompact(item.sell_price)}
                  </span>

                  {/* Profit - yellow bold */}
                  <span style={{
                    textAlign: 'right',
                    fontFamily: 'monospace',
                    color: '#ffcc00',
                    fontWeight: 700,
                  }}>
                    {formatISKCompact(item.profit_per_unit)}
                  </span>

                  {/* ROI - colored by value */}
                  <span style={{
                    textAlign: 'right',
                    fontFamily: 'monospace',
                    color: item.roi >= 50 ? '#3fb950' : item.roi >= 20 ? '#ffcc00' : 'var(--text-primary)',
                  }}>
                    {item.roi.toFixed(1)}%
                  </span>

                  {/* Risk - colored by score */}
                  <span style={{
                    textAlign: 'right',
                    fontWeight: 600,
                    color: item.risk_score < 0.3 ? '#3fb950' : item.risk_score < 0.6 ? '#ffcc00' : '#f85149',
                  }}>
                    {item.risk_score.toFixed(2)}
                  </span>
                </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
