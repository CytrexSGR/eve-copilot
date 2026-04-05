'use client';

import Image from 'next/image';
import { getTypeImageUrl } from '@/lib/eve-images';
import type { SelectedObject, MoonWithNames } from '../types';
import type { SystemDetailResponse, Moon } from '@/lib/sde-types';
import CelestialStats from './CelestialStats';

interface MoonDetailProps {
  data: Moon;
  onClose: () => void;
  systemData: SystemDetailResponse;
  setSelectedObject: (obj: SelectedObject | null) => void;
}

export default function MoonDetail({
  data,
  onClose,
  systemData,
  setSelectedObject,
}: MoonDetailProps) {
  const moonWithNames = data as MoonWithNames;
  if (!data) return null;

  const handleBackToPlanet = () => {
    const parentPlanet = systemData.planets.find((p) => p._key === data.orbitID);
    if (parentPlanet) {
      setSelectedObject({ type: 'planet', data: parentPlanet });
    }
  };

  return (
    <div className="absolute top-1/2 right-4 transform -translate-y-1/2 bg-gray-900 border border-gray-700 rounded-lg shadow-lg max-w-md w-80 overflow-hidden max-h-[90vh] overflow-y-auto detail-panel-scroll">
      {/* Header with back and close buttons */}
      <div className="bg-gray-800 px-4 py-3 flex justify-between items-center border-b border-gray-700 sticky top-0 z-10">
        <div className="flex items-center gap-2">
          <button
            onClick={handleBackToPlanet}
            className="text-gray-400 hover:text-white text-xl"
            title="Back to planet"
          >
            ←
          </button>
          <h3 className="text-white font-semibold text-lg">
            {moonWithNames.fullName || `Moon ${data.orbitIndex}`}
          </h3>
        </div>
        <button onClick={onClose} className="text-gray-400 hover:text-white text-xl">
          ×
        </button>
      </div>

      {/* Moon image */}
      <div className="bg-gradient-to-br from-gray-900 to-black p-6 flex justify-center items-center">
        <div className="relative">
          <Image
            src={getTypeImageUrl(data.typeID, { size: 128, type: 'icon' })}
            alt="Moon"
            width={96}
            height={96}
            className="w-24 h-24 rounded-full object-cover border-2 border-gray-700 shadow-lg shadow-gray-500/20"
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

      {/* Moon information */}
      <div className="p-4">
        <CelestialStats statistics={data.statistics} radius={data.radius} type="moon" />
      </div>
    </div>
  );
}
