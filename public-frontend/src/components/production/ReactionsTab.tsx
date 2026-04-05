import { useState, useEffect } from 'react';
import type { ItemSearchResult } from '../../types/market';
import type {
  ReactionRequirementsResponse,
  ReactionRequirementMaterial,
  ReactionChainNode,
  MoonGooSummary,
} from '../../types/production';
import { reactionsApi } from '../../services/api/production';

interface ReactionsTabProps {
  selectedItem: ItemSearchResult;
}

const CATEGORY_COLORS: Record<string, string> = {
  composite: '#ff8800',
  simple: '#3fb950',
  polymer: '#00d4ff',
  biochemical: '#a855f7',
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

// --- Category Badge ---
function CategoryBadge({ category }: { category: string }) {
  const color = CATEGORY_COLORS[category] || '#8b949e';
  const label = category.charAt(0).toUpperCase() + category.slice(1);
  return (
    <span style={{
      fontSize: '0.6rem', fontWeight: 700, padding: '1px 6px',
      borderRadius: 3, color, background: `${color}18`,
      border: `1px solid ${color}44`, fontFamily: 'monospace',
    }}>
      {label}
    </span>
  );
}

// --- Chain Tree Node (recursive) ---
function ChainNodeView({ node, depth }: { node: ReactionChainNode; depth: number }) {
  const indent = depth * 20;
  const isMoonGoo = node.is_moon_goo;
  const isLeaf = node.children.length === 0;
  const catColor = node.reaction_category ? CATEGORY_COLORS[node.reaction_category] || '#8b949e' : '#8b949e';

  return (
    <>
      <div style={{
        display: 'flex', alignItems: 'center', gap: '0.4rem',
        paddingLeft: indent, paddingTop: 3, paddingBottom: 3,
        fontSize: '0.75rem',
      }}>
        {depth > 0 && (
          <span style={{ color: 'var(--text-secondary)', fontSize: '0.65rem' }}>
            {isLeaf ? '\u2514' : '\u251C'}{'\u2500\u2500'}
          </span>
        )}
        {isMoonGoo ? (
          <span style={{
            fontSize: '0.6rem', fontWeight: 700, padding: '1px 6px',
            borderRadius: 3, color: '#a855f7', background: '#a855f718',
            border: '1px solid #a855f744', fontFamily: 'monospace',
          }}>
            Moon
          </span>
        ) : node.reaction_category ? (
          <CategoryBadge category={node.reaction_category} />
        ) : null}
        <span style={{ color: isMoonGoo ? '#a855f7' : catColor, fontWeight: 500 }}>
          {node.type_name}
        </span>
        <span style={{ color: 'var(--text-secondary)', fontFamily: 'monospace', fontSize: '0.7rem' }}>
          x{formatQty(node.quantity_needed)}
        </span>
        {node.runs_needed != null && (
          <span style={{ color: 'var(--text-secondary)', fontSize: '0.6rem' }}>
            ({formatQty(node.runs_needed)} runs)
          </span>
        )}
      </div>
      {node.children.map((child, i) => (
        <ChainNodeView key={`${child.type_id}-${i}`} node={child} depth={depth + 1} />
      ))}
    </>
  );
}

// --- Material Row (expandable) ---
function MaterialRow({ mat }: { mat: ReactionRequirementMaterial }) {
  const [expanded, setExpanded] = useState(false);
  const catColor = CATEGORY_COLORS[mat.reaction_category] || '#8b949e';

  return (
    <div style={{
      border: '1px solid var(--border-color)', borderRadius: 6,
      marginBottom: 6, overflow: 'hidden',
    }}>
      <div
        onClick={() => setExpanded(!expanded)}
        style={{
          display: 'grid', gridTemplateColumns: '32px 4.5rem 1fr auto auto auto',
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
        <CategoryBadge category={mat.reaction_category} />
        <span style={{ fontWeight: 600, fontSize: '0.8rem', color: catColor }}>
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

      {expanded && mat.reaction_chain && (
        <div style={{
          padding: '8px 12px 10px 12px',
          background: 'rgba(0,0,0,0.15)',
          borderTop: '1px solid var(--border-color)',
        }}>
          <div style={{ fontSize: '0.65rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: 1 }}>
            Reaction Chain
          </div>
          <ChainNodeView node={mat.reaction_chain} depth={0} />
        </div>
      )}
    </div>
  );
}

// --- Moon Goo Summary Table ---
function MoonGooSummaryTable({ materials }: { materials: MoonGooSummary[] }) {
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
        Raw Moon Materials
      </div>
      <div style={{ padding: '4px 0' }}>
        {materials.map(m => (
          <div key={m.type_id} style={{
            display: 'grid', gridTemplateColumns: '1fr auto',
            alignItems: 'center', gap: '0.5rem',
            padding: '5px 12px', fontSize: '0.75rem',
            borderBottom: '1px solid rgba(255,255,255,0.03)',
          }}>
            <span style={{ fontWeight: 500, color: '#a855f7' }}>{m.type_name}</span>
            <span style={{ fontFamily: 'monospace', color: 'var(--text-secondary)' }}>
              {formatQty(m.quantity)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

// --- Main Component ---
export function ReactionsTab({ selectedItem }: ReactionsTabProps) {
  const [data, setData] = useState<ReactionRequirementsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    setData(null);
    reactionsApi.getItemReactionRequirements(selectedItem.typeID)
      .then(setData)
      .catch(err => {
        if (err?.response?.status === 404) {
          setError('No production data available for this item.');
        } else {
          setError('Failed to load reaction requirements.');
        }
      })
      .finally(() => setLoading(false));
  }, [selectedItem.typeID]);

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-secondary)' }}>
        Loading reaction requirements...
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

  if (!data || data.reaction_materials.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-secondary)' }}>
        <p style={{ fontSize: '1rem', marginBottom: 4 }}>This item does not require any reaction materials</p>
        <p style={{ fontSize: '0.75rem' }}>Only T2 ships, modules, and some advanced items use reaction products in their manufacturing.</p>
      </div>
    );
  }

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
            Reaction Materials for {data.type_name}
          </span>
          <span style={{
            marginLeft: 8, fontSize: '0.7rem', fontWeight: 600,
            color: data.reaction_cost_percentage > 50 ? '#f85149' : data.reaction_cost_percentage > 20 ? '#d29922' : '#3fb950',
          }}>
            {data.reaction_cost_percentage}% of production cost
          </span>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>Total Reaction Cost</div>
          <div style={{ fontFamily: 'monospace', fontWeight: 700, fontSize: '0.85rem', color: '#3fb950' }}>
            {formatISK(data.total_reaction_cost)} ISK
          </div>
        </div>
      </div>

      {/* Column Headers */}
      <div>
        <div style={{
          display: 'grid', gridTemplateColumns: '32px 4.5rem 1fr auto auto auto',
          gap: '0.5rem', padding: '4px 12px', fontSize: '0.6rem',
          color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: 1,
          fontWeight: 600,
        }}>
          <span />
          <span>Type</span>
          <span>Material</span>
          <span style={{ textAlign: 'right' }}>Qty</span>
          <span style={{ textAlign: 'right', minWidth: 60 }}>Price</span>
          <span style={{ textAlign: 'right', minWidth: 70 }}>Total</span>
        </div>
        {data.reaction_materials.map(mat => (
          <MaterialRow key={mat.type_id} mat={mat} />
        ))}
      </div>

      {/* Moon Goo Summary */}
      <MoonGooSummaryTable materials={data.moon_goo_summary} />
    </div>
  );
}
