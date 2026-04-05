import { useState, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { RefreshCw, Settings } from 'lucide-react';
import { CharacterSlotsSummary } from './CharacterSlotsSummary';
import { RecommendationList } from './RecommendationList';
import { ProjectList } from './ProjectList';
import { PlanetTypeChip } from './PlanetTypeChip';
import { getSystemPlanets } from '../../api/pi';
import type { PICharacterSlots, PISystemPlanet } from '../../api/pi';

// Default system: Isikemi (home system)
const DEFAULT_SYSTEM = {
  id: 30002811,
  name: 'Isikemi',
};

// Available systems for the dropdown
const AVAILABLE_SYSTEMS = [
  { id: 30002811, name: 'Isikemi' },
  { id: 30000142, name: 'Jita' },
  { id: 30002187, name: 'Amarr' },
  { id: 30002659, name: 'Dodixie' },
  { id: 30002053, name: 'Hek' },
  { id: 30002510, name: 'Rens' },
];

type OptimizerMode = 'market_driven' | 'vertical';

interface PlanetTypeSummary {
  type: string;
  count: number;
}

function summarizePlanetTypes(planets: PISystemPlanet[]): PlanetTypeSummary[] {
  const typeCounts: Record<string, number> = {};
  for (const planet of planets) {
    const type = planet.planet_type;
    typeCounts[type] = (typeCounts[type] || 0) + 1;
  }

  return Object.entries(typeCounts)
    .map(([type, count]) => ({ type, count }))
    .sort((a, b) => a.type.localeCompare(b.type));
}

export function PIOptimizerTab() {
  const [selectedSystemId, setSelectedSystemId] = useState(DEFAULT_SYSTEM.id);
  const [selectedMode, setSelectedMode] = useState<OptimizerMode>('market_driven');
  const [characterSlots, setCharacterSlots] = useState<PICharacterSlots[]>([]);
  const [refreshKey, setRefreshKey] = useState(0);

  // Fetch planets for the selected system
  const {
    data: planets,
    isLoading: planetsLoading,
    refetch: refetchPlanets,
  } = useQuery({
    queryKey: ['pi-system-planets', selectedSystemId],
    queryFn: () => getSystemPlanets(selectedSystemId),
    enabled: selectedSystemId > 0,
  });

  // Handle character slots loaded from CharacterSlotsSummary
  const handleSlotsLoaded = useCallback((slots: PICharacterSlots[]) => {
    setCharacterSlots(slots);
  }, []);

  // Handle system change
  const handleSystemChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setSelectedSystemId(Number(e.target.value));
  };

  // Handle mode change
  const handleModeChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setSelectedMode(e.target.value as OptimizerMode);
  };

  // Handle refresh button click
  const handleRefresh = () => {
    setRefreshKey((prev) => prev + 1);
    refetchPlanets();
  };

  // Handle project created (triggers recommendation refresh)
  const handleProjectCreated = () => {
    setRefreshKey((prev) => prev + 1);
  };

  // Get current system name for display
  const currentSystem = AVAILABLE_SYSTEMS.find((s) => s.id === selectedSystemId);
  const planetSummary = planets ? summarizePlanetTypes(planets) : [];

  return (
    <div className="pi-optimizer">
      {/* Character Slots Summary Section */}
      <section className="optimizer-section">
        <CharacterSlotsSummary onSlotsLoaded={handleSlotsLoaded} />
      </section>

      {/* Controls Section */}
      <section className="optimizer-controls">
        <div className="controls-row">
          <div className="filter-group">
            <label>Target System</label>
            <select value={selectedSystemId} onChange={handleSystemChange}>
              {AVAILABLE_SYSTEMS.map((system) => (
                <option key={system.id} value={system.id}>
                  {system.name}
                </option>
              ))}
            </select>
          </div>

          <div className="filter-group">
            <label>Mode</label>
            <select value={selectedMode} onChange={handleModeChange}>
              <option value="market_driven">Market-driven</option>
              <option value="vertical">Vertical Integration</option>
            </select>
          </div>

          <div className="filter-group mode-info">
            <Settings size={14} />
            <span className="mode-description">
              {selectedMode === 'market_driven'
                ? 'Optimize for highest market profit'
                : 'Produce materials for your own chains'}
            </span>
          </div>
        </div>

        {/* Available Planets Display */}
        <div className="available-planets">
          <span className="planets-label">Available Planets in {currentSystem?.name}:</span>
          {planetsLoading ? (
            <span className="loading-text">Loading...</span>
          ) : planetSummary.length > 0 ? (
            <div className="planet-summary">
              {planetSummary.map(({ type, count }) => (
                <div key={type} className="planet-type-count">
                  <PlanetTypeChip type={type} />
                  <span className="count">({count})</span>
                </div>
              ))}
            </div>
          ) : (
            <span className="no-planets">No planet data available</span>
          )}
        </div>
      </section>

      {/* Recommendations Section */}
      <section className="optimizer-section recommendations-section">
        <div className="section-header">
          <h3>Recommendations</h3>
          <button className="btn btn-secondary btn-sm" onClick={handleRefresh}>
            <RefreshCw size={14} />
            Refresh
          </button>
        </div>
        <RecommendationList
          key={`recommendations-${refreshKey}`}
          characterSlots={characterSlots}
          systemId={selectedSystemId}
          mode={selectedMode}
          onProjectCreated={handleProjectCreated}
        />
      </section>

      {/* Active Projects Section */}
      <section className="optimizer-section projects-section">
        <ProjectList
          key={`projects-${refreshKey}`}
          onProjectDeleted={handleProjectCreated}
        />
      </section>
    </div>
  );
}
