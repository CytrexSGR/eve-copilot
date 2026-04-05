'use client';

import { useRouter } from 'next/navigation';
import Image from 'next/image';
import { getTypeImageUrl } from '@/lib/eve-images';
import type { StargateWithNames } from '../types';
import type { Stargate } from '@/lib/sde-types';

interface StargateDetailProps {
  data: Stargate;
  onClose: () => void;
  onBack?: () => void;
  showBackButton?: boolean;
  currentSystemName: string;
}

export default function StargateDetail({
  data,
  onClose,
  onBack,
  showBackButton,
  currentSystemName,
}: StargateDetailProps) {
  const router = useRouter();
  const gateWithNames = data as StargateWithNames;

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
              title="Back to stargates list"
            >
              ←
            </button>
          )}
          <h3 className="text-white font-semibold text-lg">Stargate</h3>
        </div>
        <button onClick={onClose} className="text-gray-400 hover:text-white text-xl">
          ×
        </button>
      </div>

      {/* Stargate image */}
      <div className="bg-black p-4 flex justify-center">
        <Image
          src={getTypeImageUrl(data.typeID, { size: 256, type: 'render' })}
          alt="Stargate"
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

      {/* Stargate information */}
      <div className="p-4 space-y-3">
        {/* Current System */}
        <div>
          <div className="text-gray-400 text-xs uppercase">Current System</div>
          <div className="text-white">{currentSystemName}</div>
        </div>

        {/* Destination - Clickable */}
        {gateWithNames.destinationName && data.destination?.solarSystemID && (
          <div>
            <div className="text-gray-400 text-xs uppercase">Jump To</div>
            <button
              onClick={() => {
                const destSystemId = data.destination.solarSystemID;
                router.push(`/system/${destSystemId}`);
              }}
              className="text-blue-400 hover:text-blue-300 text-lg font-semibold transition-colors underline"
            >
              {gateWithNames.destinationName} →
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
