import { useState, useCallback, useRef, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { marketApi } from '../services/api/market';
import { ModuleGate } from '../components/ModuleGate';
import { HOT_ITEM_NAMES } from '../types/market';
import type { ItemSearchResult, ItemDetail, HotItemCategories } from '../types/market';
import { formatISK } from '../utils/format';
import {
  PricesTab, HistoryTab, ArbitrageTab, OpportunitiesTab, PortfolioTab,
  MarketHeroSection, MarketTicker, MarketTabNavigation,
} from '../components/market';
import type { MarketTab } from '../components/market/MarketTabNavigation';

const CATEGORY_COLORS: Record<string, string> = {
  minerals: '#3fb950',
  isotopes: '#00d4ff',
  fuel_blocks: '#ff8800',
  moon_materials: '#a855f7',
  salvage: '#ffcc00',
  pi_commodities: '#f85149',
  ice_products: '#58a6ff',
  gas: '#d29922',
};

export function Market() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [query, setQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const [searchResults, setSearchResults] = useState<ItemSearchResult[]>([]);
  const [selectedItem, setSelectedItem] = useState<ItemSearchResult | null>(null);
  const [itemDetail, setItemDetail] = useState<ItemDetail | null>(null);
  const [hotItems, setHotItems] = useState<HotItemCategories | null>(null);
  const [hotLoading, setHotLoading] = useState(true);
  const [showDropdown, setShowDropdown] = useState(false);
  const searchRef = useRef<HTMLDivElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  const currentTab = (searchParams.get('tab') as MarketTab) || 'prices';

  const setTab = (tab: MarketTab) => {
    setSearchParams({ tab });
  };

  // Debounced search
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (query.length < 2) { setSearchResults([]); return; }
    debounceRef.current = setTimeout(() => setDebouncedQuery(query), 300);
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, [query]);

  // Fetch search results
  useEffect(() => {
    if (debouncedQuery.length < 2) return;
    marketApi.searchItems(debouncedQuery)
      .then(data => { setSearchResults(data.results); setShowDropdown(true); })
      .catch(() => {});
  }, [debouncedQuery]);

  // Fetch hot items on mount
  useEffect(() => {
    marketApi.getHotItemsByCategory()
      .then(setHotItems)
      .catch(() => {})
      .finally(() => setHotLoading(false));
  }, []);

  // Fetch item detail when item selected
  useEffect(() => {
    if (!selectedItem) return;
    setItemDetail(null);
    marketApi.getItemDetail(selectedItem.typeID)
      .then(setItemDetail)
      .catch(() => {});
  }, [selectedItem]);

  // Close dropdown on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) {
        setShowDropdown(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const handleSelectItem = useCallback((item: ItemSearchResult) => {
    setSelectedItem(item);
    setQuery(item.typeName);
    setShowDropdown(false);
    if (!['prices', 'history'].includes(currentTab)) {
      setTab('prices');
    }
  }, [currentTab]);

  const handleSelectHotItem = useCallback((typeId: number, category: string) => {
    const name = HOT_ITEM_NAMES[typeId] || `Type ${typeId}`;
    handleSelectItem({ typeID: typeId, typeName: name, groupName: category.replace(/_/g, ' ') });
  }, [handleSelectItem]);

  const tabDef = [
    { id: 'prices' as const, requiresItem: true },
    { id: 'history' as const, requiresItem: true },
    { id: 'arbitrage' as const },
    { id: 'opportunities' as const },
    { id: 'portfolio' as const },
  ].find(t => t.id === currentTab);
  const needsItem = tabDef?.requiresItem && !selectedItem;

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto', padding: '1.5rem 1rem' }}>
      {/* Hero Section */}
      <MarketHeroSection />

      {/* Scrolling Ticker */}
      <MarketTicker />

      {/* Search + Item Selection Control Bar */}
      <div ref={searchRef} style={{
        display: 'flex', alignItems: 'center', gap: '0.5rem',
        padding: '0.35rem 0.5rem', background: 'rgba(0,0,0,0.3)',
        borderRadius: '6px', border: '1px solid rgba(255,255,255,0.05)',
        marginBottom: '0.75rem', position: 'relative',
      }}>
        <span style={{
          fontSize: '0.65rem', color: 'rgba(255,255,255,0.3)',
          textTransform: 'uppercase', fontWeight: 700, letterSpacing: '0.05em',
          flexShrink: 0,
        }}>Search</span>
        <input
          type="text"
          value={query}
          onChange={e => setQuery(e.target.value)}
          onFocus={() => searchResults.length > 0 && setShowDropdown(true)}
          placeholder="Tritanium, Drake, Large Shield Extender II..."
          style={{
            flex: 1, minWidth: 0,
            padding: '0.3rem 0.5rem', fontSize: '0.82rem',
            background: 'rgba(255,255,255,0.04)',
            border: '1px solid rgba(255,255,255,0.08)',
            borderRadius: '4px', color: '#fff', outline: 'none',
          }}
        />

        {/* Selected item inline display */}
        {selectedItem && (
          <>
            <div style={{ width: '1px', height: '24px', background: 'rgba(255,255,255,0.1)', flexShrink: 0 }} />
            <img
              src={`https://images.evetech.net/types/${selectedItem.typeID}/icon?size=32`}
              alt=""
              style={{ width: 24, height: 24, borderRadius: 3, flexShrink: 0 }}
            />
            <span style={{ fontWeight: 700, fontSize: '0.85rem', whiteSpace: 'nowrap' }}>
              {selectedItem.typeName}
            </span>
            <span style={{
              padding: '2px 6px', borderRadius: '3px', fontSize: '0.6rem', fontWeight: 700,
              background: 'rgba(0,212,255,0.1)', border: '1px solid rgba(0,212,255,0.3)',
              color: '#00d4ff', whiteSpace: 'nowrap', textTransform: 'uppercase',
            }}>
              {selectedItem.groupName}
            </span>
            {itemDetail && (
              <span style={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.35)', whiteSpace: 'nowrap' }}>
                {itemDetail.volume?.toFixed(1)} m³
              </span>
            )}
            <button
              onClick={() => { setSelectedItem(null); setQuery(''); setItemDetail(null); }}
              style={{
                background: 'rgba(248,81,73,0.1)', border: '1px solid rgba(248,81,73,0.3)',
                color: '#f85149', padding: '2px 6px', borderRadius: '3px',
                fontSize: '0.7rem', fontWeight: 700, cursor: 'pointer', flexShrink: 0,
              }}
            >✕</button>
          </>
        )}

        {/* Search dropdown */}
        {showDropdown && searchResults.length > 0 && (
          <div style={{
            position: 'absolute', top: '100%', left: 0, right: 0,
            maxHeight: 320, overflowY: 'auto',
            background: '#111827',
            border: '1px solid var(--border-color)',
            borderTop: 'none', borderRadius: '0 0 8px 8px',
            zIndex: 100, marginTop: '2px',
            boxShadow: '0 8px 24px rgba(0,0,0,0.5)',
          }}>
            {searchResults.slice(0, 20).map(item => (
              <div
                key={item.typeID}
                onClick={() => handleSelectItem(item)}
                style={{
                  padding: '0.5rem 0.75rem', cursor: 'pointer',
                  display: 'flex', alignItems: 'center', gap: '0.5rem',
                  borderBottom: '1px solid rgba(255,255,255,0.04)',
                }}
                onMouseEnter={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.05)')}
                onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
              >
                <img
                  src={`https://images.evetech.net/types/${item.typeID}/icon?size=32`}
                  alt=""
                  style={{ width: 28, height: 28, borderRadius: 3 }}
                />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: '0.82rem', fontWeight: 600 }}>{item.typeName}</div>
                  <div style={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.35)' }}>{item.groupName}</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Tab Navigation */}
      <MarketTabNavigation
        activeTab={currentTab}
        onTabChange={setTab}
        hasSelectedItem={!!selectedItem}
      />

      {/* Tab Content */}
      <ModuleGate module="market_analysis" preview={true}>
        {needsItem ? (
          <div style={{
            textAlign: 'center', padding: '3rem 1rem',
            color: 'rgba(255,255,255,0.3)', fontSize: '0.85rem',
          }}>
            Search and select an item above to view {tabDef?.id === 'prices' ? 'prices' : 'order book'}
          </div>
        ) : (
          <>
            {currentTab === 'prices' && selectedItem && (
              <PricesTab selectedItem={selectedItem} itemDetail={itemDetail} />
            )}
            {currentTab === 'history' && selectedItem && (
              <HistoryTab selectedItem={selectedItem} />
            )}
            {currentTab === 'arbitrage' && <ArbitrageTab />}
            {currentTab === 'opportunities' && <OpportunitiesTab />}
            {currentTab === 'portfolio' && <PortfolioTab />}
          </>
        )}
      </ModuleGate>

      {/* Hot Items Landing */}
      {!selectedItem && currentTab === 'prices' && (
        <div style={{ marginTop: '1rem' }}>
          {hotLoading ? (
            <div className="skeleton" style={{ height: 300 }} />
          ) : hotItems && Object.entries(hotItems).map(([category, items]) => {
            const catColor = CATEGORY_COLORS[category] || '#8b949e';
            return (
              <div key={category} style={{ marginBottom: '1.25rem' }}>
                {/* Category header */}
                <div style={{
                  display: 'flex', alignItems: 'center', gap: '0.5rem',
                  marginBottom: '0.5rem',
                }}>
                  <span style={{
                    fontSize: '0.65rem', fontWeight: 700, textTransform: 'uppercase',
                    color: catColor, letterSpacing: '0.06em',
                  }}>
                    {category.replace(/_/g, ' ')}
                  </span>
                  <div style={{ flex: 1, height: '1px', background: `${catColor}22` }} />
                  <span style={{
                    fontSize: '0.6rem', color: 'rgba(255,255,255,0.25)',
                  }}>
                    {Object.keys(items).length} items
                  </span>
                </div>

                {/* Dense grid */}
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
                  gap: '0.35rem',
                }}>
                  {Object.entries(items).slice(0, 8).map(([typeId, price]) => {
                    const name = HOT_ITEM_NAMES[Number(typeId)] || `Type ${typeId}`;
                    return (
                      <div
                        key={typeId}
                        onClick={() => handleSelectHotItem(Number(typeId), category)}
                        style={{
                          padding: '0.4rem 0.6rem',
                          background: 'rgba(0,0,0,0.2)',
                          border: '1px solid rgba(255,255,255,0.05)',
                          borderRadius: '4px', cursor: 'pointer',
                          display: 'flex', alignItems: 'center', gap: '0.4rem',
                          transition: 'border-color 0.15s',
                        }}
                        onMouseEnter={e => (e.currentTarget.style.borderColor = `${catColor}44`)}
                        onMouseLeave={e => (e.currentTarget.style.borderColor = 'rgba(255,255,255,0.05)')}
                      >
                        <img
                          src={`https://images.evetech.net/types/${typeId}/icon?size=32`}
                          alt=""
                          style={{ width: 22, height: 22, borderRadius: 2, flexShrink: 0 }}
                        />
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{
                            fontSize: '0.72rem', fontWeight: 600,
                            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                          }}>
                            {name}
                          </div>
                        </div>
                        <span style={{
                          fontSize: '0.72rem', fontFamily: 'monospace',
                          color: '#3fb950', fontWeight: 600, whiteSpace: 'nowrap',
                        }}>
                          {formatISK(price.sell_price)}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
