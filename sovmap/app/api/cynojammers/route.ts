import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

export interface JammedSystemsResponse {
  system_ids: number[];
  count: number;
}

export async function GET(_request: NextRequest) {
  try {
    const response = await fetch(`${BACKEND_URL}/api/sovereignty/cynojammers/systems`, {
      headers: {
        'Accept': 'application/json',
      },
      next: { revalidate: 60 },
    });

    if (!response.ok) {
      throw new Error(`Backend returned ${response.status}`);
    }

    const data: JammedSystemsResponse = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Failed to fetch cyno jammer data:', error);
    return NextResponse.json({ system_ids: [], count: 0 }, { status: 500 });
  }
}
