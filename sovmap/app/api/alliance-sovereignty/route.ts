import { NextResponse } from 'next/server';
import { ESIAgent } from '@/lib/esi-agent';

let cachedData: {
  data: Record<number, { alliance_id: number; alliance_name: string }>;
  timestamp: number;
} | null = null;
const CACHE_DURATION = 60 * 60 * 1000;

export async function GET() {
  try {
    if (cachedData && Date.now() - cachedData.timestamp < CACHE_DURATION) {
      return NextResponse.json(cachedData.data);
    }

    const sovMap = await ESIAgent.getSovereigntyMap();

    const allianceSystems = sovMap.filter((entry) => entry.alliance_id && !entry.faction_id);

    const allianceIds = Array.from(new Set(allianceSystems.map((entry) => entry.alliance_id!)));

    const allianceNames = await ESIAgent.getNames(allianceIds);

    const allianceNameMap: Record<number, string> = {};
    for (const alliance of allianceNames) {
      if (alliance.category === 'alliance') {
        allianceNameMap[alliance.id] = alliance.name;
      }
    }

    const result: Record<number, { alliance_id: number; alliance_name: string }> = {};
    for (const entry of allianceSystems) {
      if (entry.alliance_id) {
        result[entry.system_id] = {
          alliance_id: entry.alliance_id,
          alliance_name: allianceNameMap[entry.alliance_id] || `Alliance ${entry.alliance_id}`,
        };
      }
    }

    cachedData = {
      data: result,
      timestamp: Date.now(),
    };

    return NextResponse.json(result);
  } catch (error) {
    console.error('Error fetching alliance sovereignty data:', error);
    return NextResponse.json(
      { error: 'Failed to load alliance sovereignty data' },
      { status: 500 }
    );
  }
}
