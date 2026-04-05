/**
 * Color functions for all StarMap color modes.
 */

export function systemSecurityRound(security: number): number {
  if (security >= 0 && security <= 0.05) {
    return Math.ceil(security * 10) / 10;
  }
  return Math.round(security * 10) / 10;
}

export function getSecurityColor(security: number): string {
  const rounded = systemSecurityRound(security);
  if (rounded >= 0.5) {
    const intensity = (rounded - 0.5) / 0.5;
    const hue = 60 + intensity * 180;
    const lightness = 50 - intensity * 20;
    return `hsl(${hue}, 100%, ${lightness}%)`;
  } else if (rounded > 0) {
    const intensity = (rounded - 0.1) / 0.3;
    const saturation = 60 + intensity * 40;
    const lightness = 30 + intensity * 20;
    return `hsl(30, ${saturation}%, ${lightness}%)`;
  }
  return `hsl(0, 100%, 40%)`;
}

export function getRegionColor(regionId: number): string {
  const hue = (regionId * 137.508) % 360;
  return `hsl(${hue}, 70%, 60%)`;
}

export function getFactionColor(factionId: number | undefined): string {
  if (!factionId) return 'hsl(0, 0%, 30%)';

  const factionColors: Record<number, string> = {
    500001: 'hsl(210, 100%, 50%)',
    500002: 'hsl(0, 100%, 50%)',
    500003: 'hsl(45, 100%, 50%)',
    500004: 'hsl(120, 60%, 45%)',
  };

  return factionColors[factionId] || `hsl(${(factionId * 137.508) % 360}, 70%, 60%)`;
}

export const ALLIANCE_COLORS: Record<number, string> = {
  // Blue Coalition
  99002685: '#00FFFF',   // Synergy of Steel
  1411711376: '#FF4444', // Legion of xXDEATHXx
  99012019: '#00FF00',   // Can i bring my Drake
  99007203: '#FF00FF',   // Siberian Squads

  // Imperium
  1354830081: '#FFD700', // Goonswarm Federation
  99005338: '#FFFF00',   // The Initiative.

  // PanFam
  99003214: '#1E90FF',   // Pandemic Horde
  386292982: '#4169E1',  // Pandemic Legion
  99005065: '#00CED1',   // Northern Coalition.

  // Other Major
  99012122: '#FF69B4',   // HOLD MY PROBS
  99012770: '#DC143C',   // Black Rose.
  154104258: '#9932CC',  // Apocalypse Now.
  99003581: '#32CD32',   // Brave Collective
  99010079: '#FF6347',   // Dracarys.
  99009082: '#7B68EE',   // Fraternity.
  99001258: '#20B2AA',   // TEST Alliance
  99010134: '#F0E68C',   // FI.RE
  99011223: '#DDA0DD',   // Siege Green.
};

export function getAllianceColor(allianceId: number | undefined): string {
  if (!allianceId) return 'hsl(0, 0%, 30%)';
  if (ALLIANCE_COLORS[allianceId]) return ALLIANCE_COLORS[allianceId];

  const hue = (allianceId * 137.508) % 360;
  const saturation = 85 + (allianceId % 15);
  const lightness = 50 + ((allianceId * 7) % 20);
  return `hsl(${hue}, ${saturation}%, ${lightness}%)`;
}

export function getActivityColor(
  systemId: number,
  activityData: Record<number, { value: number; normalized: number }> | null,
): string {
  const entry = activityData?.[systemId];
  if (!entry) return 'hsl(0, 0%, 15%)';
  const n = entry.normalized;
  if (n < 0.25) {
    const t = n / 0.25;
    return `hsl(${210 + t * 30}, ${40 + t * 40}%, ${20 + t * 20}%)`;
  } else if (n < 0.5) {
    const t = (n - 0.25) / 0.25;
    return `hsl(${180 - t * 120}, ${80 + t * 20}%, ${40 + t * 10}%)`;
  }
  const t = (n - 0.5) / 0.5;
  return `hsl(${60 - t * 60}, 100%, ${50 - t * 10}%)`;
}

export function getAdmColor(
  systemId: number,
  admData: Record<number, number> | null,
): string {
  const adm = admData?.[systemId];
  if (adm === undefined) return 'hsl(0, 0%, 15%)';
  const normalized = Math.max(0, Math.min(1, (adm - 1.0) / 5.0));
  const hue = normalized * 120;
  const saturation = 70 + normalized * 30;
  return `hsl(${hue}, ${saturation}%, 45%)`;
}

export function getHuntingColor(
  systemId: number,
  huntingData: { systems: Record<number, { score: number }>; max_score: number } | null,
): string {
  const entry = huntingData?.systems[systemId];
  if (!entry) return 'rgba(255, 255, 255, 0.08)';
  const n = huntingData!.max_score > 0 ? entry.score / huntingData!.max_score : 0;
  // darkblue (0) → cyan (0.25) → green (0.5) → yellow (0.75) → red (1.0)
  if (n < 0.25) return `hsl(${220 - n * 4 * 40}, ${50 + n * 4 * 30}%, ${25 + n * 4 * 15}%)`;
  if (n < 0.5) return `hsl(${180 - (n - 0.25) * 4 * 60}, 80%, ${40 + (n - 0.25) * 4 * 10}%)`;
  if (n < 0.75) return `hsl(${120 - (n - 0.5) * 4 * 60}, 90%, ${50}%)`;
  return `hsl(${60 - (n - 0.75) * 4 * 60}, 100%, ${50 - (n - 0.75) * 4 * 10}%)`;
}

export const FACTION_NAMES: Record<number, string> = {
  500001: 'Caldari State',
  500002: 'Minmatar Republic',
  500003: 'Amarr Empire',
  500004: 'Gallente Federation',
};
