import { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { projectApi } from '../services/api/production';
import { marketApi } from '../services/api/market';
import { formatISK } from '../utils/format';
import { PlannerTab } from '../components/production';
import type { ProjectDetail as ProjectDetailType, ProjectItem, ProjectShoppingList, ProjectMaterialDecision } from '../types/production';
import type { ItemSearchResult } from '../types/market';

type DetailTab = 'items' | 'planner' | 'shopping';

const STATUS_COLORS: Record<string, string> = {
  draft: '#8b949e',
  active: '#3fb950',
  complete: '#00d4ff',
};

const ITEM_STATUS_COLORS: Record<string, string> = {
  pending: '#8b949e',
  planned: '#d29922',
  complete: '#3fb950',
};

const STATUS_OPTIONS = ['draft', 'active', 'complete'];

export function ProjectDetail() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const [project, setProject] = useState<ProjectDetailType | null>(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<DetailTab>('items');
  const [plannerItemId, setPlannerItemId] = useState<number | null>(null);
  const [shoppingList, setShoppingList] = useState<ProjectShoppingList | null>(null);
  const [shoppingLoading, setShoppingLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [shoppingVersion, setShoppingVersion] = useState(0);

  // Add item form
  const [showAddItem, setShowAddItem] = useState(false);
  const [addQuery, setAddQuery] = useState('');
  const [addResults, setAddResults] = useState<ItemSearchResult[]>([]);
  const [addSelected, setAddSelected] = useState<ItemSearchResult | null>(null);
  const [addQty, setAddQty] = useState(1);
  const [addME, setAddME] = useState(10);
  const [addShowDropdown, setAddShowDropdown] = useState(false);
  const [adding, setAdding] = useState(false);
  const searchRef = useRef<HTMLDivElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(undefined);
  const saveDebounceRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  const pid = projectId ? parseInt(projectId, 10) : 0;

  const loadProject = useCallback(async () => {
    if (!pid) return;
    setLoading(true);
    try {
      const data = await projectApi.get(pid);
      setProject(data);
    } catch {
      setProject(null);
    } finally {
      setLoading(false);
    }
  }, [pid]);

  useEffect(() => {
    loadProject();
  }, [loadProject]);

  // Search for add item
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (addQuery.length < 2) { setAddResults([]); return; }
    debounceRef.current = setTimeout(() => {
      marketApi.searchItems(addQuery)
        .then(data => { setAddResults(data.results); setAddShowDropdown(true); })
        .catch(() => {});
    }, 300);
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, [addQuery]);

  // Close add item dropdown on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) {
        setAddShowDropdown(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  // Load shopping list when tab changes or decisions are saved
  useEffect(() => {
    if (tab !== 'shopping' || !pid) return;
    setShoppingLoading(true);
    projectApi.getShoppingList(pid)
      .then(setShoppingList)
      .catch(() => setShoppingList(null))
      .finally(() => setShoppingLoading(false));
  }, [tab, pid, shoppingVersion]);

  const handleStatusChange = async (status: string) => {
    if (!project) return;
    try {
      const updated = await projectApi.update(project.id, { status });
      setProject(updated);
    } catch { /* ignore */ }
  };

  const handleDelete = async () => {
    if (!project || !confirm('Delete this project? This cannot be undone.')) return;
    try {
      await projectApi.delete(project.id);
      navigate('/production/projects');
    } catch { /* ignore */ }
  };

  const handleAddItem = async () => {
    if (!project || !addSelected) return;
    setAdding(true);
    try {
      await projectApi.addItem(project.id, {
        type_id: addSelected.typeID,
        quantity: addQty,
        me_level: addME,
      });
      setShowAddItem(false);
      setAddQuery('');
      setAddSelected(null);
      setAddQty(1);
      setAddME(10);
      await loadProject();
    } catch { /* ignore */ }
    finally { setAdding(false); }
  };

  const handleDeleteItem = async (itemId: number) => {
    if (!project) return;
    try {
      await projectApi.deleteItem(project.id, itemId);
      await loadProject();
    } catch { /* ignore */ }
  };

  const handlePlanItem = (item: ProjectItem) => {
    setPlannerItemId(item.id);
    setTab('planner');
  };

  const handleDecisionsChanged = useCallback((
    itemId: number,
    _overrides: Set<number>,
    shoppingItems: Array<{ type_id: number; name: string; quantity: number }>
  ) => {
    if (saveDebounceRef.current) clearTimeout(saveDebounceRef.current);
    saveDebounceRef.current = setTimeout(async () => {
      // Save ALL shopping items as 'buy' decisions (raw materials + overridden components)
      const decisions: ProjectMaterialDecision[] = shoppingItems.map(item => ({
        material_type_id: item.type_id,
        decision: 'buy' as const,
        quantity: item.quantity,
      }));
      try {
        await projectApi.saveDecisions(itemId, decisions);
        setShoppingVersion(v => v + 1);
        // Mark as planned if decisions exist
        if (project && decisions.length > 0) {
          const item = project.items.find(i => i.id === itemId);
          if (item && item.status === 'pending') {
            await projectApi.updateItem(project.id, itemId, { status: 'planned' });
            await loadProject();
          }
        }
      } catch { /* ignore */ }
    }, 500);
  }, [project, loadProject]);

  const copyMultibuy = useCallback(() => {
    if (!shoppingList?.items?.length) return;
    const lines = shoppingList.items.map(m => `${m.type_name}\t${m.total_quantity}`);
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
  }, [shoppingList]);

  if (loading) {
    return (
      <div style={{ maxWidth: 1200, margin: '0 auto', padding: '1.5rem 1rem' }}>
        <div className="skeleton" style={{ height: 60, marginBottom: '1rem', borderRadius: 8 }} />
        <div className="skeleton" style={{ height: 400, borderRadius: 8 }} />
      </div>
    );
  }

  if (!project) {
    return (
      <div style={{ maxWidth: 1200, margin: '0 auto', padding: '3rem 1rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
        <p>Project not found.</p>
        <button
          onClick={() => navigate('/production/projects')}
          style={{ marginTop: '1rem', padding: '6px 14px', fontSize: '0.82rem', background: 'rgba(0,212,255,0.1)', border: '1px solid rgba(0,212,255,0.3)', borderRadius: 4, color: '#00d4ff', cursor: 'pointer' }}
        >
          Back to Projects
        </button>
      </div>
    );
  }

  const selectedPlannerItem = plannerItemId ? project.items.find(i => i.id === plannerItemId) : null;

  const TABS: { id: DetailTab; label: string }[] = [
    { id: 'items', label: 'Items' },
    { id: 'planner', label: 'Planner' },
    { id: 'shopping', label: 'Shopping List' },
  ];

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto', padding: '1.5rem 1rem' }}>
      {/* Back link */}
      <button
        onClick={() => navigate('/production/projects')}
        style={{
          background: 'none',
          border: 'none',
          color: 'var(--text-secondary)',
          fontSize: '0.78rem',
          cursor: 'pointer',
          padding: '0',
          marginBottom: '1rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.3rem',
        }}
      >
        &larr; All Projects
      </button>

      {/* Project Header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: '1rem',
        padding: '0.75rem 1rem',
        background: '#12121a',
        border: '1px solid rgba(255,255,255,0.06)',
        borderRadius: 8,
        flexWrap: 'wrap',
        gap: '0.75rem',
      }}>
        <div style={{ flex: 1, minWidth: 200 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
            <h1 style={{ margin: 0, fontSize: '1.2rem', fontWeight: 700 }}>{project.name}</h1>
            <span style={{
              fontSize: '0.6rem',
              fontWeight: 700,
              padding: '2px 8px',
              borderRadius: 3,
              textTransform: 'uppercase',
              letterSpacing: '0.04em',
              background: `${STATUS_COLORS[project.status]}18`,
              border: `1px solid ${STATUS_COLORS[project.status]}44`,
              color: STATUS_COLORS[project.status],
            }}>
              {project.status}
            </span>
          </div>
          {project.description && (
            <p style={{ margin: 0, fontSize: '0.78rem', color: 'var(--text-secondary)' }}>{project.description}</p>
          )}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <select
            value={project.status}
            onChange={e => handleStatusChange(e.target.value)}
            style={{
              padding: '5px 8px',
              fontSize: '0.75rem',
              background: '#1a1a24',
              border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: 4,
              color: 'var(--text-primary)',
              outline: 'none',
              cursor: 'pointer',
              colorScheme: 'dark',
            }}
          >
            {STATUS_OPTIONS.map(s => (
              <option key={s} value={s} style={{ background: '#1a1a24', color: '#e6edf3' }}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
            ))}
          </select>
          <button
            onClick={handleDelete}
            style={{
              padding: '5px 10px',
              fontSize: '0.72rem',
              fontWeight: 600,
              background: 'rgba(248,81,73,0.08)',
              border: '1px solid rgba(248,81,73,0.25)',
              borderRadius: 4,
              color: '#f85149',
              cursor: 'pointer',
            }}
          >
            Delete
          </button>
        </div>
      </div>

      {/* Tab Navigation */}
      <div style={{
        display: 'flex',
        gap: '0.25rem',
        marginBottom: '1rem',
        borderBottom: '1px solid var(--border-color)',
        paddingBottom: '0.5rem',
      }}>
        {TABS.map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            style={{
              padding: '0.5rem 1rem',
              background: 'transparent',
              border: 'none',
              borderBottom: tab === t.id ? '2px solid #00d4ff' : '2px solid transparent',
              color: tab === t.id ? '#00d4ff' : 'var(--text-secondary)',
              cursor: 'pointer',
              fontSize: '0.85rem',
              fontWeight: tab === t.id ? 600 : 400,
            }}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Items Tab */}
      {tab === 'items' && (
        <div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
            <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
              {project.items.length} item{project.items.length !== 1 ? 's' : ''} in project
            </span>
            <button
              onClick={() => setShowAddItem(true)}
              style={{
                padding: '5px 12px',
                fontSize: '0.75rem',
                fontWeight: 600,
                background: 'rgba(0,212,255,0.1)',
                border: '1px solid rgba(0,212,255,0.3)',
                borderRadius: 4,
                color: '#00d4ff',
                cursor: 'pointer',
              }}
            >
              + Add Item
            </button>
          </div>

          {/* Add Item Form */}
          {showAddItem && (
            <div style={{
              marginBottom: '1rem',
              padding: '0.85rem',
              background: '#12121a',
              border: '1px solid rgba(255,255,255,0.06)',
              borderRadius: 8,
            }}>
              <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'flex-end', flexWrap: 'wrap' }}>
                <div ref={searchRef} style={{ flex: 1, minWidth: 200, position: 'relative' }}>
                  <label style={labelStyle}>Search Item</label>
                  <input
                    type="text"
                    value={addQuery}
                    onChange={e => { setAddQuery(e.target.value); setAddSelected(null); }}
                    onFocus={() => addResults.length > 0 && setAddShowDropdown(true)}
                    placeholder="Search items..."
                    autoFocus
                    style={inputStyle}
                  />
                  {addShowDropdown && addResults.length > 0 && (
                    <div style={{
                      position: 'absolute', top: '100%', left: 0, right: 0,
                      maxHeight: 240, overflowY: 'auto',
                      background: 'var(--bg-secondary)',
                      border: '1px solid var(--border-color)',
                      borderTop: 'none', borderRadius: '0 0 8px 8px',
                      zIndex: 100,
                    }}>
                      {addResults.slice(0, 15).map(item => (
                        <div
                          key={item.typeID}
                          onClick={() => {
                            setAddSelected(item);
                            setAddQuery(item.typeName);
                            setAddShowDropdown(false);
                          }}
                          style={{
                            padding: '8px 12px', cursor: 'pointer',
                            display: 'flex', alignItems: 'center', gap: '8px',
                            borderBottom: '1px solid rgba(255,255,255,0.04)',
                          }}
                          onMouseEnter={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.04)')}
                          onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                        >
                          <img
                            src={`https://images.evetech.net/types/${item.typeID}/icon?size=32`}
                            alt=""
                            style={{ width: 24, height: 24, borderRadius: 3 }}
                            onError={e => { (e.target as HTMLImageElement).style.display = 'none'; }}
                          />
                          <div>
                            <div style={{ fontSize: '0.8rem', fontWeight: 500 }}>{item.typeName}</div>
                            <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>{item.groupName}</div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
                <div style={{ width: 80 }}>
                  <label style={labelStyle}>Quantity</label>
                  <input
                    type="number"
                    min={1}
                    value={addQty}
                    onChange={e => setAddQty(Math.max(1, parseInt(e.target.value) || 1))}
                    style={{ ...inputStyle, textAlign: 'center', fontFamily: 'monospace' }}
                  />
                </div>
                <div style={{ width: 60 }}>
                  <label style={labelStyle}>ME</label>
                  <input
                    type="number"
                    min={0}
                    max={10}
                    value={addME}
                    onChange={e => setAddME(Math.max(0, Math.min(10, parseInt(e.target.value) || 0)))}
                    style={{ ...inputStyle, textAlign: 'center', fontFamily: 'monospace' }}
                  />
                </div>
                <div style={{ display: 'flex', gap: '0.4rem' }}>
                  <button
                    onClick={handleAddItem}
                    disabled={!addSelected || adding}
                    style={{
                      padding: '7px 14px',
                      fontSize: '0.78rem',
                      fontWeight: 600,
                      background: addSelected && !adding ? 'rgba(63,185,80,0.15)' : 'rgba(255,255,255,0.03)',
                      border: `1px solid ${addSelected && !adding ? 'rgba(63,185,80,0.4)' : 'rgba(255,255,255,0.08)'}`,
                      borderRadius: 4,
                      color: addSelected && !adding ? '#3fb950' : 'var(--text-secondary)',
                      cursor: addSelected && !adding ? 'pointer' : 'not-allowed',
                    }}
                  >
                    {adding ? 'Adding...' : 'Add'}
                  </button>
                  <button
                    onClick={() => { setShowAddItem(false); setAddQuery(''); setAddSelected(null); }}
                    style={{
                      padding: '7px 10px',
                      fontSize: '0.78rem',
                      background: 'transparent',
                      border: '1px solid rgba(255,255,255,0.08)',
                      borderRadius: 4,
                      color: 'var(--text-secondary)',
                      cursor: 'pointer',
                    }}
                  >
                    Cancel
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Items Table */}
          {project.items.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '3rem 1rem', color: 'var(--text-secondary)' }}>
              <p style={{ fontSize: '0.9rem', marginBottom: '0.5rem' }}>No items in this project yet.</p>
              <p style={{ fontSize: '0.78rem' }}>Add items to start planning your production.</p>
            </div>
          ) : (
            <div style={{
              background: '#12121a',
              border: '1px solid rgba(255,255,255,0.06)',
              borderRadius: 8,
              overflow: 'hidden',
            }}>
              {/* Table Header */}
              <div style={{
                display: 'grid',
                gridTemplateColumns: '36px 1fr 80px 50px 70px 120px',
                gap: '0.5rem',
                padding: '0.5rem 0.85rem',
                borderBottom: '1px solid rgba(255,255,255,0.06)',
                background: 'rgba(255,255,255,0.015)',
                fontSize: '0.58rem',
                fontWeight: 700,
                color: 'rgba(139,148,158,0.7)',
                textTransform: 'uppercase',
                letterSpacing: '0.06em',
                alignItems: 'center',
              }}>
                <div />
                <div>Name</div>
                <div style={{ textAlign: 'right' }}>Qty</div>
                <div style={{ textAlign: 'center' }}>ME</div>
                <div style={{ textAlign: 'center' }}>Status</div>
                <div style={{ textAlign: 'right' }}>Actions</div>
              </div>

              {/* Rows */}
              {project.items.map((item, i) => (
                <div
                  key={item.id}
                  style={{
                    display: 'grid',
                    gridTemplateColumns: '36px 1fr 80px 50px 70px 120px',
                    gap: '0.5rem',
                    padding: '0.5rem 0.85rem',
                    alignItems: 'center',
                    background: i % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.015)',
                    transition: 'background 0.1s',
                  }}
                  onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.03)'; }}
                  onMouseLeave={e => { e.currentTarget.style.background = i % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.015)'; }}
                >
                  <img
                    src={`https://images.evetech.net/types/${item.type_id}/icon?size=32`}
                    alt=""
                    style={{ width: 28, height: 28, borderRadius: 4, border: '1px solid rgba(255,255,255,0.06)' }}
                    onError={e => { (e.target as HTMLImageElement).style.display = 'none'; }}
                  />
                  <div style={{ fontSize: '0.82rem', fontWeight: 500 }}>
                    {item.type_name}
                  </div>
                  <div style={{
                    fontSize: '0.78rem',
                    fontFamily: 'monospace',
                    textAlign: 'right',
                    color: 'var(--text-primary)',
                  }}>
                    {item.quantity.toLocaleString()}
                  </div>
                  <div style={{
                    fontSize: '0.72rem',
                    fontFamily: 'monospace',
                    textAlign: 'center',
                    color: '#00d4ff',
                  }}>
                    {item.me_level}
                  </div>
                  <div style={{ textAlign: 'center' }}>
                    <span style={{
                      fontSize: '0.55rem',
                      fontWeight: 700,
                      padding: '2px 6px',
                      borderRadius: 2,
                      textTransform: 'uppercase',
                      letterSpacing: '0.03em',
                      background: `${ITEM_STATUS_COLORS[item.status]}15`,
                      color: ITEM_STATUS_COLORS[item.status],
                    }}>
                      {item.status}
                    </span>
                  </div>
                  <div style={{ textAlign: 'right', display: 'flex', gap: '0.3rem', justifyContent: 'flex-end' }}>
                    <button
                      onClick={() => handlePlanItem(item)}
                      style={{
                        padding: '3px 10px',
                        fontSize: '0.68rem',
                        fontWeight: 600,
                        background: 'rgba(0,212,255,0.08)',
                        border: '1px solid rgba(0,212,255,0.25)',
                        borderRadius: 3,
                        color: '#00d4ff',
                        cursor: 'pointer',
                      }}
                    >
                      Plan
                    </button>
                    <button
                      onClick={() => handleDeleteItem(item.id)}
                      style={{
                        padding: '3px 8px',
                        fontSize: '0.68rem',
                        fontWeight: 600,
                        background: 'rgba(248,81,73,0.06)',
                        border: '1px solid rgba(248,81,73,0.2)',
                        borderRadius: 3,
                        color: '#f85149',
                        cursor: 'pointer',
                      }}
                    >
                      &times;
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Planner Tab */}
      {tab === 'planner' && (
        <div>
          {/* Item Selector */}
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ ...labelStyle, marginBottom: '0.4rem' }}>Select Item to Plan</label>
            <select
              value={plannerItemId ?? ''}
              onChange={e => setPlannerItemId(e.target.value ? parseInt(e.target.value, 10) : null)}
              style={{
                width: '100%',
                maxWidth: 400,
                padding: '8px 12px',
                fontSize: '0.85rem',
                background: '#1a1a24',
                border: '1px solid rgba(255,255,255,0.1)',
                borderRadius: 6,
                color: 'var(--text-primary)',
                outline: 'none',
                cursor: 'pointer',
                colorScheme: 'dark',
              }}
            >
              <option value="">-- Choose an item --</option>
              {project.items.map(item => (
                <option key={item.id} value={item.id}>
                  {item.type_name} (x{item.quantity}, ME{item.me_level})
                </option>
              ))}
            </select>
          </div>

          {selectedPlannerItem ? (
            <PlannerTab
              selectedItem={{ typeID: selectedPlannerItem.type_id, typeName: selectedPlannerItem.type_name, groupName: '' }}
              projectItemId={selectedPlannerItem.id}
              onDecisionsChanged={(overrides, shoppingItems) => {
                handleDecisionsChanged(selectedPlannerItem.id, overrides, shoppingItems);
              }}
            />
          ) : (
            <div style={{ textAlign: 'center', padding: '3rem 1rem', color: 'var(--text-secondary)' }}>
              <p style={{ fontSize: '0.9rem' }}>Select an item above to plan its production chain.</p>
            </div>
          )}
        </div>
      )}

      {/* Shopping List Tab */}
      {tab === 'shopping' && (
        <div>
          {shoppingLoading ? (
            <div className="skeleton" style={{ height: 300, borderRadius: 8 }} />
          ) : !shoppingList || shoppingList.items.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '3rem 1rem', color: 'var(--text-secondary)' }}>
              <p style={{ fontSize: '0.9rem', marginBottom: '0.5rem' }}>No shopping list available.</p>
              <p style={{ fontSize: '0.78rem' }}>Plan your items first using the Planner tab to generate a shopping list.</p>
            </div>
          ) : (
            <div>
              {/* Header */}
              <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                marginBottom: '0.75rem',
              }}>
                <span style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                  {shoppingList.items.length} material{shoppingList.items.length !== 1 ? 's' : ''}{' '}
                  <span style={{ color: 'var(--text-primary)', fontWeight: 600, fontFamily: 'monospace' }}>
                    {formatISK(shoppingList.total_cost)}
                  </span>
                </span>
                <button
                  onClick={copyMultibuy}
                  style={{
                    padding: '4px 14px',
                    fontSize: '0.7rem',
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

              {/* Table */}
              <div style={{
                background: '#12121a',
                border: '1px solid rgba(255,255,255,0.06)',
                borderRadius: 8,
                overflow: 'hidden',
              }}>
                {/* Table Header */}
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: '28px 1fr 90px 90px 100px 140px',
                  gap: '0.5rem',
                  padding: '0.5rem 0.85rem',
                  borderBottom: '1px solid rgba(255,255,255,0.06)',
                  background: 'rgba(255,255,255,0.015)',
                  fontSize: '0.58rem',
                  fontWeight: 700,
                  color: 'rgba(139,148,158,0.7)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.06em',
                  alignItems: 'center',
                }}>
                  <div />
                  <div>Material</div>
                  <div style={{ textAlign: 'right' }}>Total Qty</div>
                  <div style={{ textAlign: 'right' }}>Unit Price</div>
                  <div style={{ textAlign: 'right' }}>Total Cost</div>
                  <div>Needed By</div>
                </div>

                {/* Rows (sorted by total_price descending) */}
                {[...shoppingList.items]
                  .sort((a, b) => b.total_price - a.total_price)
                  .map((item, i) => (
                    <div
                      key={item.type_id}
                      style={{
                        display: 'grid',
                        gridTemplateColumns: '28px 1fr 90px 90px 100px 140px',
                        gap: '0.5rem',
                        padding: '0.4rem 0.85rem',
                        alignItems: 'center',
                        background: i % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.015)',
                        transition: 'background 0.1s',
                      }}
                      onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.03)'; }}
                      onMouseLeave={e => { e.currentTarget.style.background = i % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.015)'; }}
                    >
                      <img
                        src={`https://images.evetech.net/types/${item.type_id}/icon?size=32`}
                        alt=""
                        style={{ width: 22, height: 22, borderRadius: 3, border: '1px solid rgba(255,255,255,0.06)' }}
                        onError={e => { (e.target as HTMLImageElement).style.display = 'none'; }}
                      />
                      <div style={{ fontSize: '0.78rem', fontWeight: 500, color: 'var(--text-primary)' }}>
                        {item.type_name}
                      </div>
                      <div style={{
                        fontSize: '0.76rem',
                        fontFamily: 'monospace',
                        textAlign: 'right',
                        color: 'var(--text-primary)',
                      }}>
                        {item.total_quantity.toLocaleString()}
                      </div>
                      <div style={{
                        fontSize: '0.72rem',
                        fontFamily: 'monospace',
                        textAlign: 'right',
                        color: 'var(--text-secondary)',
                      }}>
                        {item.unit_price > 0 ? formatISK(item.unit_price) : '\u2014'}
                      </div>
                      <div style={{
                        fontSize: '0.74rem',
                        fontFamily: 'monospace',
                        textAlign: 'right',
                        color: item.total_price > 0 ? 'var(--text-primary)' : 'var(--text-secondary)',
                        fontWeight: item.total_price > 0 ? 600 : 400,
                      }}>
                        {item.total_price > 0 ? formatISK(item.total_price) : '\u2014'}
                      </div>
                      <div style={{ display: 'flex', gap: '0.25rem', flexWrap: 'wrap' }}>
                        {item.needed_by.map(name => (
                          <span
                            key={name}
                            style={{
                              fontSize: '0.55rem',
                              padding: '1px 5px',
                              borderRadius: 2,
                              background: 'rgba(0,212,255,0.08)',
                              color: 'rgba(0,212,255,0.7)',
                              whiteSpace: 'nowrap',
                              maxWidth: 120,
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                            }}
                          >
                            {name}
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}

                {/* Total row */}
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: '28px 1fr 90px 90px 100px 140px',
                  gap: '0.5rem',
                  padding: '0.55rem 0.85rem',
                  borderTop: '1px solid rgba(255,255,255,0.06)',
                  background: 'rgba(0,212,255,0.03)',
                  alignItems: 'center',
                }}>
                  <div />
                  <div style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                    Total
                  </div>
                  <div />
                  <div />
                  <div style={{
                    fontSize: '0.82rem',
                    fontFamily: 'monospace',
                    color: '#00d4ff',
                    textAlign: 'right',
                    fontWeight: 700,
                  }}>
                    {formatISK(shoppingList.total_cost)}
                  </div>
                  <div />
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

const labelStyle: React.CSSProperties = {
  display: 'block',
  fontSize: '0.65rem',
  fontWeight: 600,
  color: 'var(--text-secondary)',
  textTransform: 'uppercase',
  letterSpacing: '0.04em',
  marginBottom: '0.3rem',
};

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '7px 10px',
  fontSize: '0.82rem',
  background: 'rgba(255,255,255,0.04)',
  border: '1px solid rgba(255,255,255,0.08)',
  borderRadius: 5,
  color: 'var(--text-primary)',
  outline: 'none',
  boxSizing: 'border-box',
};
