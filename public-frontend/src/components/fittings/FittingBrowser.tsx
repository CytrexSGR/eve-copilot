import { useState, useEffect, useCallback, useRef } from 'react';
import { sdeApi } from '../../services/api/fittings';
import MarketTreeNode from './MarketTreeNode';
import type { MarketGroupNode as MarketGroupNodeType, BrowserTab, SlotType, ModuleSummary } from '../../types/fittings';
import { MARKET_ROOTS, SLOT_COLORS, getTypeIconUrl } from '../../types/fittings';

interface FittingBrowserProps {
  activeTab: BrowserTab;
  onTabChange: (tab: BrowserTab) => void;
  slotFilter: SlotType | null;
  onSlotFilterChange: (slot: SlotType | null) => void;
  shipTypeId: number | null;
  onSelectShip: (typeId: number) => void;
  onSelectModule: (typeId: number, slotType?: string, hardpointType?: string | null) => void;
  onAutoFitModule?: (typeId: number, slotType?: string, hardpointType?: string | null) => void;
  onSelectCharge: (chargeTypeId: number) => void;
}

const TAB_CONFIG: Record<BrowserTab, { label: string; shortLabel: string; rootId: number }> = {
  hulls:   { label: 'Hulls & Fits', shortLabel: 'Hulls',  rootId: MARKET_ROOTS.ships },
  modules: { label: 'Modules',      shortLabel: 'Mods',   rootId: MARKET_ROOTS.modules },
  charges: { label: 'Charges',      shortLabel: 'Ammo',   rootId: MARKET_ROOTS.charges },
  drones:  { label: 'Drones',       shortLabel: 'Drones', rootId: MARKET_ROOTS.drones },
};

const SLOT_FILTERS: { key: SlotType; label: string }[] = [
  { key: 'high', label: 'H' },
  { key: 'mid',  label: 'M' },
  { key: 'low',  label: 'L' },
  { key: 'rig',  label: 'R' },
];

const TABS = Object.keys(TAB_CONFIG) as BrowserTab[];

export default function FittingBrowser({
  activeTab, onTabChange, slotFilter, onSlotFilterChange,
  shipTypeId, onSelectShip, onSelectModule, onAutoFitModule, onSelectCharge,
}: FittingBrowserProps) {
  const [expandedNodes, setExpandedNodes] = useState<Set<number>>(new Set());
  const [childrenCache, setChildrenCache] = useState<Map<number, MarketGroupNodeType[]>>(new Map());
  const [itemsCache, setItemsCache] = useState<Map<number, any[]>>(new Map());
  const [search, setSearch] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [rootNodes, setRootNodes] = useState<MarketGroupNodeType[]>([]);
  const [loading, setLoading] = useState(false);
  const [hoveredResult, setHoveredResult] = useState(-1);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  // Load root children when tab, slot filter, or ship changes
  useEffect(() => {
    const rootId = TAB_CONFIG[activeTab].rootId;
    setLoading(true);
    sdeApi.getMarketTreeChildren({
      category_root: rootId,
      ...(slotFilter && activeTab === 'modules' ? { slot_type: slotFilter } : {}),
      ...(shipTypeId ? { ship_type_id: shipTypeId } : {}),
    }).then(nodes => {
      setRootNodes(nodes);
    }).finally(() => setLoading(false));
    // Reset tree state when filter context changes
    setExpandedNodes(new Set());
    setChildrenCache(new Map());
    setItemsCache(new Map());
    setSearch('');
    setSearchResults([]);
  }, [activeTab, slotFilter, shipTypeId]);

  // Debounced search
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (search.length < 2) {
      setSearchResults([]);
      return;
    }
    debounceRef.current = setTimeout(async () => {
      setLoading(true);
      try {
        let results: any[] = [];
        if (activeTab === 'hulls') {
          results = await sdeApi.getShips({ search, limit: 50 });
        } else if (activeTab === 'modules') {
          results = await sdeApi.getModules({
            search,
            ...(slotFilter ? { slot_type: slotFilter } : {}),
            limit: 50,
          });
        } else if (activeTab === 'drones') {
          results = await sdeApi.getDrones({ search, limit: 50 });
        } else if (activeTab === 'charges') {
          results = await sdeApi.searchCharges({ search, limit: 50 });
        }
        setSearchResults(results);
      } finally {
        setLoading(false);
      }
    }, 300);
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, [search, activeTab, slotFilter]);

  // Tree node callbacks
  const handleToggleNode = useCallback((nodeId: number) => {
    setExpandedNodes(prev => {
      const next = new Set(prev);
      if (next.has(nodeId)) next.delete(nodeId);
      else next.add(nodeId);
      return next;
    });
  }, []);

  const handleChildrenLoaded = useCallback((nodeId: number, children: MarketGroupNodeType[]) => {
    setChildrenCache(prev => new Map(prev).set(nodeId, children));
  }, []);

  const handleItemsLoaded = useCallback((nodeId: number, items: any[]) => {
    setItemsCache(prev => new Map(prev).set(nodeId, items));
  }, []);

  const handleSearchResultClick = useCallback((item: any) => {
    if (activeTab === 'hulls') onSelectShip(item.type_id);
    else if (activeTab === 'charges') onSelectCharge(item.type_id);
    else onSelectModule(item.type_id, item.slot_type, item.hardpoint_type ?? null);
  }, [activeTab, onSelectShip, onSelectModule, onSelectCharge]);

  const handleSearchResultDoubleClick = useCallback((item: any) => {
    if (activeTab === 'hulls') onSelectShip(item.type_id);
    else if (activeTab === 'charges') onSelectCharge(item.type_id);
    else onAutoFitModule?.(item.type_id, item.slot_type, item.hardpoint_type ?? null);
  }, [activeTab, onSelectShip, onAutoFitModule, onSelectCharge]);

  const showTree = search.length < 2;
  const categoryRoot = TAB_CONFIG[activeTab].rootId;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: 'var(--bg-secondary)' }}>
      {/* Tab header */}
      <div style={{
        display: 'flex', borderBottom: '1px solid var(--border-primary)',
        background: 'var(--bg-primary)',
      }}>
        {TABS.map(tab => {
          const active = tab === activeTab;
          return (
            <button
              key={tab}
              onClick={() => onTabChange(tab)}
              style={{
                flex: 1, padding: '8px 4px', border: 'none',
                borderBottom: active ? '2px solid var(--accent-primary)' : '2px solid transparent',
                background: 'transparent', cursor: 'pointer',
                color: active ? 'var(--text-primary)' : 'var(--text-tertiary)',
                fontSize: '0.75rem', fontWeight: active ? 600 : 400,
                transition: 'color 0.15s, border-color 0.15s',
              }}
            >
              {TAB_CONFIG[tab].shortLabel}
            </button>
          );
        })}
      </div>

      {/* Search bar */}
      <div style={{ padding: '6px 8px', borderBottom: '1px solid var(--border-primary)' }}>
        <div style={{ position: 'relative' }}>
          <span style={{
            position: 'absolute', left: 8, top: '50%', transform: 'translateY(-50%)',
            fontSize: '0.75rem', color: 'var(--text-tertiary)', pointerEvents: 'none',
          }}>
            &#x1F50D;
          </span>
          <input
            type="text"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder={`Search ${TAB_CONFIG[activeTab].shortLabel.toLowerCase()}...`}
            style={{
              width: '100%', padding: '6px 8px 6px 28px', border: '1px solid var(--border-primary)',
              borderRadius: 4, background: 'var(--bg-primary)', color: 'var(--text-primary)',
              fontSize: '0.8rem', outline: 'none', boxSizing: 'border-box',
            }}
          />
          {search && (
            <button
              onClick={() => setSearch('')}
              style={{
                position: 'absolute', right: 6, top: '50%', transform: 'translateY(-50%)',
                background: 'none', border: 'none', color: 'var(--text-tertiary)',
                cursor: 'pointer', fontSize: '0.75rem', padding: 2,
              }}
            >
              &#x2715;
            </button>
          )}
        </div>
      </div>

      {/* Slot filter (modules tab only) */}
      {activeTab === 'modules' && (
        <div style={{
          display: 'flex', gap: 4, padding: '4px 8px',
          borderBottom: '1px solid var(--border-primary)', alignItems: 'center',
        }}>
          {SLOT_FILTERS.map(sf => {
            const active = slotFilter === sf.key;
            const color = SLOT_COLORS[sf.key];
            return (
              <button
                key={sf.key}
                onClick={() => onSlotFilterChange(active ? null : sf.key)}
                style={{
                  padding: '2px 10px', border: `1px solid ${active ? color : 'var(--border-primary)'}`,
                  borderRadius: 3, cursor: 'pointer', fontSize: '0.7rem', fontWeight: 600,
                  background: active ? `${color}22` : 'transparent',
                  color: active ? color : 'var(--text-tertiary)',
                  transition: 'all 0.15s',
                }}
              >
                {sf.label}
              </button>
            );
          })}
          {slotFilter && (
            <button
              onClick={() => onSlotFilterChange(null)}
              style={{
                marginLeft: 'auto', padding: '1px 6px', border: 'none',
                background: 'none', color: 'var(--text-tertiary)', cursor: 'pointer',
                fontSize: '0.65rem',
              }}
            >
              &#x2715; clear
            </button>
          )}
        </div>
      )}

      {/* Content area */}
      <div style={{ flex: 1, overflowY: 'auto', minHeight: 0 }}>
        {loading && rootNodes.length === 0 && searchResults.length === 0 && (
          <div style={{ padding: 16, textAlign: 'center', color: 'var(--text-tertiary)', fontSize: '0.8rem' }}>
            Loading...
          </div>
        )}

        {/* Search results (flat list) */}
        {!showTree && search.length >= 2 && (
          <>
            {searchResults.length === 0 && !loading && (
              <div style={{ padding: 16, textAlign: 'center', color: 'var(--text-tertiary)', fontSize: '0.8rem' }}>
                No results for "{search}"
              </div>
            )}
            {searchResults.map((item, i) => (
              <div
                key={item.type_id}
                onClick={() => handleSearchResultClick(item)}
                onDoubleClick={() => handleSearchResultDoubleClick(item)}
                onMouseEnter={() => setHoveredResult(i)}
                onMouseLeave={() => setHoveredResult(-1)}
                style={{
                  display: 'flex', alignItems: 'center', gap: 8,
                  padding: '4px 8px', cursor: 'pointer',
                  background: hoveredResult === i ? 'rgba(255,255,255,0.08)' : 'transparent',
                }}
              >
                <img
                  src={getTypeIconUrl(item.type_id, 32)}
                  alt=""
                  style={{ width: 28, height: 28, borderRadius: 3 }}
                  loading="lazy"
                />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {item.type_name || item.name}
                  </div>
                  {item.group_name && (
                    <div style={{ fontSize: '0.6rem', color: 'var(--text-tertiary)' }}>
                      {item.group_name}
                    </div>
                  )}
                </div>
                {(item as ModuleSummary).meta_level != null && (item as ModuleSummary).meta_level > 0 && (
                  <MetaBadge metaLevel={(item as ModuleSummary).meta_level} />
                )}
              </div>
            ))}
          </>
        )}

        {/* Tree view */}
        {showTree && rootNodes.map(node => (
          <MarketTreeNode
            key={node.market_group_id}
            node={node}
            categoryRoot={categoryRoot}
            depth={0}
            slotType={slotFilter}
            shipTypeId={shipTypeId}
            onSelectShip={onSelectShip}
            onSelectModule={onSelectModule}
            onAutoFitModule={onAutoFitModule}
            onSelectCharge={onSelectCharge}
            expandedNodes={expandedNodes}
            onToggleNode={handleToggleNode}
            childrenCache={childrenCache}
            itemsCache={itemsCache}
            onChildrenLoaded={handleChildrenLoaded}
            onItemsLoaded={handleItemsLoaded}
          />
        ))}
      </div>
    </div>
  );
}

function MetaBadge({ metaLevel }: { metaLevel: number }) {
  const color = metaLevel >= 14 ? '#a855f7' : metaLevel >= 5 ? '#00d4ff' : '#3fb950';
  const bg = metaLevel >= 14
    ? 'rgba(168, 85, 247, 0.15)'
    : metaLevel >= 5
      ? 'rgba(0, 212, 255, 0.15)'
      : 'rgba(63, 185, 80, 0.15)';
  const label = metaLevel >= 14 ? 'Officer' : metaLevel >= 6 ? 'Faction' : metaLevel === 5 ? 'T2' : `M${metaLevel}`;
  return (
    <span style={{
      fontSize: '0.55rem', fontWeight: 700, padding: '1px 4px',
      borderRadius: 3, background: bg, color, whiteSpace: 'nowrap',
    }}>
      {label}
    </span>
  );
}
