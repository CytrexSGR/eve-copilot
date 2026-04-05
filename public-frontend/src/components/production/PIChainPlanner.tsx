import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { piApi } from '../../services/api/production';
import type {
  PIPlanListItem, PIPlan, PIPlanNode, PIPlanEdge, PIPlanNodeStatus,
} from '../../types/production';
import { PIChainBrowser } from './PIChainBrowser';

// ── Constants ────────────────────────────────────────────

const STATUS_COLORS: Record<string, string> = {
  planning: '#8b949e',
  active: '#3fb950',
  paused: '#d29922',
  completed: '#00d4ff',
};

const TIER_COLORS: Record<number, string> = {
  0: '#8b949e', 1: '#3fb950', 2: '#d29922', 3: '#ff6a00', 4: '#f85149',
};

const NODE_STATUS_COLORS: Record<string, string> = {
  ok: '#3fb950',
  warning: '#d29922',
  critical: '#f85149',
  unassigned: '#8b949e',
};

// ── Helpers ──────────────────────────────────────────────

function formatQty(v: number): string {
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`;
  if (v >= 1_000) return `${(v / 1_000).toFixed(1)}K`;
  return v % 1 === 0 ? v.toFixed(0) : v.toFixed(1);
}

function StatusBadge({ status, small }: { status: string; small?: boolean }) {
  const color = STATUS_COLORS[status] || NODE_STATUS_COLORS[status] || '#8b949e';
  return (
    <span style={{
      fontSize: small ? '0.55rem' : '0.6rem', fontWeight: 700,
      padding: small ? '1px 4px' : '2px 6px', borderRadius: 3,
      color, background: `${color}18`, border: `1px solid ${color}44`,
      textTransform: 'uppercase', letterSpacing: 0.5,
    }}>
      {status}
    </span>
  );
}

function TierBadge({ tier }: { tier: number }) {
  const color = TIER_COLORS[tier] || '#8b949e';
  return (
    <span style={{
      fontSize: '0.55rem', fontWeight: 700, padding: '1px 5px',
      borderRadius: 3, color, background: `${color}18`,
      border: `1px solid ${color}44`, fontFamily: 'monospace',
    }}>
      P{tier}
    </span>
  );
}

// ── Product Search (for adding targets) ─────────────────

interface PISchematicResult {
  schematic_id: number;
  output_type_id: number;
  output_name: string;
  tier: number;
  cycle_time: number;
  output_quantity: number;
  inputs: { type_id: number; type_name: string; quantity: number }[];
}

function ProductSearch({ onSelect }: { onSelect: (typeId: number, name: string) => void }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<PISchematicResult[]>([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(undefined);
  const wrapRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (query.length < 2) { setResults([]); return; }
    debounceRef.current = setTimeout(() => {
      fetch(`/api/pi/formulas/search?q=${encodeURIComponent(query)}&limit=15`)
        .then(r => r.json())
        .then((data: PISchematicResult[]) => { setResults(data); setShowDropdown(true); })
        .catch(() => {});
    }, 250);
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, [query]);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) setShowDropdown(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  return (
    <div ref={wrapRef} style={{ position: 'relative', flex: 1 }}>
      <input
        type="text"
        value={query}
        onChange={e => setQuery(e.target.value)}
        onFocus={() => results.length > 0 && setShowDropdown(true)}
        placeholder="Search PI product..."
        style={{
          width: '100%', padding: '6px 10px', fontSize: '0.8rem',
          background: 'var(--bg-primary)', border: '1px solid var(--border-color)',
          borderRadius: 4, color: 'var(--text-primary)', outline: 'none', boxSizing: 'border-box',
        }}
      />
      {showDropdown && results.length > 0 && (
        <div style={{
          position: 'absolute', top: '100%', left: 0, right: 0, maxHeight: 240, overflowY: 'auto',
          background: 'var(--bg-secondary)', border: '1px solid var(--border-color)',
          borderTop: 'none', borderRadius: '0 0 6px 6px', zIndex: 100,
        }}>
          {results.map(s => (
            <div
              key={s.schematic_id}
              onClick={() => {
                onSelect(s.output_type_id, s.output_name);
                setQuery('');
                setShowDropdown(false);
                setResults([]);
              }}
              style={{
                padding: '6px 10px', cursor: 'pointer', display: 'flex',
                alignItems: 'center', gap: 8, fontSize: '0.8rem',
                borderBottom: '1px solid rgba(255,255,255,0.05)',
              }}
              onMouseEnter={e => (e.currentTarget.style.background = 'var(--bg-elevated)')}
              onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
            >
              <img
                src={`https://images.evetech.net/types/${s.output_type_id}/icon?size=32`}
                alt="" style={{ width: 24, height: 24, borderRadius: 3 }}
                onError={e => { (e.target as HTMLImageElement).style.display = 'none'; }}
              />
              <span style={{ color: TIER_COLORS[s.tier] || '#8b949e', fontWeight: 600 }}>{s.output_name}</span>
              <span style={{ fontSize: '0.6rem', color: 'var(--text-secondary)', marginLeft: 'auto' }}>P{s.tier}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ══════════════════════════════════════════════════════════
// PIChainPlanner — Main Component with Tabs
// ══════════════════════════════════════════════════════════

type PITab = 'plans' | 'browser';

const TAB_ITEMS: { key: PITab; label: string }[] = [
  { key: 'plans', label: 'My Plans' },
  { key: 'browser', label: 'Chain Browser' },
];

export function PIChainPlanner() {
  const [tab, setTab] = useState<PITab>('plans');
  const [selectedPlanId, setSelectedPlanId] = useState<number | null>(null);

  // When plan is created from browser, switch to plans tab and open it
  const handlePlanCreated = (planId: number) => {
    setSelectedPlanId(planId);
    setTab('plans');
  };

  // If viewing a plan detail, skip tabs
  if (selectedPlanId !== null) {
    return (
      <PlanDetail
        planId={selectedPlanId}
        onBack={() => setSelectedPlanId(null)}
      />
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      {/* Tab Bar */}
      <div style={{ display: 'flex', gap: '0.25rem', borderBottom: '1px solid var(--border-color)', paddingBottom: 0 }}>
        {TAB_ITEMS.map(t => {
          const active = tab === t.key;
          return (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              style={{
                padding: '8px 18px', fontSize: '0.8rem', fontWeight: 600,
                cursor: active ? 'default' : 'pointer',
                background: active ? 'var(--bg-secondary)' : 'transparent',
                border: active
                  ? '1px solid var(--border-color)'
                  : '1px solid transparent',
                borderBottom: active ? '1px solid var(--bg-secondary)' : '1px solid transparent',
                borderRadius: '6px 6px 0 0',
                color: active ? '#00d4ff' : 'var(--text-secondary)',
                marginBottom: -1,
              }}
            >
              {t.label}
            </button>
          );
        })}
      </div>

      {/* Tab Content */}
      {tab === 'plans' && <PlanList onSelect={setSelectedPlanId} />}
      {tab === 'browser' && <PIChainBrowser onPlanCreated={handlePlanCreated} />}
    </div>
  );
}

// ══════════════════════════════════════════════════════════
// Plan List View
// ══════════════════════════════════════════════════════════

function PlanList({ onSelect }: { onSelect: (id: number) => void }) {
  const [plans, setPlans] = useState<PIPlanListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState('');
  const [creating, setCreating] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string | null>(null);

  const loadPlans = useCallback(() => {
    setLoading(true);
    piApi.listPlans(statusFilter ?? undefined)
      .then(setPlans)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [statusFilter]);

  useEffect(() => { loadPlans(); }, [loadPlans]);

  const handleCreate = () => {
    if (!newName.trim() || creating) return;
    setCreating(true);
    piApi.createPlan(newName.trim())
      .then(plan => {
        setNewName('');
        setShowCreate(false);
        onSelect(plan.id);
      })
      .catch(() => {})
      .finally(() => setCreating(false));
  };

  const handleDelete = (e: React.MouseEvent, planId: number) => {
    e.stopPropagation();
    piApi.deletePlan(planId).then(() => loadPlans()).catch(() => {});
  };

  if (loading) {
    return <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-secondary)' }}>Loading plans...</div>;
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 700 }}>Chain Planner</h3>
          <p style={{ margin: '2px 0 0', fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
            Plan PI production chains, assign characters, compare actual vs planned
          </p>
        </div>
        <button
          onClick={() => setShowCreate(!showCreate)}
          style={{
            background: 'rgba(0,212,255,0.1)', border: '1px solid rgba(0,212,255,0.3)',
            color: '#00d4ff', padding: '6px 14px', borderRadius: 6,
            cursor: 'pointer', fontSize: '0.8rem', fontWeight: 600,
          }}
        >
          + New Plan
        </button>
      </div>

      {/* Status Filter */}
      <div style={{ display: 'flex', gap: '0.3rem' }}>
        {[null, 'planning', 'active', 'paused', 'completed'].map(s => {
          const active = statusFilter === s;
          const label = s ?? 'All';
          const color = s ? STATUS_COLORS[s] : '#8b949e';
          return (
            <button
              key={label}
              onClick={() => setStatusFilter(s)}
              style={{
                padding: '3px 10px', fontSize: '0.65rem', borderRadius: 4,
                cursor: active ? 'default' : 'pointer', fontWeight: 600,
                textTransform: 'capitalize',
                background: active ? `${color}22` : 'transparent',
                border: `1px solid ${active ? color : 'var(--border-color)'}`,
                color: active ? color : 'var(--text-secondary)',
              }}
            >
              {label}
            </button>
          );
        })}
      </div>

      {/* Create Form */}
      {showCreate && (
        <div style={{
          display: 'flex', gap: '0.5rem', padding: '10px 14px',
          background: 'var(--bg-secondary)', border: '1px solid var(--border-color)',
          borderRadius: 8,
        }}>
          <input
            type="text"
            value={newName}
            onChange={e => setNewName(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleCreate()}
            placeholder="Plan name (e.g. P4 Wetware Farm)"
            autoFocus
            style={{
              flex: 1, padding: '8px 12px', fontSize: '0.85rem',
              background: 'var(--bg-primary)', border: '1px solid var(--border-color)',
              borderRadius: 6, color: 'var(--text-primary)', outline: 'none',
            }}
          />
          <button
            onClick={handleCreate}
            disabled={!newName.trim() || creating}
            style={{
              background: '#3fb950', border: 'none', color: '#000',
              padding: '8px 16px', borderRadius: 6, cursor: 'pointer',
              fontSize: '0.8rem', fontWeight: 700, opacity: newName.trim() ? 1 : 0.4,
            }}
          >
            Create
          </button>
          <button
            onClick={() => { setShowCreate(false); setNewName(''); }}
            style={{
              background: 'transparent', border: '1px solid var(--border-color)',
              color: 'var(--text-secondary)', padding: '8px 12px',
              borderRadius: 6, cursor: 'pointer', fontSize: '0.8rem',
            }}
          >
            Cancel
          </button>
        </div>
      )}

      {/* Plans Grid */}
      {plans.length === 0 ? (
        <div style={{
          textAlign: 'center', padding: '3rem', color: 'var(--text-secondary)',
          border: '1px dashed var(--border-color)', borderRadius: 8,
        }}>
          <p style={{ fontSize: '0.9rem', marginBottom: 4 }}>No plans created yet</p>
          <p style={{ fontSize: '0.75rem' }}>Create a new plan to manage PI production chains.</p>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '0.75rem' }}>
          {plans.map(plan => (
            <div
              key={plan.id}
              onClick={() => onSelect(plan.id)}
              style={{
                padding: '14px', background: 'var(--bg-secondary)',
                border: '1px solid var(--border-color)', borderRadius: 8,
                cursor: 'pointer', transition: 'border-color 0.15s',
              }}
              onMouseEnter={e => (e.currentTarget.style.borderColor = '#00d4ff44')}
              onMouseLeave={e => (e.currentTarget.style.borderColor = 'var(--border-color)')}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                <div>
                  <div style={{ fontWeight: 700, fontSize: '0.9rem', marginBottom: 4 }}>{plan.name}</div>
                  <StatusBadge status={plan.status} />
                </div>
                <button
                  onClick={e => handleDelete(e, plan.id)}
                  style={{
                    background: 'transparent', border: 'none', color: '#f85149',
                    cursor: 'pointer', fontSize: '0.75rem', padding: '2px 6px',
                    opacity: 0.6,
                  }}
                  onMouseEnter={e => (e.currentTarget.style.opacity = '1')}
                  onMouseLeave={e => (e.currentTarget.style.opacity = '0.6')}
                >
                  x
                </button>
              </div>
              <div style={{
                display: 'grid', gridTemplateColumns: '1fr 1fr 1fr',
                gap: '0.25rem', fontSize: '0.7rem',
              }}>
                <div>
                  <div style={{ color: 'var(--text-secondary)', fontSize: '0.6rem' }}>Nodes</div>
                  <div style={{ fontWeight: 600, fontFamily: 'monospace' }}>{plan.node_count}</div>
                </div>
                <div>
                  <div style={{ color: 'var(--text-secondary)', fontSize: '0.6rem' }}>Targets</div>
                  <div style={{ fontWeight: 600, fontFamily: 'monospace' }}>{plan.target_count}</div>
                </div>
                <div>
                  <div style={{ color: 'var(--text-secondary)', fontSize: '0.6rem' }}>Assigned</div>
                  <div style={{ fontWeight: 600, fontFamily: 'monospace', color: plan.assigned_count === plan.node_count && plan.node_count > 0 ? '#3fb950' : 'inherit' }}>
                    {plan.assigned_count}/{plan.node_count}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ══════════════════════════════════════════════════════════
// Plan Detail View — DAG + Assignment + IST/SOLL
// ══════════════════════════════════════════════════════════

function PlanDetail({ planId, onBack }: { planId: number; onBack: () => void }) {
  const [plan, setPlan] = useState<PIPlan | null>(null);
  const [statusData, setStatusData] = useState<PIPlanNodeStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [targetQty, setTargetQty] = useState('1');
  const [selectedNodeId, setSelectedNodeId] = useState<number | null>(null);

  const loadPlan = useCallback(() => {
    setLoading(true);
    Promise.all([
      piApi.getPlan(planId),
      piApi.getStatusCheck(planId),
    ]).then(([planData, status]) => {
      setPlan(planData);
      setStatusData(status);
    }).catch(() => {})
      .finally(() => setLoading(false));
  }, [planId]);

  useEffect(() => { loadPlan(); }, [loadPlan]);

  const handleAddTarget = (typeId: number, _name: string) => {
    const qty = parseFloat(targetQty) || 1;
    piApi.addTarget(planId, typeId, qty)
      .then(() => {
        setTargetQty('1');
        loadPlan();
      })
      .catch(() => {});
  };

  const handleRemoveTarget = (typeId: number) => {
    piApi.removeTarget(planId, typeId).then(() => loadPlan());
  };

  const handleAssign = (nodeId: number, characterId: number | null, planetId: number | null) => {
    piApi.assignNode(planId, nodeId, characterId, planetId).then(() => loadPlan());
  };

  const handleStatusChange = (status: string) => {
    piApi.updatePlanStatus(planId, status).then(() => loadPlan());
  };

  if (loading || !plan) {
    return <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-secondary)' }}>Loading plan...</div>;
  }

  const targets = plan.nodes.filter(n => n.is_target);
  const selectedNode = selectedNodeId ? plan.nodes.find(n => n.id === selectedNodeId) : null;
  const selectedStatus = selectedNodeId ? statusData.find(s => s.id === selectedNodeId) : null;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      {/* Header */}
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        padding: '10px 14px', background: 'var(--bg-secondary)',
        border: '1px solid var(--border-color)', borderRadius: 8,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <button
            onClick={onBack}
            style={{
              background: 'transparent', border: '1px solid var(--border-color)',
              color: 'var(--text-secondary)', padding: '4px 10px',
              borderRadius: 4, cursor: 'pointer', fontSize: '0.8rem',
            }}
          >
            &larr; Back
          </button>
          <div>
            <div style={{ fontWeight: 700, fontSize: '1rem' }}>{plan.name}</div>
            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', marginTop: 2 }}>
              <StatusBadge status={plan.status} />
              <span style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>
                {plan.nodes.length} Nodes · {targets.length} Targets · {plan.edges.length} Edges
              </span>
            </div>
          </div>
        </div>
        <div style={{ display: 'flex', gap: '0.4rem' }}>
          {['planning', 'active', 'paused', 'completed'].map(s => (
            <button
              key={s}
              onClick={() => handleStatusChange(s)}
              disabled={plan.status === s}
              style={{
                padding: '4px 8px', fontSize: '0.6rem', borderRadius: 4,
                cursor: plan.status === s ? 'default' : 'pointer',
                background: plan.status === s ? `${STATUS_COLORS[s]}22` : 'transparent',
                border: `1px solid ${plan.status === s ? STATUS_COLORS[s] : 'var(--border-color)'}`,
                color: plan.status === s ? STATUS_COLORS[s] : 'var(--text-secondary)',
                fontWeight: 600, textTransform: 'capitalize',
              }}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {/* Add Target */}
      <div style={{
        display: 'flex', gap: '0.5rem', alignItems: 'center',
        padding: '8px 14px', background: 'var(--bg-secondary)',
        border: '1px solid var(--border-color)', borderRadius: 8,
      }}>
        <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>
          + Target:
        </span>
        <ProductSearch onSelect={handleAddTarget} />
        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <input
            type="number"
            value={targetQty}
            onChange={e => setTargetQty(e.target.value)}
            min="0.01" step="0.1"
            style={{
              width: 60, padding: '4px 6px', fontSize: '0.8rem',
              background: 'var(--bg-primary)', border: '1px solid var(--border-color)',
              borderRadius: 4, color: 'var(--text-primary)', outline: 'none', textAlign: 'right',
            }}
          />
          <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>/h</span>
        </div>
      </div>

      {/* Target Chips */}
      {targets.length > 0 && (
        <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
          {targets.map(t => (
            <span key={t.id} style={{
              display: 'inline-flex', alignItems: 'center', gap: 4,
              padding: '3px 8px', fontSize: '0.7rem', fontWeight: 600,
              background: 'rgba(248,81,73,0.1)', border: '1px solid rgba(248,81,73,0.3)',
              borderRadius: 4, color: '#f85149',
            }}>
              <img
                src={`https://images.evetech.net/types/${t.type_id}/icon?size=32`}
                alt="" style={{ width: 18, height: 18, borderRadius: 2 }}
                onError={e => { (e.target as HTMLImageElement).style.display = 'none'; }}
              />
              <TierBadge tier={t.tier} />
              {t.type_name} ({formatQty(t.soll_qty_per_hour)}/h)
              <button
                onClick={() => handleRemoveTarget(t.type_id)}
                style={{
                  background: 'none', border: 'none', color: '#f85149',
                  cursor: 'pointer', padding: '0 2px', fontSize: '0.65rem',
                }}
              >x</button>
            </span>
          ))}
        </div>
      )}

      {/* DAG Graph + Status Panel */}
      {plan.nodes.length > 0 && (
        <div style={{ display: 'grid', gridTemplateColumns: selectedNode ? '1fr 300px' : '1fr', gap: '1rem' }}>
          <DAGGraph
            nodes={plan.nodes}
            edges={plan.edges}
            statusData={statusData}
            selectedNodeId={selectedNodeId}
            onSelectNode={setSelectedNodeId}
          />
          {selectedNode && (
            <NodeDetailPanel
              node={selectedNode}
              status={selectedStatus || null}
              onAssign={handleAssign}
              onClose={() => setSelectedNodeId(null)}
            />
          )}
        </div>
      )}

      {/* IST/SOLL Status Table */}
      {statusData.length > 0 && (
        <StatusTable data={statusData} onSelectNode={setSelectedNodeId} />
      )}
    </div>
  );
}

// ══════════════════════════════════════════════════════════
// DAG Graph (SVG) — Tier-based layout
// ══════════════════════════════════════════════════════════

const NODE_W = 130;
const NODE_H = 42;
const H_GAP = 14;
const V_GAP = 42;
const PAD = 16;

const EDGE_TIER_COLORS: Record<number, string> = {
  0: 'rgba(139,148,158,0.3)',
  1: 'rgba(63,185,80,0.3)',
  2: 'rgba(210,153,34,0.3)',
  3: 'rgba(255,106,0,0.3)',
  4: 'rgba(248,81,73,0.3)',
};

const EDGE_TIER_COLORS_BRIGHT: Record<number, string> = {
  0: 'rgba(139,148,158,0.85)',
  1: 'rgba(63,185,80,0.85)',
  2: 'rgba(210,153,34,0.85)',
  3: 'rgba(255,106,0,0.85)',
  4: 'rgba(248,81,73,0.85)',
};

/** BFS trace all connected node IDs from a starting node */
function traceConnectedNodes(
  startId: number,
  edges: PIPlanEdge[],
): Set<number> {
  const visited = new Set<number>();
  visited.add(startId);
  // Forward (source → target)
  const fwd = [startId];
  while (fwd.length > 0) {
    const cur = fwd.shift()!;
    for (const e of edges) {
      if (e.target_node_id === cur && !visited.has(e.source_node_id)) {
        visited.add(e.source_node_id);
        fwd.push(e.source_node_id);
      }
    }
  }
  // Backward (target → source)
  const bwd = [startId];
  while (bwd.length > 0) {
    const cur = bwd.shift()!;
    for (const e of edges) {
      if (e.source_node_id === cur && !visited.has(e.target_node_id)) {
        visited.add(e.target_node_id);
        bwd.push(e.target_node_id);
      }
    }
  }
  return visited;
}

function DAGGraph({
  nodes, edges, statusData, selectedNodeId, onSelectNode,
}: {
  nodes: PIPlanNode[];
  edges: PIPlanEdge[];
  statusData: PIPlanNodeStatus[];
  selectedNodeId: number | null;
  onSelectNode: (id: number) => void;
}) {
  const [hoveredNodeId, setHoveredNodeId] = useState<number | null>(null);

  const statusMap = useMemo(() => {
    const m: Record<number, PIPlanNodeStatus> = {};
    statusData.forEach(s => { m[s.id] = s; });
    return m;
  }, [statusData]);

  const nodeById = useMemo(() => {
    const m: Record<number, PIPlanNode> = {};
    nodes.forEach(n => { m[n.id] = n; });
    return m;
  }, [nodes]);

  const highlightedNodes = useMemo(() => {
    if (hoveredNodeId === null) return null;
    return traceConnectedNodes(hoveredNodeId, edges);
  }, [hoveredNodeId, edges]);

  // Group nodes by tier (descending: highest tier at top)
  const tiers = useMemo(() => {
    const tierMap: Record<number, PIPlanNode[]> = {};
    nodes.forEach(n => {
      if (!tierMap[n.tier]) tierMap[n.tier] = [];
      tierMap[n.tier].push(n);
    });
    return Object.keys(tierMap)
      .map(Number)
      .sort((a, b) => b - a)
      .map(tier => ({ tier, nodes: tierMap[tier] }));
  }, [nodes]);

  // Calculate positions
  const positions = useMemo(() => {
    const pos: Record<number, { x: number; y: number }> = {};
    tiers.forEach((row, rowIdx) => {
      const totalWidth = row.nodes.length * NODE_W + (row.nodes.length - 1) * H_GAP;
      const startX = PAD + (tiers.reduce((max, r) => Math.max(max, r.nodes.length), 0) * (NODE_W + H_GAP) - H_GAP - totalWidth) / 2;
      row.nodes.forEach((node, colIdx) => {
        pos[node.id] = {
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
        borderRadius: 8, overflow: 'auto', maxHeight: 500,
      }}
      onMouseLeave={() => setHoveredNodeId(null)}
    >
      <svg width={svgWidth} height={svgHeight} style={{ display: 'block' }}>
        {/* Bezier Edges */}
        {edges.map(edge => {
          const from = positions[edge.source_node_id];
          const to = positions[edge.target_node_id];
          if (!from || !to) return null;

          const x1 = from.x + NODE_W / 2;
          const y1 = from.y + NODE_H;
          const x2 = to.x + NODE_W / 2;
          const y2 = to.y;
          const midY = (y1 + y2) / 2;

          const targetNode = nodeById[edge.target_node_id];
          const tier = targetNode?.tier ?? 0;

          const edgeHighlighted = isHovering &&
            highlightedNodes!.has(edge.source_node_id) &&
            highlightedNodes!.has(edge.target_node_id);
          const edgeDimmed = isHovering && !edgeHighlighted;

          return (
            <path
              key={edge.id}
              d={`M ${x1} ${y1} C ${x1} ${midY}, ${x2} ${midY}, ${x2} ${y2}`}
              stroke={edgeHighlighted
                ? (EDGE_TIER_COLORS_BRIGHT[tier] || 'rgba(255,255,255,0.85)')
                : (EDGE_TIER_COLORS[tier] || 'rgba(255,255,255,0.15)')}
              strokeWidth={edgeHighlighted ? 2.5 : 1.5}
              fill="none"
              opacity={edgeDimmed ? 0.12 : 1}
              style={{ transition: 'opacity 0.15s, stroke-width 0.15s' }}
            />
          );
        })}
        {/* Nodes */}
        {nodes.map(node => {
          const p = positions[node.id];
          if (!p) return null;
          const st = statusMap[node.id];
          const stColor = st ? NODE_STATUS_COLORS[st.status] : '#8b949e';
          const isSelected = node.id === selectedNodeId;
          const tierColor = TIER_COLORS[node.tier] || '#8b949e';
          const nodeHighlighted = isHovering && highlightedNodes!.has(node.id);
          const nodeDimmed = isHovering && !nodeHighlighted;

          return (
            <g
              key={node.id}
              onClick={() => onSelectNode(node.id)}
              onMouseEnter={() => setHoveredNodeId(node.id)}
              style={{
                cursor: 'pointer',
                opacity: nodeDimmed ? 0.25 : 1,
                transition: 'opacity 0.15s',
              }}
            >
              <rect
                x={p.x} y={p.y} width={NODE_W} height={NODE_H}
                rx={6} fill="var(--bg-primary)"
                stroke={isSelected ? '#00d4ff' : nodeHighlighted ? tierColor : stColor}
                strokeWidth={isSelected ? 2 : nodeHighlighted ? 2 : 1}
              />
              {/* Status indicator dot */}
              <circle cx={p.x + 8} cy={p.y + 8} r={3.5} fill={stColor} />
              {/* Item icon */}
              <image
                href={`https://images.evetech.net/types/${node.type_id}/icon?size=32`}
                x={p.x + 16} y={p.y + 1} width={14} height={14}
              />
              {/* Tier badge */}
              <text
                x={p.x + NODE_W - 6} y={p.y + 11}
                fill={tierColor} fontSize={9} fontWeight={700}
                textAnchor="end" fontFamily="monospace"
              >
                P{node.tier}
              </text>
              {/* Name */}
              <text
                x={p.x + NODE_W / 2} y={p.y + 22}
                fill={nodeHighlighted ? '#fff' : 'var(--text-primary)'} fontSize={10} fontWeight={600}
                textAnchor="middle"
              >
                {node.type_name.length > 16 ? node.type_name.slice(0, 15) + '…' : node.type_name}
              </text>
              {/* Qty */}
              <text
                x={p.x + NODE_W / 2} y={p.y + 34}
                fill="var(--text-secondary)" fontSize={9}
                textAnchor="middle" fontFamily="monospace"
              >
                {formatQty(node.soll_qty_per_hour)}/h
                {st && st.status !== 'unassigned' && (
                  <tspan fill={stColor}> ({formatQty(st.ist_qty_per_hour)})</tspan>
                )}
              </text>
              {/* Target marker */}
              {node.is_target && (
                <text
                  x={p.x + 18} y={p.y + 11}
                  fill="#f85149" fontSize={8} fontWeight={700}
                >
                  TARGET
                </text>
              )}
            </g>
          );
        })}
      </svg>
    </div>
  );
}

// ══════════════════════════════════════════════════════════
// Node Detail Panel — Assignment + Status
// ══════════════════════════════════════════════════════════

const CHARACTERS = [
  { id: 526379435, name: 'Artallus' },
  { id: 110592475, name: 'Cytricia' },
];

function NodeDetailPanel({
  node, status, onAssign, onClose,
}: {
  node: PIPlanNode;
  status: PIPlanNodeStatus | null;
  onAssign: (nodeId: number, charId: number | null, planetId: number | null) => void;
  onClose: () => void;
}) {
  const [charId, setCharId] = useState<string>(node.character_id?.toString() || '');
  const [planetId, setPlanetId] = useState<string>(node.planet_id?.toString() || '');

  useEffect(() => {
    setCharId(node.character_id?.toString() || '');
    setPlanetId(node.planet_id?.toString() || '');
  }, [node.id, node.character_id, node.planet_id]);

  const handleSave = () => {
    onAssign(
      node.id,
      charId ? parseInt(charId) : null,
      planetId ? parseInt(planetId) : null,
    );
  };

  const stColor = status ? NODE_STATUS_COLORS[status.status] : '#8b949e';

  return (
    <div style={{
      background: 'var(--bg-secondary)', border: '1px solid var(--border-color)',
      borderRadius: 8, padding: '14px', display: 'flex', flexDirection: 'column', gap: '0.75rem',
    }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
            <img
              src={`https://images.evetech.net/types/${node.type_id}/icon?size=32`}
              alt="" style={{ width: 28, height: 28, borderRadius: 4 }}
              onError={e => { (e.target as HTMLImageElement).style.display = 'none'; }}
            />
            <div>
              <div style={{ fontWeight: 700, fontSize: '0.85rem' }}>{node.type_name}</div>
              <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
                <TierBadge tier={node.tier} />
                {node.is_target && <span style={{ fontSize: '0.55rem', color: '#f85149', fontWeight: 700 }}>TARGET</span>}
              </div>
            </div>
          </div>
        </div>
        <button onClick={onClose} style={{
          background: 'none', border: 'none', color: 'var(--text-secondary)',
          cursor: 'pointer', fontSize: '1rem', padding: 0, lineHeight: 1,
        }}>x</button>
      </div>

      {/* Status */}
      {status && (
        <div style={{
          padding: '8px 10px', borderRadius: 6,
          background: `${stColor}08`, border: `1px solid ${stColor}33`,
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
            <StatusBadge status={status.status} />
            <span style={{ fontSize: '0.7rem', fontFamily: 'monospace', color: stColor }}>
              {status.delta_percent > 0 ? '+' : ''}{status.delta_percent}%
            </span>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.25rem', fontSize: '0.7rem' }}>
            <div>
              <div style={{ color: 'var(--text-secondary)', fontSize: '0.6rem' }}>SOLL</div>
              <div style={{ fontFamily: 'monospace', fontWeight: 600 }}>{formatQty(node.soll_qty_per_hour)}/h</div>
            </div>
            <div>
              <div style={{ color: 'var(--text-secondary)', fontSize: '0.6rem' }}>IST</div>
              <div style={{ fontFamily: 'monospace', fontWeight: 600, color: stColor }}>
                {formatQty(status.ist_qty_per_hour)}/h
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Assignment */}
      <div>
        <div style={{ fontSize: '0.65rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: 1 }}>
          Assignment
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
          <select
            value={charId}
            onChange={e => setCharId(e.target.value)}
            style={{
              padding: '6px 8px', fontSize: '0.8rem',
              background: 'var(--bg-primary)', border: '1px solid var(--border-color)',
              borderRadius: 4, color: 'var(--text-primary)', outline: 'none',
            }}
          >
            <option value="">-- No Character --</option>
            {CHARACTERS.map(c => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
          <input
            type="number"
            value={planetId}
            onChange={e => setPlanetId(e.target.value)}
            placeholder="Planet ID"
            style={{
              padding: '6px 8px', fontSize: '0.8rem',
              background: 'var(--bg-primary)', border: '1px solid var(--border-color)',
              borderRadius: 4, color: 'var(--text-primary)', outline: 'none',
            }}
          />
          <button onClick={handleSave} style={{
            background: 'rgba(0,212,255,0.1)', border: '1px solid rgba(0,212,255,0.3)',
            color: '#00d4ff', padding: '6px 12px', borderRadius: 4,
            cursor: 'pointer', fontSize: '0.75rem', fontWeight: 600,
          }}>
            Assign
          </button>
        </div>
      </div>
    </div>
  );
}

// ══════════════════════════════════════════════════════════
// IST/SOLL Status Table
// ══════════════════════════════════════════════════════════

function StatusTable({
  data, onSelectNode,
}: {
  data: PIPlanNodeStatus[];
  onSelectNode: (id: number) => void;
}) {
  const summary = useMemo(() => {
    const s = { ok: 0, warning: 0, critical: 0, unassigned: 0 };
    data.forEach(d => { if (d.status in s) s[d.status as keyof typeof s]++; });
    return s;
  }, [data]);

  return (
    <div style={{
      border: '1px solid var(--border-color)', borderRadius: 8, overflow: 'hidden',
    }}>
      {/* Summary Header */}
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        padding: '8px 14px', background: 'var(--bg-secondary)',
        borderBottom: '1px solid var(--border-color)',
      }}>
        <span style={{ fontSize: '0.75rem', fontWeight: 700 }}>IST/SOLL Status</span>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          {(['ok', 'warning', 'critical', 'unassigned'] as const).map(s => (
            <span key={s} style={{
              fontSize: '0.6rem', fontWeight: 600, fontFamily: 'monospace',
              color: NODE_STATUS_COLORS[s],
            }}>
              {summary[s]} {s}
            </span>
          ))}
        </div>
      </div>

      {/* Table Header */}
      <div style={{
        display: 'grid', gridTemplateColumns: '2.5rem 28px 1fr 5rem 5rem 4rem 5rem',
        gap: '0.5rem', padding: '4px 14px', fontSize: '0.6rem',
        color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: 1,
        fontWeight: 600, borderBottom: '1px solid rgba(255,255,255,0.05)',
      }}>
        <span>Tier</span><span /><span>Material</span>
        <span style={{ textAlign: 'right' }}>SOLL/h</span>
        <span style={{ textAlign: 'right' }}>IST/h</span>
        <span style={{ textAlign: 'right' }}>Delta</span>
        <span>Status</span>
      </div>

      {/* Rows */}
      {data.map(node => {
        const stColor = NODE_STATUS_COLORS[node.status];
        return (
          <div
            key={node.id}
            onClick={() => onSelectNode(node.id)}
            style={{
              display: 'grid', gridTemplateColumns: '2.5rem 28px 1fr 5rem 5rem 4rem 5rem',
              gap: '0.5rem', padding: '6px 14px', fontSize: '0.75rem',
              borderBottom: '1px solid rgba(255,255,255,0.03)',
              cursor: 'pointer', alignItems: 'center',
            }}
            onMouseEnter={e => (e.currentTarget.style.background = 'var(--bg-elevated)')}
            onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
          >
            <TierBadge tier={node.tier} />
            <img
              src={`https://images.evetech.net/types/${node.type_id}/icon?size=32`}
              alt="" style={{ width: 24, height: 24, borderRadius: 3 }}
              onError={e => { (e.target as HTMLImageElement).style.display = 'none'; }}
            />
            <span style={{ fontWeight: 500, display: 'flex', alignItems: 'center', gap: 4 }}>
              {node.type_name}
              {node.is_target && <span style={{ fontSize: '0.5rem', color: '#f85149', fontWeight: 700 }}>T</span>}
            </span>
            <span style={{ textAlign: 'right', fontFamily: 'monospace' }}>
              {formatQty(node.soll_qty_per_hour)}
            </span>
            <span style={{ textAlign: 'right', fontFamily: 'monospace', color: stColor }}>
              {formatQty(node.ist_qty_per_hour)}
            </span>
            <span style={{
              textAlign: 'right', fontFamily: 'monospace', fontSize: '0.7rem',
              color: node.delta_percent >= 0 ? '#3fb950' : stColor,
            }}>
              {node.delta_percent > 0 ? '+' : ''}{node.delta_percent}%
            </span>
            <StatusBadge status={node.status} small />
          </div>
        );
      })}
    </div>
  );
}
