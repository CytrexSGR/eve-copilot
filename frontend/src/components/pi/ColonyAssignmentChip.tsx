import { useState } from 'react';
import { ChevronDown } from 'lucide-react';
import type { PIMaterialAssignment, PIProjectColony } from '../../api/pi';

interface ColonyAssignmentChipProps {
  assignment: PIMaterialAssignment | null;
  availableColonies: PIProjectColony[];
  materialTypeId: number;
  materialName: string;
  tier: number;
  validPlanetTypes?: string[]; // For P0 filtering
  onAssign: (colonyId: number | null) => void;
  disabled?: boolean;
}

const STATUS_COLORS: Record<string, string> = {
  active: '#3fb950',
  planned: '#d29922',
  unassigned: '#f85149',
};

export function ColonyAssignmentChip({
  assignment,
  availableColonies,
  materialTypeId,
  materialName,
  tier,
  validPlanetTypes,
  onAssign,
  disabled = false,
}: ColonyAssignmentChipProps) {
  const [isOpen, setIsOpen] = useState(false);

  const status = assignment?.status || 'unassigned';
  const colonyName = assignment?.colony_name || 'Not assigned';
  const statusColor = STATUS_COLORS[status];

  // Output percentage display
  const outputPercentage = assignment?.output_percentage;
  const getOutputClass = (pct: number | null | undefined) => {
    if (pct === null || pct === undefined) return 'no-data';
    if (pct >= 100) return 'over-target';
    if (pct >= 50) return 'under-target';
    return 'critical';
  };

  // Filter colonies for P0 by planet type
  const filteredColonies = tier === 0 && validPlanetTypes
    ? availableColonies.filter(c =>
        validPlanetTypes.includes(c.planet_type?.toLowerCase() || '')
      )
    : availableColonies;

  const handleSelect = (colonyId: number | null) => {
    onAssign(colonyId);
    setIsOpen(false);
  };

  return (
    <div className="colony-assignment-chip-container">
      <button
        className={`colony-assignment-chip ${disabled ? 'disabled' : ''}`}
        onClick={() => !disabled && setIsOpen(!isOpen)}
        disabled={disabled}
      >
        <span
          className="status-dot"
          style={{ backgroundColor: statusColor }}
        />
        <span className="colony-name">{colonyName}</span>
        {outputPercentage !== null && outputPercentage !== undefined && (
          <span className={`output-percentage ${getOutputClass(outputPercentage)}`}>
            {outputPercentage}%
          </span>
        )}
        {assignment?.soll_variance_percent !== null && assignment?.soll_variance_percent !== undefined && (
          <span
            className={`soll-variance ${
              Math.abs(assignment.soll_variance_percent) <= 10
                ? 'on-target'
                : assignment.soll_variance_percent < -10
                ? 'under-soll'
                : 'over-soll'
            }`}
            title={`SOLL variance: ${assignment.soll_variance_percent > 0 ? '+' : ''}${assignment.soll_variance_percent}%`}
          >
            SOLL: {assignment.soll_variance_percent > 0 ? '+' : ''}{assignment.soll_variance_percent}%
          </span>
        )}
        {!disabled && <ChevronDown size={12} className={isOpen ? 'rotated' : ''} />}
      </button>

      {isOpen && (
        <div className="colony-dropdown">
          <div
            className="colony-option"
            onClick={() => handleSelect(null)}
          >
            <span className="status-dot" style={{ backgroundColor: STATUS_COLORS.unassigned }} />
            <span>Not assigned</span>
          </div>
          {filteredColonies.map((colony) => (
            <div
              key={colony.id}
              className={`colony-option ${colony.id === assignment?.colony_id ? 'selected' : ''}`}
              onClick={() => handleSelect(colony.id)}
            >
              <span
                className="status-dot"
                style={{ backgroundColor: colony.id === assignment?.colony_id ? statusColor : '#6b7280' }}
              />
              <span>{colony.role || `${colony.planet_type} ${colony.planet_id}`}</span>
            </div>
          ))}
          {tier === 0 && filteredColonies.length === 0 && (
            <div className="colony-option disabled">
              No compatible planets for {materialName}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
