'use client';

interface SystemHeaderProps {
  systemName: string;
  regionName: string;
  securityStatus: number;
  onClose: () => void;
}

export default function SystemHeader({
  systemName,
  regionName,
  securityStatus,
  onClose,
}: SystemHeaderProps) {
  const systemSecurityRound = (security: number) => {
    if (security >= 0 && security <= 0.05) {
      return Math.ceil(security * 10) / 10;
    } else {
      return Math.round(security * 10) / 10;
    }
  };

  const getSecurityClass = (security: number) => {
    const rounded = systemSecurityRound(security);
    if (rounded >= 0.5) {
      return 'High-Sec';
    } else if (rounded > 0.0) {
      return 'Low-Sec';
    } else {
      return 'Null-Sec';
    }
  };

  return (
    <div className="absolute top-4 left-4 right-4 flex justify-between items-start pointer-events-none">
      <div className="flex gap-4">
        <div className="bg-gray-900 border border-gray-700 rounded-lg p-4 shadow-lg pointer-events-auto">
          <h2 className="text-2xl font-bold text-white">{systemName}</h2>
          <div className="text-gray-400 text-sm mt-1">{regionName}</div>
          <div className="text-gray-400 text-sm mt-1">
            {getSecurityClass(securityStatus)} ({systemSecurityRound(securityStatus).toFixed(1)})
          </div>
        </div>
      </div>

      <button
        onClick={onClose}
        className="bg-gray-900 border border-gray-700 rounded-lg px-4 py-2 text-gray-400 hover:text-white hover:bg-gray-800 transition-colors shadow-lg pointer-events-auto"
      >
        ← Back to Galaxy Map
      </button>
    </div>
  );
}
