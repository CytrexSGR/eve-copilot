import { useState, useEffect } from 'react';
import type { ItemSearchResult } from '../../types/market';
import type {
  PIRequirementsResponse,
  PIRequirementMaterial,
  PIRequirementP0,
  PIRequirementChainNode,
} from '../../types/production';
import { PI_PLANET_COLORS } from '../../types/production';
import { piApi } from '../../services/api/production';
import { PIChainPlanner } from './PIChainPlanner';
import { PIEmpireOverview } from './PIEmpireOverview';
import { PIProductionChainViz, buildChainDataFromRequirements } from './PIProductionChainViz';

type PISubTab = 'analyse' | 'planner' | 'empire';

interface PITabProps {
  selectedItem: ItemSearchResult | null;
}

const TIER_COLORS: Record<number, string> = {
  1: '#8b949e',
  2: '#3fb950',
  3: '#d29922',
  4: '#f85149',
};

function formatISK(value: number): string {
  if (value >= 1_000_000_000) return `${(value / 1_000_000_000).toFixed(1)}B`;
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
  return value.toFixed(0);
}

function formatQty(value: number): string {
  return value.toLocaleString('en-US', { maximumFractionDigits: 0 });
}

// ─── Planet Badge ───
function PlanetBadge({ planet }: { planet: string }) {
  const color = PI_PLANET_COLORS[planet] || '#8b949e';
  return (
    <span style={{
      fontSize: '0.6rem', fontWeight: 600, padding: '1px 5px',
      borderRadius: 3, color, background: `${color}22`,
      border: `1px solid ${color}44`, textTransform: 'capitalize',
    }}>
      {planet}
    </span>
  );
}

// ─── Tier Badge ───
function TierBadge({ tier }: { tier: number }) {
  const color = TIER_COLORS[tier] || '#8b949e';
  return (
    <span style={{
      fontSize: '0.6rem', fontWeight: 700, padding: '1px 6px',
      borderRadius: 3, color, background: `${color}18`,
      border: `1px solid ${color}44`, fontFamily: 'monospace',
    }}>
      P{tier}
    </span>
  );
}

// ─── Chain Tree Node ───
function ChainNode({ node, depth }: { node: PIRequirementChainNode; depth: number }) {
  const indent = depth * 20;
  const isP0 = node.tier === 0;
  const tierColor = TIER_COLORS[node.tier] || '#8b949e';

  return (
    <>
      <div style={{
        display: 'flex', alignItems: 'center', gap: '0.4rem',
        paddingLeft: indent, paddingTop: 3, paddingBottom: 3,
        fontSize: '0.75rem',
      }}>
        {depth > 0 && (
          <span style={{ color: 'var(--text-secondary)', fontSize: '0.65rem' }}>
            {isP0 ? '\u2514' : '\u251C'}\u2500\u2500
          </span>
        )}
        <TierBadge tier={node.tier} />
        <span style={{ color: tierColor, fontWeight: 500 }}>{node.type_name}</span>
        <span style={{ color: 'var(--text-secondary)', fontFamily: 'monospace', fontSize: '0.7rem' }}>
          x{formatQty(node.quantity_needed)}
        </span>
        {isP0 && node.planet_sources && (
          <span style={{ display: 'flex', gap: 3, marginLeft: 4 }}>
            {node.planet_sources.map(p => <PlanetBadge key={p} planet={p} />)}
          </span>
        )}
      </div>
      {node.children.map((child, i) => (
        <ChainNode key={`${child.type_id}-${i}`} node={child} depth={depth + 1} />
      ))}
    </>
  );
}

// ─── Material Row (expandable) ───
function MaterialRow({ mat }: { mat: PIRequirementMaterial }) {
  const [expanded, setExpanded] = useState(false);
  const tierColor = TIER_COLORS[mat.tier] || '#8b949e';

  return (
    <div style={{
      border: '1px solid var(--border-color)', borderRadius: 6,
      marginBottom: 6, overflow: 'hidden',
    }}>
      <div
        onClick={() => setExpanded(!expanded)}
        style={{
          display: 'grid', gridTemplateColumns: '32px 2.5rem 1fr auto auto auto',
          alignItems: 'center', gap: '0.5rem', padding: '8px 12px',
          cursor: 'pointer', background: expanded ? 'var(--bg-elevated)' : 'transparent',
        }}
        onMouseEnter={e => { if (!expanded) e.currentTarget.style.background = 'var(--bg-elevated)'; }}
        onMouseLeave={e => { if (!expanded) e.currentTarget.style.background = 'transparent'; }}
      >
        <img
          src={`https://images.evetech.net/types/${mat.type_id}/icon?size=32`}
          alt=""
          style={{ width: 28, height: 28, borderRadius: 4 }}
          onError={e => { (e.target as HTMLImageElement).style.display = 'none'; }}
        />
        <TierBadge tier={mat.tier} />
        <span style={{ fontWeight: 600, fontSize: '0.8rem', color: tierColor }}>
          {mat.type_name}
        </span>
        <span style={{ fontFamily: 'monospace', fontSize: '0.75rem', color: 'var(--text-secondary)', textAlign: 'right' }}>
          x{formatQty(mat.quantity)}
        </span>
        <span style={{ fontFamily: 'monospace', fontSize: '0.75rem', textAlign: 'right', minWidth: 60 }}>
          {formatISK(mat.unit_price)}
        </span>
        <span style={{ fontFamily: 'monospace', fontSize: '0.75rem', fontWeight: 600, textAlign: 'right', minWidth: 70, color: '#3fb950' }}>
          {formatISK(mat.total_cost)}
        </span>
      </div>

      {expanded && mat.pi_chain && (
        <div style={{
          padding: '8px 12px 10px 12px',
          background: 'rgba(0,0,0,0.15)',
          borderTop: '1px solid var(--border-color)',
        }}>
          <div style={{ fontSize: '0.65rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: 1 }}>
            Production Chain
          </div>
          <ChainNode node={mat.pi_chain} depth={0} />
        </div>
      )}
    </div>
  );
}

// ─── P0 Summary Table ───
function P0Summary({ materials }: { materials: PIRequirementP0[] }) {
  if (!materials.length) return null;
  return (
    <div style={{
      border: '1px solid var(--border-color)', borderRadius: 8,
      overflow: 'hidden',
    }}>
      <div style={{
        padding: '8px 12px', fontSize: '0.7rem', fontWeight: 700,
        textTransform: 'uppercase', letterSpacing: 1,
        color: 'var(--text-secondary)', background: 'var(--bg-secondary)',
        borderBottom: '1px solid var(--border-color)',
      }}>
        Raw Resources (P0)
      </div>
      <div style={{ padding: '4px 0' }}>
        {materials.map(p0 => (
          <div key={p0.type_id} style={{
            display: 'grid', gridTemplateColumns: '1fr auto 1fr',
            alignItems: 'center', gap: '0.5rem',
            padding: '5px 12px', fontSize: '0.75rem',
            borderBottom: '1px solid rgba(255,255,255,0.03)',
          }}>
            <span style={{ fontWeight: 500 }}>{p0.type_name}</span>
            <span style={{ fontFamily: 'monospace', color: 'var(--text-secondary)' }}>
              {formatQty(p0.quantity)}
            </span>
            <span style={{ display: 'flex', gap: 3, flexWrap: 'wrap' }}>
              {p0.planet_sources.map(ps => <PlanetBadge key={ps} planet={ps} />)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Item Analysis Sub-Component ───
export function PIItemAnalysis({ selectedItem }: { selectedItem: ItemSearchResult }) {
  const [data, setData] = useState<PIRequirementsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    setData(null);
    piApi.getItemPIRequirements(selectedItem.typeID)
      .then(setData)
      .catch(err => {
        if (err?.response?.status === 404) {
          setError('No production data available for this item.');
        } else {
          setError('Failed to load PI requirements.');
        }
      })
      .finally(() => setLoading(false));
  }, [selectedItem.typeID]);

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-secondary)' }}>
        Loading PI requirements...
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-secondary)' }}>
        {error}
      </div>
    );
  }

  if (!data || data.pi_materials.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-secondary)' }}>
        <p style={{ fontSize: '1rem', marginBottom: 4 }}>This item does not require any PI materials</p>
        <p style={{ fontSize: '0.75rem' }}>Only T2 ships, modules, and some advanced items use planetary commodities.</p>
      </div>
    );
  }

  const { columns, connections, typeIds, p0PlanetMap } = buildChainDataFromRequirements(data);
  const hasChainData = Object.keys(columns).length > 0 && connections.length > 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      {/* Header */}
      <div style={{
        display: 'flex', alignItems: 'baseline', justifyContent: 'space-between',
        padding: '10px 14px', background: 'var(--bg-secondary)',
        border: '1px solid var(--border-color)', borderRadius: 8,
      }}>
        <div>
          <span style={{ fontWeight: 700, fontSize: '0.9rem' }}>
            PI Materials for {data.type_name}
          </span>
          <span style={{
            marginLeft: 8, fontSize: '0.7rem', fontWeight: 600,
            color: data.pi_cost_percentage > 5 ? '#f85149' : data.pi_cost_percentage > 2 ? '#d29922' : '#3fb950',
          }}>
            {data.pi_cost_percentage}% of production cost
          </span>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>Total PI Cost</div>
          <div style={{ fontFamily: 'monospace', fontWeight: 700, fontSize: '0.85rem', color: '#3fb950' }}>
            {formatISK(data.total_pi_cost)} ISK
          </div>
        </div>
      </div>

      {/* Production Chain Visualization */}
      {hasChainData && (
        <PIProductionChainViz
          tierColumns={columns}
          connections={connections}
          chainTypeIds={typeIds}
          p0PlanetMap={p0PlanetMap}
          title={`PI Production Chains for ${data.type_name}`}
        />
      )}

      {/* Materials Cost Table */}
      <div>
        <div style={{
          display: 'grid', gridTemplateColumns: '32px 2.5rem 1fr auto auto auto',
          gap: '0.5rem', padding: '4px 12px', fontSize: '0.6rem',
          color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: 1,
          fontWeight: 600,
        }}>
          <span />
          <span>Tier</span>
          <span>Material</span>
          <span style={{ textAlign: 'right' }}>Qty</span>
          <span style={{ textAlign: 'right', minWidth: 60 }}>Price</span>
          <span style={{ textAlign: 'right', minWidth: 70 }}>Total</span>
        </div>
        {data.pi_materials.map(mat => (
          <MaterialRow key={mat.type_id} mat={mat} />
        ))}
      </div>

      {/* P0 Summary */}
      <P0Summary materials={data.p0_summary} />
    </div>
  );
}

// ─── Main Component (Sub-Tab Router) ───
export function PITab({ selectedItem }: PITabProps) {
  const [subTab, setSubTab] = useState<PISubTab>(selectedItem ? 'analyse' : 'empire');

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      {/* Sub-Tab Selector */}
      <div style={{
        display: 'flex', gap: '0.25rem',
        borderBottom: '1px solid var(--border-color)', paddingBottom: '0.4rem',
      }}>
        <button
          onClick={() => setSubTab('analyse')}
          disabled={!selectedItem}
          style={{
            padding: '0.4rem 0.8rem',
            background: 'transparent',
            border: 'none',
            borderBottom: subTab === 'analyse' ? '2px solid #3fb950' : '2px solid transparent',
            color: subTab === 'analyse' ? '#3fb950' : 'var(--text-secondary)',
            cursor: selectedItem ? 'pointer' : 'default',
            fontSize: '0.8rem',
            fontWeight: subTab === 'analyse' ? 600 : 400,
            opacity: selectedItem ? 1 : 0.4,
          }}
        >
          Item-Analyse
        </button>
        <button
          onClick={() => setSubTab('planner')}
          style={{
            padding: '0.4rem 0.8rem',
            background: 'transparent',
            border: 'none',
            borderBottom: subTab === 'planner' ? '2px solid #a855f7' : '2px solid transparent',
            color: subTab === 'planner' ? '#a855f7' : 'var(--text-secondary)',
            cursor: 'pointer',
            fontSize: '0.8rem',
            fontWeight: subTab === 'planner' ? 600 : 400,
          }}
        >
          Chain Planner
        </button>
        <button
          onClick={() => setSubTab('empire')}
          style={{
            padding: '0.4rem 0.8rem',
            background: 'transparent',
            border: 'none',
            borderBottom: subTab === 'empire' ? '2px solid #d4a017' : '2px solid transparent',
            color: subTab === 'empire' ? '#d4a017' : 'var(--text-secondary)',
            cursor: 'pointer',
            fontSize: '0.8rem',
            fontWeight: subTab === 'empire' ? 600 : 400,
          }}
        >
          Empire
        </button>
      </div>

      {/* Sub-Tab Content */}
      {subTab === 'analyse' && selectedItem && (
        <PIItemAnalysis selectedItem={selectedItem} />
      )}
      {subTab === 'analyse' && !selectedItem && (
        <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-secondary)' }}>
          <p style={{ fontSize: '1rem', marginBottom: 4 }}>Select an item above to view PI requirements</p>
          <p style={{ fontSize: '0.75rem' }}>Or switch to the Chain Planner tab to manage production chains.</p>
        </div>
      )}
      {subTab === 'planner' && <PIChainPlanner />}
      {subTab === 'empire' && <PIEmpireOverview />}
    </div>
  );
}
