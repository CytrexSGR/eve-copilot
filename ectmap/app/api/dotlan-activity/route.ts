import { NextResponse } from 'next/server';

// In-memory cache with 5-minute TTL
let cache: { data: Record<number, { value: number; normalized: number }> | null; key: string; ts: number } = {
  data: null, key: '', ts: 0,
};
const CACHE_TTL = 5 * 60 * 1000;

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const metric = searchParams.get('metric') || 'npc_kills';
    const hours = searchParams.get('hours') || '24';
    const cacheKey = `${metric}:${hours}`;

    if (cache.data && cache.key === cacheKey && Date.now() - cache.ts < CACHE_TTL) {
      return NextResponse.json(cache.data);
    }

    const url = `http://dotlan-service:8000/api/dotlan/activity/heatmap?metric=${metric}&hours=${hours}`;
    const response = await fetch(url, { cache: 'no-store' });

    if (!response.ok) {
      console.error('[ectmap/dotlan-activity] Backend error:', response.status);
      return NextResponse.json({});
    }

    const raw: Array<{ solar_system_id: number; value: number; normalized: number }> = await response.json();

    // Convert array to Record<systemId, {value, normalized}> for fast lookup
    const result: Record<number, { value: number; normalized: number }> = {};
    for (const entry of raw) {
      result[entry.solar_system_id] = { value: entry.value, normalized: entry.normalized };
    }

    cache = { data: result, key: cacheKey, ts: Date.now() };
    console.log(`[ectmap/dotlan-activity] Loaded ${raw.length} systems (${metric}, ${hours}h)`);

    return NextResponse.json(result, {
      headers: { 'Cache-Control': 'public, max-age=300' },
    });
  } catch (error) {
    console.error('[ectmap/dotlan-activity] Failed:', error);
    return NextResponse.json({});
  }
}
