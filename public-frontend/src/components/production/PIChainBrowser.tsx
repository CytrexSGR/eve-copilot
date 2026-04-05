import { useState, useEffect, useMemo, useCallback } from 'react';
import { piApi } from '../../services/api/production';
import type { PISchematicFormula, PIProfitability } from '../../types/production';

// ── Constants ────────────────────────────────────────────

const TIER_COLORS: Record<number, string> = {
  0: '#8b949e', 1: '#3fb950', 2: '#58a6ff', 3: '#a855f7', 4: '#d4a017',
};

const TIER_LABELS: Record<number, string> = {
  0: 'Raw', 1: 'P1', 2: 'P2', 3: 'P3', 4: 'P4',
};

const NODE_W = 130;
const NODE_H = 50;
const H_GAP = 16;
const V_GAP = 48;
const PAD = 20;

const EDGE_TIER_COLORS: Record<number, string> = {
  0: 'rgba(139,148,158,0.25)',
  1: 'rgba(63,185,80,0.25)',
  2: 'rgba(88,166,255,0.25)',
  3: 'rgba(168,85,247,0.25)',
  4: 'rgba(212,160,23,0.25)',
};

const EDGE_TIER_COLORS_BRIGHT: Record<number, string> = {
  0: 'rgba(139,148,158,0.85)',
  1: 'rgba(63,185,80,0.85)',
  2: 'rgba(88,166,255,0.85)',
  3: 'rgba(168,85,247,0.85)',
  4: 'rgba(212,160,23,0.85)',
};

function formatISK(v: number): string {
  if (Math.abs(v) >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`;
  if (Math.abs(v) >= 1_000) return `${(v / 1_000).toFixed(1)}K`;
  return v.toFixed(0);
}

// ── Types ────────────────────────────────────────────────

interface DAGNode {
  type_id: number;
  type_name: string;
  tier: number;
}

interface DAGEdge {
  source_type_id: number; // input (lower tier)
  target_type_id: number; // output (higher tier)
  quantity: number;
}

interface CartItem {
  type_id: number;
  type_name: string;
  tier: number;
  qty_per_hour: number;
}

// ── Build DAG from schematics for a selected P4 product ──

function buildDAG(
  rootTypeId: number,
  schematics: PISchematicFormula[],
): { nodes: DAGNode[]; edges: DAGEdge[] } {
  const outputMap = new Map<number, PISchematicFormula>();
  schematics.forEach(s => outputMap.set(s.output_type_id, s));

  const nodes = new Map<number, DAGNode>();
  const edges: DAGEdge[] = [];

  function visit(typeId: number, typeName: string) {
    if (nodes.has(typeId)) return;
    const schematic = outputMap.get(typeId);
    const tier = schematic ? schematic.tier : 0;
    nodes.set(typeId, { type_id: typeId, type_name: typeName, tier });

    if (schematic) {
      for (const input of schematic.inputs) {
        edges.push({
          source_type_id: input.type_id,
          target_type_id: typeId,
          quantity: input.quantity,
        });
        visit(input.type_id, input.type_name);
      }
    }
  }

  const rootSchematic = outputMap.get(rootTypeId);
  if (rootSchematic) {
    visit(rootTypeId, rootSchematic.output_name);
  }

  return { nodes: Array.from(nodes.values()), edges };
}

// ── BFS trace connected nodes ────────────────────────────

function traceConnectedNodes(
  startId: number,
  edges: DAGEdge[],
): Set<number> {
  const visited = new Set<number>();
  visited.add(startId);
  // Upstream (inputs feeding into this node)
  const up = [startId];
  while (up.length > 0) {
    const cur = up.shift()!;
    for (const e of edges) {
      if (e.target_type_id === cur && !visited.has(e.source_type_id)) {
        visited.add(e.source_type_id);
        up.push(e.source_type_id);
      }
    }
  }
  // Downstream (outputs consuming this node)
  const down = [startId];
  while (down.length > 0) {
    const cur = down.shift()!;
    for (const e of edges) {
      if (e.source_type_id === cur && !visited.has(e.target_type_id)) {
        visited.add(e.target_type_id);
        down.push(e.target_type_id);
      }
    }
  }
  return visited;
}

// ── ChainDAG SVG Component ──────────────────────────────

function ChainDAG({
  dagNodes,
  dagEdges,
  profitMap,
  cartSet,
  onToggleCart,
}: {
  dagNodes: DAGNode[];
  dagEdges: DAGEdge[];
  profitMap: Map<number, PIProfitability>;
  cartSet: Set<number>;
  onToggleCart: (node: DAGNode) => void;
}) {
  const [hoveredNodeId, setHoveredNodeId] = useState<number | null>(null);

  const highlightedNodes = useMemo(() => {
    if (hoveredNodeId === null) return null;
    return traceConnectedNodes(hoveredNodeId, dagEdges);
  }, [hoveredNodeId, dagEdges]);

  // Group nodes by tier (descending: highest tier at top)
  const tiers = useMemo(() => {
    const tierMap: Record<number, DAGNode[]> = {};
    dagNodes.forEach(n => {
      if (!tierMap[n.tier]) tierMap[n.tier] = [];
      tierMap[n.tier].push(n);
    });
    return Object.keys(tierMap)
      .map(Number)
      .sort((a, b) => b - a)
      .map(tier => ({ tier, nodes: tierMap[tier] }));
  }, [dagNodes]);

  // Calculate positions
  const positions = useMemo(() => {
    const pos: Record<number, { x: number; y: number }> = {};
    const maxCols = tiers.reduce((max, r) => Math.max(max, r.nodes.length), 0);
    tiers.forEach((row, rowIdx) => {
      const totalWidth = row.nodes.length * NODE_W + (row.nodes.length - 1) * H_GAP;
      const maxTotalWidth = maxCols * NODE_W + (maxCols - 1) * H_GAP;
      const startX = PAD + (maxTotalWidth - totalWidth) / 2;
      row.nodes.forEach((node, colIdx) => {
        pos[node.type_id] = {
          x: startX + colIdx * (NODE_W + H_GAP),
          y: PAD + rowIdx * (NODE_H + V_GAP),
        };
      });
    });
    return pos;
  }, [tiers]);

  const maxCols = tiers.reduce((max, r) => Math.max(max, r.nodes.length), 0);
  const svgWidth = PAD * 2 + maxCols * NODE_W + (maxCols - 1) * H_GAP;
  const svgHeight = PAD * 2 + tiers.length * NODE_H + (tiers.length - 1) * V_GAP;

  const isHovering = highlightedNodes !== null;

  return (
    <div
      style={{
        background: 'var(--bg-secondary)', border: '1px solid var(--border-color)',
        borderRadius: 8, overflow: 'auto', flex: 1,
      }}
      onMouseLeave={() => setHoveredNodeId(null)}
    >
      <svg width={svgWidth} height={svgHeight} style={{ display: 'block', margin: '0 auto' }}>
        {/* Bezier Edges */}
        {dagEdges.map((edge, i) => {
          const from = positions[edge.source_type_id];
          const to = positions[edge.target_type_id];
          if (!from || !to) return null;

          const x1 = from.x + NODE_W / 2;
          const y1 = from.y;
          const x2 = to.x + NODE_W / 2;
          const y2 = to.y + NODE_H;
          const midY = (y1 + y2) / 2;

          const sourceTier = dagNodes.find(n => n.type_id === edge.source_type_id)?.tier ?? 0;

          const edgeHighlighted = isHovering &&
            highlightedNodes!.has(edge.source_type_id) &&
            highlightedNodes!.has(edge.target_type_id);
          const edgeDimmed = isHovering && !edgeHighlighted;

          return (
            <g key={`${edge.source_type_id}-${edge.target_type_id}-${i}`}>
              <path
                d={`M ${x1} ${y1} C ${x1} ${midY}, ${x2} ${midY}, ${x2} ${y2}`}
                stroke={edgeHighlighted
                  ? (EDGE_TIER_COLORS_BRIGHT[sourceTier] || 'rgba(255,255,255,0.85)')
                  : (EDGE_TIER_COLORS[sourceTier] || 'rgba(255,255,255,0.15)')}
                strokeWidth={edgeHighlighted ? 2.5 : 1.5}
                fill="none"
                opacity={edgeDimmed ? 0.12 : 1}
                style={{ transition: 'opacity 0.15s, stroke-width 0.15s' }}
              />
              {edgeHighlighted && (
                <text
                  x={(x1 + x2) / 2 + (x1 === x2 ? 0 : 8)}
                  y={midY - 3}
                  fill="var(--text-secondary)"
                  fontSize={8}
                  fontWeight={600}
                  textAnchor="middle"
                  fontFamily="monospace"
                >
                  x{edge.quantity}
                </text>
              )}
            </g>
          );
        })}

        {/* Nodes */}
        {dagNodes.map(node => {
          const p = positions[node.type_id];
          if (!p) return null;
          const tierColor = TIER_COLORS[node.tier] || '#8b949e';
          const inCart = cartSet.has(node.type_id);
          const profit = profitMap.get(node.type_id);
          const nodeHighlighted = isHovering && highlightedNodes!.has(node.type_id);
          const nodeDimmed = isHovering && !nodeHighlighted;

          return (
            <g
              key={node.type_id}
              onClick={() => node.tier >= 1 && onToggleCart(node)}
              onMouseEnter={() => setHoveredNodeId(node.type_id)}
              style={{
                cursor: node.tier >= 1 ? 'pointer' : 'default',
                opacity: nodeDimmed ? 0.2 : 1,
                transition: 'opacity 0.15s',
              }}
            >
              <rect
                x={p.x} y={p.y} width={NODE_W} height={NODE_H}
                rx={6}
                fill={inCart ? `${tierColor}15` : 'var(--bg-primary)'}
                stroke={inCart ? '#3fb950' : nodeHighlighted ? tierColor : `${tierColor}44`}
                strokeWidth={inCart ? 2 : nodeHighlighted ? 2 : 1}
              />
              {/* Cart checkmark */}
              {inCart && (
                <text
                  x={p.x + 8} y={p.y + 12}
                  fill="#3fb950" fontSize={11} fontWeight={700}
                >
                  ✓
                </text>
              )}
              {/* Item icon */}
              <image
                href={`https://images.evetech.net/types/${node.type_id}/icon?size=32`}
                x={p.x + (inCart ? 20 : 6)} y={p.y + 2}
                width={14} height={14}
              />
              {/* Tier badge */}
              <text
                x={p.x + NODE_W - 6} y={p.y + 12}
                fill={tierColor} fontSize={9} fontWeight={700}
                textAnchor="end" fontFamily="monospace"
              >
                {TIER_LABELS[node.tier] || `P${node.tier}`}
              </text>
              {/* Name */}
              <text
                x={p.x + NODE_W / 2} y={p.y + 26}
                fill={nodeHighlighted ? '#fff' : 'var(--text-primary)'} fontSize={10} fontWeight={600}
                textAnchor="middle"
              >
                {node.type_name.length > 16 ? node.type_name.slice(0, 15) + '\u2026' : node.type_name}
              </text>
              {/* Profit / Raw indicator */}
              {profit && profit.profit_per_hour > 0 ? (
                <text
                  x={p.x + NODE_W / 2} y={p.y + 39}
                  fill="#3fb950" fontSize={8}
                  textAnchor="middle" fontFamily="monospace"
                >
                  {formatISK(profit.profit_per_hour)}/h {'\u00B7'} {profit.roi_percent.toFixed(0)}%
                </text>
              ) : node.tier === 0 ? (
                <text
                  x={p.x + NODE_W / 2} y={p.y + 39}
                  fill="var(--text-secondary)" fontSize={8}
                  textAnchor="middle" fontFamily="monospace" fontStyle="italic"
                >
                  Raw
                </text>
              ) : null}
            </g>
          );
        })}
      </svg>
    </div>
  );
}

// ── P4 Product Selector ──────────────────────────────────

function P4Selector({
  products,
  profitMap,
  selectedId,
  onSelect,
}: {
  products: PISchematicFormula[];
  profitMap: Map<number, PIProfitability>;
  selectedId: number | null;
  onSelect: (typeId: number) => void;
}) {
  return (
    <div style={{
      display: 'flex', gap: 6, flexWrap: 'wrap', padding: '6px 0',
    }}>
      {products.map(p => {
        const isSelected = p.output_type_id === selectedId;
        const profit = profitMap.get(p.output_type_id);
        return (
          <button
            key={p.output_type_id}
            onClick={() => onSelect(p.output_type_id)}
            style={{
              display: 'flex', alignItems: 'center', gap: 6,
              padding: '5px 10px', borderRadius: 6,
              background: isSelected ? 'rgba(212,160,23,0.15)' : 'var(--bg-secondary)',
              border: `1px solid ${isSelected ? '#d4a017' : 'var(--border-color)'}`,
              cursor: 'pointer', color: isSelected ? '#d4a017' : 'var(--text-primary)',
              fontSize: '0.72rem', fontWeight: isSelected ? 700 : 500,
              transition: 'all 0.15s',
            }}
          >
            <img
              src={`https://images.evetech.net/types/${p.output_type_id}/icon?size=32`}
              alt="" style={{ width: 22, height: 22, borderRadius: 3 }}
              onError={e => { (e.target as HTMLImageElement).style.display = 'none'; }}
            />
            <div style={{ textAlign: 'left' }}>
              <div style={{ lineHeight: 1.2 }}>{p.output_name}</div>
              {profit && profit.profit_per_hour > 0 && (
                <div style={{ fontSize: '0.58rem', color: '#3fb950', fontFamily: 'monospace' }}>
                  {formatISK(profit.profit_per_hour)}/h
                </div>
              )}
            </div>
          </button>
        );
      })}
    </div>
  );
}

// ── TierBadge (cart panel) ───────────────────────────────

function TierBadge({ tier }: { tier: number }) {
  const color = TIER_COLORS[tier] || '#8b949e';
  return (
    <span style={{
      fontSize: '0.55rem', fontWeight: 700, padding: '1px 5px',
      borderRadius: 3, color, background: `${color}18`,
      border: `1px solid ${color}44`, fontFamily: 'monospace',
    }}>
      {TIER_LABELS[tier] || `P${tier}`}
    </span>
  );
}

// ══════════════════════════════════════════════════════════
// PIChainBrowser — Main Export
// ══════════════════════════════════════════════════════════

export function PIChainBrowser({ onPlanCreated }: { onPlanCreated: (planId: number) => void }) {
  const [schematics, setSchematics] = useState<PISchematicFormula[]>([]);
  const [profitData, setProfitData] = useState<PIProfitability[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedP4, setSelectedP4] = useState<number | null>(null);
  const [cart, setCart] = useState<CartItem[]>([]);
  const [creating, setCreating] = useState(false);

  // Load data
  useEffect(() => {
    setLoading(true);
    Promise.all([
      piApi.getFormulas(),
      piApi.getOpportunities({ limit: 200 }),
    ]).then(([formulas, profits]) => {
      setSchematics(formulas);
      setProfitData(profits);
      const p4 = formulas.filter(s => s.tier === 4).sort((a, b) => a.output_name.localeCompare(b.output_name));
      if (p4.length > 0) setSelectedP4(p4[0].output_type_id);
    }).catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  // P4 products sorted alphabetically
  const p4Products = useMemo(() =>
    schematics.filter(s => s.tier === 4).sort((a, b) => a.output_name.localeCompare(b.output_name)),
    [schematics],
  );

  // Build DAG for selected P4
  const { nodes: dagNodes, edges: dagEdges } = useMemo(() => {
    if (!selectedP4) return { nodes: [], edges: [] };
    return buildDAG(selectedP4, schematics);
  }, [selectedP4, schematics]);

  // Profit map
  const profitMap = useMemo(() => {
    const m = new Map<number, PIProfitability>();
    profitData.forEach(p => m.set(p.type_id, p));
    return m;
  }, [profitData]);

  // Cart set for O(1) lookup
  const cartSet = useMemo(() => new Set(cart.map(c => c.type_id)), [cart]);

  // Toggle cart
  const handleToggleCart = useCallback((node: DAGNode) => {
    setCart(prev => {
      if (prev.some(c => c.type_id === node.type_id)) {
        return prev.filter(c => c.type_id !== node.type_id);
      }
      return [...prev, {
        type_id: node.type_id,
        type_name: node.type_name,
        tier: node.tier,
        qty_per_hour: 1.0,
      }];
    });
  }, []);

  // Update qty
  const updateQty = (typeId: number, qty: number) => {
    setCart(prev => prev.map(c => c.type_id === typeId ? { ...c, qty_per_hour: qty } : c));
  };

  // Remove from cart
  const removeFromCart = (typeId: number) => {
    setCart(prev => prev.filter(c => c.type_id !== typeId));
  };

  // Create plan
  const handleCreatePlan = async () => {
    if (cart.length === 0 || creating) return;
    setCreating(true);
    try {
      const name = cart.length === 1
        ? cart[0].type_name
        : cart.map(c => c.type_name).slice(0, 3).join(', ') + (cart.length > 3 ? '...' : '');
      const plan = await piApi.createPlan(name);
      for (const item of cart) {
        await piApi.addTarget(plan.id, item.type_id, item.qty_per_hour);
      }
      setCart([]);
      onPlanCreated(plan.id);
    } catch {
      // error handling
    } finally {
      setCreating(false);
    }
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-secondary)' }}>
        Loading production chains...
      </div>
    );
  }

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 300px', gap: '1rem', minHeight: 400 }}>
      {/* Left: DAG */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', overflow: 'hidden' }}>
        {/* P4 Product Selector */}
        <P4Selector
          products={p4Products}
          profitMap={profitMap}
          selectedId={selectedP4}
          onSelect={setSelectedP4}
        />

        {/* DAG Graph */}
        {dagNodes.length > 0 ? (
          <ChainDAG
            dagNodes={dagNodes}
            dagEdges={dagEdges}
            profitMap={profitMap}
            cartSet={cartSet}
            onToggleCart={handleToggleCart}
          />
        ) : (
          <div style={{
            flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: 'var(--text-secondary)', fontSize: '0.8rem',
            background: 'var(--bg-secondary)', border: '1px solid var(--border-color)',
            borderRadius: 8,
          }}>
            Select a P4 product above to view its production chain
          </div>
        )}

        {/* Legend */}
        <div style={{
          display: 'flex', gap: '0.75rem', padding: '4px 0',
          fontSize: '0.55rem', color: 'var(--text-secondary)',
        }}>
          {[4, 3, 2, 1, 0].map(t => (
            <span key={t} style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
              <span style={{ width: 8, height: 8, borderRadius: 2, background: TIER_COLORS[t] }} />
              {TIER_LABELS[t]}
            </span>
          ))}
          <span style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 3 }}>
            <span style={{ color: '#3fb950', fontWeight: 700 }}>{'\u2713'}</span> In Cart
          </span>
        </div>
      </div>

      {/* Right: Cart */}
      <div style={{
        background: 'var(--bg-secondary)', border: '1px solid var(--border-color)',
        borderRadius: 8, display: 'flex', flexDirection: 'column', overflow: 'hidden',
      }}>
        {/* Cart header */}
        <div style={{
          padding: '10px 14px', borderBottom: '1px solid var(--border-color)',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        }}>
          <span style={{ fontSize: '0.8rem', fontWeight: 700 }}>Cart</span>
          <span style={{
            fontSize: '0.6rem', fontWeight: 600, fontFamily: 'monospace',
            color: cart.length > 0 ? '#00d4ff' : 'var(--text-secondary)',
          }}>
            {cart.length} items
          </span>
        </div>

        {/* Cart items */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '6px 0' }}>
          {cart.length === 0 ? (
            <div style={{
              textAlign: 'center', padding: '2rem 1rem',
              color: 'var(--text-secondary)', fontSize: '0.75rem',
            }}>
              Click nodes in the graph to add them to the cart.
            </div>
          ) : (
            cart.map(item => {
              const profit = profitMap.get(item.type_id);
              return (
                <div
                  key={item.type_id}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 6,
                    padding: '6px 12px', borderBottom: '1px solid rgba(255,255,255,0.03)',
                  }}
                >
                  <img
                    src={`https://images.evetech.net/types/${item.type_id}/icon?size=32`}
                    alt="" style={{ width: 24, height: 24, borderRadius: 3 }}
                    onError={e => { (e.target as HTMLImageElement).style.display = 'none'; }}
                  />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{
                      fontSize: '0.75rem', fontWeight: 600,
                      overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                    }}>
                      {item.type_name}
                    </div>
                    <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
                      <TierBadge tier={item.tier} />
                      {profit && (
                        <span style={{ fontSize: '0.55rem', color: '#3fb950', fontFamily: 'monospace' }}>
                          {formatISK(profit.profit_per_hour * item.qty_per_hour)}/h
                        </span>
                      )}
                    </div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
                    <input
                      type="number"
                      value={item.qty_per_hour}
                      onChange={e => updateQty(item.type_id, parseFloat(e.target.value) || 1)}
                      min="0.01" step="0.5"
                      style={{
                        width: 50, padding: '3px 4px', fontSize: '0.7rem', textAlign: 'right',
                        background: 'var(--bg-primary)', border: '1px solid var(--border-color)',
                        borderRadius: 3, color: 'var(--text-primary)', outline: 'none',
                      }}
                    />
                    <span style={{ fontSize: '0.6rem', color: 'var(--text-secondary)' }}>/h</span>
                  </div>
                  <button
                    onClick={() => removeFromCart(item.type_id)}
                    style={{
                      background: 'none', border: 'none', color: '#f85149',
                      cursor: 'pointer', fontSize: '0.8rem', padding: '2px 4px',
                      opacity: 0.6,
                    }}
                    onMouseEnter={e => (e.currentTarget.style.opacity = '1')}
                    onMouseLeave={e => (e.currentTarget.style.opacity = '0.6')}
                  >
                    {'\u00D7'}
                  </button>
                </div>
              );
            })
          )}
        </div>

        {/* Create plan button */}
        <div style={{ padding: '10px 12px', borderTop: '1px solid var(--border-color)' }}>
          <button
            onClick={handleCreatePlan}
            disabled={cart.length === 0 || creating}
            style={{
              width: '100%', padding: '10px', fontSize: '0.8rem', fontWeight: 700,
              borderRadius: 6, cursor: cart.length > 0 ? 'pointer' : 'default',
              background: cart.length > 0 ? '#3fb950' : 'rgba(139,148,158,0.15)',
              border: 'none',
              color: cart.length > 0 ? '#000' : 'var(--text-secondary)',
              opacity: creating ? 0.6 : 1,
            }}
          >
            {creating ? 'Creating plan...' : `Create Plan (${cart.length})`}
          </button>
        </div>
      </div>
    </div>
  );
}
