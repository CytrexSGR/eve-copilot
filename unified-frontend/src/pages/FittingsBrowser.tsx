import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Search, Plus, Users, User, Upload } from 'lucide-react'
import { getCharacterFittings, getSharedFittings } from '@/api/fittings'
import { useCharacterContext } from '@/contexts/CharacterContext'
import { ImportDialog } from '@/components/fittings/ImportDialog'
import { getShipRenderUrl } from '@/types/fittings'
import type { ESIFitting, CustomFitting, ShipClass } from '@/types/fittings'

const SHIP_CLASSES: { label: string; value: ShipClass }[] = [
  { label: 'All', value: 'all' },
  { label: 'Frigate', value: 'Frigate' },
  { label: 'Destroyer', value: 'Destroyer' },
  { label: 'Cruiser', value: 'Cruiser' },
  { label: 'BC', value: 'Battlecruiser' },
  { label: 'BS', value: 'Battleship' },
  { label: 'Capital', value: 'Capital' },
]

function getSlotCount(items: { flag: number }[]): number {
  return items.filter((i) => i.flag >= 11 && i.flag <= 99).length
}

export default function FittingsBrowser() {
  const { characters, selectedCharacter } = useCharacterContext()
  const [search, setSearch] = useState('')
  const [shipClass, setShipClass] = useState<ShipClass>('all')
  const [tab, setTab] = useState<'my' | 'shared'>('my')
  const [showImport, setShowImport] = useState(false)

  const charId = selectedCharacter?.character_id || characters[0]?.character_id

  // Fetch ESI fittings for selected character
  const { data: esiFittings = [], isLoading: loadingEsi } = useQuery({
    queryKey: ['esi-fittings', charId],
    queryFn: () => getCharacterFittings(charId!),
    enabled: tab === 'my' && !!charId,
    staleTime: 5 * 60 * 1000,
  })

  // Fetch shared fittings
  const { data: sharedFittings = [], isLoading: loadingShared } = useQuery({
    queryKey: ['shared-fittings', search],
    queryFn: () => getSharedFittings({ search: search || undefined, limit: 100 }),
    enabled: tab === 'shared',
    staleTime: 5 * 60 * 1000,
  })

  const isLoading = tab === 'my' ? loadingEsi : loadingShared

  // Filter ESI fittings
  const filteredFittings = useMemo(() => {
    const fittings = tab === 'my' ? esiFittings : []
    let result = fittings

    if (search) {
      const q = search.toLowerCase()
      result = result.filter((f) => f.name.toLowerCase().includes(q))
    }

    return result
  }, [esiFittings, search, tab])

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Fittings</h1>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowImport(true)}
            className="inline-flex items-center gap-2 rounded-lg border border-border px-4 py-2 text-sm font-medium hover:bg-accent transition-colors"
          >
            <Upload className="h-4 w-4" />
            Import EFT
          </button>
          <Link
            to="/fittings/new"
            className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
          >
            <Plus className="h-4 w-4" />
            New Fitting
          </Link>
        </div>
      </div>

      {/* Search & Tabs */}
      <div className="space-y-3">
        <div className="flex gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search fittings..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="h-10 w-full rounded-lg border border-border bg-background pl-10 pr-4 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>
          <div className="flex rounded-lg border border-border">
            <button
              onClick={() => setTab('my')}
              className={`flex items-center gap-1.5 px-4 py-2 text-sm font-medium rounded-l-lg transition-colors ${
                tab === 'my'
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:bg-accent'
              }`}
            >
              <User className="h-3.5 w-3.5" />
              My Fits
            </button>
            <button
              onClick={() => setTab('shared')}
              className={`flex items-center gap-1.5 px-4 py-2 text-sm font-medium rounded-r-lg transition-colors ${
                tab === 'shared'
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:bg-accent'
              }`}
            >
              <Users className="h-3.5 w-3.5" />
              Shared
            </button>
          </div>
        </div>

        {/* Ship Class Filter */}
        <div className="flex gap-1.5 flex-wrap">
          {SHIP_CLASSES.map((cls) => (
            <button
              key={cls.value}
              onClick={() => setShipClass(cls.value)}
              className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                shipClass === cls.value
                  ? 'bg-primary/20 text-primary border border-primary/40'
                  : 'bg-card text-muted-foreground border border-border hover:border-primary/30'
              }`}
            >
              {cls.label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="h-28 animate-pulse rounded-lg bg-card border border-border" />
          ))}
        </div>
      ) : tab === 'my' ? (
        <ESIFittingGrid fittings={filteredFittings} />
      ) : (
        <SharedFittingGrid fittings={sharedFittings} />
      )}

      <ImportDialog open={showImport} onClose={() => setShowImport(false)} />
    </div>
  )
}

function ESIFittingGrid({ fittings }: { fittings: ESIFitting[] }) {
  if (fittings.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
        <p className="text-sm">No fittings found</p>
        <p className="text-xs mt-1">Import fittings in-game or create a new one</p>
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      {fittings.map((f, i) => (
        <Link
          key={f.fitting_id || i}
          to={`/fittings/esi/${f.fitting_id}?ship=${f.ship_type_id}`}
          className="group rounded-lg border border-border bg-card p-4 hover:border-primary/40 transition-colors"
        >
          <div className="flex gap-3">
            <img
              src={getShipRenderUrl(f.ship_type_id, 64)}
              alt=""
              className="h-14 w-14 rounded-md object-cover"
              loading="lazy"
            />
            <div className="min-w-0 flex-1">
              <h3 className="text-sm font-medium truncate group-hover:text-primary transition-colors">
                {f.name}
              </h3>
              <p className="text-xs text-muted-foreground mt-0.5 truncate">
                {f.description || 'No description'}
              </p>
              <div className="flex items-center gap-2 mt-2">
                <span className="text-xs text-muted-foreground">
                  {getSlotCount(f.items)} modules
                </span>
              </div>
            </div>
          </div>
        </Link>
      ))}
    </div>
  )
}

function SharedFittingGrid({ fittings }: { fittings: CustomFitting[] }) {
  if (fittings.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
        <p className="text-sm">No shared fittings yet</p>
        <p className="text-xs mt-1">Save a fitting as public to share it</p>
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      {fittings.map((f) => (
        <Link
          key={f.id}
          to={`/fittings/custom/${f.id}`}
          className="group rounded-lg border border-border bg-card p-4 hover:border-primary/40 transition-colors"
        >
          <div className="flex gap-3">
            <img
              src={getShipRenderUrl(f.ship_type_id, 64)}
              alt=""
              className="h-14 w-14 rounded-md object-cover"
              loading="lazy"
            />
            <div className="min-w-0 flex-1">
              <h3 className="text-sm font-medium truncate group-hover:text-primary transition-colors">
                {f.name}
              </h3>
              <p className="text-xs text-muted-foreground mt-0.5">
                {f.ship_name}
              </p>
              <div className="flex items-center gap-2 mt-2 flex-wrap">
                {f.tags.slice(0, 3).map((tag) => (
                  <span
                    key={tag}
                    className="px-1.5 py-0.5 text-[10px] font-medium rounded bg-primary/10 text-primary"
                  >
                    {tag}
                  </span>
                ))}
                <span className="text-xs text-muted-foreground">
                  {f.items.length} mods
                </span>
              </div>
            </div>
          </div>
        </Link>
      ))}
    </div>
  )
}
