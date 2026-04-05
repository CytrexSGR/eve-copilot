import { useRef, useState, useLayoutEffect, useCallback } from 'react';
import { PI_PLANET_COLORS } from '../../types/production';
import type {
  PIAdvisorOpportunity,
  PIProductionChain,
  PIChainPrice,
  PIRequirementsResponse,
  PIRequirementChainNode,
} from '../../types/production';

// ─── Shared Types ───

export interface ChainItem {
  name: string;
  subtitle?: string;
}

export interface Connection {
  from: string;
  fromTier: number;
  to: string;
  toTier: number;
}

interface SvgLine {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  color: string;
}

// ─── Constants ───

const TIER_BADGE_COLORS: Record<number, string> = {
  1: '#8b949e',
  2: '#3fb950',
  3: '#58a6ff',
  4: '#00d4ff',
};

const TIER_LABELS: Record<number, string> = {
  0: 'P0 (Raw)',
  1: 'P1 (Basic)',
  2: 'P2 (Refined)',
  3: 'P3 (Specialized)',
  4: 'P4 (Advanced)',
};

const CONNECTION_COLORS: Record<number, string> = {
  1: 'rgba(139,148,158,0.35)',
  2: 'rgba(63,185,80,0.35)',
  3: 'rgba(88,166,255,0.35)',
  4: 'rgba(0,212,255,0.35)',
};

const CONNECTION_COLORS_BRIGHT: Record<number, string> = {
  1: 'rgba(139,148,158,0.8)',
  2: 'rgba(63,185,80,0.8)',
  3: 'rgba(88,166,255,0.8)',
  4: 'rgba(0,212,255,0.8)',
};

const EVE_ICON = (typeId: number, size = 32) =>
  `https://images.evetech.net/types/${typeId}/icon?size=${size}`;

function formatISK(value: number): string {
  if (value >= 1_000_000_000) return `${(value / 1_000_000_000).toFixed(1)}B`;
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
  return value.toFixed(0);
}

function formatVolume(vol: number): string {
  if (vol >= 1_000_000) return `${(vol / 1_000_000).toFixed(1)}M`;
  if (vol >= 1_000) return `${(vol / 1_000).toFixed(0)}K`;
  return vol.toString();
}

// ─── Graph Helpers ───

function traceConnectedItems(startKey: string, connections: Connection[]): Set<string> {
  const visited = new Set<string>();
  visited.add(startKey);
  const fwdQueue = [startKey];
  while (fwdQueue.length > 0) {
    const current = fwdQueue.shift()!;
    for (const conn of connections) {
      const fromKey = `${conn.fromTier}-${conn.from}`;
      const toKey = `${conn.toTier}-${conn.to}`;
      if (fromKey === current && !visited.has(toKey)) {
        visited.add(toKey);
        fwdQueue.push(toKey);
      }
    }
  }
  const bwdQueue = [startKey];
  while (bwdQueue.length > 0) {
    const current = bwdQueue.shift()!;
    for (const conn of connections) {
      const fromKey = `${conn.fromTier}-${conn.from}`;
      const toKey = `${conn.toTier}-${conn.to}`;
      if (toKey === current && !visited.has(fromKey)) {
        visited.add(fromKey);
        bwdQueue.push(fromKey);
      }
    }
  }
  return visited;
}

function isConnectionHighlighted(conn: Connection, highlightedItems: Set<string>): boolean {
  return highlightedItems.has(`${conn.fromTier}-${conn.from}`) &&
         highlightedItems.has(`${conn.toTier}-${conn.to}`);
}

// ─── Data Builders ───

/** Build tier columns + connections from PIAdvisorOpportunity data */
export function buildChainDataFromAdvisor(
  opp: PIAdvisorOpportunity,
  chain: PIProductionChain,
): { columns: Record<number, ChainItem[]>; connections: Connection[] } {
  const columns: Record<number, ChainItem[]> = {};
  const connections: Connection[] = [];

  const p0Names = (opp.p0_materials || []).map(m => m.type_name);
  if (p0Names.length > 0) columns[0] = p0Names.map(name => ({ name }));

  const p1Set = new Set<string>();
  for (const [p0, p1] of Object.entries(chain.p0_to_p1)) {
    p1Set.add(p1);
    connections.push({ from: p0, fromTier: 0, to: p1, toTier: 1 });
  }
  if (p1Set.size > 0) columns[1] = [...p1Set].sort().map(name => ({ name }));

  for (const recipe of chain.recipes) {
    if (!columns[recipe.tier]) columns[recipe.tier] = [];
    columns[recipe.tier].push({ name: recipe.output, subtitle: recipe.inputs.join(' + ') });
    const inputTier = recipe.tier - 1;
    for (const input of recipe.inputs) {
      connections.push({ from: input, fromTier: inputTier, to: recipe.output, toTier: recipe.tier });
    }
  }

  for (const tier of Object.keys(columns).map(Number)) {
    columns[tier].sort((a, b) => {
      if (a.name === opp.type_name) return 1;
      if (b.name === opp.type_name) return -1;
      return a.name.localeCompare(b.name);
    });
  }

  return { columns, connections };
}

/** Build tier columns + connections from PIRequirementsResponse (item analysis) */
export function buildChainDataFromRequirements(
  data: PIRequirementsResponse,
): {
  columns: Record<number, ChainItem[]>;
  connections: Connection[];
  typeIds: Record<string, number>;
  p0PlanetMap: Record<string, string[]>;
} {
  const itemsByTier: Record<number, Map<string, ChainItem>> = {};
  const connections: Connection[] = [];
  const typeIds: Record<string, number> = {};
  const p0PlanetMap: Record<string, string[]> = {};
  const connSet = new Set<string>();

  function walkTree(node: PIRequirementChainNode, parentName?: string, parentTier?: number) {
    const tier = node.tier;
    if (!itemsByTier[tier]) itemsByTier[tier] = new Map();

    typeIds[node.type_name] = node.type_id;

    if (!itemsByTier[tier].has(node.type_name)) {
      const subtitle = tier >= 2 && node.children.length > 0
        ? node.children.map(c => c.type_name).join(' + ')
        : undefined;
      itemsByTier[tier].set(node.type_name, { name: node.type_name, subtitle });
    }

    if (tier === 0 && node.planet_sources?.length) {
      p0PlanetMap[node.type_name] = node.planet_sources;
    }

    if (parentName !== undefined && parentTier !== undefined) {
      const key = `${tier}-${node.type_name}->${parentTier}-${parentName}`;
      if (!connSet.has(key)) {
        connSet.add(key);
        connections.push({ from: node.type_name, fromTier: tier, to: parentName, toTier: parentTier });
      }
    }

    for (const child of node.children) {
      walkTree(child, node.type_name, tier);
    }
  }

  for (const mat of data.pi_materials) {
    if (mat.pi_chain) walkTree(mat.pi_chain);
  }

  const columns: Record<number, ChainItem[]> = {};
  for (const [tier, map] of Object.entries(itemsByTier)) {
    columns[Number(tier)] = [...map.values()].sort((a, b) => a.name.localeCompare(b.name));
  }

  return { columns, connections, typeIds, p0PlanetMap };
}

// ─── Main Visualization Component ───

export interface PIProductionChainVizProps {
  tierColumns: Record<number, ChainItem[]>;
  connections: Connection[];
  finalProduct?: { name: string; tier: number };
  p0PlanetMap?: Record<string, string[]>;
  chainPrices?: Record<string, PIChainPrice>;
  chainTypeIds?: Record<string, number>;
  title?: string;
}

export function PIProductionChainViz({
  tierColumns,
  connections,
  finalProduct,
  p0PlanetMap = {},
  chainPrices = {},
  chainTypeIds = {},
  title = 'Production Chain',
}: PIProductionChainVizProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [lines, setLines] = useState<SvgLine[]>([]);
  const [containerSize, setContainerSize] = useState({ w: 0, h: 0 });
  const [hoveredItem, setHoveredItem] = useState<string | null>(null);

  const presentTiers = Object.keys(tierColumns).map(Number).sort();

  const highlightedItems = hoveredItem
    ? traceConnectedItems(hoveredItem, connections)
    : null;

  const measureAndDraw = useCallback(() => {
    const container = containerRef.current;
    if (!container) return;

    const rect = container.getBoundingClientRect();
    setContainerSize({ w: rect.width, h: rect.height });

    const newLines: SvgLine[] = [];
    for (const conn of connections) {
      const fromEl = container.querySelector(`[data-chain-item="${conn.fromTier}-${conn.from}"]`);
      const toEl = container.querySelector(`[data-chain-item="${conn.toTier}-${conn.to}"]`);
      if (!fromEl || !toEl) continue;

      const fromRect = (fromEl as HTMLElement).getBoundingClientRect();
      const toRect = (toEl as HTMLElement).getBoundingClientRect();

      newLines.push({
        x1: fromRect.right - rect.left,
        y1: fromRect.top + fromRect.height / 2 - rect.top,
        x2: toRect.left - rect.left,
        y2: toRect.top + toRect.height / 2 - rect.top,
        color: CONNECTION_COLORS[conn.toTier] || 'rgba(255,255,255,0.2)',
      });
    }
    setLines(newLines);
  }, [connections]);

  useLayoutEffect(() => {
    measureAndDraw();
  }, [measureAndDraw]);

  const isHovering = highlightedItems !== null;

  if (presentTiers.length === 0) return null;

  return (
    <div style={{
      padding: '1rem 1.25rem', marginBottom: '1rem',
      background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: 8,
    }}>
      <div style={{
        fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase',
        color: 'var(--text-secondary)', letterSpacing: '0.05em', marginBottom: '0.75rem',
      }}>
        {title}
      </div>

      <div
        ref={containerRef}
        onMouseLeave={() => setHoveredItem(null)}
        style={{
          display: 'flex',
          gap: 0,
          overflowX: 'auto',
          paddingBottom: '0.5rem',
          position: 'relative',
        }}
      >
        {/* SVG connection lines */}
        {containerSize.w > 0 && (
          <svg
            style={{
              position: 'absolute', top: 0, left: 0,
              width: containerSize.w, height: containerSize.h,
              pointerEvents: 'none', zIndex: 1,
            }}
          >
            {lines.map((line, i) => {
              const conn = connections[i];
              const highlighted = isHovering && conn && isConnectionHighlighted(conn, highlightedItems!);
              const dimmed = isHovering && !highlighted;
              const midX = (line.x1 + line.x2) / 2;
              return (
                <path
                  key={i}
                  d={`M ${line.x1} ${line.y1} C ${midX} ${line.y1}, ${midX} ${line.y2}, ${line.x2} ${line.y2}`}
                  stroke={highlighted
                    ? (CONNECTION_COLORS_BRIGHT[conn.toTier] || 'rgba(255,255,255,0.8)')
                    : line.color}
                  strokeWidth={highlighted ? 2.5 : 1.5}
                  fill="none"
                  opacity={dimmed ? 0.15 : 1}
                  style={{ transition: 'opacity 0.15s, stroke-width 0.15s' }}
                />
              );
            })}
          </svg>
        )}

        {/* Tier columns */}
        {presentTiers.map((tier, idx) => (
          <div key={tier} style={{ display: 'flex', alignItems: 'stretch', position: 'relative', zIndex: 2 }}>
            <div style={{ minWidth: 170, maxWidth: 230 }}>
              {/* Column header */}
              <div style={{
                fontSize: '0.6rem', fontWeight: 700, textTransform: 'uppercase',
                padding: '4px 8px', marginBottom: '0.4rem', textAlign: 'center',
                background: `${TIER_BADGE_COLORS[tier] || '#8b949e'}15`,
                border: `1px solid ${TIER_BADGE_COLORS[tier] || '#8b949e'}33`,
                borderRadius: 4,
                color: TIER_BADGE_COLORS[tier] || '#8b949e',
              }}>
                {TIER_LABELS[tier] || `P${tier}`}
              </div>

              {/* Items */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
                {tierColumns[tier].map(item => {
                  const isFinal = finalProduct && tier === finalProduct.tier && item.name === finalProduct.name;
                  const planetSources = tier === 0 ? (p0PlanetMap[item.name] || []) : [];
                  const itemKey = `${tier}-${item.name}`;
                  const isItemHighlighted = isHovering && highlightedItems!.has(itemKey);
                  const isItemDimmed = isHovering && !isItemHighlighted;

                  return (
                    <div
                      key={item.name}
                      data-chain-item={itemKey}
                      onMouseEnter={() => setHoveredItem(itemKey)}
                      style={{
                        padding: '0.35rem 0.5rem',
                        background: isItemHighlighted
                          ? (isFinal ? 'rgba(0,212,255,0.15)' : 'rgba(255,255,255,0.08)')
                          : (isFinal ? 'rgba(0,212,255,0.08)' : 'rgba(255,255,255,0.03)'),
                        border: `1px solid ${
                          isItemHighlighted
                            ? (TIER_BADGE_COLORS[tier] || '#8b949e') + '88'
                            : isFinal ? 'rgba(0,212,255,0.4)' : 'rgba(255,255,255,0.06)'
                        }`,
                        borderRadius: 4,
                        borderLeft: tier === 0 && planetSources.length > 0
                          ? `3px solid ${PI_PLANET_COLORS[planetSources[0]] || '#8b949e'}`
                          : undefined,
                        opacity: isItemDimmed ? 0.3 : 1,
                        transition: 'opacity 0.15s, background 0.15s, border-color 0.15s',
                        cursor: 'default',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                        {chainTypeIds[item.name] && (
                          <img
                            src={EVE_ICON(chainTypeIds[item.name])}
                            alt=""
                            style={{
                              width: 20, height: 20, borderRadius: 3, flexShrink: 0,
                              opacity: isItemDimmed ? 0.4 : 1,
                            }}
                            onError={e => { (e.target as HTMLImageElement).style.display = 'none'; }}
                          />
                        )}
                        <span style={{
                          fontSize: '0.75rem', fontWeight: isFinal || isItemHighlighted ? 700 : 600,
                          color: isFinal ? '#00d4ff' : isItemHighlighted ? '#fff' : '#ccc',
                          flex: 1,
                        }}>
                          {item.name}
                        </span>
                      </div>

                      {/* Planet badges for P0 items */}
                      {tier === 0 && planetSources.length > 0 && (
                        <div style={{ display: 'flex', gap: '0.2rem', marginTop: '0.15rem', flexWrap: 'wrap' }}>
                          {planetSources.map(pt => {
                            const pc = PI_PLANET_COLORS[pt] || '#8b949e';
                            return (
                              <span key={pt} style={{
                                fontSize: '0.5rem', fontWeight: 700, padding: '0px 4px',
                                borderRadius: 2, background: `${pc}20`, color: pc,
                                textTransform: 'capitalize', lineHeight: '1.3',
                              }}>
                                {pt}
                              </span>
                            );
                          })}
                        </div>
                      )}

                      {/* Input subtitle for P2+ items */}
                      {item.subtitle && (
                        <div style={{ fontSize: '0.6rem', color: '#8b949e', marginTop: '0.1rem' }}>
                          &larr; {item.subtitle}
                        </div>
                      )}

                      {/* Price + Volume */}
                      {(() => {
                        const p = chainPrices[item.name];
                        if (!p) return null;
                        return (
                          <div style={{
                            display: 'flex', gap: '0.4rem', marginTop: '0.15rem',
                            fontSize: '0.55rem', fontFamily: 'monospace', color: '#8b949e',
                          }}>
                            {p.price != null && <span>{formatISK(p.price)}</span>}
                            {p.volume_m3 != null && (
                              <span>{p.volume_m3 < 0.1 ? p.volume_m3.toFixed(3) : p.volume_m3 < 1 ? p.volume_m3.toFixed(2) : p.volume_m3.toFixed(1)} m³</span>
                            )}
                            {p.daily_volume > 0 && (
                              <span style={{ color: '#6e7681' }}>{formatVolume(p.daily_volume)}/d</span>
                            )}
                          </div>
                        );
                      })()}
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Gap between columns */}
            {idx < presentTiers.length - 1 && <div style={{ minWidth: 40 }} />}
          </div>
        ))}
      </div>
    </div>
  );
}
