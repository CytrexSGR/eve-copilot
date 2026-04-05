import { NextResponse } from 'next/server';

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
  x: number;
  z: number;
}

export interface BattlesResponse {
  battles: Battle[];
  count: number;
  timestamp: string;
}

export async function GET() {
  try {
    // Fetch battles from war-intel-service (port 8002)
    const response = await fetch('http://localhost:8002/api/war/battles/active?limit=1000', {
      cache: 'no-store', // Always get fresh data
    });

    if (!response.ok) {
      console.error('[ectmap/battles] Backend API error:', response.status);
      return NextResponse.json(
        { battles: [], count: 0, timestamp: new Date().toISOString() },
        { status: 200 }
      );
    }

    const data: BattlesResponse = await response.json();

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
