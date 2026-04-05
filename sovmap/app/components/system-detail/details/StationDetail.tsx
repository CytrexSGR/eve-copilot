'use client';

import Image from 'next/image';
import { getTypeImageUrl } from '@/lib/eve-images';
import type { StationWithNames } from '../types';
import type { Station } from '@/lib/sde-types';

interface StationDetailProps {
  data: Station;
  onClose: () => void;
  onBack?: () => void;
  showBackButton?: boolean;
}

export default function StationDetail({ data, onClose, onBack, showBackButton }: StationDetailProps) {
  const stationWithNames = data as StationWithNames;
  if (!data) return null;

  return (
    <div className="absolute top-1/2 right-4 transform -translate-y-1/2 bg-gray-900 border border-gray-700 rounded-lg shadow-lg max-w-md w-80 overflow-hidden max-h-[90vh] overflow-y-auto detail-panel-scroll">
      {/* Header with back and close buttons */}
      <div className="bg-gray-800 px-4 py-3 flex justify-between items-center border-b border-gray-700 sticky top-0 z-10">
        <div className="flex items-center gap-2">
          {showBackButton && onBack && (
            <button
              onClick={onBack}
              className="text-gray-400 hover:text-white text-xl"
              title="Back to stations list"
            >
              ←
            </button>
          )}
          <h3 className="text-white font-semibold text-lg">Station</h3>
        </div>
        <button onClick={onClose} className="text-gray-400 hover:text-white text-xl">
          ×
        </button>
      </div>

      {/* Station image */}
      <div className="bg-black p-4 flex justify-center">
        <Image
          src={getTypeImageUrl(data.typeID, { size: 256, type: 'render' })}
          alt="Station"
          width={256}
          height={256}
          className="w-64 h-64 object-contain"
          unoptimized
          onError={(e) => {
            const img = e.target as HTMLImageElement;
            if (img.src.includes('render')) {
              img.src = getTypeImageUrl(data.typeID, { size: 256, type: 'icon' });
            }
          }}
        />
      </div>

      {/* Station information */}
      <div className="p-4 space-y-3">
        {/* Station Name */}
        <div>
          <div className="text-gray-400 text-xs uppercase">Name</div>
          <div className="text-white text-lg font-semibold">
            {stationWithNames.fullName || 'Station'}
          </div>
        </div>

        {/* Station Type */}
        {stationWithNames.typeName && (
          <div>
            <div className="text-gray-400 text-xs uppercase">Type</div>
            <div className="text-white">{stationWithNames.typeName}</div>
          </div>
        )}

        {/* Reprocessing Efficiency */}
        {data.reprocessingEfficiency !== undefined && (
          <div>
            <div className="text-gray-400 text-xs uppercase">Reprocessing Efficiency</div>
            <div className="text-white">{(data.reprocessingEfficiency * 100).toFixed(1)}%</div>
          </div>
        )}

        {/* Reprocessing Station's Take */}
        {data.reprocessingStationsTake !== undefined && (
          <div>
            <div className="text-gray-400 text-xs uppercase">Station&apos;s Take</div>
            <div className="text-white">{(data.reprocessingStationsTake * 100).toFixed(1)}%</div>
          </div>
        )}

        {/* Security Level */}
        {data.security !== undefined && (
          <div>
            <div className="text-gray-400 text-xs uppercase">Security Level</div>
            <div className="text-white">{data.security.toFixed(1)}</div>
          </div>
        )}

        {/* Services */}
        {stationWithNames.services && stationWithNames.services.length > 0 && (
          <div>
            <div className="text-gray-400 text-xs uppercase">Available Services</div>
            <div className="text-white text-sm space-y-1">
              {stationWithNames.services.map((service: string, index: number) => (
                <div key={index} className="flex items-start">
                  <span className="text-green-400 mr-2">•</span>
                  <span>{service}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
