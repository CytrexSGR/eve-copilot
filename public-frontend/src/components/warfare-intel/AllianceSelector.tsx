// src/components/warfare-intel/AllianceSelector.tsx
import { useMemo } from 'react';
import type { CoalitionSummary } from '../../types/reports';
import type { FastAllianceSummary } from '../../types/intelligence';

interface AllianceSelectorProps {
  coalitions: CoalitionSummary[];
  alliances: FastAllianceSummary[];
  selectedCoalitionId: number | null;
  selectedAllianceId: number | null;
  onCoalitionChange: (coalitionId: number | null) => void;
  onAllianceChange: (allianceId: number) => void;
  loading?: boolean;
}

export function AllianceSelector({
  coalitions,
  alliances,
  selectedCoalitionId,
  selectedAllianceId,
  onCoalitionChange,
  onAllianceChange,
  loading = false
}: AllianceSelectorProps) {
  // Filter alliances by selected coalition
  const filteredAlliances = useMemo(() => {
    if (selectedCoalitionId === null) {
      return alliances;
    }
    const coalition = coalitions.find(c => c.coalition_id === selectedCoalitionId);
    if (!coalition) return alliances;
    const memberIds = new Set(coalition.members.map(m => m.alliance_id));
    return alliances.filter(a => memberIds.has(a.alliance_id));
  }, [coalitions, alliances, selectedCoalitionId]);

  const selectStyle: React.CSSProperties = {
    padding: '0.625rem 1rem',
    fontSize: '0.875rem',
    fontWeight: 600,
    border: '1px solid rgba(100, 150, 255, 0.2)',
    borderRadius: '8px',
    backgroundColor: 'rgba(15, 20, 30, 0.95)',
    color: '#fff',
    cursor: 'pointer',
    minWidth: '200px',
    colorScheme: 'dark',  // Enables dark mode for dropdown options
    WebkitAppearance: 'none',
    appearance: 'none',
    backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%23888' d='M6 8L1 3h10z'/%3E%3C/svg%3E")`,
    backgroundRepeat: 'no-repeat',
    backgroundPosition: 'right 0.75rem center',
    paddingRight: '2.5rem'
  };

  return (
    <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', flexWrap: 'wrap' }}>
      {/* Coalition Dropdown */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <label style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.5)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Coalition
        </label>
        <select
          value={selectedCoalitionId ?? ''}
          onChange={(e) => onCoalitionChange(e.target.value ? Number(e.target.value) : null)}
          style={selectStyle}
          disabled={loading}
        >
          <option value="">All Coalitions</option>
          {coalitions.map(c => (
            <option key={c.coalition_id} value={c.coalition_id}>
              {c.leader_name} ({c.member_count} alliances)
            </option>
          ))}
        </select>
      </div>

      {/* Alliance Dropdown */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <label style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.5)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Alliance
        </label>
        <select
          value={selectedAllianceId ?? ''}
          onChange={(e) => onAllianceChange(Number(e.target.value))}
          style={selectStyle}
          disabled={loading || filteredAlliances.length === 0}
        >
          <option value="" disabled>Select Alliance...</option>
          {filteredAlliances.map(a => (
            <option key={a.alliance_id} value={a.alliance_id}>
              {a.alliance_name} ({a.kills} kills)
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
