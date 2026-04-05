// unified-frontend/src/api/capital.ts

import { apiClient } from './client'
import type {
  JumpShip,
  JumpRange,
  FatigueCalculation,
  SystemDistance,
  CynoAltRoute,
  TimersResponse,
  StructureTimer,
  TimerCreateInput,
  CynoJammerResponse,
} from '@/types/capital'

const WAR_INTEL_BASE = typeof window !== 'undefined'
  ? `http://${window.location.hostname}:8002`
  : 'http://localhost:8002'

// ==============================================================================
// Jump Planner API
// ==============================================================================

export async function getJumpShips(): Promise<{ ships: JumpShip[] }> {
  const response = await fetch(`${WAR_INTEL_BASE}/api/jump/ships`)
  if (!response.ok) throw new Error('Failed to fetch jump ships')
  return response.json()
}

export async function getJumpRange(
  shipName: string,
  jdcLevel = 5,
  jfLevel = 5
): Promise<JumpRange> {
  const params = new URLSearchParams({
    jdc_level: jdcLevel.toString(),
    jf_level: jfLevel.toString(),
  })
  const response = await fetch(`${WAR_INTEL_BASE}/api/jump/range/${encodeURIComponent(shipName)}?${params}`)
  if (!response.ok) throw new Error('Failed to calculate jump range')
  return response.json()
}

export async function calculateFatigue(
  distanceLy: number,
  currentFatigue = 0
): Promise<FatigueCalculation> {
  const params = new URLSearchParams({
    distance_ly: distanceLy.toString(),
    current_fatigue: currentFatigue.toString(),
  })
  const response = await fetch(`${WAR_INTEL_BASE}/api/jump/fatigue?${params}`)
  if (!response.ok) throw new Error('Failed to calculate fatigue')
  return response.json()
}

export async function getSystemDistance(
  originId: number,
  destinationId: number
): Promise<SystemDistance> {
  const params = new URLSearchParams({
    origin_id: originId.toString(),
    destination_id: destinationId.toString(),
  })
  const response = await fetch(`${WAR_INTEL_BASE}/api/jump/distance?${params}`)
  if (!response.ok) throw new Error('Failed to calculate distance')
  return response.json()
}

export async function planCynoAltRoute(
  originId: number,
  destinationId: number,
  shipName = 'Rhea',
  jdcLevel = 5,
  jfLevel = 5,
  preferStations = true,
  maxSecurity = 0.45,
  minSecurity = -1.0
): Promise<CynoAltRoute> {
  const params = new URLSearchParams({
    origin_id: originId.toString(),
    destination_id: destinationId.toString(),
    ship_name: shipName,
    jdc_level: jdcLevel.toString(),
    jf_level: jfLevel.toString(),
    prefer_stations: preferStations.toString(),
    max_security: maxSecurity.toString(),
    min_security: minSecurity.toString(),
  })
  const response = await fetch(`${WAR_INTEL_BASE}/api/jump/cyno-alts?${params}`)
  if (!response.ok) throw new Error('Failed to plan cyno route')
  return response.json()
}

// ==============================================================================
// Structure Timers API
// ==============================================================================

export async function getUpcomingTimers(
  hours = 72,
  category?: string,
  regionId?: number,
  allianceId?: number
): Promise<TimersResponse> {
  const params = new URLSearchParams({ hours: hours.toString() })
  if (category) params.append('category', category)
  if (regionId) params.append('region_id', regionId.toString())
  if (allianceId) params.append('alliance_id', allianceId.toString())

  const response = await fetch(`${WAR_INTEL_BASE}/api/timers/upcoming?${params}`)
  if (!response.ok) throw new Error('Failed to fetch timers')
  return response.json()
}

export async function getTimer(timerId: number): Promise<StructureTimer> {
  const response = await fetch(`${WAR_INTEL_BASE}/api/timers/${timerId}`)
  if (!response.ok) throw new Error('Failed to fetch timer')
  return response.json()
}

export async function createTimer(timer: TimerCreateInput): Promise<{ id: number; message: string }> {
  const response = await fetch(`${WAR_INTEL_BASE}/api/timers/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(timer),
  })
  if (!response.ok) throw new Error('Failed to create timer')
  return response.json()
}

export async function updateTimer(
  timerId: number,
  update: { timer_end?: string; result?: string; is_active?: boolean; notes?: string }
): Promise<{ message: string }> {
  const response = await fetch(`${WAR_INTEL_BASE}/api/timers/${timerId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(update),
  })
  if (!response.ok) throw new Error('Failed to update timer')
  return response.json()
}

export async function deleteTimer(timerId: number): Promise<{ message: string }> {
  const response = await fetch(`${WAR_INTEL_BASE}/api/timers/${timerId}`, {
    method: 'DELETE',
  })
  if (!response.ok) throw new Error('Failed to delete timer')
  return response.json()
}

export async function getTimerStats(): Promise<{
  active_timers: { by_category: Record<string, number>; by_urgency: Record<string, number>; total: number }
  recent_results: Record<string, number>
}> {
  const response = await fetch(`${WAR_INTEL_BASE}/api/timers/stats/summary`)
  if (!response.ok) throw new Error('Failed to fetch timer stats')
  return response.json()
}

// ==============================================================================
// Cyno Jammer API
// ==============================================================================

export async function getCynoJammers(regionId?: number): Promise<CynoJammerResponse> {
  const params = regionId ? new URLSearchParams({ region_id: regionId.toString() }) : ''
  const response = await fetch(`${WAR_INTEL_BASE}/api/sovereignty/cynojammers${params ? '?' + params : ''}`)
  if (!response.ok) throw new Error('Failed to fetch cyno jammers')
  return response.json()
}
