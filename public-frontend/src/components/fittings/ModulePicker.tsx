import { useState, useEffect, useRef, useCallback } from 'react';
import { sdeApi, cacheTypeName } from '../../services/api/fittings';
import type { ModuleSummary, SlotType, GroupSummary } from '../../types/fittings';
import { getTypeIconUrl, SLOT_COLORS } from '../../types/fittings';

interface ModulePickerProps {
  slotType: SlotType | null;
  droneMode?: boolean;
  onSelectModule: (typeId: number) => void;
  shipTypeId?: number | null;
}

function MetaBadge({ metaLevel }: { metaLevel: number }) {
  if (metaLevel === 5) {
    return (
      <span style={{
        fontSize: '0.6rem',
        fontWeight: 700,
        padding: '1px 4px',
        borderRadius: '3px',
        background: 'rgba(0, 212, 255, 0.15)',
        color: '#00d4ff',
        marginLeft: '0.35rem',
        whiteSpace: 'nowrap',
      }}>
        T2
      </span>
    );
  }
  if (metaLevel >= 6) {
    return (
      <span style={{
        fontSize: '0.6rem',
        fontWeight: 700,
        padding: '1px 4px',
        borderRadius: '3px',
        background: 'rgba(210, 153, 34, 0.15)',
        color: '#d29922',
        marginLeft: '0.35rem',
        whiteSpace: 'nowrap',
      }}>
        Faction
      </span>
    );
  }
  return null;
}

function ModuleRow({ mod, droneMode, onSelect }: {
  mod: ModuleSummary;
  droneMode: boolean;
  onSelect: (mod: ModuleSummary) => void;
}) {
  const name = (mod as any).type_name || mod.name;
  return (
    <div
      onClick={() => onSelect(mod)}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '0.5rem',
        padding: '0.4rem 0.5rem',
        cursor: 'pointer',
        borderRadius: '4px',
        marginBottom: '1px',
      }}
      onMouseEnter={e => (e.currentTarget.style.background = 'var(--bg-elevated)')}
      onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
    >
      <img
        src={getTypeIconUrl(mod.type_id, 32)}
        alt={name}
        style={{ width: 32, height: 32, borderRadius: 4, flexShrink: 0 }}
      />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: '0.8rem', fontWeight: 600, display: 'flex', alignItems: 'center' }}>
          <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{name}</span>
          <MetaBadge metaLevel={mod.meta_level} />
        </div>
        {!droneMode && (
          <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>
            {(mod.power ?? 0).toFixed(0)} PG / {(mod.cpu ?? 0).toFixed(0)} CPU
          </div>
        )}
      </div>
    </div>
  );
}

function GroupRow({ group, expanded, loading, onClick }: {
  group: GroupSummary;
  expanded: boolean;
  loading: boolean;
  onClick: () => void;
}) {
  return (
    <div
      onClick={onClick}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '0.4rem',
        padding: '0.45rem 0.5rem',
        cursor: 'pointer',
        borderRadius: '4px',
        background: expanded ? 'var(--bg-elevated)' : 'rgba(255,255,255,0.02)',
        marginBottom: '2px',
        userSelect: 'none',
      }}
      onMouseEnter={e => {
        if (!expanded) e.currentTarget.style.background = 'rgba(255,255,255,0.04)';
      }}
      onMouseLeave={e => {
        if (!expanded) e.currentTarget.style.background = 'rgba(255,255,255,0.02)';
      }}
    >
      <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', width: '0.8rem', textAlign: 'center' }}>
        {loading && expanded ? '...' : expanded ? '\u25BE' : '\u25B8'}
      </span>
      <span style={{ fontSize: '0.85rem', fontWeight: 600, flex: 1 }}>{group.group_name}</span>
      <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>({group.count})</span>
    </div>
  );
}

export function ModulePicker({ slotType, droneMode = false, onSelectModule, shipTypeId }: ModulePickerProps) {
  const [search, setSearch] = useState('');
  const [searchResults, setSearchResults] = useState<ModuleSummary[]>([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  // Browse state
  const [groups, setGroups] = useState<GroupSummary[]>([]);
  const [groupsLoading, setGroupsLoading] = useState(false);
  const [expandedGroup, setExpandedGroup] = useState<number | null>(null);
  const [groupModules, setGroupModules] = useState<Map<number, ModuleSummary[]>>(new Map());
  const [groupLoading, setGroupLoading] = useState(false);

  const active = droneMode || slotType !== null;
  const isSearching = search.trim().length >= 2;

  // Fetch groups when slot type or drone mode changes
  useEffect(() => {
    if (!active) {
      setGroups([]);
      return;
    }
    setExpandedGroup(null);
    setGroupModules(new Map());
    setSearch('');
    setSearchResults([]);
    setGroupsLoading(true);

    const params = droneMode
      ? { category: 'drone' as const }
      : { slot_type: slotType!, ...(shipTypeId ? { ship_type_id: shipTypeId } : {}) };

    sdeApi.getModuleGroups(params)
      .then(setGroups)
      .catch(() => setGroups([]))
      .finally(() => setGroupsLoading(false));
  }, [slotType, droneMode, active, shipTypeId]);

  // Debounced search when 2+ chars typed
  useEffect(() => {
    if (!active || !isSearching) {
      setSearchResults([]);
      return;
    }

    if (debounceRef.current) clearTimeout(debounceRef.current);

    setSearchLoading(true);
    debounceRef.current = setTimeout(() => {
      const params = droneMode
        ? { search: search.trim(), category: 'drone' as const, limit: 50 }
        : { slot_type: slotType!, search: search.trim(), ...(shipTypeId ? { ship_type_id: shipTypeId } : {}), limit: 50 };

      sdeApi.getModules(params)
        .then(setSearchResults)
        .catch(() => setSearchResults([]))
        .finally(() => setSearchLoading(false));
    }, 300);

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [search, slotType, droneMode, active, isSearching]);

  // Group expand with caching
  const handleGroupClick = useCallback((groupId: number) => {
    if (expandedGroup === groupId) {
      setExpandedGroup(null);
      return;
    }
    setExpandedGroup(groupId);
    if (groupModules.has(groupId)) return;

    setGroupLoading(true);
    const params = droneMode
      ? { group_id: groupId, category: 'drone' as const, limit: 200 }
      : { slot_type: slotType!, group_id: groupId, ...(shipTypeId ? { ship_type_id: shipTypeId } : {}), limit: 200 };

    sdeApi.getModules(params)
      .then(mods => {
        setGroupModules(prev => new Map(prev).set(groupId, mods));
        setGroupLoading(false);
      })
      .catch(() => setGroupLoading(false));
  }, [expandedGroup, groupModules, slotType, droneMode, shipTypeId]);

  // Module select handler
  const handleSelect = useCallback((mod: ModuleSummary) => {
    const name = (mod as any).type_name || mod.name;
    cacheTypeName(mod.type_id, name);
    onSelectModule(mod.type_id);
  }, [onSelectModule]);

  // Inactive state
  if (!active) {
    return (
      <div style={{
        background: 'var(--bg-secondary)',
        border: '1px solid var(--border-color)',
        borderRadius: '8px',
        padding: '1rem',
        textAlign: 'center',
        color: 'var(--text-secondary)',
        fontSize: '0.85rem',
      }}>
        Click an empty slot to browse modules
      </div>
    );
  }

  const slotColor = droneMode ? '#a855f7' : (slotType ? SLOT_COLORS[slotType] : '#888');
  const title = droneMode
    ? 'Drone Bay'
    : `${(slotType || '').charAt(0).toUpperCase() + (slotType || '').slice(1)} Slot Modules`;
  const searchPlaceholder = droneMode ? 'Search drones...' : 'Search modules...';

  return (
    <div style={{
      background: 'var(--bg-secondary)',
      border: `1px solid ${slotColor}44`,
      borderRadius: '8px',
      padding: '0.75rem',
    }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '0.5rem',
        marginBottom: '0.5rem',
      }}>
        <div style={{ width: 8, height: 8, borderRadius: '50%', background: slotColor }} />
        <span style={{ fontWeight: 600, fontSize: '0.85rem' }}>{title}</span>
      </div>

      {/* Search input */}
      <input
        type="text"
        value={search}
        onChange={e => setSearch(e.target.value)}
        placeholder={searchPlaceholder}
        style={{
          width: '100%',
          padding: '0.5rem',
          background: 'var(--bg-primary)',
          border: '1px solid var(--border-color)',
          borderRadius: '6px',
          color: 'var(--text-primary)',
          fontSize: '0.85rem',
          outline: 'none',
          marginBottom: '0.5rem',
          boxSizing: 'border-box',
        }}
      />

      {/* Scrollable list area */}
      <div style={{ maxHeight: '500px', overflowY: 'auto' }}>
        {/* --- Search Mode --- */}
        {isSearching && (
          <>
            {searchLoading && (
              <div style={{ padding: '1rem', textAlign: 'center', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                Searching...
              </div>
            )}
            {!searchLoading && searchResults.length === 0 && (
              <div style={{ padding: '1rem', textAlign: 'center', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                {droneMode ? 'No drones found' : 'No modules found'}
              </div>
            )}
            {!searchLoading && searchResults.map(mod => (
              <ModuleRow key={mod.type_id} mod={mod} droneMode={droneMode} onSelect={handleSelect} />
            ))}
          </>
        )}

        {/* --- Browse Mode --- */}
        {!isSearching && (
          <>
            {groupsLoading && (
              <div style={{ padding: '1rem', textAlign: 'center', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                Loading groups...
              </div>
            )}
            {!groupsLoading && groups.length === 0 && (
              <div style={{ padding: '1rem', textAlign: 'center', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                {droneMode ? 'No drone groups found' : 'No module groups found'}
              </div>
            )}
            {!groupsLoading && groups.map(group => (
              <div key={group.group_id}>
                <GroupRow
                  group={group}
                  expanded={expandedGroup === group.group_id}
                  loading={groupLoading && expandedGroup === group.group_id}
                  onClick={() => handleGroupClick(group.group_id)}
                />
                {expandedGroup === group.group_id && (
                  <div style={{ paddingLeft: '0.75rem', borderLeft: `2px solid ${slotColor}33` }}>
                    {groupLoading && !groupModules.has(group.group_id) && (
                      <div style={{ padding: '0.5rem', color: 'var(--text-secondary)', fontSize: '0.75rem' }}>
                        Loading modules...
                      </div>
                    )}
                    {groupModules.get(group.group_id)?.map(mod => (
                      <ModuleRow key={mod.type_id} mod={mod} droneMode={droneMode} onSelect={handleSelect} />
                    ))}
                    {groupModules.has(group.group_id) && groupModules.get(group.group_id)!.length === 0 && (
                      <div style={{ padding: '0.5rem', color: 'var(--text-secondary)', fontSize: '0.75rem' }}>
                        No modules in this group
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </>
        )}
      </div>
    </div>
  );
}
