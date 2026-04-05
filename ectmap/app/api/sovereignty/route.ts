import { NextResponse } from 'next/server';
import { ESIAgent } from '@/lib/esi-agent';
import { findRecords } from '@/lib/sde-loader';

interface Faction {
  _key: number;
  name: {
    en: string;
  };
  [key: string]: unknown;
}

let cachedData: { data: Map<number, number>; timestamp: number } | null = null;
const CACHE_DURATION = 30 * 60 * 1000;

export async function GET() {
  try {
    if (cachedData && Date.now() - cachedData.timestamp < CACHE_DURATION) {
      return NextResponse.json(Object.fromEntries(cachedData.data));
    }

    const fwSystems = await ESIAgent.getFactionWarfareSystems();

    const systemFactionMap = new Map<number, number>();

    for (const system of fwSystems) {
      systemFactionMap.set(system.solar_system_id, system.owner_faction_id);
    }

    cachedData = {
      data: systemFactionMap,
      timestamp: Date.now(),
    };

    return NextResponse.json(Object.fromEntries(systemFactionMap));
  } catch (error) {
    console.error('Error fetching FW data:', error);
    return NextResponse.json({ error: 'Failed to load FW data' }, { status: 500 });
  }
}

export async function POST() {
  try {
    const factions = await findRecords<Faction>('types.jsonl', (record) => {
      return record._key >= 500000 && record._key < 501000;
    });

    const factionMap: Record<number, string> = {};
    for (const faction of factions) {
      if (faction.name?.en) {
        factionMap[faction._key] = faction.name.en;
      }
    }

    return NextResponse.json(factionMap);
  } catch (error) {
    console.error('Error loading faction data:', error);
    return NextResponse.json({ error: 'Failed to load faction data' }, { status: 500 });
  }
}
