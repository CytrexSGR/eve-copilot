import { useState, useCallback, useRef, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { marketApi } from '../services/api/market';
import type { ItemSearchResult, ItemDetail } from '../types/market';
import { CalculatorTab, EconomicsTab, InventionTab, ReactionsTab, PlannerTab, PITab } from '../components/production';

type ProductionTab = 'calculator' | 'economics' | 'invention' | 'reactions' | 'planner' | 'pi';

const TABS: { id: ProductionTab; label: string; icon: string; requiresItem?: boolean }[] = [
  { id: 'economics', label: 'Economics', icon: '\uD83D\uDCC8' },
  { id: 'calculator', label: 'Calculator', icon: '\u2699', requiresItem: true },
  { id: 'planner', label: 'Planner', icon: '\uD83D\uDD17', requiresItem: true },
  { id: 'reactions', label: 'Reactions', icon: '\u269B', requiresItem: true },
  { id: 'invention', label: 'Invention', icon: '\uD83D\uDD2C', requiresItem: true },
  { id: 'pi', label: 'PI', icon: '\uD83C\uDF0D' },
];

export function Production() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [query, setQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const [searchResults, setSearchResults] = useState<ItemSearchResult[]>([]);
  const [selectedItem, setSelectedItem] = useState<ItemSearchResult | null>(null);
  const [itemDetail, setItemDetail] = useState<ItemDetail | null>(null);
  const [showDropdown, setShowDropdown] = useState(false);
  const searchRef = useRef<HTMLDivElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(undefined);
  const lastRestoredTypeId = useRef<number | null>(null);

  const currentTab = (searchParams.get('tab') as ProductionTab) || 'economics';
  const urlTypeId = searchParams.get('typeId');

  const setTab = (tab: ProductionTab) => {
    const p: Record<string, string> = { tab };
    if (selectedItem) p.typeId = String(selectedItem.typeID);
    setSearchParams(p);
  };

  // Restore item from URL typeId (supports browser back/forward)
  useEffect(() => {
    const tid = urlTypeId ? parseInt(urlTypeId, 10) : null;
    if (!tid || isNaN(tid)) return;
    if (selectedItem?.typeID === tid) return;
    if (lastRestoredTypeId.current === tid) return;
    lastRestoredTypeId.current = tid;
    marketApi.getItemDetail(tid).then(detail => {
      const item: ItemSearchResult = { typeID: detail.typeID, typeName: detail.typeName, groupName: detail.groupName };
      setSelectedItem(item);
      setQuery(detail.typeName);
    }).catch(() => {});
  }, [urlTypeId]);

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
    lastRestoredTypeId.current = item.typeID;
    // Switch to calculator tab when item selected (if on a non-item tab)
    const tab = ['calculator', 'invention', 'planner', 'pi'].includes(currentTab) ? currentTab : 'calculator';
    setSearchParams({ tab, typeId: String(item.typeID) });
  }, [currentTab, setSearchParams]);

  const handleNavigateToMaterial = useCallback((typeId: number, typeName: string) => {
    const item: ItemSearchResult = { typeID: typeId, typeName, groupName: '' };
    setSelectedItem(item);
    setQuery(typeName);
    lastRestoredTypeId.current = typeId;
    setSearchParams({ tab: 'calculator', typeId: String(typeId) });
  }, [setSearchParams]);

  // Check if current tab requires an item but none is selected
  const tabDef = TABS.find(t => t.id === currentTab);
  const needsItem = tabDef?.requiresItem && !selectedItem;

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto', padding: '1.5rem 1rem' }}>
      {/* Hero */}
      <div style={{ marginBottom: '1.5rem' }}>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 700, margin: '0 0 0.25rem 0' }}>
          Production Suite
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', margin: 0 }}>
          Manufacturing, invention, and reactions
        </p>
      </div>

      {/* Search Bar */}
      <div ref={searchRef} style={{ position: 'relative', marginBottom: '1rem' }}>
        <input
          type="text"
          value={query}
          onChange={e => setQuery(e.target.value)}
          onFocus={() => searchResults.length > 0 && setShowDropdown(true)}
          placeholder="Search items... (e.g. Tritanium, Drake, Large Shield Extender II)"
          style={{
            width: '100%',
            padding: '12px 16px',
            fontSize: '1rem',
            background: 'var(--bg-secondary)',
            border: '1px solid var(--border-color)',
            borderRadius: '8px',
            color: 'var(--text-primary)',
            outline: 'none',
            boxSizing: 'border-box',
          }}
        />
        {showDropdown && searchResults.length > 0 && (
          <div style={{
            position: 'absolute', top: '100%', left: 0, right: 0,
            maxHeight: 320, overflowY: 'auto',
            background: 'var(--bg-secondary)',
            border: '1px solid var(--border-color)',
            borderTop: 'none', borderRadius: '0 0 8px 8px',
            zIndex: 100,
          }}>
            {searchResults.slice(0, 20).map(item => (
              <div
                key={item.typeID}
                onClick={() => handleSelectItem(item)}
                style={{
                  padding: '10px 16px', cursor: 'pointer',
                  display: 'flex', alignItems: 'center', gap: '10px',
                  borderBottom: '1px solid rgba(255,255,255,0.05)',
                }}
                onMouseEnter={e => (e.currentTarget.style.background = 'var(--bg-elevated)')}
                onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
              >
                <img src={`https://images.evetech.net/types/${item.typeID}/icon?size=32`} alt="" style={{ width: 32, height: 32, borderRadius: 4 }} onError={e => { (e.target as HTMLImageElement).style.display = 'none'; }} />
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: '0.9rem', fontWeight: 600 }}>{item.typeName}</div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>{item.groupName}</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Selected Item Header */}
      {selectedItem && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: '1rem',
          marginBottom: '1rem', padding: '0.75rem 1rem',
          background: 'var(--bg-secondary)',
          border: '1px solid var(--border-color)', borderRadius: '8px',
        }}>
          <img
            src={`https://images.evetech.net/types/${selectedItem.typeID}/icon?size=64`}
            alt={selectedItem.typeName}
            style={{ width: 48, height: 48, borderRadius: 8 }}
            onError={e => { (e.target as HTMLImageElement).style.display = 'none'; }}
          />
          <div style={{ flex: 1 }}>
            <h2 style={{ margin: '0 0 0.15rem 0', fontSize: '1.1rem' }}>{selectedItem.typeName}</h2>
            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
              <span style={{
                fontSize: '0.65rem', padding: '2px 8px',
                background: 'rgba(0,212,255,0.1)', border: '1px solid rgba(0,212,255,0.3)',
                borderRadius: 3, color: '#00d4ff',
              }}>{selectedItem.groupName}</span>
              {itemDetail && (
                <span style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>
                  {itemDetail.categoryName} · {itemDetail.volume?.toFixed(2)} m³
                </span>
              )}
            </div>
          </div>
          <button
            onClick={() => setTab('planner')}
            style={{
              background: 'rgba(0,212,255,0.1)', border: '1px solid rgba(0,212,255,0.3)',
              color: '#00d4ff', padding: '4px 10px',
              borderRadius: 4, cursor: 'pointer', fontSize: '0.75rem', fontWeight: 600,
            }}
          >Full Chain</button>
          <button
            onClick={() => { setSelectedItem(null); setQuery(''); setItemDetail(null); }}
            style={{
              background: 'transparent', border: '1px solid var(--border-color)',
              color: 'var(--text-secondary)', padding: '4px 10px',
              borderRadius: 4, cursor: 'pointer', fontSize: '0.75rem',
            }}
          >Clear</button>
        </div>
      )}

      {/* Tab Navigation */}
      <div style={{
        display: 'flex', gap: '0.25rem', marginBottom: '1rem',
        borderBottom: '1px solid var(--border-color)', paddingBottom: '0.5rem',
      }}>
        {TABS.map(tab => (
          <button
            key={tab.id}
            onClick={() => setTab(tab.id)}
            style={{
              padding: '0.5rem 1rem',
              background: 'transparent',
              border: 'none',
              borderBottom: currentTab === tab.id ? '2px solid #00d4ff' : '2px solid transparent',
              color: currentTab === tab.id ? '#00d4ff' : 'var(--text-secondary)',
              cursor: 'pointer',
              fontSize: '0.85rem',
              fontWeight: currentTab === tab.id ? 600 : 400,
              display: 'flex', alignItems: 'center', gap: '0.3rem',
              opacity: tab.requiresItem && !selectedItem ? 0.4 : 1,
            }}
            disabled={tab.requiresItem && !selectedItem}
          >
            <span>{tab.icon}</span>
            <span>{tab.label}</span>
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {needsItem ? (
        <div style={{ textAlign: 'center', padding: '3rem 1rem', color: 'var(--text-secondary)' }}>
          <p style={{ fontSize: '1rem', marginBottom: '0.5rem' }}>Search and select an item above to view {tabDef?.label.toLowerCase()}</p>
        </div>
      ) : (
        <>
          {currentTab === 'calculator' && selectedItem && <CalculatorTab selectedItem={selectedItem} onNavigateToMaterial={handleNavigateToMaterial} />}
          {currentTab === 'economics' && <EconomicsTab onNavigateToItem={handleNavigateToMaterial} />}
          {currentTab === 'invention' && selectedItem && <InventionTab selectedItem={selectedItem} />}
          {currentTab === 'reactions' && selectedItem && <ReactionsTab selectedItem={selectedItem} />}
          {currentTab === 'planner' && selectedItem && <PlannerTab selectedItem={selectedItem} onNavigateToMaterial={handleNavigateToMaterial} />}
          {currentTab === 'pi' && <PITab selectedItem={selectedItem} />}
        </>
      )}
    </div>
  );
}
