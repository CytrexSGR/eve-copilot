import { useState, useEffect } from 'react';
import { marketApi } from '../../services/api/market';
import { HOT_ITEM_NAMES } from '../../types/market';
import { formatISKCompact } from '../../utils/format';
import type { HotItemCategories } from '../../types/market';

interface TickerItem {
  id: string;
  name: string;
  price: number;
  category: string;
}

const CATEGORY_COLORS: Record<string, string> = {
  minerals: '#3fb950',
  isotopes: '#00d4ff',
  fuel_blocks: '#ff8800',
  moon_materials: '#a855f7',
  salvage: '#ffcc00',
};

export function MarketTicker() {
  const [items, setItems] = useState<TickerItem[]>([]);
  const [isPaused, setIsPaused] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = () => {
      marketApi.getHotItemsByCategory()
        .then((hotItems: HotItemCategories) => {
          const tickerItems: TickerItem[] = [];
          for (const [category, categoryItems] of Object.entries(hotItems)) {
            for (const [typeId, price] of Object.entries(categoryItems)) {
              const name = HOT_ITEM_NAMES[Number(typeId)];
              if (name && price.sell_price > 0) {
                tickerItems.push({ id: typeId, name, price: price.sell_price, category });
              }
            }
          }
          tickerItems.sort((a, b) => b.price - a.price);
          setItems(tickerItems.slice(0, 30));
        })
        .catch(() => {})
        .finally(() => setLoading(false));
    };

    fetchData();
    const interval = setInterval(fetchData, 60000);
    return () => clearInterval(interval);
  }, []);

  if (loading || items.length === 0) {
    return <div style={{ height: '36px', background: 'var(--bg-elevated)', borderRadius: '4px', marginBottom: '0.75rem' }} />;
  }

  const duplicatedItems = [...items, ...items];

  return (
    <div style={{ marginBottom: '0.75rem' }}>
      <div style={{
        position: 'relative', overflow: 'hidden',
        background: 'var(--bg-elevated)', borderRadius: '4px', height: '36px',
      }}
        onMouseEnter={() => setIsPaused(true)}
        onMouseLeave={() => setIsPaused(false)}
      >
        {/* Gradient overlays */}
        <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: '40px', background: 'linear-gradient(to right, var(--bg-elevated), transparent)', zIndex: 2, pointerEvents: 'none' }} />
        <div style={{ position: 'absolute', right: 0, top: 0, bottom: 0, width: '40px', background: 'linear-gradient(to left, var(--bg-elevated), transparent)', zIndex: 2, pointerEvents: 'none' }} />

        <div style={{
          display: 'flex', alignItems: 'center', height: '100%',
          animation: isPaused ? 'none' : `marketTicker ${Math.max(items.length * 3, 20)}s linear infinite`,
          whiteSpace: 'nowrap',
        }}>
          {duplicatedItems.map((item, index) => {
            const catColor = CATEGORY_COLORS[item.category] || '#8b949e';
            return (
              <div key={`${item.id}-${index}`} style={{
                display: 'inline-flex', alignItems: 'center', gap: '0.4rem',
                padding: '0 1.2rem', borderRight: '1px solid var(--border-color)', height: '100%',
              }}>
                <img src={`https://images.evetech.net/types/${item.id}/icon?size=32`} alt="" style={{ width: 20, height: 20, borderRadius: 2 }} />
                <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-primary)' }}>{item.name}</span>
                <span style={{ fontSize: '0.75rem', fontWeight: 700, fontFamily: 'monospace', color: '#3fb950' }}>
                  {formatISKCompact(item.price)}
                </span>
                <span style={{
                  fontSize: '0.55rem', fontWeight: 700, padding: '1px 4px', borderRadius: 2,
                  background: `${catColor}22`, color: catColor, textTransform: 'uppercase',
                }}>
                  {item.category.replace(/_/g, ' ')}
                </span>
              </div>
            );
          })}
        </div>

        <style>{`
          @keyframes marketTicker {
            0% { transform: translateX(0); }
            100% { transform: translateX(-50%); }
          }
        `}</style>
      </div>
    </div>
  );
}
