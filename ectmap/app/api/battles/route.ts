import { NextResponse } from 'next/server';

export interface BattleAllianceInfo {
  alliance_id: number;
  alliance_name: string | null;
  kill_count: number;
}

export interface Battle {
  battle_id: number;
  system_id: number;
  system_name: string;
  region_name: string;
  security: number;
  total_kills: number;
  total_isk_destroyed: number;
  last_milestone: number;
  started_at: string;
  last_kill_at: string;
  duration_minutes: number;
  telegram_sent: boolean;
  intensity: 'extreme' | 'high' | 'moderate' | 'low';
  status_level?: 'gank' | 'brawl' | 'battle' | 'hellcamp';
  x: number;
  z: number;
  top_alliances?: BattleAllianceInfo[];
}

export interface BattlesResponse {
  battles: Battle[];
  count: number;
  timestamp: string;
}

export async function GET(request: Request) {
  try {
    // Get minutes from query params
    const { searchParams } = new URL(request.url);
    const minutes = searchParams.get('minutes') || '';

    // Fetch battles from war-intel-service (Docker service DNS)
    // Use service name:internal_port (war-intel-service:8000) not localhost:host_port
    const url = minutes
      ? `http://war-intel-service:8000/api/war/battles/active?limit=1000&minutes=${minutes}`
      : 'http://war-intel-service:8000/api/war/battles/active?limit=1000';

    const response = await fetch(url, {
      cache: 'no-store', // Always get fresh data
    });

    if (!response.ok) {
      console.error('[ectmap/battles] Backend API error:', response.status);
      return NextResponse.json(
        { battles: [], count: 0, timestamp: new Date().toISOString() },
        { status: 200 }
      );
    }

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const raw = await response.json();

    // Backend uses CamelModel (camelCase), but StarMap.tsx expects snake_case
    // Map camelCase keys to snake_case for frontend compatibility
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const battles: Battle[] = (raw.battles || []).map((b: any) => ({
      battle_id: b.battleId ?? b.battle_id,
      system_id: b.systemId ?? b.solarSystemId ?? b.system_id,
      system_name: b.systemName ?? b.solarSystemName ?? b.system_name,
      region_name: b.regionName ?? b.region_name,
      security: b.security ?? 0,
      total_kills: b.totalKills ?? b.total_kills ?? 0,
      total_isk_destroyed: b.totalIskDestroyed ?? b.total_isk_destroyed ?? 0,
      last_milestone: b.lastMilestone ?? b.last_milestone ?? 0,
      started_at: b.startedAt ?? b.started_at,
      last_kill_at: b.lastKillAt ?? b.last_kill_at,
      duration_minutes: b.durationMinutes ?? b.duration_minutes ?? 0,
      telegram_sent: b.telegramSent ?? b.telegram_sent ?? false,
      intensity: b.intensity ?? 'low',
      status_level: b.statusLevel ?? b.status_level,
      x: b.x ?? 0,
      z: b.z ?? 0,
      top_alliances: b.topAlliances?.map((a: any) => ({
        alliance_id: a.allianceId ?? a.alliance_id,
        alliance_name: a.allianceName ?? a.alliance_name,
        kill_count: a.killCount ?? a.kill_count ?? 0,
      })) ?? b.top_alliances ?? null,
    }));

    const data: BattlesResponse = {
      battles,
      count: battles.length,
      timestamp: raw.timestamp || new Date().toISOString(),
    };

    console.log(`[ectmap/battles] Loaded ${data.battles.length} battles`);

    return NextResponse.json(data, {
      headers: {
        'Cache-Control': 'no-store, must-revalidate',
      },
    });
  } catch (error) {
    console.error('[ectmap/battles] Failed to fetch battles:', error);
    return NextResponse.json(
      { battles: [], count: 0, timestamp: new Date().toISOString() },
      { status: 200 }
    );
  }
}
