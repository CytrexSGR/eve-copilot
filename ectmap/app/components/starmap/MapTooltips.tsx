'use client';

import { systemSecurityRound } from './lib/colorFunctions';
import type { HoveredBattle, HoveredKill, HoveredSystem, HoveredCampaign, HoveredTheraConnection } from './types';

interface BattleTooltipProps {
  hovered: HoveredBattle;
}

export function BattleTooltip({ hovered }: BattleTooltipProps) {
  const { battle } = hovered;
  const level = battle.status_level || 'gank';

  const borderClass =
    level === 'hellcamp' ? 'border-cyan-500' :
    level === 'battle' ? 'border-yellow-500' :
    level === 'brawl' ? 'border-orange-500' : 'border-red-500';

  const badgeClass =
    level === 'hellcamp' ? 'bg-cyan-500 text-black' :
    level === 'battle' ? 'bg-yellow-500 text-black' :
    level === 'brawl' ? 'bg-orange-500 text-white' : 'bg-red-500 text-white';

  return (
    <div
      className={`absolute pointer-events-none bg-gray-900 border-2 rounded-lg px-4 py-3 shadow-xl z-30 ${borderClass}`}
      style={{ left: `${hovered.x + 15}px`, top: `${hovered.y + 15}px`, minWidth: '280px' }}
    >
      <div className="flex items-center justify-between mb-2">
        <div className="text-white font-bold text-base flex items-center gap-2">
          <StatusIcon level={level} />
          {battle.system_name}
        </div>
        <div className={`text-xs font-semibold px-2 py-1 rounded ${badgeClass}`}>
          {level.toUpperCase()}
        </div>
      </div>
      <div className="text-gray-400 text-xs mb-2">
        {battle.region_name} • {battle.security.toFixed(1)} sec
      </div>
      <div className="grid grid-cols-2 gap-2 text-xs">
        <div>
          <div className="text-gray-500">Kills</div>
          <div className="text-blue-400 font-semibold">{battle.total_kills}</div>
        </div>
        <div>
          <div className="text-gray-500">ISK Destroyed</div>
          <div className="text-red-400 font-semibold">
            {(battle.total_isk_destroyed / 1_000_000_000).toFixed(1)}B
          </div>
        </div>
        <div>
          <div className="text-gray-500">Duration</div>
          <div className="text-white font-semibold">
            {Math.floor(battle.duration_minutes / 60)}h {battle.duration_minutes % 60}m
          </div>
        </div>
        <div>
          <div className="text-gray-500">Status</div>
          <div className="text-green-400 font-semibold flex items-center gap-1">
            <span className="inline-block w-2 h-2 rounded-full bg-green-500 animate-pulse" />
            ACTIVE
          </div>
        </div>
      </div>
      {battle.top_alliances && battle.top_alliances.length > 0 && (
        <div className="mt-2 pt-2 border-t border-gray-700">
          <div className="text-gray-500 text-xs mb-1">Top Alliances</div>
          {battle.top_alliances.map((a) => (
            <div key={a.alliance_id} className="text-cyan-400 text-xs flex justify-between">
              <span>{a.alliance_name || `Alliance ${a.alliance_id}`}</span>
              <span className="text-gray-500">{a.kill_count} kills</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function StatusIcon({ level }: { level: string }) {
  const iconClass = "w-5 h-5 flex-shrink-0";
  if (level === 'hellcamp') {
    return (
      <svg viewBox="0 0 64 64" className={iconClass} style={{ filter: 'drop-shadow(0 0 4px #00ffff)' }}>
        <g fill="none" stroke="#00ffff" strokeWidth="2">
          <polygon points="32,4 56,18 56,46 32,60 8,46 8,18"/>
          <path d="M22,50 Q27,35 32,50 Q37,35 42,50" stroke="#ff8800" strokeWidth="3"/>
          <circle cx="32" cy="32" r="6" fill="#00ffff"/>
          <circle cx="32" cy="32" r="3" fill="#ffffff"/>
        </g>
      </svg>
    );
  }
  if (level === 'battle') {
    return (
      <svg viewBox="0 0 64 64" className={iconClass} style={{ filter: 'drop-shadow(0 0 4px #ffcc00)' }}>
        <g fill="none" stroke="#ffcc00" strokeWidth="2">
          <polygon points="32,8 52,20 52,44 32,56 12,44 12,20"/>
          <line x1="14" y1="50" x2="32" y2="32" strokeWidth="3"/>
          <line x1="14" y1="14" x2="22" y2="22"/>
          <line x1="50" y1="50" x2="32" y2="32" strokeWidth="3"/>
          <line x1="50" y1="14" x2="42" y2="22"/>
          <polygon points="32,26 38,32 32,38 26,32" fill="#ffcc00"/>
        </g>
      </svg>
    );
  }
  if (level === 'brawl') {
    return (
      <svg viewBox="0 0 64 64" className={iconClass} style={{ filter: 'drop-shadow(0 0 4px #ff8800)' }}>
        <g fill="none" stroke="#ff8800" strokeWidth="2">
          <line x1="10" y1="54" x2="32" y2="32" strokeWidth="3"/>
          <line x1="10" y1="10" x2="18" y2="16"/>
          <line x1="54" y1="54" x2="32" y2="32" strokeWidth="3"/>
          <line x1="54" y1="44" x2="46" y2="48"/>
          <circle cx="32" cy="32" r="4" fill="#ff8800"/>
        </g>
      </svg>
    );
  }
  // gank
  return (
    <svg viewBox="0 0 64 64" className={iconClass} style={{ filter: 'drop-shadow(0 0 4px #ff4444)' }}>
      <g fill="none" stroke="#ff4444" strokeWidth="2">
        <path d="M32,6 L36,20 L32,52 L28,20 Z" fill="#ff4444"/>
        <line x1="24" y1="20" x2="40" y2="20" strokeWidth="3"/>
        <line x1="32" y1="44" x2="32" y2="58"/>
        <circle cx="32" cy="58" r="3" fill="#ff4444"/>
      </g>
    </svg>
  );
}

interface KillTooltipProps {
  hovered: HoveredKill;
}

export function KillTooltip({ hovered }: KillTooltipProps) {
  const { kill } = hovered;
  const iskLabel = kill.ship_value >= 1_000_000_000
    ? `${(kill.ship_value / 1_000_000_000).toFixed(1)}B`
    : kill.ship_value >= 1_000_000
    ? `${(kill.ship_value / 1_000_000).toFixed(0)}M`
    : `${(kill.ship_value / 1000).toFixed(0)}K`;

  const iskClass = kill.ship_value >= 1_000_000_000 ? 'bg-red-600' :
    kill.ship_value >= 100_000_000 ? 'bg-yellow-600' : 'bg-gray-600';

  return (
    <div
      className="absolute pointer-events-none bg-gray-900 border-2 border-yellow-500 rounded-lg px-4 py-3 shadow-xl z-30"
      style={{ left: `${hovered.x + 15}px`, top: `${hovered.y + 15}px`, minWidth: '240px' }}
    >
      <div className="flex items-center justify-between mb-2">
        <div className="text-white font-bold text-base flex items-center gap-2">
          <svg viewBox="0 0 64 64" className="w-5 h-5 flex-shrink-0" style={{ filter: 'drop-shadow(0 0 4px #ff4444)' }}>
            <g fill="none" stroke="#ff4444" strokeWidth="2">
              <path d="M32 8 C18 8 10 18 10 30 C10 38 14 44 18 48 L18 56 L26 56 L26 52 L30 56 L34 56 L38 52 L38 56 L46 56 L46 48 C50 44 54 38 54 30 C54 18 46 8 32 8Z"/>
              <circle cx="24" cy="30" r="6"/>
              <circle cx="40" cy="30" r="6"/>
              <path d="M32 38 L28 44 L36 44 Z"/>
              <line x1="4" y1="30" x2="10" y2="30"/>
              <line x1="54" y1="30" x2="60" y2="30"/>
            </g>
          </svg>
          {kill.ship_name || 'Unknown Ship'}
        </div>
        <div className={`text-xs font-semibold px-2 py-1 rounded ${iskClass} text-white`}>
          {iskLabel}
        </div>
      </div>
      {kill.victim_corp_name && (
        <div className="text-cyan-400 text-xs mb-1">{kill.victim_corp_name}</div>
      )}
      <div className="text-gray-400 text-xs mb-2">
        {hovered.systemName} • {hovered.regionName}
      </div>
      <div className="text-gray-500 text-xs">
        {new Date(kill.killmail_time).toLocaleTimeString()}
      </div>
    </div>
  );
}

interface SystemTooltipProps {
  hovered: HoveredSystem;
}

export function SystemTooltip({ hovered }: SystemTooltipProps) {
  return (
    <div
      className="absolute pointer-events-none bg-gray-900 border border-gray-700 rounded px-3 py-2 shadow-lg z-20"
      style={{ left: `${hovered.x + 15}px`, top: `${hovered.y + 15}px` }}
    >
      <div className="text-white font-semibold text-sm">{hovered.name}</div>
      <div className="text-gray-400 text-xs">
        Security: {systemSecurityRound(hovered.security).toFixed(1)}
      </div>
      {hovered.regionName && (
        <div className="text-blue-400 text-xs mt-1">Region: {hovered.regionName}</div>
      )}
      {hovered.factionName && (
        <div className="text-purple-400 text-xs mt-1">Faction: {hovered.factionName}</div>
      )}
      {hovered.allianceName && (
        <div className="text-green-400 text-xs mt-1">Sovereignty: {hovered.allianceName}</div>
      )}
      {hovered.activityValue !== undefined && hovered.activityMetric && (
        <div className="text-orange-400 text-xs mt-1">
          {hovered.activityMetric === 'npc_kills' ? 'NPC Kills' :
           hovered.activityMetric === 'ship_kills' ? 'Ship Kills' : 'Jumps'}
          : {hovered.activityValue.toLocaleString()} (24h)
        </div>
      )}
      {hovered.admLevel !== undefined && (
        <div className="text-emerald-400 text-xs mt-1">
          ADM: {hovered.admLevel.toFixed(1)}
        </div>
      )}
      {hovered.huntingScore !== undefined && (
        <div className="mt-1 pt-1 border-t border-gray-700">
          <div className="text-orange-400 text-xs font-semibold">
            Hunting Score: {hovered.huntingScore.toFixed(1)}
          </div>
          {hovered.huntingDeaths !== undefined && (
            <div className="text-gray-400 text-xs">
              Deaths: {hovered.huntingDeaths} | Avg ISK: {
                hovered.huntingAvgIsk !== undefined
                  ? hovered.huntingAvgIsk >= 1_000_000_000
                    ? `${(hovered.huntingAvgIsk / 1_000_000_000).toFixed(1)}B`
                    : `${(hovered.huntingAvgIsk / 1_000_000).toFixed(0)}M`
                  : '?'
              }
            </div>
          )}
          {hovered.huntingCapitals && (
            <div className="text-red-400 text-xs font-semibold">⚠ Capital Umbrella</div>
          )}
        </div>
      )}
      <div className="text-gray-500 text-[9px] mt-1 pt-1 border-t border-gray-800">Click for Intel details</div>
    </div>
  );
}

interface CampaignTooltipProps {
  hovered: HoveredCampaign;
}

export function CampaignTooltip({ hovered }: CampaignTooltipProps) {
  const { campaign } = hovered;
  return (
    <div
      className="absolute pointer-events-none bg-gray-900 border-2 border-amber-500 rounded-lg px-3 py-2 shadow-xl z-30"
      style={{ left: `${hovered.x + 15}px`, top: `${hovered.y + 15}px`, minWidth: '200px' }}
    >
      <div className="text-white font-bold text-sm">
        {campaign.solar_system_name || `System ${campaign.solar_system_id}`}
      </div>
      {campaign.region_name && (
        <div className="text-blue-400 text-xs">{campaign.region_name}</div>
      )}
      <div className="text-gray-300 text-xs mt-1">
        Structure: {campaign.structure_type}
      </div>
      {campaign.defender_name && (
        <div className="text-yellow-400 text-xs">
          Defender: {campaign.defender_name}
        </div>
      )}
      {campaign.score !== null && (
        <div className="mt-1">
          <div className="flex items-center gap-2">
            <div className="flex-1 bg-gray-700 rounded-full h-2">
              <div
                className={`h-2 rounded-full ${
                  campaign.score! > 70 ? 'bg-red-500' :
                  campaign.score! > 40 ? 'bg-yellow-500' : 'bg-green-500'
                }`}
                style={{ width: `${Math.min(100, campaign.score!)}%` }}
              />
            </div>
            <span className="text-white text-xs font-mono">{campaign.score}%</span>
          </div>
        </div>
      )}
    </div>
  );
}

interface TheraTooltipProps {
  hovered: HoveredTheraConnection;
}

const SHIP_SIZE_LABELS: Record<string, string> = {
  small: 'Frigate',
  medium: 'Cruiser',
  large: 'Battleship',
  xlarge: 'Freighter',
  capital: 'Capital',
};

const SHIP_SIZE_COLORS: Record<string, string> = {
  small: '#00ccff',
  medium: '#00ccff',
  large: '#ffcc00',
  xlarge: '#ff8800',
  capital: '#ff4444',
};

export function TheraTooltip({ hovered }: TheraTooltipProps) {
  const { connection } = hovered;
  const sizeColor = SHIP_SIZE_COLORS[connection.max_ship_size] || '#ffffff';
  const secClass = connection.in_system_class?.toUpperCase() || '?';
  const secColor = secClass === 'HS' ? '#00ff00' : secClass === 'LS' ? '#ffcc00' : '#ff4444';
  const hoursLeft = connection.remaining_hours;
  const timeColor = hoursLeft < 2 ? '#ff4444' : hoursLeft < 6 ? '#ffcc00' : '#00ff88';

  return (
    <div
      className="absolute pointer-events-none bg-gray-900 border-2 rounded-lg px-3 py-2 shadow-xl z-30"
      style={{
        left: `${hovered.x + 15}px`,
        top: `${hovered.y + 15}px`,
        minWidth: '220px',
        borderColor: '#9333ea',
      }}
    >
      <div className="flex items-center justify-between mb-1">
        <div className="text-white font-bold text-sm flex items-center gap-1.5">
          <span style={{ color: '#9333ea' }}>&#9678;</span>
          {connection.in_system_name}
        </div>
        <span
          className="text-[10px] font-semibold px-1.5 py-0.5 rounded"
          style={{ backgroundColor: secColor + '33', color: secColor }}
        >
          {secClass}
        </span>
      </div>
      <div className="text-blue-400 text-xs">{connection.in_region_name}</div>
      <div className="grid grid-cols-2 gap-x-3 gap-y-1 mt-2 text-xs">
        <div>
          <span className="text-gray-500">Hub</span>
          <div className="text-purple-400 font-semibold">{connection.out_system_name}</div>
        </div>
        <div>
          <span className="text-gray-500">WH Type</span>
          <div className="text-gray-300">{connection.wh_type}</div>
        </div>
        <div>
          <span className="text-gray-500">Max Size</span>
          <div style={{ color: sizeColor }} className="font-semibold">
            {SHIP_SIZE_LABELS[connection.max_ship_size] || connection.max_ship_size}
          </div>
        </div>
        <div>
          <span className="text-gray-500">Expires</span>
          <div style={{ color: timeColor }} className="font-semibold">
            {hoursLeft < 1
              ? `${Math.round(hoursLeft * 60)}m`
              : `${hoursLeft.toFixed(1)}h`}
          </div>
        </div>
      </div>
    </div>
  );
}
