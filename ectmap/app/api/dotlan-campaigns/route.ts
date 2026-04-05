import { NextResponse } from 'next/server';

export interface SovCampaign {
  campaign_id: number;
  solar_system_id: number;
  structure_type: string;
  defender_name: string | null;
  defender_id: number | null;
  score: number | null;
  status: string;
  solar_system_name: string | null;
  region_name: string | null;
}

// In-memory cache with 2-minute TTL
let cache: { data: SovCampaign[] | null; ts: number } = { data: null, ts: 0 };
const CACHE_TTL = 2 * 60 * 1000;

export async function GET() {
  try {
    if (cache.data && Date.now() - cache.ts < CACHE_TTL) {
      return NextResponse.json(cache.data);
    }

    const url = 'http://dotlan-service:8000/api/dotlan/sovereignty/campaigns/map';
    const response = await fetch(url, { cache: 'no-store' });

    if (!response.ok) {
      console.error('[ectmap/dotlan-campaigns] Backend error:', response.status);
      return NextResponse.json([]);
    }

    const data: SovCampaign[] = await response.json();
    cache = { data, ts: Date.now() };
    console.log(`[ectmap/dotlan-campaigns] Loaded ${data.length} active campaigns`);

    return NextResponse.json(data, {
      headers: { 'Cache-Control': 'public, max-age=120' },
    });
  } catch (error) {
    console.error('[ectmap/dotlan-campaigns] Failed:', error);
    return NextResponse.json([]);
  }
}
