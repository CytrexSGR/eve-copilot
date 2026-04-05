import { NextResponse } from 'next/server';

export interface LiveKill {
  killmail_id: number;
  killmail_time: string;
  solar_system_id: number;
  ship_type_id: number;
  ship_name: string | null;
  ship_value: number;
}

export interface LiveKillsResponse {
  kills: LiveKill[];
  count: number;
  minutes: number;
}

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const minutes = searchParams.get('minutes') || '5';

  try {
    const response = await fetch(
      `http://localhost:8002/api/war/live/kills/recent?minutes=${minutes}&limit=500`,
      { cache: 'no-store' }
    );

    if (!response.ok) {
      console.error('[ectmap/live-kills] Backend API error:', response.status);
      return NextResponse.json(
        { kills: [], count: 0, minutes: parseInt(minutes) },
        { status: 200 }
      );
    }

    const data: LiveKillsResponse = await response.json();
    console.log(`[ectmap/live-kills] Loaded ${data.kills.length} kills (${minutes}m window)`);

    return NextResponse.json(data, {
      headers: {
        'Cache-Control': 'no-store, must-revalidate',
      },
    });
  } catch (error) {
    console.error('[ectmap/live-kills] Failed to fetch kills:', error);
    return NextResponse.json(
      { kills: [], count: 0, minutes: parseInt(minutes) },
      { status: 200 }
    );
  }
}
