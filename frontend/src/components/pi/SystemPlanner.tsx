import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Map, Star } from 'lucide-react';
import { searchSystems } from '../../api/pi';
import type { PISystem } from '../../api/pi';
import { PlanetTypeChip } from './PlanetTypeChip';

const REGIONS = [
  { id: 10000002, name: 'The Forge' },
  { id: 10000043, name: 'Domain' },
  { id: 10000030, name: 'Heimatar' },
  { id: 10000032, name: 'Sinq Laison' },
  { id: 10000042, name: 'Metropolis' },
];

const PLANET_TYPES = ['Barren', 'Gas', 'Ice', 'Lava', 'Oceanic', 'Plasma', 'Storm', 'Temperate'];

export function SystemPlanner() {
  const [regionId, setRegionId] = useState<number | undefined>(undefined);
  const [minSecurity, setMinSecurity] = useState(0.5);
  const [selectedTypes, setSelectedTypes] = useState<string[]>([]);
  const [selectedSystem, setSelectedSystem] = useState<PISystem | null>(null);

  const { data: systems, isLoading } = useQuery({
    queryKey: ['pi-systems', regionId, minSecurity, selectedTypes],
    queryFn: () => searchSystems({
      region_id: regionId,
      min_security: minSecurity,
      planet_types: selectedTypes.length > 0 ? selectedTypes : undefined,
      limit: 100,
    }),
  });

  const toggleType = (type: string) => {
    setSelectedTypes(prev =>
      prev.includes(type)
        ? prev.filter(t => t !== type)
        : [...prev, type]
    );
  };

  return (
    <div className="system-planner">
      <div className="planner-left">
        <div className="filter-bar">
          <div className="filter-group">
            <label>Region</label>
            <select
              value={regionId || ''}
              onChange={(e) => setRegionId(e.target.value ? Number(e.target.value) : undefined)}
            >
              <option value="">All Regions</option>
              {REGIONS.map(r => (
                <option key={r.id} value={r.id}>{r.name}</option>
              ))}
            </select>
          </div>

          <div className="filter-group">
            <label>Min Security: {minSecurity.toFixed(1)}</label>
            <input
              type="range"
              min={0}
              max={1}
              step={0.1}
              value={minSecurity}
              onChange={(e) => setMinSecurity(Number(e.target.value))}
            />
          </div>
        </div>

        <div className="planet-filter">
          <label>Required Planet Types:</label>
          <div className="planet-chips">
            {PLANET_TYPES.map(type => (
              <PlanetTypeChip
                key={type}
                type={type}
                selected={selectedTypes.includes(type)}
                onClick={() => toggleType(type)}
              />
            ))}
          </div>
        </div>

        {isLoading ? (
          <div className="loading">Searching systems...</div>
        ) : (
          <div className="systems-table-container">
            <table className="systems-table">
              <thead>
                <tr>
                  <th>System</th>
                  <th>Region</th>
                  <th>Security</th>
                  <th>Planets</th>
                  <th>Types</th>
                </tr>
              </thead>
              <tbody>
                {systems?.map(system => (
                  <tr
                    key={system.system_id}
                    className={selectedSystem?.system_id === system.system_id ? 'selected' : ''}
                    onClick={() => setSelectedSystem(system)}
                  >
                    <td className="system-name">
                      {system.planet_count >= 6 && <Star size={14} className="ideal-badge" />}
                      {system.system_name}
                    </td>
                    <td>{system.region_name}</td>
                    <td className={system.security >= 0.5 ? 'sec-high' : 'sec-low'}>
                      {system.security.toFixed(2)}
                    </td>
                    <td>{system.planet_count}</td>
                    <td className="planet-types-cell">
                      {system.planet_types.map(t => (
                        <PlanetTypeChip key={t} type={t} />
                      ))}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="planner-right">
        <div className="map-placeholder">
          <Map size={48} />
          <p>PI Map</p>
          <p className="map-note">Coming in next phase</p>
          {selectedSystem && (
            <div className="selected-system-info">
              <h4>{selectedSystem.system_name}</h4>
              <p>{selectedSystem.region_name} - {selectedSystem.security.toFixed(2)} security</p>
              <p>{selectedSystem.planet_count} planets</p>
              <div className="selected-types">
                {selectedSystem.planet_types.map(t => (
                  <PlanetTypeChip key={t} type={t} />
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
