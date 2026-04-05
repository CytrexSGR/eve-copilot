'use client';

import Image from 'next/image';
import { getTypeImageUrl, metersToSolarRadii, formatAge } from '@/lib/eve-images';
import type { Star } from '@/lib/sde-types';

interface StarDetailProps {
  data: Star;
  onClose: () => void;
}

export default function StarDetail({ data, onClose }: StarDetailProps) {
  if (!data) return null;

  return (
    <div className="absolute top-1/2 right-4 transform -translate-y-1/2 bg-gray-900 border border-gray-700 rounded-lg shadow-lg max-w-md w-80 overflow-hidden max-h-[90vh] overflow-y-auto detail-panel-scroll">
      {/* Header with close button */}
      <div className="bg-gray-800 px-4 py-3 flex justify-between items-center border-b border-gray-700 sticky top-0 z-10">
        <h3 className="text-white font-semibold text-lg">Star Details</h3>
        <button onClick={onClose} className="text-gray-400 hover:text-white text-xl">
          ×
        </button>
      </div>

      {/* Star image */}
      <div className="bg-black p-4 flex justify-center">
        <Image
          src={getTypeImageUrl(data.typeID, { size: 256, type: 'render' })}
          alt="Star"
          width={256}
          height={256}
          className="w-64 h-64 object-contain"
          unoptimized
        />
      </div>

      {/* Star information */}
      <div className="p-4 space-y-3">
        {/* Spectral class */}
        {data.statistics?.spectralClass && (
          <div>
            <div className="text-gray-400 text-xs uppercase">Spectral Class</div>
            <div className="text-white text-lg font-semibold">{data.statistics.spectralClass}</div>
          </div>
        )}

        {/* Temperature */}
        {data.statistics?.temperature && (
          <div>
            <div className="text-gray-400 text-xs uppercase">Temperature</div>
            <div className="text-white">{data.statistics.temperature.toLocaleString()} K</div>
          </div>
        )}

        {/* Luminosity */}
        {data.statistics?.luminosity !== undefined && (
          <div>
            <div className="text-gray-400 text-xs uppercase">Luminosity</div>
            <div className="text-white">{(data.statistics.luminosity * 100).toFixed(1)}% of Sol</div>
          </div>
        )}

        {/* Radius */}
        {data.radius && (
          <div>
            <div className="text-gray-400 text-xs uppercase">Radius</div>
            <div className="text-white">
              {metersToSolarRadii(data.radius).toFixed(2)} R☉
              <span className="text-gray-500 text-sm ml-2">
                ({(data.radius / 1000).toLocaleString()} km)
              </span>
            </div>
          </div>
        )}

        {/* Age and lifespan */}
        {data.statistics?.age && data.statistics?.life && (
          <div>
            <div className="text-gray-400 text-xs uppercase">Age</div>
            <div className="text-white">{formatAge(data.statistics.age)} billion years</div>
            <div className="text-gray-500 text-sm mt-1">
              {((data.statistics.age / data.statistics.life) * 100).toFixed(1)}% through lifespan
            </div>
            <div className="mt-2 bg-gray-800 rounded-full h-2 overflow-hidden">
              <div
                className="bg-yellow-500 h-full"
                style={{
                  width: `${(data.statistics.age / data.statistics.life) * 100}%`,
                }}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
