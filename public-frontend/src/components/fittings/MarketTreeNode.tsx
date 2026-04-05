import { useState, useCallback } from 'react';
import { sdeApi } from '../../services/api/fittings';
import type { MarketGroupNode as MarketGroupNodeType, ModuleSummary } from '../../types/fittings';
import { getTypeIconUrl, MARKET_ROOTS } from '../../types/fittings';

interface MarketTreeNodeProps {
  node: MarketGroupNodeType;
  categoryRoot: number;
  depth: number;
  slotType?: string | null;
  shipTypeId?: number | null;
  onSelectShip?: (typeId: number) => void;
  onSelectModule?: (typeId: number, slotType?: string, hardpointType?: string | null) => void;
  onAutoFitModule?: (typeId: number, slotType?: string, hardpointType?: string | null) => void;
  onSelectCharge?: (chargeTypeId: number) => void;
  expandedNodes: Set<number>;
  onToggleNode: (nodeId: number) => void;
  childrenCache: Map<number, MarketGroupNodeType[]>;
  itemsCache: Map<number, any[]>;
  onChildrenLoaded: (nodeId: number, children: MarketGroupNodeType[]) => void;
  onItemsLoaded: (nodeId: number, items: any[]) => void;
}

function MetaBadge({ metaLevel }: { metaLevel: number }) {
  if (metaLevel <= 0) return null;
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
      borderRadius: 3, background: bg, color, marginLeft: 4, whiteSpace: 'nowrap',
    }}>
      {label}
    </span>
  );
}

export default function MarketTreeNode({
  node, categoryRoot, depth, slotType, shipTypeId,
  onSelectShip, onSelectModule, onAutoFitModule, onSelectCharge,
  expandedNodes, onToggleNode, childrenCache, itemsCache,
  onChildrenLoaded, onItemsLoaded,
}: MarketTreeNodeProps) {
  const [loading, setLoading] = useState(false);
  const [hovered, setHovered] = useState(-1);
  const expanded = expandedNodes.has(node.market_group_id);
  const hasChildren = node.child_count > 0 || node.has_types;

  const handleToggle = useCallback(async () => {
    onToggleNode(node.market_group_id);
    if (expanded || loading) return;

    const id = node.market_group_id;
    if (node.has_types && !itemsCache.has(id)) {
      setLoading(true);
      try {
        const items = await sdeApi.getMarketTreeItems({
          market_group_id: id, category_root: categoryRoot,
          ...(slotType ? { slot_type: slotType } : {}),
          ...(shipTypeId ? { ship_type_id: shipTypeId } : {}),
        });
        onItemsLoaded(id, items);
      } finally { setLoading(false); }
    } else if (!node.has_types && !childrenCache.has(id)) {
      setLoading(true);
      try {
        const children = await sdeApi.getMarketTreeChildren({
          category_root: categoryRoot, parent_id: id,
          ...(slotType ? { slot_type: slotType } : {}),
          ...(shipTypeId ? { ship_type_id: shipTypeId } : {}),
        });
        onChildrenLoaded(id, children);
      } finally { setLoading(false); }
    }
  }, [expanded, loading, node, categoryRoot, slotType, shipTypeId, itemsCache, childrenCache, onToggleNode, onItemsLoaded, onChildrenLoaded]);

  const handleItemClick = useCallback((item: any) => {
    if (categoryRoot === MARKET_ROOTS.ships) onSelectShip?.(item.type_id);
    else if (categoryRoot === MARKET_ROOTS.charges) onSelectCharge?.(item.type_id);
    else onSelectModule?.(item.type_id, item.slot_type, item.hardpoint_type ?? null);
  }, [categoryRoot, onSelectShip, onSelectModule, onSelectCharge]);

  const handleItemDoubleClick = useCallback((item: any) => {
    if (categoryRoot === MARKET_ROOTS.ships) onSelectShip?.(item.type_id);
    else if (categoryRoot === MARKET_ROOTS.charges) onSelectCharge?.(item.type_id);
    else onAutoFitModule?.(item.type_id, item.slot_type, item.hardpoint_type ?? null);
  }, [categoryRoot, onSelectShip, onAutoFitModule, onSelectCharge]);

  const isModule = categoryRoot === MARKET_ROOTS.modules || categoryRoot === MARKET_ROOTS.drones;
  const children = childrenCache.get(node.market_group_id);
  const items = itemsCache.get(node.market_group_id);

  return (
    <div>
      {/* Node row */}
      <div
        onClick={handleToggle}
        style={{
          display: 'flex', alignItems: 'center', padding: '4px 8px',
          paddingLeft: depth * 16 + 8, cursor: 'pointer',
          background: hovered === -2 ? 'rgba(255,255,255,0.05)' : 'transparent',
        }}
        onMouseEnter={() => setHovered(-2)}
        onMouseLeave={() => setHovered(-1)}
      >
        <span style={{ width: 16, fontSize: '0.7rem', color: 'var(--text-tertiary)', flexShrink: 0 }}>
          {hasChildren ? (expanded ? '\u25BC' : '\u25B6') : ''}
        </span>
        <span style={{ fontSize: '0.8rem', color: 'var(--text-primary)', flex: 1 }}>
          {node.name}
        </span>
        {/* No counts displayed — matches EVE client behavior */}
      </div>

      {/* Expanded content */}
      {expanded && (
        <div>
          {loading && (
            <div style={{ paddingLeft: (depth + 1) * 16 + 8, padding: '4px 8px', fontSize: '0.75rem', color: 'var(--text-tertiary)' }}>
              Loading...
            </div>
          )}

          {/* Branch: child nodes */}
          {!node.has_types && children?.map(child => (
            <MarketTreeNode
              key={child.market_group_id}
              node={child}
              categoryRoot={categoryRoot}
              depth={depth + 1}
              slotType={slotType}
              shipTypeId={shipTypeId}
              onSelectShip={onSelectShip}
              onSelectModule={onSelectModule}
              onAutoFitModule={onAutoFitModule}
              onSelectCharge={onSelectCharge}
              expandedNodes={expandedNodes}
              onToggleNode={onToggleNode}
              childrenCache={childrenCache}
              itemsCache={itemsCache}
              onChildrenLoaded={onChildrenLoaded}
              onItemsLoaded={onItemsLoaded}
            />
          ))}

          {/* Leaf: empty state */}
          {node.has_types && !loading && items && items.length === 0 && (
            <div style={{
              paddingLeft: (depth + 1) * 16 + 8, padding: '4px 8px',
              fontSize: '0.75rem', color: 'var(--text-tertiary)', fontStyle: 'italic',
            }}>
              No items
            </div>
          )}

          {/* Leaf: item rows */}
          {node.has_types && items?.map((item, i) => (
            <div
              key={item.type_id}
              onClick={() => handleItemClick(item)}
              onDoubleClick={() => handleItemDoubleClick(item)}
              onMouseEnter={() => setHovered(i)}
              onMouseLeave={() => setHovered(-1)}
              style={{
                display: 'flex', alignItems: 'center', gap: 8,
                padding: '3px 8px', paddingLeft: (depth + 1) * 16 + 8,
                cursor: 'pointer',
                background: hovered === i ? 'rgba(255,255,255,0.08)' : 'transparent',
              }}
            >
              <img
                src={getTypeIconUrl(item.type_id, 32)}
                alt=""
                style={{ width: 28, height: 28, borderRadius: 3 }}
                loading="lazy"
              />
              <span style={{ fontSize: '0.8rem', color: 'var(--text-primary)', flex: 1 }}>
                {item.type_name || item.name}
              </span>
              {isModule && (item as ModuleSummary).meta_level != null && (
                <MetaBadge metaLevel={(item as ModuleSummary).meta_level} />
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
