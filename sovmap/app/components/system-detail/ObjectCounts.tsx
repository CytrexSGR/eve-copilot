'use client';

import type { Star, Planet, Stargate, Station } from './types';

interface ObjectCountsProps {
  star: Star | null;
  planets: Planet[];
  stargates: Stargate[];
  stations: Station[];
  onSelectStar: () => void;
  onSelectPlanets: () => void;
  onSelectStargates: () => void;
  onSelectStations: () => void;
}

export default function ObjectCounts({
  star,
  planets,
  stargates,
  stations,
  onSelectStar,
  onSelectPlanets,
  onSelectStargates,
  onSelectStations,
}: ObjectCountsProps) {
  return (
    <div className="absolute bottom-4 left-4 bg-gray-900 border border-gray-700 rounded-lg p-4 shadow-lg">
      <div className="grid grid-cols-4 gap-4 text-center text-sm">
        {star && (
          <button
            onClick={onSelectStar}
            className="bg-gray-800 hover:bg-gray-700 rounded p-2 transition-colors cursor-pointer"
          >
            <div className="text-yellow-400 font-semibold">1</div>
            <div className="text-gray-400">Star</div>
          </button>
        )}
        <button
          onClick={onSelectPlanets}
          className="bg-gray-800 hover:bg-gray-700 rounded p-2 transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
          disabled={planets.length === 0}
        >
          <div className="text-blue-400 font-semibold">{planets.length}</div>
          <div className="text-gray-400">Planets</div>
        </button>
        <button
          onClick={onSelectStargates}
          className="bg-gray-800 hover:bg-gray-700 rounded p-2 transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
          disabled={stargates.length === 0}
        >
          <div className="text-cyan-400 font-semibold">{stargates.length}</div>
          <div className="text-gray-400">Stargates</div>
        </button>
        <button
          onClick={onSelectStations}
          className="bg-gray-800 hover:bg-gray-700 rounded p-2 transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
          disabled={stations.length === 0}
        >
          <div className="text-fuchsia-400 font-semibold">{stations.length}</div>
          <div className="text-gray-400">Stations</div>
        </button>
      </div>
    </div>
  );
}
