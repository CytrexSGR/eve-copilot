import { useState, useEffect } from 'react';
import { marketApi } from '../../services/api/market';
import type { HotItemCategories } from '../../types/market';

interface MarketSummary {
  totalItems: number;
  avgSpread: number;
}

export function MarketHeroSection() {
  const [summary, setSummary] = useState<MarketSummary | null>(null);

  useEffect(() => {
    marketApi.getHotItemsByCategory().then((hotItems: HotItemCategories) => {
      let totalItems = 0;
      let spreadSum = 0;
      let spreadCount = 0;

      for (const [, items] of Object.entries(hotItems)) {
        for (const [, price] of Object.entries(items)) {
          totalItems++;
          if (price.sell_price > 0 && price.buy_price > 0) {
            const spread = ((price.sell_price - price.buy_price) / price.sell_price) * 100;
            spreadSum += spread;
            spreadCount++;
          }
        }
      }

      setSummary({
        totalItems,
        avgSpread: spreadCount > 0 ? spreadSum / spreadCount : 0,
      });
    }).catch(() => {});
  }, []);

  return (
    <>
      <div style={{
        position: 'relative',
        background: 'linear-gradient(135deg, #0a0f1a 0%, #1a1f2e 50%, #0d1520 100%)',
        borderRadius: '8px',
        padding: '0.75rem 1rem',
        marginBottom: '0.75rem',
        border: '1px solid rgba(63, 185, 80, 0.2)',
        overflow: 'hidden',
      }}>
        {/* Glowing corner accent (green for market) */}
        <div style={{
          position: 'absolute', top: 0, right: 0, width: '200px', height: '200px',
          background: 'radial-gradient(circle at top right, rgba(63,185,80,0.15) 0%, transparent 70%)',
          pointerEvents: 'none',
        }} />

        {/* Single Row Layout */}
        <div style={{ position: 'relative', display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
          {/* Title */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
            <span style={{ fontSize: '1.5rem' }}>📊</span>
            <h1 style={{
              margin: 0, fontSize: '1.5rem', fontWeight: 800,
              background: 'linear-gradient(135deg, #fff 0%, #a0ffc4 100%)',
              WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
              letterSpacing: '0.03em', textTransform: 'uppercase', whiteSpace: 'nowrap',
            }}>
              Market Suite
            </h1>
            <span style={{
              display: 'flex', alignItems: 'center', gap: '3px',
              padding: '2px 6px', background: 'rgba(0,255,136,0.15)',
              border: '1px solid rgba(0,255,136,0.3)', borderRadius: '999px',
              fontSize: '0.75rem', fontWeight: 700, color: '#00ff88', textTransform: 'uppercase',
            }}>
              <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#00ff88', animation: 'pulse 2s infinite' }} />
              Live
            </span>
          </div>

          {/* Divider */}
          <div style={{ width: '1px', height: '32px', background: 'rgba(255,255,255,0.1)' }} />

          {/* Stats */}
          <div style={{ display: 'flex', alignItems: 'center', flex: 1 }}>
            <StatBox value={String(summary?.totalItems || '—')} label="Items" color="#3fb950" />
            <StatBox value={summary ? `${summary.avgSpread.toFixed(1)}%` : '—'} label="Spread" color="#ffcc00" />
            <StatBox value="5" label="Hubs" color="#00d4ff" />
          </div>

          {/* Market Health */}
          <div style={{
            display: 'flex', alignItems: 'center', gap: '0.45rem',
            padding: '0.3rem 0.6rem', background: 'rgba(0,0,0,0.3)', borderRadius: '4px',
          }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase' }}>Health</span>
            <span style={{ fontSize: '0.9rem', fontWeight: 800, color: '#3fb950' }}>ACTIVE</span>
          </div>
        </div>

        {/* Quick Intel footer */}
        <div style={{ display: 'flex', gap: '1.15rem', marginTop: '0.45rem', fontSize: '0.8rem', color: 'rgba(255,255,255,0.35)' }}>
          <span>📈 Prices from <span style={{ color: '#3fb950' }}>Jita, Amarr, Rens, Dodixie, Hek</span></span>
          <span>🔄 Updates every <span style={{ color: '#ffcc00' }}>15 min</span></span>
        </div>
      </div>

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.5; transform: scale(1.2); }
        }
      `}</style>
    </>
  );
}

function StatBox({ value, label, color }: { value: string; label: string; color: string }) {
  return (
    <div style={{ padding: '0 0.7rem', borderRight: '1px solid rgba(255,255,255,0.06)' }}>
      <span style={{ fontSize: '1.25rem', fontWeight: 800, color, fontFamily: 'monospace' }}>{value}</span>
      <span style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', marginLeft: '5px' }}>{label}</span>
    </div>
  );
}
