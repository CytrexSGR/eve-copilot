import { Clock, Building2, ChevronRight } from 'lucide-react';
import type { PIColony } from '../../api/pi';

interface ColonyCardProps {
  colony: PIColony;
  onViewDetails: () => void;
}

const PLANET_COLORS: Record<string, string> = {
  'barren': '#6b7280',
  'gas': '#22c55e',
  'ice': '#06b6d4',
  'lava': '#f97316',
  'oceanic': '#3b82f6',
  'plasma': '#a855f7',
  'storm': '#eab308',
  'temperate': '#10b981',
};

function capitalize(str: string): string {
  return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase();
}

export function ColonyCard({ colony, onViewDetails }: ColonyCardProps) {
  const planetType = colony.planet_type.toLowerCase();
  const planetColor = PLANET_COLORS[planetType] || '#6b7280';
  const displayType = capitalize(colony.planet_type);

  return (
    <div className="colony-card">
      <div className="colony-header">
        <div
          className="planet-icon"
          style={{ backgroundColor: planetColor }}
          title={displayType}
        >
          {displayType.charAt(0)}
        </div>
        <div className="colony-info">
          <h4>{displayType} Planet</h4>
          <span className="system-name">{colony.solar_system_name}</span>
        </div>
      </div>

      <div className="colony-stats">
        <div className="stat">
          <Building2 size={14} />
          <span>{colony.num_pins} pins</span>
        </div>
        <div className="stat">
          <Clock size={14} />
          <span>Level {colony.upgrade_level}</span>
        </div>
      </div>

      <button className="colony-details-btn" onClick={onViewDetails}>
        Details <ChevronRight size={14} />
      </button>
    </div>
  );
}
