import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

export interface SystemADM {
  solar_system_id: number;
  solar_system_name: string;
  region_id: number;
  region_name: string;
  security_status: number;
  alliance_id: number;
  alliance_name: string;
  adm_level: number;
  vulnerable_start_time: string | null;
  vulnerable_end_time: string | null;
}

export interface ADMResponse {
  systems: SystemADM[];
  count: number;
  region_id: number | null;
}

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const regionId = searchParams.get('region_id');

    let url = `${BACKEND_URL}/api/sovereignty/adm`;
    if (regionId) {
      url += `?region_id=${regionId}`;
    }

    const response = await fetch(url, {
      headers: {
        'Accept': 'application/json',
      },
      next: { revalidate: 300 }, // Cache for 5 minutes
    });

    if (!response.ok) {
      throw new Error(`Backend returned ${response.status}`);
    }

    const data: ADMResponse = await response.json();

    return NextResponse.json(data);
  } catch (error) {
    console.error('Failed to fetch sovereignty data:', error);
    return NextResponse.json(
      { error: 'Failed to fetch sovereignty data' },
      { status: 500 }
    );
  }
}
