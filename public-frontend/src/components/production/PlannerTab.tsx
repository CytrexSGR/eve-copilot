import { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { productionApi, projectApi } from '../../services/api/production';
import { marketApi } from '../../services/api/market';
import { formatISK } from '../../utils/format';
import type { MaterialChain, ChainNode } from '../../types/production';
import type { ItemSearchResult } from '../../types/market';

interface Props {
  selectedItem: ItemSearchResult;
  onNavigateToMaterial?: (typeId: number, typeName: string) => void;
  projectItemId?: number;
  onDecisionsChanged?: (overrides: Set<number>, shoppingItems: ShoppingItem[]) => void;
}

interface ShoppingItem {
  type_id: number;
  name: string;
  quantity: number;
  is_component: boolean;
}

/** Collect shopping items respecting buy overrides. If a BUILD node is overridden to BUY,
 *  it becomes a shopping item itself and its subtree is not walked. */
function collectShoppingItems(node: ChainNode, buyOverrides: Set<number>, parentKey: string): ShoppingItem[] {
  const key = `${parentKey}-${node.type_id}`;

  if (node.is_manufacturable && node.children?.length > 0 && buyOverrides.has(node.type_id)) {
    return [{ type_id: node.type_id, name: node.name, quantity: node.quantity, is_component: true }];
  }

  if (!node.children?.length) {
    if (!node.is_manufacturable) {
      return [{ type_id: node.type_id, name: node.name, quantity: node.quantity, is_component: false }];
    }
    return [];
  }

  const items: ShoppingItem[] = [];
  for (const child of node.children) {
    items.push(...collectShoppingItems(child, buyOverrides, key));
  }
  return items;
}

function aggregateShoppingItems(node: ChainNode, buyOverrides: Set<number>): ShoppingItem[] {
  const all = collectShoppingItems(node, buyOverrides, 'root');
  const map = new Map<number, ShoppingItem>();
  for (const m of all) {
    const existing = map.get(m.type_id);
    if (existing) {
      existing.quantity += m.quantity;
    } else {
      map.set(m.type_id, { ...m });
    }
  }
  const components = Array.from(map.values()).filter(m => m.is_component).sort((a, b) => a.name.localeCompare(b.name));
  const raw = Array.from(map.values()).filter(m => !m.is_component).sort((a, b) => b.quantity - a.quantity);
  return [...components, ...raw];
}

const DEPTH_COLORS = [
  '#00d4ff',
  '#3fb950',
  '#d29922',
  '#a855f7',
  '#f85149',
];

export function PlannerTab({ selectedItem, onNavigateToMaterial, projectItemId, onDecisionsChanged }: Props) {
  const [chain, setChain] = useState<MaterialChain | null>(null);
  const [loading, setLoading] = useState(true);
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());
  const [buyOverrides, setBuyOverrides] = useState<Set<number>>(new Set());
  const [quantity, setQuantity] = useState(1);
  const [copied, setCopied] = useState(false);
  const [prices, setPrices] = useState<Record<number, { sell_price: number; buy_price: number }>>({});
  const priceAbortRef = useRef<AbortController | null>(null);
  const decisionsLoadedRef = useRef<number | null>(null);

  useEffect(() => {
    setLoading(true);
    setChain(null);
    setCollapsed(new Set());
    setBuyOverrides(new Set());
    setQuantity(1);
    decisionsLoadedRef.current = null;
    productionApi.getChain(selectedItem.typeID, { format: 'tree' })
      .then(data => {
        setChain(data);
        // Load saved decisions when used in project context
        if (projectItemId && decisionsLoadedRef.current !== projectItemId) {
          decisionsLoadedRef.current = projectItemId;
          projectApi.getDecisions(projectItemId).then(decisions => {
            // Collect all manufacturable type_ids from the chain
            const mfg = new Set<number>();
            const walk = (node: ChainNode) => {
              if (node.is_manufacturable && node.children?.length > 0) mfg.add(node.type_id);
              for (const c of node.children ?? []) walk(c);
            };
            walk(data.chain);
            // Set overrides: decisions with 'buy' that are manufacturable
            const overrides = new Set<number>();
            if (decisions && decisions.length > 0) {
              for (const d of decisions) {
                if (d.decision === 'buy' && mfg.has(d.material_type_id)) {
                  overrides.add(d.material_type_id);
                }
              }
            }
            setBuyOverrides(overrides);
            // Auto-sync: notify parent with current shopping items
            if (onDecisionsChanged && data.chain) {
              const items = aggregateShoppingItems(data.chain, overrides);
              onDecisionsChanged(overrides, items);
            }
          }).catch(() => {
            // No saved decisions — notify parent with default state (all build)
            if (onDecisionsChanged && data.chain) {
              const items = aggregateShoppingItems(data.chain, new Set());
              onDecisionsChanged(new Set(), items);
            }
          });
        }
      })
      .catch(() => setChain(null))
      .finally(() => setLoading(false));
  }, [selectedItem.typeID, projectItemId]);

  const shoppingItems = useMemo(() => {
    if (!chain?.chain) return [];
    return aggregateShoppingItems(chain.chain, buyOverrides);
  }, [chain, buyOverrides]);

  useEffect(() => {
    if (shoppingItems.length === 0) return;
    const typeIds = shoppingItems.map(m => m.type_id);
    const missing = typeIds.filter(id => !(id in prices));
    if (missing.length === 0) return;

    if (priceAbortRef.current) priceAbortRef.current.abort();
    const ctrl = new AbortController();
    priceAbortRef.current = ctrl;

    marketApi.getPricesBulk(typeIds)
      .then(data => {
        if (ctrl.signal.aborted) return;
        const map: Record<number, { sell_price: number; buy_price: number }> = {};
        for (const [key, val] of Object.entries(data)) {
          map[Number(key)] = { sell_price: val.sell_price, buy_price: val.buy_price };
        }
        setPrices(prev => ({ ...prev, ...map }));
      })
      .catch(() => {});

    return () => ctrl.abort();
  }, [shoppingItems]);

  const toggleCollapse = useCallback((key: string) => {
    setCollapsed(prev => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }, []);

  const toggleBuyOverride = useCallback((typeId: number) => {
    setBuyOverrides(prev => {
      const next = new Set(prev);
      if (next.has(typeId)) next.delete(typeId);
      else next.add(typeId);
      // Notify project if in project context
      if (onDecisionsChanged && chain?.chain) {
        const items = aggregateShoppingItems(chain.chain, next);
        onDecisionsChanged(next, items);
      }
      return next;
    });
  }, [onDecisionsChanged, chain]);

  const collapseAll = useCallback(() => {
    if (!chain?.chain) return;
    const keys = new Set<string>();
    const walk = (node: ChainNode, parentKey: string) => {
      const key = `${parentKey}-${node.type_id}`;
      if (node.is_manufacturable && node.children?.length > 0) {
        keys.add(key);
        for (const child of node.children) walk(child, key);
      }
    };
    walk(chain.chain, 'root');
    setCollapsed(keys);
  }, [chain]);

  const expandAll = useCallback(() => {
    setCollapsed(new Set());
  }, []);

  const buyAll = useCallback(() => {
    if (!chain?.chain) return;
    const ids = new Set<number>();
    const walk = (node: ChainNode) => {
      if (node.is_manufacturable && node.children?.length > 0 && node.type_id !== chain.chain.type_id) {
        ids.add(node.type_id);
      }
      for (const child of node.children ?? []) walk(child);
    };
    walk(chain.chain);
    setBuyOverrides(ids);
  }, [chain]);

  const buildAll = useCallback(() => {
    setBuyOverrides(new Set());
  }, []);

  const copyMultibuy = useCallback(() => {
    const lines = shoppingItems.map(m => `${m.name} ${m.quantity * quantity}`);
    const text = lines.join('\n');
    if (navigator.clipboard?.writeText) {
      navigator.clipboard.writeText(text).then(() => { setCopied(true); setTimeout(() => setCopied(false), 2000); });
    } else {
      const ta = document.createElement('textarea');
      ta.value = text;
      ta.style.position = 'fixed';
      ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }, [shoppingItems, quantity]);

  const renderNode = useCallback((node: ChainNode, depth: number, parentKey: string) => {
    const key = `${parentKey}-${node.type_id}`;
    const hasMfgChildren = node.is_manufacturable && node.children?.length > 0;
    const isBuyOverride = hasMfgChildren && buyOverrides.has(node.type_id);
    const isCollapsed = collapsed.has(key);
    const depthColor = DEPTH_COLORS[depth % DEPTH_COLORS.length];
    const isRoot = depth === 0;
    const scaledQty = node.quantity * quantity;
    const showChildren = hasMfgChildren && !isBuyOverride && !isCollapsed;
    const effectiveBuild = node.is_manufacturable && !isBuyOverride;
    const canNavigate = onNavigateToMaterial && node.type_id !== selectedItem.typeID;

    return (
      <div key={key}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.4rem',
            padding: isRoot ? '0.6rem 0.75rem' : '0.3rem 0.5rem',
            paddingLeft: isRoot ? 12 : depth * 22 + 8,
            marginLeft: isRoot ? 0 : (depth > 1 ? (depth - 1) * 22 + 8 : 8),
            borderLeft: depth > 0 ? `2px solid ${depthColor}40` : 'none',
            background: isBuyOverride
              ? 'rgba(210,153,34,0.05)'
              : isRoot
                ? 'rgba(0,212,255,0.04)'
                : 'transparent',
            borderBottom: isRoot ? '1px solid rgba(255,255,255,0.04)' : 'none',
            transition: 'background 0.15s',
            opacity: isBuyOverride ? 0.7 : 1,
          }}
          onMouseEnter={e => {
            if (!isRoot) e.currentTarget.style.background = isBuyOverride
              ? 'rgba(210,153,34,0.1)'
              : 'rgba(255,255,255,0.03)';
          }}
          onMouseLeave={e => {
            if (!isRoot) e.currentTarget.style.background = isBuyOverride
              ? 'rgba(210,153,34,0.05)'
              : 'transparent';
          }}
        >
          {/* Expand/collapse toggle */}
          {hasMfgChildren && !isBuyOverride ? (
            <span
              onClick={() => toggleCollapse(key)}
              style={{
                cursor: 'pointer',
                fontSize: '0.55rem',
                color: isCollapsed ? 'var(--text-secondary)' : depthColor,
                width: 16,
                height: 16,
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                borderRadius: 3,
                background: isCollapsed ? 'rgba(255,255,255,0.04)' : `${depthColor}15`,
                userSelect: 'none',
                transition: 'all 0.15s',
                flexShrink: 0,
              }}
            >
              {isCollapsed ? '\u25B6' : '\u25BC'}
            </span>
          ) : (
            <span style={{ width: 16, flexShrink: 0 }} />
          )}

          {/* Icon */}
          <img
            src={`https://images.evetech.net/types/${node.type_id}/icon?size=32`}
            alt=""
            style={{
              width: isRoot ? 28 : 20,
              height: isRoot ? 28 : 20,
              borderRadius: isRoot ? 4 : 2,
              flexShrink: 0,
              border: isRoot ? '1px solid rgba(0,212,255,0.3)' : '1px solid rgba(255,255,255,0.06)',
            }}
            onError={e => { (e.target as HTMLImageElement).style.display = 'none'; }}
          />

          {/* Name */}
          <span
            onClick={canNavigate ? () => onNavigateToMaterial(node.type_id, node.name) : undefined}
            style={{
              fontSize: isRoot ? '0.88rem' : '0.78rem',
              fontWeight: isRoot ? 700 : (effectiveBuild ? 600 : 400),
              color: isBuyOverride ? '#d29922' : (effectiveBuild ? (isRoot ? '#00d4ff' : 'var(--text-primary)') : 'var(--text-primary)'),
              cursor: canNavigate ? 'pointer' : 'default',
              flex: 1,
              textDecoration: isBuyOverride ? 'line-through' : 'none',
              textDecorationColor: 'rgba(210,153,34,0.4)',
              transition: 'color 0.1s',
            }}
            onMouseEnter={canNavigate
              ? e => { e.currentTarget.style.color = '#00d4ff'; e.currentTarget.style.textDecoration = isBuyOverride ? 'line-through underline' : 'underline'; }
              : undefined}
            onMouseLeave={canNavigate
              ? e => {
                  e.currentTarget.style.color = isBuyOverride ? '#d29922' : (effectiveBuild ? (isRoot ? '#00d4ff' : 'var(--text-primary)') : 'var(--text-primary)');
                  e.currentTarget.style.textDecoration = isBuyOverride ? 'line-through' : 'none';
                }
              : undefined}
          >
            {node.name}
          </span>

          {/* Quantity */}
          <span style={{
            fontSize: isRoot ? '0.82rem' : '0.72rem',
            fontFamily: 'monospace',
            color: isRoot ? 'rgba(0,212,255,0.8)' : 'var(--text-secondary)',
            minWidth: 70,
            textAlign: 'right',
            fontWeight: isRoot ? 700 : 400,
          }}>
            \u00D7{scaledQty.toLocaleString()}
          </span>

          {/* Badge */}
          {hasMfgChildren && !isRoot ? (
            <span
              onClick={() => toggleBuyOverride(node.type_id)}
              style={{
                fontSize: '0.55rem',
                fontWeight: 700,
                padding: '2px 7px',
                borderRadius: 3,
                lineHeight: '1.3',
                cursor: 'pointer',
                userSelect: 'none',
                transition: 'all 0.15s',
                letterSpacing: '0.03em',
                minWidth: 36,
                textAlign: 'center',
                ...(isBuyOverride
                  ? { background: 'rgba(210,153,34,0.2)', border: '1px solid rgba(210,153,34,0.5)', color: '#d29922' }
                  : { background: 'rgba(63,185,80,0.12)', border: '1px solid rgba(63,185,80,0.35)', color: '#3fb950' }),
              }}
              title={isBuyOverride ? 'Click to build this yourself' : 'Click to buy from market instead'}
            >
              {isBuyOverride ? 'BUY' : 'BUILD'}
            </span>
          ) : isRoot ? (
            <span style={{
              fontSize: '0.55rem',
              fontWeight: 700,
              padding: '2px 7px',
              borderRadius: 3,
              lineHeight: '1.3',
              letterSpacing: '0.03em',
              minWidth: 36,
              textAlign: 'center',
              background: 'rgba(0,212,255,0.12)',
              border: '1px solid rgba(0,212,255,0.35)',
              color: '#00d4ff',
            }}>
              BUILD
            </span>
          ) : (
            <span style={{
              fontSize: '0.5rem',
              fontWeight: 600,
              padding: '2px 6px',
              borderRadius: 2,
              lineHeight: '1.3',
              letterSpacing: '0.03em',
              minWidth: 30,
              textAlign: 'center',
              ...(node.is_manufacturable
                ? { background: 'rgba(63,185,80,0.1)', color: 'rgba(63,185,80,0.6)' }
                : { background: 'rgba(139,148,158,0.06)', color: 'rgba(139,148,158,0.5)' }),
            }}>
              {node.is_manufacturable ? 'BUILD' : 'BUY'}
            </span>
          )}
        </div>

        {showChildren && (
          <div>
            {node.children.map(child => renderNode(child, depth + 1, key))}
          </div>
        )}
      </div>
    );
  }, [collapsed, toggleCollapse, toggleBuyOverride, buyOverrides, onNavigateToMaterial, selectedItem.typeID, quantity]);

  if (loading) return <div className="skeleton" style={{ height: 300 }} />;

  if (!chain?.chain) {
    return (
      <div style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', padding: '3rem 0', textAlign: 'center' }}>
        No production chain data available for this item.
      </div>
    );
  }

  const componentCount = shoppingItems.filter(m => m.is_component).length;
  const rawCount = shoppingItems.filter(m => !m.is_component).length;
  const totalCost = shoppingItems.reduce((sum, m) => {
    const p = prices[m.type_id];
    return sum + (p?.sell_price ?? 0) * m.quantity * quantity;
  }, 0);

  return (
    <div>
      {/* Controls Bar */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '0.75rem',
        marginBottom: '1rem',
        padding: '0.6rem 0.85rem',
        background: 'var(--bg-secondary)',
        border: '1px solid var(--border-color)',
        borderRadius: 8,
        flexWrap: 'wrap',
      }}>
        {/* Quantity */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
          <label style={labelStyle}>Runs</label>
          <input
            type="number"
            min={1}
            max={10000}
            value={quantity}
            onChange={e => {
              const v = Math.max(1, Math.min(10000, Number(e.target.value) || 1));
              setQuantity(v);
            }}
            style={{
              width: 64,
              padding: '5px 8px',
              fontSize: '0.82rem',
              fontFamily: 'monospace',
              fontWeight: 700,
              background: 'var(--bg-elevated, rgba(255,255,255,0.04))',
              border: '1px solid var(--border-color)',
              borderRadius: 5,
              color: '#00d4ff',
              textAlign: 'center',
              outline: 'none',
            }}
          />
        </div>

        <Divider />

        <div style={{ display: 'flex', gap: '0.3rem' }}>
          <ControlBtn onClick={expandAll} label="Expand" />
          <ControlBtn onClick={collapseAll} label="Collapse" />
        </div>

        <Divider />

        <div style={{ display: 'flex', gap: '0.3rem' }}>
          <ControlBtn onClick={buildAll} label="Build All" accent="#3fb950" />
          <ControlBtn onClick={buyAll} label="Buy All" accent="#d29922" />
        </div>

        {/* Total cost badge (right-aligned) */}
        {totalCost > 0 && (
          <div style={{
            marginLeft: 'auto',
            display: 'flex',
            alignItems: 'center',
            gap: '0.4rem',
          }}>
            <span style={{ fontSize: '0.65rem', color: 'var(--text-secondary)', textTransform: 'uppercase', fontWeight: 600 }}>Total</span>
            <span style={{
              fontSize: '0.85rem',
              fontFamily: 'monospace',
              fontWeight: 700,
              color: '#00d4ff',
              background: 'rgba(0,212,255,0.08)',
              padding: '3px 10px',
              borderRadius: 4,
              border: '1px solid rgba(0,212,255,0.2)',
            }}>
              {formatISK(totalCost)}
            </span>
          </div>
        )}
      </div>

      {/* Production Chain */}
      <div style={{ marginBottom: '1.5rem' }}>
        <SectionHeader title="Production Chain" />
        <div style={{
          background: 'var(--bg-secondary)',
          border: '1px solid var(--border-color)',
          borderRadius: 8,
          padding: '0.35rem 0',
          overflow: 'hidden',
        }}>
          {renderNode(chain.chain, 0, 'root')}
        </div>
      </div>

      {/* Shopping List */}
      {shoppingItems.length > 0 && (
        <div>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            marginBottom: '0.4rem',
          }}>
            <SectionHeader title="Shopping List" inline />
            <span style={{
              fontSize: '0.6rem',
              color: 'var(--text-secondary)',
              padding: '2px 8px',
              background: 'rgba(255,255,255,0.03)',
              borderRadius: 10,
              border: '1px solid rgba(255,255,255,0.06)',
            }}>
              {componentCount > 0 ? `${componentCount} comp + ${rawCount} raw` : `${rawCount} materials`}
            </span>
            <button
              onClick={copyMultibuy}
              style={{
                marginLeft: 'auto',
                padding: '3px 12px',
                fontSize: '0.65rem',
                fontWeight: 600,
                background: copied ? 'rgba(63,185,80,0.12)' : 'rgba(255,255,255,0.03)',
                border: `1px solid ${copied ? 'rgba(63,185,80,0.4)' : 'rgba(255,255,255,0.08)'}`,
                borderRadius: 4,
                color: copied ? '#3fb950' : 'var(--text-secondary)',
                cursor: 'pointer',
                transition: 'all 0.2s',
              }}
            >
              {copied ? 'Copied!' : 'Copy Multibuy'}
            </button>
          </div>

          <div style={{
            background: 'var(--bg-secondary)',
            border: '1px solid var(--border-color)',
            borderRadius: 8,
            overflow: 'hidden',
          }}>
            {/* Header */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: '26px 1fr 44px 80px 90px 100px',
              gap: '0.5rem',
              padding: '0.5rem 0.85rem',
              borderBottom: '1px solid var(--border-color)',
              background: 'rgba(255,255,255,0.015)',
              fontSize: '0.58rem',
              fontWeight: 700,
              color: 'rgba(139,148,158,0.7)',
              textTransform: 'uppercase',
              letterSpacing: '0.06em',
            }}>
              <div />
              <div>Material</div>
              <div style={{ textAlign: 'center' }}>Type</div>
              <div style={{ textAlign: 'right' }}>Qty</div>
              <div style={{ textAlign: 'right' }}>Unit</div>
              <div style={{ textAlign: 'right' }}>Total</div>
            </div>

            {/* Rows */}
            {shoppingItems.map((mat, i) => {
              const p = prices[mat.type_id];
              const unitPrice = p?.sell_price ?? 0;
              const totalPrice = unitPrice * mat.quantity * quantity;
              return (
                <div
                  key={mat.type_id}
                  style={{
                    display: 'grid',
                    gridTemplateColumns: '26px 1fr 44px 80px 90px 100px',
                    gap: '0.5rem',
                    padding: '0.35rem 0.85rem',
                    alignItems: 'center',
                    background: i % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.015)',
                    transition: 'background 0.1s',
                  }}
                  onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.04)'; }}
                  onMouseLeave={e => { e.currentTarget.style.background = i % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.015)'; }}
                >
                  <img
                    src={`https://images.evetech.net/types/${mat.type_id}/icon?size=32`}
                    alt=""
                    style={{ width: 20, height: 20, borderRadius: 2, border: '1px solid rgba(255,255,255,0.06)' }}
                    onError={e => { (e.target as HTMLImageElement).style.display = 'none'; }}
                  />
                  <div style={{
                    fontSize: '0.76rem',
                    color: mat.is_component ? '#d29922' : 'var(--text-primary)',
                    fontWeight: mat.is_component ? 600 : 400,
                  }}>
                    {mat.name}
                  </div>
                  <div style={{ textAlign: 'center' }}>
                    <span style={{
                      fontSize: '0.48rem',
                      fontWeight: 700,
                      padding: '1px 5px',
                      borderRadius: 2,
                      letterSpacing: '0.04em',
                      ...(mat.is_component
                        ? { background: 'rgba(210,153,34,0.12)', color: '#d29922' }
                        : { background: 'rgba(139,148,158,0.08)', color: 'rgba(139,148,158,0.6)' }),
                    }}>
                      {mat.is_component ? 'COMP' : 'RAW'}
                    </span>
                  </div>
                  <div style={{
                    fontSize: '0.76rem',
                    fontFamily: 'monospace',
                    color: 'var(--text-primary)',
                    textAlign: 'right',
                    fontWeight: 500,
                  }}>
                    {(mat.quantity * quantity).toLocaleString()}
                  </div>
                  <div style={{
                    fontSize: '0.7rem',
                    fontFamily: 'monospace',
                    color: 'var(--text-secondary)',
                    textAlign: 'right',
                  }}>
                    {unitPrice > 0 ? formatISK(unitPrice) : '\u2014'}
                  </div>
                  <div style={{
                    fontSize: '0.72rem',
                    fontFamily: 'monospace',
                    color: totalPrice > 0 ? 'var(--text-primary)' : 'var(--text-secondary)',
                    textAlign: 'right',
                    fontWeight: totalPrice > 0 ? 600 : 400,
                  }}>
                    {totalPrice > 0 ? formatISK(totalPrice) : '\u2014'}
                  </div>
                </div>
              );
            })}

            {/* Total row */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: '26px 1fr 44px 80px 90px 100px',
              gap: '0.5rem',
              padding: '0.55rem 0.85rem',
              borderTop: '1px solid var(--border-color)',
              background: 'rgba(0,212,255,0.03)',
            }}>
              <div />
              <div style={{
                fontSize: '0.76rem',
                fontWeight: 700,
                color: 'var(--text-primary)',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
              }}>
                Total
                <span style={{ fontSize: '0.6rem', fontWeight: 400, color: 'var(--text-secondary)' }}>
                  Jita Sell
                </span>
              </div>
              <div />
              <div />
              <div />
              <div style={{
                fontSize: '0.82rem',
                fontFamily: 'monospace',
                color: '#00d4ff',
                textAlign: 'right',
                fontWeight: 700,
              }}>
                {formatISK(totalCost)}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/* ---- Tiny helper components ---- */

const labelStyle: React.CSSProperties = {
  fontSize: '0.65rem',
  color: 'var(--text-secondary)',
  textTransform: 'uppercase',
  fontWeight: 600,
  letterSpacing: '0.04em',
};

function Divider() {
  return <div style={{ width: 1, height: 18, background: 'rgba(255,255,255,0.08)', flexShrink: 0 }} />;
}

function ControlBtn({ onClick, label, accent }: { onClick: () => void; label: string; accent?: string }) {
  return (
    <button
      onClick={onClick}
      style={{
        padding: '4px 10px',
        fontSize: '0.65rem',
        fontWeight: 600,
        background: accent ? `${accent}10` : 'rgba(255,255,255,0.03)',
        border: `1px solid ${accent ? `${accent}40` : 'rgba(255,255,255,0.08)'}`,
        borderRadius: 4,
        color: accent ?? 'var(--text-secondary)',
        cursor: 'pointer',
        transition: 'all 0.15s',
      }}
      onMouseEnter={e => { e.currentTarget.style.background = accent ? `${accent}20` : 'rgba(255,255,255,0.06)'; }}
      onMouseLeave={e => { e.currentTarget.style.background = accent ? `${accent}10` : 'rgba(255,255,255,0.03)'; }}
    >
      {label}
    </button>
  );
}

function SectionHeader({ title, inline }: { title: string; inline?: boolean }) {
  return (
    <div style={{
      fontSize: '0.7rem',
      fontWeight: 700,
      color: 'var(--text-secondary)',
      textTransform: 'uppercase',
      letterSpacing: '0.06em',
      marginBottom: inline ? 0 : '0.4rem',
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
    }}>
      <span style={{
        width: 3,
        height: 12,
        background: '#00d4ff',
        borderRadius: 1,
        flexShrink: 0,
      }} />
      {title}
    </div>
  );
}
