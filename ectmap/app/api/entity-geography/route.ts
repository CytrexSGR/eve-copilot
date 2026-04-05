import { NextRequest, NextResponse } from 'next/server';

const INTEL_SERVICE_URL = process.env.INTEL_SERVICE_URL || 'http://war-intel-service:8000';

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const entityType = searchParams.get('entityType');
  const entityId = searchParams.get('entityId');
  const days = parseInt(searchParams.get('days') || '30');

  if (!entityType || !entityId) {
    return NextResponse.json({ error: 'entityType and entityId required' }, { status: 400 });
  }

  let url: string;
  switch (entityType) {
    case 'corporation':
      url = `${INTEL_SERVICE_URL}/api/intelligence/fast/corporation/${entityId}/geography/extended?days=${days}`;
      break;
    case 'alliance':
      url = `${INTEL_SERVICE_URL}/api/intelligence/fast/alliance/${entityId}/geography/extended?days=${days}`;
      break;
    case 'powerbloc':
      url = `${INTEL_SERVICE_URL}/api/powerbloc/${entityId}/geography/extended?minutes=${days * 1440}`;
      break;
    default:
      return NextResponse.json({ error: 'Invalid entityType' }, { status: 400 });
  }

  try {
    const res = await fetch(url, { next: { revalidate: 300 } });
    if (!res.ok) {
      return NextResponse.json({ error: `Upstream ${res.status}` }, { status: res.status });
    }
    const data = await res.json();

    const systems: Record<number, { activity: number; isHome: boolean; kills: number; deaths: number }> = {};
    let maxActivity = 0;

    for (const s of data.top_systems || []) {
      systems[s.system_id] = {
        activity: s.activity || 0,
        isHome: false,
        kills: s.kills || 0,
        deaths: s.deaths || 0,
      };
      if (s.activity > maxActivity) maxActivity = s.activity;
    }

    for (const s of data.home_systems || []) {
      if (systems[s.system_id]) {
        systems[s.system_id].isHome = true;
      } else {
        systems[s.system_id] = {
          activity: s.activity || 0,
          isHome: true,
          kills: s.kills || 0,
          deaths: s.deaths || 0,
        };
        if (s.activity > maxActivity) maxActivity = s.activity;
      }
    }

    const regions = (data.regions || []).map((r: any) => ({
      region_id: r.region_id,
      region_name: r.region_name,
      activity: r.activity || 0,
    }));

    // Include alliance_id for battle filtering
    const allianceId = data.alliance_power?.alliances?.[0]?.alliance_id ?? null;

    return NextResponse.json({ systems, regions, maxActivity, allianceId }, {
      headers: { 'Cache-Control': 'public, max-age=300' },
    });
  } catch (err) {
    console.error('Entity geography fetch error:', err);
    return NextResponse.json({ error: 'Failed to fetch geography' }, { status: 502 });
  }
}
