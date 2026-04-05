// capitalmap/lib/api.ts

const WAR_INTEL_BASE = typeof window !== 'undefined'
  ? `http://${window.location.hostname}:8002`
  : 'http://localhost:8002'

export async function apiFetch(path: string, options?: RequestInit) {
  return fetch(`${WAR_INTEL_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  })
}

export interface CynoJammer {
  solar_system_id: number
  solar_system_name: string
  region_id: number
  region_name: string
  alliance_id: number | null
  alliance_name: string | null
}

export interface StructureTimer {
  id: number
  structure_name: string
  system_id: number
  system_name: string
  timer_end: string
  hours_until: number
  urgency: string
  cyno_jammed: boolean
}

export async function getCynoJammers(): Promise<{ jammers: CynoJammer[] }> {
  const res = await apiFetch('/api/sovereignty/cynojammers')
  if (!res.ok) throw new Error('Failed to fetch jammers')
  return res.json()
}

export async function getUpcomingTimers(hours = 72): Promise<{ timers: StructureTimer[] }> {
  const res = await apiFetch(`/api/timers/upcoming?hours=${hours}`)
  if (!res.ok) throw new Error('Failed to fetch timers')
  return res.json()
}
