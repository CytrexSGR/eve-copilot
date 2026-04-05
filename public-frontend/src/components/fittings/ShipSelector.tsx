import { useState, useEffect, useRef, useCallback } from 'react';
import { sdeApi } from '../../services/api/fittings';
import type { ShipSummary, ShipDetail, GroupSummary } from '../../types/fittings';
import { getShipRenderUrl } from '../../types/fittings';

interface ShipSelectorProps {
  selectedShip: ShipDetail | null;
  onSelect: (ship: ShipDetail) => void;
}

// Backend returns type_name / power_output; fittings.ts declares name / powergrid_output.
// These helpers read whichever field is actually present at runtime.
function shipName(s: ShipSummary | ShipDetail): string {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return (s as any).type_name ?? s.name ?? '';
}
function shipPG(s: ShipSummary | ShipDetail): number {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return (s as any).power_output ?? s.power_output ?? 0;
}

export function ShipSelector({ selectedShip, onSelect }: ShipSelectorProps) {
  // Search state
  const [search, setSearch] = useState('');
  const [results, setResults] = useState<ShipSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  // Browse state
  const [groups, setGroups] = useState<GroupSummary[]>([]);
  const [expandedGroup, setExpandedGroup] = useState<number | null>(null);
  const [groupShips, setGroupShips] = useState<Map<number, ShipSummary[]>>(new Map());
  const [groupLoading, setGroupLoading] = useState(false);

  // Fetch groups on mount
  useEffect(() => {
    sdeApi.getShipGroups().then(setGroups).catch(() => {});
  }, []);

  // Debounced search (existing behavior)
  useEffect(() => {
    if (search.length < 2) {
      setResults([]);
      return;
    }
    if (debounceRef.current) clearTimeout(debounceRef.current);
    setLoading(true);
    debounceRef.current = setTimeout(() => {
      sdeApi.getShips({ search, limit: 30 })
        .then(ships => {
          setResults(ships);
          setLoading(false);
        })
        .catch(() => {
          setResults([]);
          setLoading(false);
        });
    }, 300);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [search]);

  // Group expand handler with caching
  const handleGroupClick = useCallback((groupId: number) => {
    if (expandedGroup === groupId) {
      setExpandedGroup(null);
      return;
    }
    setExpandedGroup(groupId);
    if (groupShips.has(groupId)) return;
    setGroupLoading(true);
    sdeApi.getShips({ group_id: groupId, limit: 200 })
      .then(ships => {
        setGroupShips(prev => new Map(prev).set(groupId, ships));
        setGroupLoading(false);
      })
      .catch(() => setGroupLoading(false));
  }, [expandedGroup, groupShips]);

  // Ship select handler
  const handleShipSelect = (typeId: number) => {
    sdeApi.getShipDetail(typeId).then(ship => {
      onSelect(ship);
      setExpandedGroup(null);
      setSearch('');
    }).catch(() => {});
  };

  const isSearchMode = search.length >= 2;

  return (
    <div style={{
      background: 'var(--bg-secondary)',
      border: '1px solid var(--border-color)',
      borderRadius: '8px',
      padding: '0.75rem',
    }}>
      <div style={{ fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.5rem' }}>
        Ship Hull
      </div>

      {/* Selected ship display */}
      {selectedShip && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '0.5rem' }}>
          <img
            src={getShipRenderUrl(selectedShip.type_id, 128)}
            alt={shipName(selectedShip)}
            style={{ width: 64, height: 64, objectFit: 'contain' }}
          />
          <div>
            <div style={{ fontWeight: 600, fontSize: '1rem' }}>{shipName(selectedShip)}</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
              {selectedShip.group_name}
            </div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-tertiary)', marginTop: '0.25rem' }}>
              H:{selectedShip.hi_slots ?? 0} M:{selectedShip.med_slots ?? 0} L:{selectedShip.low_slots ?? 0} R:{selectedShip.rig_slots ?? 0}
              {' | '}PG:{(shipPG(selectedShip)).toLocaleString()} CPU:{(selectedShip.cpu_output ?? 0).toLocaleString()}
            </div>
          </div>
        </div>
      )}

      {/* Search input */}
      <div style={{ position: 'relative', marginBottom: isSearchMode ? 0 : '0.5rem' }}>
        <input
          type="text"
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder={selectedShip ? 'Change ship...' : 'Search for a ship hull...'}
          style={{
            width: '100%',
            padding: '0.5rem',
            background: 'var(--bg-primary)',
            border: '1px solid var(--border-color)',
            borderRadius: '6px',
            color: 'var(--text-primary)',
            fontSize: '0.85rem',
            outline: 'none',
            boxSizing: 'border-box',
          }}
        />
        {loading && (
          <div style={{
            position: 'absolute',
            right: '0.5rem',
            top: '50%',
            transform: 'translateY(-50%)',
            fontSize: '0.75rem',
            color: 'var(--text-secondary)',
          }}>
            ...
          </div>
        )}
      </div>

      {/* Search mode: flat results dropdown */}
      {isSearchMode && (
        <div style={{
          background: 'var(--bg-primary)',
          border: '1px solid var(--border-color)',
          borderRadius: '6px',
          marginTop: '4px',
          maxHeight: '400px',
          overflowY: 'auto',
        }}>
          {loading && results.length === 0 && (
            <div style={{ padding: '0.75rem', fontSize: '0.8rem', color: 'var(--text-secondary)', textAlign: 'center' }}>
              Searching...
            </div>
          )}
          {!loading && results.length === 0 && (
            <div style={{ padding: '0.75rem', fontSize: '0.8rem', color: 'var(--text-secondary)', textAlign: 'center' }}>
              No ships found
            </div>
          )}
          {results.map(ship => (
            <ShipRow key={ship.type_id} ship={ship} onSelect={handleShipSelect} />
          ))}
        </div>
      )}

      {/* Browse mode: group hierarchy */}
      {!isSearchMode && groups.length > 0 && (
        <div style={{
          maxHeight: '400px',
          overflowY: 'auto',
          border: '1px solid var(--border-color)',
          borderRadius: '6px',
          background: 'var(--bg-primary)',
        }}>
          {groups.map(group => (
            <div key={group.group_id}>
              {/* Group header row */}
              <div
                onClick={() => handleGroupClick(group.group_id)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '0.5rem 0.65rem',
                  cursor: 'pointer',
                  fontSize: '0.85rem',
                  fontWeight: 600,
                  background: expandedGroup === group.group_id ? 'var(--bg-elevated)' : 'transparent',
                  borderBottom: '1px solid rgba(255,255,255,0.04)',
                  userSelect: 'none',
                }}
                onMouseEnter={e => {
                  if (expandedGroup !== group.group_id) {
                    e.currentTarget.style.background = 'var(--bg-elevated)';
                  }
                }}
                onMouseLeave={e => {
                  if (expandedGroup !== group.group_id) {
                    e.currentTarget.style.background = 'transparent';
                  }
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <span style={{ color: '#00d4ff', fontSize: '0.75rem', width: '0.75rem', textAlign: 'center' }}>
                    {expandedGroup === group.group_id ? '\u25BE' : '\u25B8'}
                  </span>
                  <span style={{ color: 'var(--text-primary)' }}>{group.group_name}</span>
                </div>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)' }}>
                  {group.count}
                </span>
              </div>

              {/* Expanded group: ship list */}
              {expandedGroup === group.group_id && (
                <div style={{ background: 'rgba(0,0,0,0.15)' }}>
                  {groupLoading && !groupShips.has(group.group_id) && (
                    <div style={{ padding: '0.5rem 1rem', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                      Loading ships...
                    </div>
                  )}
                  {(groupShips.get(group.group_id) || []).map(ship => (
                    <ShipRow key={ship.type_id} ship={ship} onSelect={handleShipSelect} indent />
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// --- Ship row component (reused in both search and browse modes) ---

function ShipRow({
  ship,
  onSelect,
  indent = false,
}: {
  ship: ShipSummary;
  onSelect: (typeId: number) => void;
  indent?: boolean;
}) {
  const name = shipName(ship);
  return (
    <div
      onClick={() => onSelect(ship.type_id)}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '0.5rem',
        padding: indent ? '0.35rem 0.65rem 0.35rem 1.75rem' : '0.5rem 0.65rem',
        cursor: 'pointer',
        borderBottom: '1px solid rgba(255,255,255,0.04)',
      }}
      onMouseEnter={e => (e.currentTarget.style.background = 'var(--bg-elevated)')}
      onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
    >
      <img
        src={getShipRenderUrl(ship.type_id, 64)}
        alt={name}
        style={{ width: 32, height: 32, objectFit: 'contain', borderRadius: '4px' }}
      />
      <div style={{ minWidth: 0 }}>
        <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-primary)' }}>{name}</div>
        <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
          {ship.group_name} · H:{ship.hi_slots ?? 0} M:{ship.med_slots ?? 0} L:{ship.low_slots ?? 0}
        </div>
      </div>
    </div>
  );
}
