'use client';

import { useState } from 'react';
import Image from 'next/image';
import { getTypeImageUrl } from '@/lib/eve-images';
import type { SelectedObject, PlanetWithNames, MoonWithNames, AsteroidBeltWithNames } from '../types';
import type { Planet } from '@/lib/sde-types';
import type { SystemDetailResponse } from '@/lib/sde-types';
import CelestialStats from './CelestialStats';

// Planet type information
const PLANET_TYPES: Record<number, { name: string; resources: string }> = {
  11: { name: 'Temperate Planet', resources: 'Rich in Carbon Compounds, Complex Organisms, and Aqueous Liquids' },
  12: { name: 'Ice Planet', resources: 'Rich in Aqueous Liquids, Heavy Water, and Noble Gas' },
  13: { name: 'Gas Giant', resources: 'Rich in Noble Gas, Ionic Solutions, and Electrolytes' },
  2014: { name: 'Oceanic Planet', resources: 'Rich in Aqueous Liquids, Complex Organisms, and Carbon Compounds' },
  2015: { name: 'Lava Planet', resources: 'Rich in Base Metals, Heavy Metals, and Non-CS Crystals' },
  2016: { name: 'Barren Planet', resources: 'Rich in Base Metals, Carbon Compounds, and Heavy Metals' },
  2017: { name: 'Storm Planet', resources: 'Rich in Noble Gas, Suspended Plasma, and Ionic Solutions' },
  2063: { name: 'Plasma Planet', resources: 'Rich in Suspended Plasma, Noble Gas, and Non-CS Crystals' },
  30889: { name: 'Shattered Planet', resources: 'Mixed resources from fractured planetary remnants' },
  73911: { name: 'Scorched Barren Planet', resources: 'Rich in Base Metals and Heavy Metals' },
};

interface PlanetDetailProps {
  data: Planet;
  onClose: () => void;
  onBack?: () => void;
  showBackButton?: boolean;
  systemData: SystemDetailResponse;
  setSelectedObject: (obj: SelectedObject | null) => void;
}

export default function PlanetDetail({
  data,
  onClose,
  onBack,
  showBackButton,
  systemData,
  setSelectedObject,
}: PlanetDetailProps) {
  const planetWithNames = data as PlanetWithNames;
  const [expandedMoonsList, setExpandedMoonsList] = useState(false);
  const [expandedAsteroidBeltsList, setExpandedAsteroidBeltsList] = useState(false);

  if (!data) return null;

  const typeInfo = PLANET_TYPES[data.typeID] || { name: 'Unknown Planet Type', resources: '' };

  return (
    <div className="absolute top-1/2 right-4 transform -translate-y-1/2 bg-gray-900 border border-gray-700 rounded-lg shadow-lg max-w-md w-80 overflow-hidden max-h-[90vh] overflow-y-auto detail-panel-scroll">
      {/* Header with back and close buttons */}
      <div className="bg-gray-800 px-4 py-3 flex justify-between items-center border-b border-gray-700 sticky top-0 z-10">
        <div className="flex items-center gap-2">
          {showBackButton && onBack && (
            <button
              onClick={onBack}
              className="text-gray-400 hover:text-white text-xl"
              title="Back to planets list"
            >
              ←
            </button>
          )}
          <h3 className="text-white font-semibold text-lg">
            {planetWithNames.fullName || `Planet ${data.celestialIndex}`}
          </h3>
        </div>
        <button onClick={onClose} className="text-gray-400 hover:text-white text-xl">
          ×
        </button>
      </div>

      {/* Planet image */}
      <div className="bg-gradient-to-br from-gray-900 to-black p-6 flex justify-center items-center">
        <div className="relative">
          <Image
            src={getTypeImageUrl(data.typeID, { size: 128, type: 'icon' })}
            alt="Planet"
            width={96}
            height={96}
            className="w-24 h-24 rounded-full object-cover border-2 border-gray-700 shadow-lg shadow-blue-500/20"
            unoptimized
            onError={(e) => {
              const img = e.target as HTMLImageElement;
              if (img.src.includes('icon')) {
                img.src = getTypeImageUrl(data.typeID, { size: 128, type: 'render' });
              }
            }}
          />
        </div>
      </div>

      {/* Planet information */}
      <div className="p-4 space-y-3">
        {/* Planet Type */}
        <div className="bg-gray-800 rounded p-3 -mt-1">
          <div className="text-gray-400 text-xs uppercase">Planet Type</div>
          <div className="text-white font-semibold">{typeInfo.name}</div>
          {typeInfo.resources && (
            <div className="text-gray-400 text-xs mt-2 leading-relaxed">{typeInfo.resources}</div>
          )}
        </div>

        {/* Celestial statistics */}
        <CelestialStats statistics={data.statistics} radius={data.radius} type="planet" />

        {/* Moons */}
        {data.moonIDs && data.moonIDs.length > 0 && (
          <div>
            <div className="text-gray-400 text-xs uppercase">Moons</div>
            <button
              onClick={() => setExpandedMoonsList(!expandedMoonsList)}
              className="text-white hover:text-blue-400 transition-colors text-left w-full"
            >
              {data.moonIDs.length} moon{data.moonIDs.length !== 1 ? 's' : ''}{' '}
              <span className="text-gray-500">{expandedMoonsList ? '▼' : '▶'}</span>
            </button>

            {expandedMoonsList && systemData && (
              <div className="mt-2 space-y-1 bg-gray-800 rounded p-2">
                {systemData.moons
                  .filter((moon) => data.moonIDs?.includes(moon._key))
                  .sort((a, b) => (a.orbitIndex || 0) - (b.orbitIndex || 0))
                  .map((moon) => (
                    <button
                      key={moon._key}
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedObject({ type: 'moon', data: moon });
                      }}
                      className="w-full text-left px-2 py-1 hover:bg-gray-700 rounded text-sm text-gray-300 hover:text-white transition-colors"
                    >
                      {(moon as MoonWithNames).fullName || `Moon ${moon.orbitIndex || moon._key}`}
                    </button>
                  ))}
              </div>
            )}
          </div>
        )}

        {/* Asteroid Belts */}
        {data.asteroidBeltIDs && data.asteroidBeltIDs.length > 0 && (
          <div>
            <div className="text-gray-400 text-xs uppercase">Asteroid Belts</div>
            <button
              onClick={() => setExpandedAsteroidBeltsList(!expandedAsteroidBeltsList)}
              className="text-white hover:text-blue-400 transition-colors text-left w-full"
            >
              {data.asteroidBeltIDs.length} belt{data.asteroidBeltIDs.length !== 1 ? 's' : ''}{' '}
              <span className="text-gray-500">{expandedAsteroidBeltsList ? '▼' : '▶'}</span>
            </button>

            {expandedAsteroidBeltsList && systemData && (
              <div className="mt-2 space-y-1 bg-gray-800 rounded p-2">
                {systemData.asteroidBelts
                  .filter((belt) => data.asteroidBeltIDs?.includes(belt._key))
                  .sort((a, b) => (a.orbitIndex || 0) - (b.orbitIndex || 0))
                  .map((belt) => (
                    <button
                      key={belt._key}
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedObject({ type: 'asteroidBelt', data: belt });
                      }}
                      className="w-full text-left px-2 py-1 hover:bg-gray-700 rounded text-sm text-gray-300 hover:text-white transition-colors"
                    >
                      {(belt as AsteroidBeltWithNames).fullName || `Asteroid Belt ${belt.orbitIndex || belt._key}`}
                    </button>
                  ))}
              </div>
            )}
          </div>
        )}

        {/* Population */}
        {data.attributes?.population !== undefined && (
          <div>
            <div className="text-gray-400 text-xs uppercase">Inhabited</div>
            <div className="text-white">{data.attributes.population ? 'Yes' : 'No'}</div>
          </div>
        )}
      </div>
    </div>
  );
}
