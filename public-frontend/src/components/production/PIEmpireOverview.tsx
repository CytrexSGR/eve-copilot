import { useState, useEffect, useMemo } from 'react';
import { piApi } from '../../services/api/production';
import type {
  PISchematicFormula,
  EmpireAnalysis,
  EmpireP4Feasibility,
  EmpireProductionEntry,
  EmpireFactoryEntry,
} from '../../types/production';

// ── Constants (matching ChainBrowser) ────────────────────

const TIER_COLORS: Record<number, string> = {
  0: '#8b949e', 1: '#3fb950', 2: '#58a6ff', 3: '#a855f7', 4: '#d4a017',
};
const TIER_LABELS: Record<number, string> = {
  0: 'Raw', 1: 'P1', 2: 'P2', 3: 'P3', 4: 'P4',
};
const NODE_W = 140;
const NODE_H = 56;
const H_GAP = 16;
const V_GAP = 48;
const PAD = 20;

const EDGE_TIER_COLORS: Record<number, string> = {
  0: 'rgba(139,148,158,0.25)', 1: 'rgba(63,185,80,0.25)',
  2: 'rgba(88,166,255,0.25)', 3: 'rgba(168,85,247,0.25)',
  4: 'rgba(212,160,23,0.25)',
};
const EDGE_TIER_COLORS_BRIGHT: Record<number, string> = {
  0: 'rgba(139,148,158,0.85)', 1: 'rgba(63,185,80,0.85)',
  2: 'rgba(88,166,255,0.85)', 3: 'rgba(168,85,247,0.85)',
  4: 'rgba(212,160,23,0.85)',
};

// Availability status colors
const STATUS_COLORS = {
  available: '#3fb950',
  partial: '#d29922',
  missing: '#f85149',
  factory: '#58a6ff',
};

function formatISK(v: number): string {
  if (Math.abs(v) >= 1_000_000_000) return `${(v / 1_000_000_000).toFixed(1)}B`;
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
  source_type_id: number;
  target_type_id: number;
  quantity: number;
}

type NodeStatus = 'available' | 'partial' | 'missing' | 'factory';

// ── Build DAG from schematics ────────────────────────────

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
  if (rootSchematic) visit(rootTypeId, rootSchematic.output_name);
  return { nodes: Array.from(nodes.values()), edges };
}

// ── BFS trace connected nodes ────────────────────────────

function traceConnectedNodes(startId: number, edges: DAGEdge[]): Set<number> {
  const visited = new Set<number>();
  visited.add(startId);
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

// ── Determine node availability status ───────────────────

function getNodeStatus(
  typeId: number,
  tier: number,
  productionMap: Record<string, EmpireProductionEntry>,
  factoryOutput: Record<string, EmpireFactoryEntry>,
): NodeStatus {
  const key = String(typeId);
  // P0: check extractor production
  if (tier === 0) {
    return productionMap[key] ? 'available' : 'missing';
  }
  // P1+: check factory output first, then extractor map
  if (factoryOutput[key]) return 'factory';
  if (productionMap[key]) return 'available';
  return 'missing';
}

// ── Empire DAG SVG Component ─────────────────────────────

function EmpireDAG({
  dagNodes,
  dagEdges,
  productionMap,
  factoryOutput,
  characterNames,
}: {
  dagNodes: DAGNode[];
  dagEdges: DAGEdge[];
  productionMap: Record<string, EmpireProductionEntry>;
  factoryOutput: Record<string, EmpireFactoryEntry>;
  characterNames: Record<number, string>;
}) {
  const [hoveredNodeId, setHoveredNodeId] = useState<number | null>(null);

  const highlightedNodes = useMemo(() => {
    if (hoveredNodeId === null) return null;
    return traceConnectedNodes(hoveredNodeId, dagEdges);
  }, [hoveredNodeId, dagEdges]);

  // Group nodes by tier (descending)
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
                  fontSize={8} fontWeight={600}
                  textAnchor="middle" fontFamily="monospace"
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
          const status = getNodeStatus(node.type_id, node.tier, productionMap, factoryOutput);
          const statusColor = STATUS_COLORS[status];
          const nodeHighlighted = isHovering && highlightedNodes!.has(node.type_id);
          const nodeDimmed = isHovering && !nodeHighlighted;

          // Get production info for subtitle
          const prodEntry = productionMap[String(node.type_id)];
          const factEntry = factoryOutput[String(node.type_id)];
          const entry = factEntry || prodEntry;
          const charNames = entry
            ? entry.characters.map(cid => characterNames[cid] || String(cid))
            : [];

          return (
            <g
              key={node.type_id}
              onMouseEnter={() => setHoveredNodeId(node.type_id)}
              style={{
                cursor: 'default',
                opacity: nodeDimmed ? 0.2 : 1,
                transition: 'opacity 0.15s',
              }}
            >
              {/* Node rect */}
              <rect
                x={p.x} y={p.y} width={NODE_W} height={NODE_H}
                rx={6}
                fill={`${statusColor}08`}
                stroke={nodeHighlighted ? statusColor : `${statusColor}66`}
                strokeWidth={nodeHighlighted ? 2 : 1}
                strokeDasharray={status === 'missing' ? '4 3' : undefined}
              />
              {/* Status indicator dot */}
              <circle
                cx={p.x + 10} cy={p.y + 10}
                r={4}
                fill={statusColor}
                opacity={0.9}
              />
              {/* Item icon */}
              <image
                href={`https://images.evetech.net/types/${node.type_id}/icon?size=32`}
                x={p.x + 18} y={p.y + 2}
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
                x={p.x + NODE_W / 2} y={p.y + 28}
                fill={nodeHighlighted ? '#fff' : 'var(--text-primary)'}
                fontSize={10} fontWeight={600} textAnchor="middle"
              >
                {node.type_name.length > 18 ? node.type_name.slice(0, 17) + '\u2026' : node.type_name}
              </text>
              {/* Production info or "Missing" */}
              {entry ? (
                <>
                  <text
                    x={p.x + NODE_W / 2} y={p.y + 40}
                    fill={statusColor} fontSize={8}
                    textAnchor="middle" fontFamily="monospace"
                  >
                    {entry.qty_per_hour.toFixed(0)}/h
                  </text>
                  <text
                    x={p.x + NODE_W / 2} y={p.y + 50}
                    fill="var(--text-secondary)" fontSize={7}
                    textAnchor="middle"
                  >
                    {charNames.join(', ')}
                  </text>
                </>
              ) : (
                <text
                  x={p.x + NODE_W / 2} y={p.y + 42}
                  fill={STATUS_COLORS.missing} fontSize={8}
                  textAnchor="middle" fontFamily="monospace" fontStyle="italic"
                >
                  {node.tier === 0 ? 'Not extracted' : 'Not produced'}
                </text>
              )}
            </g>
          );
        })}
      </svg>
    </div>
  );
}

// ── P4 Selector with Feasibility ─────────────────────────

function P4FeasibilitySelector({
  feasibility,
  selectedId,
  onSelect,
}: {
  feasibility: EmpireP4Feasibility[];
  selectedId: number | null;
  onSelect: (typeId: number) => void;
}) {
  // Sort by feasibility descending
  const sorted = useMemo(() =>
    [...feasibility].sort((a, b) => b.feasibility_pct - a.feasibility_pct),
    [feasibility],
  );

  return (
    <div style={{
      display: 'flex', gap: 6, flexWrap: 'wrap', padding: '6px 0',
    }}>
      {sorted.map(p => {
        const isSelected = p.type_id === selectedId;
        const pct = p.feasibility_pct;
        const pctColor = pct >= 75 ? '#3fb950' : pct >= 50 ? '#d29922' : pct >= 25 ? '#d4a017' : '#f85149';
        return (
          <button
            key={p.type_id}
            onClick={() => onSelect(p.type_id)}
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
              src={`https://images.evetech.net/types/${p.type_id}/icon?size=32`}
              alt="" style={{ width: 22, height: 22, borderRadius: 3 }}
              onError={e => { (e.target as HTMLImageElement).style.display = 'none'; }}
            />
            <div style={{ textAlign: 'left' }}>
              <div style={{ lineHeight: 1.2 }}>{p.type_name}</div>
              <div style={{ display: 'flex', gap: 4, alignItems: 'center', marginTop: 1 }}>
                <span style={{
                  fontSize: '0.58rem', color: pctColor, fontFamily: 'monospace', fontWeight: 700,
                }}>
                  {pct.toFixed(0)}%
                </span>
                <span style={{
                  fontSize: '0.52rem', color: 'var(--text-secondary)', fontFamily: 'monospace',
                }}>
                  {p.inputs_available}/{p.inputs_total}
                </span>
                {p.sell_price != null && (
                  <span style={{ fontSize: '0.52rem', color: '#d4a017', fontFamily: 'monospace' }}>
                    {formatISK(p.sell_price)}
                  </span>
                )}
                {p.profit_per_hour != null && p.profit_per_hour > 0 && (
                  <span style={{ fontSize: '0.52rem', color: '#3fb950', fontFamily: 'monospace' }}>
                    +{formatISK(p.profit_per_hour)}/h
                  </span>
                )}
              </div>
            </div>
          </button>
        );
      })}
    </div>
  );
}

// ── Sidebar ──────────────────────────────────────────────

function EmpireSidebar({
  analysis,
  selectedP4,
}: {
  analysis: EmpireAnalysis;
  selectedP4: EmpireP4Feasibility | null;
}) {
  const totalExtractors = analysis.characters.reduce((s, c) => s + c.extractors, 0);
  const totalFactories = analysis.characters.reduce((s, c) => s + c.factories, 0);
  const totalColonies = analysis.characters.reduce((s, c) => s + c.colonies, 0);

  return (
    <div style={{
      background: 'var(--bg-secondary)', border: '1px solid var(--border-color)',
      borderRadius: 8, display: 'flex', flexDirection: 'column', overflow: 'hidden',
    }}>
      {/* Empire Summary Header */}
      <div style={{
        padding: '10px 14px', borderBottom: '1px solid var(--border-color)',
      }}>
        <div style={{ fontSize: '0.8rem', fontWeight: 700, marginBottom: 8 }}>Empire Status</div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 6 }}>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '1.2rem', fontWeight: 700, color: '#58a6ff' }}>{totalColonies}</div>
            <div style={{ fontSize: '0.55rem', color: 'var(--text-secondary)' }}>Kolonien</div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '1.2rem', fontWeight: 700, color: '#3fb950' }}>{totalExtractors}</div>
            <div style={{ fontSize: '0.55rem', color: 'var(--text-secondary)' }}>Extraktoren</div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '1.2rem', fontWeight: 700, color: '#a855f7' }}>{totalFactories}</div>
            <div style={{ fontSize: '0.55rem', color: 'var(--text-secondary)' }}>Fabriken</div>
          </div>
        </div>

        {/* Characters */}
        <div style={{ marginTop: 10 }}>
          {analysis.characters.map(char => (
            <div key={char.character_id} style={{
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              padding: '4px 0', fontSize: '0.7rem',
              borderBottom: '1px solid rgba(255,255,255,0.04)',
            }}>
              <span style={{ fontWeight: 600 }}>{char.character_name}</span>
              <span style={{ color: 'var(--text-secondary)', fontFamily: 'monospace', fontSize: '0.6rem' }}>
                {char.colonies}P {char.extractors}E {char.factories}F
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Selected P4 Details */}
      {selectedP4 && (
        <div style={{ flex: 1, overflowY: 'auto' }}>
          {/* P4 Header */}
          <div style={{
            padding: '10px 14px', borderBottom: '1px solid var(--border-color)',
            display: 'flex', alignItems: 'center', gap: 8,
          }}>
            <img
              src={`https://images.evetech.net/types/${selectedP4.type_id}/icon?size=32`}
              alt="" style={{ width: 28, height: 28, borderRadius: 4 }}
              onError={e => { (e.target as HTMLImageElement).style.display = 'none'; }}
            />
            <div>
              <div style={{ fontSize: '0.8rem', fontWeight: 700 }}>{selectedP4.type_name}</div>
              <div style={{
                fontSize: '0.65rem', fontFamily: 'monospace',
                color: selectedP4.feasibility_pct >= 75 ? '#3fb950' :
                  selectedP4.feasibility_pct >= 50 ? '#d29922' : '#f85149',
              }}>
                {selectedP4.feasibility_pct.toFixed(0)}% machbar
                ({selectedP4.inputs_available}/{selectedP4.inputs_total} Inputs)
              </div>
            </div>
          </div>

          {/* Jita Prices */}
          <div style={{
            padding: '8px 14px', borderBottom: '1px solid var(--border-color)',
            display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6,
          }}>
            {selectedP4.sell_price != null && (
              <div>
                <div style={{ fontSize: '0.55rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: 0.5 }}>
                  Jita Sell
                </div>
                <div style={{ fontFamily: 'monospace', fontWeight: 700, fontSize: '0.8rem', color: '#d4a017' }}>
                  {formatISK(selectedP4.sell_price)}
                </div>
              </div>
            )}
            {selectedP4.input_cost != null && (
              <div>
                <div style={{ fontSize: '0.55rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: 0.5 }}>
                  Input-Kosten
                </div>
                <div style={{ fontFamily: 'monospace', fontWeight: 700, fontSize: '0.8rem', color: 'var(--text-primary)' }}>
                  {formatISK(selectedP4.input_cost)}
                </div>
              </div>
            )}
            {selectedP4.missing_buy_cost > 0 && (
              <div style={{ gridColumn: '1 / -1' }}>
                <div style={{ fontSize: '0.55rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: 0.5 }}>
                  Fehlende kaufen (Jita)
                </div>
                <div style={{ fontFamily: 'monospace', fontWeight: 700, fontSize: '0.8rem', color: '#f85149' }}>
                  {formatISK(selectedP4.missing_buy_cost)}
                </div>
              </div>
            )}
          </div>

          {/* Available Inputs */}
          {selectedP4.available_inputs.length > 0 && (
            <div style={{ padding: '8px 14px' }}>
              <div style={{
                fontSize: '0.6rem', fontWeight: 700, textTransform: 'uppercase',
                letterSpacing: 1, color: '#3fb950', marginBottom: 6,
              }}>
                Verfügbar ({selectedP4.available_inputs.length})
              </div>
              {selectedP4.available_inputs.map(input => (
                <div key={input.type_id} style={{
                  display: 'flex', alignItems: 'center', gap: 6,
                  padding: '3px 0', fontSize: '0.7rem',
                  borderBottom: '1px solid rgba(255,255,255,0.03)',
                }}>
                  <span style={{
                    width: 6, height: 6, borderRadius: '50%',
                    background: '#3fb950', flexShrink: 0,
                  }} />
                  <span style={{
                    fontSize: '0.55rem', fontWeight: 600, color: TIER_COLORS[input.tier],
                    fontFamily: 'monospace', minWidth: 20,
                  }}>
                    P{input.tier}
                  </span>
                  <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {input.type_name}
                  </span>
                  {input.qty_per_hour != null && (
                    <span style={{ fontFamily: 'monospace', fontSize: '0.6rem', color: 'var(--text-secondary)' }}>
                      {input.qty_per_hour.toFixed(0)}/h
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Missing Inputs */}
          {selectedP4.missing_inputs.length > 0 && (
            <div style={{ padding: '8px 14px' }}>
              <div style={{
                fontSize: '0.6rem', fontWeight: 700, textTransform: 'uppercase',
                letterSpacing: 1, color: '#f85149', marginBottom: 6,
              }}>
                Fehlt ({selectedP4.missing_inputs.length})
              </div>
              {selectedP4.missing_inputs.map(input => (
                <div key={input.type_id} style={{
                  display: 'flex', alignItems: 'center', gap: 6,
                  padding: '3px 0', fontSize: '0.7rem',
                  borderBottom: '1px solid rgba(255,255,255,0.03)',
                }}>
                  <span style={{
                    width: 6, height: 6, borderRadius: '50%',
                    background: '#f85149', flexShrink: 0,
                  }} />
                  <span style={{
                    fontSize: '0.55rem', fontWeight: 600, color: TIER_COLORS[input.tier],
                    fontFamily: 'monospace', minWidth: 20,
                  }}>
                    P{input.tier}
                  </span>
                  <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {input.type_name}
                  </span>
                  {input.market_price != null && (
                    <span style={{ fontFamily: 'monospace', fontSize: '0.6rem', color: '#d29922' }}>
                      {formatISK(input.market_price)}
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Profit Estimate */}
          {selectedP4.profit_per_hour != null && (
            <div style={{
              padding: '10px 14px', borderTop: '1px solid var(--border-color)',
              marginTop: 'auto',
            }}>
              <div style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              }}>
                <span style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>Profit/h</span>
                <span style={{
                  fontFamily: 'monospace', fontWeight: 700, fontSize: '0.85rem',
                  color: selectedP4.profit_per_hour > 0 ? '#3fb950' : '#f85149',
                }}>
                  {formatISK(selectedP4.profit_per_hour)} ISK
                </span>
              </div>
              {selectedP4.roi_percent != null && (
                <div style={{
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  marginTop: 2,
                }}>
                  <span style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>ROI</span>
                  <span style={{
                    fontFamily: 'monospace', fontWeight: 600, fontSize: '0.75rem',
                    color: selectedP4.roi_percent > 0 ? '#3fb950' : '#f85149',
                  }}>
                    {selectedP4.roi_percent.toFixed(1)}%
                  </span>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* No selection placeholder */}
      {!selectedP4 && (
        <div style={{
          flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center',
          padding: '2rem 1rem', textAlign: 'center',
          color: 'var(--text-secondary)', fontSize: '0.75rem',
        }}>
          P4-Produkt oben auswählen um Details zu sehen
        </div>
      )}
    </div>
  );
}

// ══════════════════════════════════════════════════════════
// PIEmpireOverview — Main Export
// ══════════════════════════════════════════════════════════

const CHARACTER_IDS = [110592475, 526379435]; // Cytricia, Artallus

export function PIEmpireOverview() {
  const [analysis, setAnalysis] = useState<EmpireAnalysis | null>(null);
  const [schematics, setSchematics] = useState<PISchematicFormula[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedP4, setSelectedP4] = useState<number | null>(null);

  // Load data
  useEffect(() => {
    setLoading(true);
    setError(null);
    Promise.all([
      piApi.getEmpireAnalysis(CHARACTER_IDS),
      piApi.getFormulas(),
    ]).then(([empireData, formulas]) => {
      setAnalysis(empireData);
      setSchematics(formulas);
      // Auto-select the most feasible P4
      if (empireData.p4_feasibility.length > 0) {
        const best = empireData.p4_feasibility.reduce((a, b) =>
          b.feasibility_pct > a.feasibility_pct ? b : a,
        );
        setSelectedP4(best.type_id);
      }
    }).catch(() => {
      setError('Empire-Analyse konnte nicht geladen werden.');
    }).finally(() => setLoading(false));
  }, []);

  // Build DAG for selected P4
  const { nodes: dagNodes, edges: dagEdges } = useMemo(() => {
    if (!selectedP4) return { nodes: [], edges: [] };
    return buildDAG(selectedP4, schematics);
  }, [selectedP4, schematics]);

  // Character name lookup
  const characterNames = useMemo(() => {
    if (!analysis) return {};
    const map: Record<number, string> = {};
    analysis.characters.forEach(c => { map[c.character_id] = c.character_name; });
    return map;
  }, [analysis]);

  // Current P4 feasibility details
  const currentP4 = useMemo(() => {
    if (!analysis || !selectedP4) return null;
    return analysis.p4_feasibility.find(f => f.type_id === selectedP4) || null;
  }, [analysis, selectedP4]);

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-secondary)' }}>
        Empire-Analyse wird geladen...
      </div>
    );
  }

  if (error || !analysis) {
    return (
      <div style={{ textAlign: 'center', padding: '3rem', color: '#f85149' }}>
        {error || 'Keine Daten verfügbar'}
      </div>
    );
  }

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 320px', gap: '1rem', minHeight: 400 }}>
      {/* Left: DAG */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', overflow: 'hidden' }}>
        {/* P4 Selector with Feasibility */}
        <P4FeasibilitySelector
          feasibility={analysis.p4_feasibility}
          selectedId={selectedP4}
          onSelect={setSelectedP4}
        />

        {/* DAG Graph */}
        {dagNodes.length > 0 ? (
          <EmpireDAG
            dagNodes={dagNodes}
            dagEdges={dagEdges}
            productionMap={analysis.production_map}
            factoryOutput={analysis.factory_output}
            characterNames={characterNames}
          />
        ) : (
          <div style={{
            flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: 'var(--text-secondary)', fontSize: '0.8rem',
            background: 'var(--bg-secondary)', border: '1px solid var(--border-color)',
            borderRadius: 8,
          }}>
            P4-Produkt oben auswählen
          </div>
        )}

        {/* Legend */}
        <div style={{
          display: 'flex', gap: '0.75rem', padding: '4px 0',
          fontSize: '0.55rem', color: 'var(--text-secondary)',
          flexWrap: 'wrap',
        }}>
          {[4, 3, 2, 1, 0].map(t => (
            <span key={t} style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
              <span style={{ width: 8, height: 8, borderRadius: 2, background: TIER_COLORS[t] }} />
              {TIER_LABELS[t]}
            </span>
          ))}
          <span style={{ marginLeft: 'auto' }} />
          <span style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: STATUS_COLORS.available }} />
            Verfügbar
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: STATUS_COLORS.factory }} />
            Fabrik
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: STATUS_COLORS.missing }} />
            Fehlt
          </span>
        </div>
      </div>

      {/* Right: Sidebar */}
      <EmpireSidebar
        analysis={analysis}
        selectedP4={currentP4}
      />
    </div>
  );
}