import { NextResponse } from 'next/server';

// In-memory cache with 10-minute TTL
let cache: { data: Record<number, number> | null; ts: number } = { data: null, ts: 0 };
const CACHE_TTL = 10 * 60 * 1000;

export async function GET() {
  try {
    if (cache.data && Date.now() - cache.ts < CACHE_TTL) {
      return NextResponse.json(cache.data);
    }

    const url = 'http://dotlan-service:8000/api/dotlan/activity/adm';
    const response = await fetch(url, { cache: 'no-store' });

    if (!response.ok) {
      console.error('[ectmap/dotlan-adm] Backend error:', response.status);
      return NextResponse.json({});
    }

    const raw: Array<{ solar_system_id: number; adm_level: number }> = await response.json();

    // Convert to Record<systemId, admLevel> for fast lookup
    const result: Record<number, number> = {};
    for (const entry of raw) {
      result[entry.solar_system_id] = entry.adm_level;
    }

    cache = { data: result, ts: Date.now() };
    console.log(`[ectmap/dotlan-adm] Loaded ${raw.length} systems with ADM data`);

    return NextResponse.json(result, {
      headers: { 'Cache-Control': 'public, max-age=600' },
    });
  } catch (error) {
    console.error('[ectmap/dotlan-adm] Failed:', error);
    return NextResponse.json({});
  }
}
