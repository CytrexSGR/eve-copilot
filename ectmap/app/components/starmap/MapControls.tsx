'use client';

import type { ColorMode } from './types';

interface ColorModeButtonsProps {
  colorMode: ColorMode;
  setColorMode: (mode: ColorMode) => void;
  showCampaigns: boolean;
  setShowCampaigns: (v: boolean) => void;
  campaignCount: number;
  showCapitalActivity: boolean;
  setShowCapitalActivity: (v: boolean) => void;
  capitalCount: number;
  showLogiPresence: boolean;
  setShowLogiPresence: (v: boolean) => void;
  logiCount: number;
  intelDays: number;
  setIntelDays: (days: number) => void;
  showWormholes: boolean;
  setShowWormholes: (v: boolean) => void;
  wormholeCount: number;
}

export function ColorModeButtons({
  colorMode, setColorMode,
  showCampaigns, setShowCampaigns, campaignCount,
  showCapitalActivity, setShowCapitalActivity, capitalCount,
  showLogiPresence, setShowLogiPresence, logiCount,
  intelDays, setIntelDays,
  showWormholes, setShowWormholes, wormholeCount,
}: ColorModeButtonsProps) {
  const btn = (mode: ColorMode, label: string, activeClass = 'bg-blue-600') => (
    <button
      onClick={() => setColorMode(mode)}
      className={`px-2 py-1 text-xs rounded transition-colors ${
        colorMode === mode
          ? `${activeClass} text-white`
          : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
      }`}
    >
      {label}
    </button>
  );

  return (
    <div className="absolute top-4 left-4 bg-gray-900/90 border border-gray-700 rounded-lg p-2 shadow-lg">
      <div className="flex items-center gap-1">
        {btn('region', 'Reg')}
        {btn('security', 'Sec')}
        {btn('faction', 'FW')}
        {btn('alliance', 'Sov')}
      </div>
      <div className="flex items-center gap-1 mt-1">
        <span className="text-gray-500 text-[9px] mr-0.5">DOTLAN</span>
        {btn('npc_kills', 'NPC', 'bg-orange-600')}
        {btn('ship_kills', 'Kills', 'bg-orange-600')}
        {btn('jumps', 'Jump', 'bg-orange-600')}
        {btn('adm', 'ADM', 'bg-orange-600')}
        <button
          onClick={() => setShowCampaigns(!showCampaigns)}
          className={`px-2 py-1 text-xs rounded transition-colors ${
            showCampaigns ? 'bg-purple-600 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
          }`}
        >
          IHUB {showCampaigns && campaignCount > 0 && campaignCount}
        </button>
      </div>
      <div className="flex items-center gap-1 mt-1">
        <span className="text-gray-500 text-[9px] mr-0.5">INTEL</span>
        {btn('hunting', 'Hunt', 'bg-orange-600')}
        <button
          onClick={() => setShowCapitalActivity(!showCapitalActivity)}
          className={`px-2 py-1 text-xs rounded transition-colors ${
            showCapitalActivity ? 'bg-red-600 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
          }`}
        >
          Cap {showCapitalActivity && capitalCount > 0 && capitalCount}
        </button>
        <button
          onClick={() => setShowLogiPresence(!showLogiPresence)}
          className={`px-2 py-1 text-xs rounded transition-colors ${
            showLogiPresence ? 'bg-cyan-600 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
          }`}
        >
          Logi {showLogiPresence && logiCount > 0 && logiCount}
        </button>
        <button
          onClick={() => setShowWormholes(!showWormholes)}
          className={`px-2 py-1 text-xs rounded transition-colors ${
            showWormholes ? 'bg-purple-600 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
          }`}
        >
          WH {showWormholes && wormholeCount > 0 && wormholeCount}
        </button>
        <div className="w-px h-4 bg-gray-600 mx-0.5" />
        {([7, 14, 30] as const).map((d) => (
          <button
            key={d}
            onClick={() => setIntelDays(d)}
            className={`px-1.5 py-0.5 text-[10px] rounded transition-colors ${
              intelDays === d
                ? 'bg-gray-600 text-white font-semibold'
                : 'bg-gray-800 text-gray-500 hover:bg-gray-700'
            }`}
          >
            {d}d
          </button>
        ))}
      </div>
    </div>
  );
}

type StatusLevel = 'gank' | 'brawl' | 'battle' | 'hellcamp';

const STATUS_CONFIG: Record<StatusLevel, { label: string; borderColor: string }> = {
  gank: { label: 'Gank', borderColor: '#ff4444' },
  brawl: { label: 'Brawl', borderColor: '#ff8800' },
  battle: { label: 'Fleet', borderColor: '#ffcc00' },
  hellcamp: { label: 'Hellcamp', borderColor: '#00ffff' },
};

interface OverlayControlsProps {
  statusFilters: Record<StatusLevel, boolean>;
  setStatusFilters: (filters: Record<StatusLevel, boolean>) => void;
  statusCounts: Record<StatusLevel, number>;
  activityMinutes: number;
  setActivityMinutes: (v: number) => void;
}

export function OverlayControls({
  statusFilters, setStatusFilters, statusCounts,
  activityMinutes, setActivityMinutes,
}: OverlayControlsProps) {
  const toggleStatus = (level: StatusLevel) => {
    setStatusFilters({ ...statusFilters, [level]: !statusFilters[level] });
  };

  return (
    <div className="absolute bottom-4 right-4 bg-gray-900/90 border border-gray-700 rounded-lg p-2 shadow-lg">
      <div className="flex items-center gap-1">
        {(Object.keys(STATUS_CONFIG) as StatusLevel[]).map((level) => {
          const count = statusCounts[level];
          const isActive = statusFilters[level];
          const { label, borderColor } = STATUS_CONFIG[level];
          return (
            <button
              key={level}
              onClick={() => toggleStatus(level)}
              style={{
                borderColor: isActive ? borderColor : 'transparent',
                color: isActive ? borderColor : 'rgba(255,255,255,0.4)',
                backgroundColor: isActive ? `${borderColor}22` : 'rgba(0,0,0,0.3)',
              }}
              className="px-1.5 py-0.5 text-[10px] font-semibold rounded border transition-colors hover:opacity-80"
            >
              {label}{count > 0 ? ` ${count}` : ''}
            </button>
          );
        })}
        <div className="w-px h-5 bg-gray-700 mx-1" />
        <select
          value={activityMinutes}
          onChange={(e) => setActivityMinutes(parseInt(e.target.value))}
          className="px-2 py-1 text-xs rounded bg-gray-800 text-gray-300 border border-gray-700 focus:outline-none cursor-pointer"
        >
          <option value={10} className="bg-gray-800 text-gray-300">10m</option>
          <option value={60} className="bg-gray-800 text-gray-300">1h</option>
        </select>
      </div>
    </div>
  );
}

interface HeatmapLegendProps {
  colorMode: ColorMode;
}

export function HeatmapLegend({ colorMode }: HeatmapLegendProps) {
  if (!['npc_kills', 'ship_kills', 'jumps', 'adm', 'hunting'].includes(colorMode)) return null;

  return (
    <div className="absolute bottom-4 left-4 bg-gray-900/90 border border-gray-700 rounded-lg p-2 shadow-lg">
      <div className="text-gray-400 text-[10px] mb-1">
        {colorMode === 'hunting' ? 'Hunting Score' :
         colorMode === 'adm' ? 'ADM Level' :
         colorMode === 'npc_kills' ? 'NPC Kills (24h)' :
         colorMode === 'ship_kills' ? 'Ship Kills (24h)' : 'Jumps (24h)'}
      </div>
      <div className="flex items-center gap-1">
        <span className="text-gray-500 text-[9px]">
          {colorMode === 'hunting' ? '0' : colorMode === 'adm' ? '1.0' : 'Low'}
        </span>
        <div
          className="w-24 h-2 rounded"
          style={{
            background: colorMode === 'hunting'
              ? 'linear-gradient(to right, hsl(220, 50%, 25%), hsl(180, 80%, 40%), hsl(120, 80%, 50%), hsl(60, 90%, 50%), hsl(0, 100%, 45%))'
              : colorMode === 'adm'
              ? 'linear-gradient(to right, hsl(0, 70%, 45%), hsl(60, 85%, 45%), hsl(120, 100%, 45%))'
              : 'linear-gradient(to right, hsl(210, 40%, 20%), hsl(180, 80%, 40%), hsl(60, 100%, 50%), hsl(0, 100%, 40%))',
          }}
        />
        <span className="text-gray-500 text-[9px]">
          {colorMode === 'hunting' ? '100' : colorMode === 'adm' ? '6.0' : 'High'}
        </span>
      </div>
    </div>
  );
}
