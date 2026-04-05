import { useMemo } from 'react'
import { useParams, useSearchParams, Link, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, Copy, Check, Pencil, Upload } from 'lucide-react'
import { useState } from 'react'
import { getCharacterFittings, getFittingStats } from '@/api/fittings'
import { apiClient } from '@/api/client'
import { useCharacterContext } from '@/contexts/CharacterContext'
import { SlotPanel } from '@/components/fittings/SlotPanel'
import { StatsPanel } from '@/components/fittings/StatsPanel'
import { ResistProfile } from '@/components/fittings/ResistProfile'
import {
  getShipRenderUrl,
  SLOT_RANGES,
} from '@/types/fittings'
import { generateEft } from '@/lib/eft-parser'
import { ImportDialog } from '@/components/fittings/ImportDialog'
import type { ESIFitting, FittingItem } from '@/types/fittings'

export default function FittingDetail() {
  const { fittingId } = useParams<{ fittingId: string }>()
  const [searchParams] = useSearchParams()
  const shipTypeId = searchParams.get('ship')
  const navigate = useNavigate()
  const { characters, selectedCharacter } = useCharacterContext()
  const charId = selectedCharacter?.character_id || characters[0]?.character_id
  const [copied, setCopied] = useState(false)
  const [showImport, setShowImport] = useState(false)

  // Fetch ESI fittings to find this one
  const { data: fittings = [] } = useQuery({
    queryKey: ['esi-fittings', charId],
    queryFn: () => getCharacterFittings(charId!),
    enabled: !!charId,
    staleTime: 5 * 60 * 1000,
  })

  const fitting: ESIFitting | undefined = useMemo(() => {
    if (!fittingId) return undefined
    return fittings.find((f) => String(f.fitting_id) === fittingId)
  }, [fittings, fittingId])

  const actualShipTypeId = fitting?.ship_type_id || (shipTypeId ? Number(shipTypeId) : 0)

  // Fetch combined stats
  const { data: stats, isLoading: loadingStats } = useQuery({
    queryKey: ['fitting-stats', actualShipTypeId, fitting?.items],
    queryFn: () =>
      getFittingStats(
        actualShipTypeId,
        fitting?.items || [],
      ),
    enabled: !!fitting && actualShipTypeId > 0,
    staleTime: 10 * 60 * 1000,
  })

  // Group items by slot
  const slotGroups = useMemo(() => {
    if (!fitting) return { high: [], mid: [], low: [], rig: [] }
    const grouped: Record<string, FittingItem[]> = { high: [], mid: [], low: [], rig: [] }
    for (const item of fitting.items) {
      for (const [slot, [min, max]] of Object.entries(SLOT_RANGES)) {
        if (item.flag >= min && item.flag <= max) {
          grouped[slot].push(item)
          break
        }
      }
    }
    return grouped
  }, [fitting])

  // Resolve type names for EFT export
  const allTypeIds = useMemo(() => {
    if (!fitting) return []
    return [...new Set(fitting.items.map((i) => i.type_id))]
  }, [fitting])

  const { data: typeNames = {} } = useQuery({
    queryKey: ['type-names-eft', allTypeIds.sort().join(',')],
    queryFn: async () => {
      if (allTypeIds.length === 0) return {}
      const { data } = await apiClient.get<{ types: Record<string, string> }>(
        '/dogma/types/names',
        { params: { ids: allTypeIds.join(',') } }
      )
      const result: Record<number, string> = {}
      for (const [k, v] of Object.entries(data.types || {})) {
        result[Number(k)] = v
      }
      return result
    },
    staleTime: 60 * 60 * 1000,
    enabled: allTypeIds.length > 0,
  })

  // Generate EFT format with resolved names
  const eftText = useMemo(() => {
    if (!fitting || !stats) return ''
    const modulesBySlot: Record<string, string[]> = { low: [], mid: [], high: [], rig: [] }
    const drones: { name: string; quantity: number }[] = []

    for (const [slot, items] of Object.entries(slotGroups)) {
      for (const item of items) {
        const name = typeNames[item.type_id] || `Unknown (${item.type_id})`
        modulesBySlot[slot].push(name)
      }
    }

    // Collect drones (flag 87)
    for (const item of fitting.items) {
      if (item.flag === 87) {
        const name = typeNames[item.type_id] || `Unknown (${item.type_id})`
        drones.push({ name, quantity: item.quantity })
      }
    }

    return generateEft(stats.ship.name, fitting.name, modulesBySlot as any, drones)
  }, [fitting, stats, slotGroups, typeNames])

  const handleCopyEft = async () => {
    if (!eftText) return
    try {
      await navigator.clipboard.writeText(eftText)
    } catch {
      // Fallback for non-HTTPS contexts
      const ta = document.createElement('textarea')
      ta.value = eftText
      ta.style.position = 'fixed'
      ta.style.opacity = '0'
      document.body.appendChild(ta)
      ta.select()
      document.execCommand('copy')
      document.body.removeChild(ta)
    }
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  if (!fitting) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-muted-foreground">
        <p className="text-sm">
          {fittings.length > 0 ? 'Fitting not found' : 'Loading...'}
        </p>
        <Link to="/fittings" className="text-primary text-sm mt-2 hover:underline">
          Back to Fittings
        </Link>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link
            to="/fittings"
            className="flex h-9 w-9 items-center justify-center rounded-lg text-muted-foreground hover:bg-accent transition-colors"
          >
            <ArrowLeft className="h-5 w-5" />
          </Link>
          <img
            src={getShipRenderUrl(actualShipTypeId, 128)}
            alt=""
            className="h-16 w-16 rounded-lg"
          />
          <div>
            <h1 className="text-xl font-bold">{fitting.name}</h1>
            <p className="text-sm text-muted-foreground">
              {stats?.ship.name || 'Loading...'} &mdash; {stats?.ship.group_name || ''}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() =>
              navigate('/fittings/new', {
                state: {
                  shipTypeId: actualShipTypeId,
                  items: fitting.items,
                  name: fitting.name,
                },
              })
            }
            className="inline-flex items-center gap-2 rounded-lg border border-border px-3 py-2 text-sm hover:bg-accent transition-colors"
          >
            <Pencil className="h-4 w-4" />
            Edit
          </button>
          <button
            onClick={handleCopyEft}
            className="inline-flex items-center gap-2 rounded-lg border border-border px-3 py-2 text-sm hover:bg-accent transition-colors"
          >
            {copied ? <Check className="h-4 w-4 text-green-400" /> : <Copy className="h-4 w-4" />}
            {copied ? 'Copied' : 'Export EFT'}
          </button>
          <button
            onClick={() => setShowImport(true)}
            className="inline-flex items-center gap-2 rounded-lg border border-border px-3 py-2 text-sm hover:bg-accent transition-colors"
          >
            <Upload className="h-4 w-4" />
            Import
          </button>
        </div>
      </div>

      {/* Stats Overview */}
      {loadingStats ? (
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-20 animate-pulse rounded-lg bg-card border border-border" />
          ))}
        </div>
      ) : stats ? (
        <StatsPanel stats={stats} />
      ) : null}

      {/* Module Slots */}
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="space-y-3">
          <SlotPanel
            label="High Slots"
            items={slotGroups.high}
            total={stats?.slots.hi_total || 0}
            color="#f85149"
          />
          <SlotPanel
            label="Mid Slots"
            items={slotGroups.mid}
            total={stats?.slots.med_total || 0}
            color="#00d4ff"
          />
          <SlotPanel
            label="Low Slots"
            items={slotGroups.low}
            total={stats?.slots.low_total || 0}
            color="#ff8800"
          />
          <SlotPanel
            label="Rig Slots"
            items={slotGroups.rig}
            total={stats?.slots.rig_total || 0}
            color="#a855f7"
          />
        </div>

        {/* Resist Profile + Navigation */}
        <div className="space-y-3">
          {stats && <ResistProfile defense={stats.defense} />}

          {/* Navigation */}
          {stats && (
            <div className="rounded-lg border border-border bg-card p-4">
              <h3 className="text-sm font-medium mb-3">Navigation</h3>
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <p className="text-xs text-muted-foreground">Max Velocity</p>
                  <p className="text-sm font-mono font-medium">{stats.navigation.max_velocity.toFixed(0)} m/s</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Agility</p>
                  <p className="text-sm font-mono font-medium">{stats.navigation.agility.toFixed(2)}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Sig Radius</p>
                  <p className="text-sm font-mono font-medium">{stats.navigation.signature_radius.toFixed(0)} m</p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      <ImportDialog open={showImport} onClose={() => setShowImport(false)} />
    </div>
  )
}
