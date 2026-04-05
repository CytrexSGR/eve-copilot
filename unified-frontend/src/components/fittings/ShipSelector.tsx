import { useState, useRef, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Search, ChevronDown, X } from 'lucide-react'
import { getShips, getShipDetail } from '@/api/fittings'
import { getShipRenderUrl } from '@/types/fittings'
import type { ShipDetail, ShipSummary } from '@/types/fittings'

interface ShipSelectorProps {
  selectedShip: ShipDetail | null
  onSelect: (ship: ShipDetail) => void
}

export function ShipSelector({ selectedShip, onSelect }: ShipSelectorProps) {
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState('')
  const ref = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // Close on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  // Focus input when opened
  useEffect(() => {
    if (open) inputRef.current?.focus()
  }, [open])

  const { data: ships = [], isFetching } = useQuery({
    queryKey: ['sde-ships', search],
    queryFn: () => getShips({ search: search || undefined, limit: 30 }),
    enabled: open && search.length >= 2,
    staleTime: 60 * 1000,
  })

  async function handleSelect(ship: ShipSummary) {
    setOpen(false)
    setSearch('')
    const detail = await getShipDetail(ship.type_id)
    onSelect(detail)
  }

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-3 rounded-lg border border-border bg-card p-3 hover:border-primary/40 transition-colors text-left"
      >
        {selectedShip ? (
          <>
            <img
              src={getShipRenderUrl(selectedShip.type_id, 64)}
              alt=""
              className="h-10 w-10 rounded-md"
            />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">{selectedShip.type_name}</p>
              <p className="text-xs text-muted-foreground">{selectedShip.group_name}</p>
            </div>
            <div className="text-xs text-muted-foreground font-mono">
              {selectedShip.hi_slots}H {selectedShip.med_slots}M {selectedShip.low_slots}L {selectedShip.rig_slots}R
            </div>
          </>
        ) : (
          <span className="text-sm text-muted-foreground flex-1">Select a ship...</span>
        )}
        <ChevronDown className="h-4 w-4 text-muted-foreground shrink-0" />
      </button>

      {open && (
        <div className="absolute z-50 mt-1 w-full rounded-lg border border-border bg-card shadow-lg">
          <div className="p-2 border-b border-border">
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
              <input
                ref={inputRef}
                type="text"
                placeholder="Search ships (min 2 chars)..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="h-8 w-full rounded-md border border-border bg-background pl-8 pr-8 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
              />
              {search && (
                <button
                  onClick={() => setSearch('')}
                  className="absolute right-2 top-1/2 -translate-y-1/2"
                >
                  <X className="h-3.5 w-3.5 text-muted-foreground" />
                </button>
              )}
            </div>
          </div>

          <div className="max-h-64 overflow-y-auto p-1">
            {search.length < 2 ? (
              <p className="px-3 py-4 text-xs text-muted-foreground text-center">
                Type at least 2 characters to search
              </p>
            ) : isFetching ? (
              <div className="px-3 py-4 text-xs text-muted-foreground text-center">Searching...</div>
            ) : ships.length === 0 ? (
              <p className="px-3 py-4 text-xs text-muted-foreground text-center">No ships found</p>
            ) : (
              ships.map((ship) => (
                <button
                  key={ship.type_id}
                  onClick={() => handleSelect(ship)}
                  className="w-full flex items-center gap-2.5 rounded-md px-2 py-1.5 text-left hover:bg-accent transition-colors"
                >
                  <img
                    src={getShipRenderUrl(ship.type_id, 64)}
                    alt=""
                    className="h-8 w-8 rounded"
                    loading="lazy"
                  />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm truncate">{ship.type_name}</p>
                    <p className="text-[10px] text-muted-foreground">{ship.group_name}</p>
                  </div>
                  <span className="text-[10px] text-muted-foreground font-mono shrink-0">
                    {ship.hi_slots}H {ship.med_slots}M {ship.low_slots}L
                  </span>
                </button>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  )
}
