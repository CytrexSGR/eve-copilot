import { NextRequest, NextResponse } from 'next/server';

const INTEL_SERVICE_URL = process.env.INTEL_SERVICE_URL || 'http://war-intel-service:8000';

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const days = searchParams.get('days') || '30';

  try {
    const res = await fetch(
      `${INTEL_SERVICE_URL}/api/intelligence/map/logi-presence?days=${days}`,
      { next: { revalidate: 300 } }
    );
    if (!res.ok) {
      return NextResponse.json({ error: `Upstream ${res.status}` }, { status: res.status });
    }
    const data = await res.json();
    return NextResponse.json(data, {
      headers: { 'Cache-Control': 'public, max-age=300' },
    });
  } catch (err) {
    console.error('Intel logi fetch error:', err);
    return NextResponse.json({ error: 'Failed to fetch logi data' }, { status: 502 });
  }
}
