import { NextResponse } from 'next/server';

const EVE_SCOUT_URL = 'https://api.eve-scout.com/v2/public/signatures';

export async function GET() {
  try {
    const res = await fetch(EVE_SCOUT_URL, {
      next: { revalidate: 300 },
      headers: { 'Accept': 'application/json' },
    });

    if (!res.ok) {
      return NextResponse.json(
        { error: `Eve-Scout API returned ${res.status}` },
        { status: 502 }
      );
    }

    const raw = await res.json();

    // Transform Eve-Scout format to our TheraConnection format
    // Filter to only k-space exits (hs, ls, ns) since J-space isn't on the 2D map
    const connections = (Array.isArray(raw) ? raw : [])
      .filter((sig: Record<string, unknown>) =>
        sig.signature_type === 'wormhole' &&
        typeof sig.in_system_id === 'number' &&
        ['hs', 'ls', 'ns'].includes(String(sig.in_system_class || '').toLowerCase())
      )
      .map((sig: Record<string, unknown>) => ({
        id: String(sig.id || ''),
        wh_type: String(sig.wh_type || ''),
        max_ship_size: String(sig.max_ship_size || 'large'),
        remaining_hours: Number(sig.remaining_hours || 0),
        expires_at: String(sig.expires_at || ''),
        out_system_id: Number(sig.out_system_id || 0),
        out_system_name: String(sig.out_system_name || ''),
        in_system_id: Number(sig.in_system_id || 0),
        in_system_name: String(sig.in_system_name || ''),
        in_system_class: String(sig.in_system_class || ''),
        in_region_id: Number(sig.in_region_id || 0),
        in_region_name: String(sig.in_region_name || ''),
      }));

    return NextResponse.json(connections, {
      headers: { 'Cache-Control': 'public, max-age=300' },
    });
  } catch (err) {
    console.error('Thera connections fetch error:', err);
    return NextResponse.json(
      { error: 'Failed to fetch Thera connections' },
      { status: 502 }
    );
  }
}
