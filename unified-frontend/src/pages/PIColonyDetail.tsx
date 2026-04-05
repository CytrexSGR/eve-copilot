import { useMemo } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Header } from '@/components/layout/Header'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { piApi, type PIPin } from '@/api/pi'
import { cn } from '@/lib/utils'
import {
  Globe2,
  Factory,
  Flame,
  Droplets,
  Wind,
  Mountain,
  Leaf,
  Snowflake,
  Zap,
  ArrowLeft,
  Clock,
  Package,
  ArrowRight,
  Drill,
  Warehouse,
  Rocket,
  AlertTriangle,
} from 'lucide-react'

/**
 * Planet type icons and colors
 */
const PLANET_CONFIG: Record<string, { icon: React.ElementType; color: string; bg: string }> = {
  barren: { icon: Mountain, color: 'text-stone-400', bg: 'bg-stone-500/20' },
  gas: { icon: Wind, color: 'text-cyan-400', bg: 'bg-cyan-500/20' },
  ice: { icon: Snowflake, color: 'text-blue-300', bg: 'bg-blue-500/20' },
  lava: { icon: Flame, color: 'text-orange-400', bg: 'bg-orange-500/20' },
  oceanic: { icon: Droplets, color: 'text-blue-400', bg: 'bg-blue-500/20' },
  plasma: { icon: Zap, color: 'text-purple-400', bg: 'bg-purple-500/20' },
  storm: { icon: Wind, color: 'text-yellow-400', bg: 'bg-yellow-500/20' },
  temperate: { icon: Leaf, color: 'text-green-400', bg: 'bg-green-500/20' },
}

/**
 * Pin type categories
 */
const PIN_CATEGORIES: Record<string, { icon: React.ElementType; color: string; label: string }> = {
  'Command Center': { icon: Globe2, color: 'text-blue-400', label: 'Command' },
  'Extractor Control Unit': { icon: Drill, color: 'text-green-400', label: 'Extractor' },
  'Basic Industry Facility': { icon: Factory, color: 'text-yellow-400', label: 'Basic Factory' },
  'Advanced Industry Facility': { icon: Factory, color: 'text-orange-400', label: 'Advanced Factory' },
  'High-Tech Production Plant': { icon: Factory, color: 'text-purple-400', label: 'High-Tech' },
  Launchpad: { icon: Rocket, color: 'text-cyan-400', label: 'Launchpad' },
  'Storage Facility': { icon: Warehouse, color: 'text-gray-400', label: 'Storage' },
}

/**
 * Get pin category from type name
 */
function getPinCategory(typeName: string) {
  for (const [key, value] of Object.entries(PIN_CATEGORIES)) {
    if (typeName.includes(key)) {
      return value
    }
  }
  return { icon: Package, color: 'text-gray-400', label: 'Unknown' }
}

/**
 * Format time remaining
 */
function formatTimeRemaining(expiryTime: string | null): { text: string; isExpired: boolean; isWarning: boolean } {
  if (!expiryTime) return { text: 'N/A', isExpired: false, isWarning: false }

  const expiry = new Date(expiryTime)
  const now = new Date()
  const diffMs = expiry.getTime() - now.getTime()

  if (diffMs <= 0) {
    return { text: 'Expired', isExpired: true, isWarning: false }
  }

  const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
  const diffMins = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60))

  if (diffHours < 1) {
    return { text: `${diffMins}m`, isExpired: false, isWarning: true }
  }
  if (diffHours < 24) {
    return { text: `${diffHours}h ${diffMins}m`, isExpired: false, isWarning: diffHours < 6 }
  }

  const diffDays = Math.floor(diffHours / 24)
  return { text: `${diffDays}d ${diffHours % 24}h`, isExpired: false, isWarning: false }
}

/**
 * Format number
 */
function formatNumber(value: number): string {
  return value.toLocaleString()
}

/**
 * Pin card component
 */
function PinCard({ pin }: { pin: PIPin }) {
  const category = getPinCategory(pin.type_name)
  const CategoryIcon = category.icon
  const timeInfo = formatTimeRemaining(pin.expiry_time)
  const isExtractor = pin.type_name.includes('Extractor')
  const isFactory = pin.type_name.includes('Industry') || pin.type_name.includes('Production')

  return (
    <Card className={cn(
      'overflow-hidden',
      timeInfo.isExpired && 'border-red-500/50',
      timeInfo.isWarning && !timeInfo.isExpired && 'border-yellow-500/50'
    )}>
      <CardContent className="pt-4">
        <div className="flex items-start gap-3">
          <div className={cn('p-2 rounded-lg bg-secondary')}>
            <CategoryIcon className={cn('h-5 w-5', category.color)} />
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="font-medium text-sm">{category.label}</span>
              {isExtractor && pin.expiry_time && (
                <Badge
                  variant="outline"
                  className={cn(
                    'text-xs',
                    timeInfo.isExpired && 'border-red-500 text-red-400',
                    timeInfo.isWarning && !timeInfo.isExpired && 'border-yellow-500 text-yellow-400'
                  )}
                >
                  {timeInfo.isExpired && <AlertTriangle className="h-3 w-3 mr-1" />}
                  <Clock className="h-3 w-3 mr-1" />
                  {timeInfo.text}
                </Badge>
              )}
            </div>

            {/* Product info */}
            {pin.product_name && (
              <div className="flex items-center gap-2 mt-2 text-sm">
                <ArrowRight className="h-3 w-3 text-muted-foreground" />
                <span className="text-muted-foreground">Producing:</span>
                <span className="text-foreground">{pin.product_name}</span>
              </div>
            )}

            {/* Extractor output */}
            {isExtractor && pin.qty_per_cycle && pin.cycle_time && (
              <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
                <span>
                  {formatNumber(pin.qty_per_cycle)} / {pin.cycle_time / 60}min
                </span>
                <span>
                  ({formatNumber(Math.round(pin.qty_per_cycle * (3600 / pin.cycle_time)))}/h)
                </span>
              </div>
            )}

            {/* Factory schematic */}
            {isFactory && pin.schematic_name && (
              <div className="flex items-center gap-2 mt-2 text-xs text-muted-foreground">
                <Factory className="h-3 w-3" />
                <span>{pin.schematic_name}</span>
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

/**
 * Loading skeleton
 */
function ColonyDetailSkeleton() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-4 gap-4">
        {[1, 2, 3, 4].map((i) => (
          <Skeleton key={i} className="h-24" />
        ))}
      </div>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        {[1, 2, 3, 4, 5, 6].map((i) => (
          <Skeleton key={i} className="h-32" />
        ))}
      </div>
    </div>
  )
}

/**
 * Main Colony Detail page
 */
export function PIColonyDetail() {
  const { characterId, planetId } = useParams<{ characterId: string; planetId: string }>()

  const { data, isLoading, isError } = useQuery({
    queryKey: ['pi', 'colony', characterId, planetId],
    queryFn: () => piApi.getColonyDetail(Number(characterId), Number(planetId)),
    enabled: !!characterId && !!planetId,
    staleTime: 2 * 60 * 1000,
  })

  // Categorize pins
  const categorizedPins = useMemo(() => {
    if (!data?.pins) return { extractors: [], factories: [], storage: [], other: [] }

    const extractors = data.pins.filter((p) => p.type_name.includes('Extractor'))
    const factories = data.pins.filter(
      (p) => p.type_name.includes('Industry') || p.type_name.includes('Production')
    )
    const storage = data.pins.filter(
      (p) => p.type_name.includes('Launchpad') || p.type_name.includes('Storage')
    )
    const other = data.pins.filter(
      (p) =>
        !p.type_name.includes('Extractor') &&
        !p.type_name.includes('Industry') &&
        !p.type_name.includes('Production') &&
        !p.type_name.includes('Launchpad') &&
        !p.type_name.includes('Storage')
    )

    return { extractors, factories, storage, other }
  }, [data?.pins])

  // Check for expired extractors
  const expiredExtractors = useMemo(() => {
    return categorizedPins.extractors.filter((p) => {
      if (!p.expiry_time) return false
      return new Date(p.expiry_time) < new Date()
    })
  }, [categorizedPins.extractors])

  if (!characterId || !planetId) {
    return (
      <div>
        <Header title="Colony Detail" subtitle="Invalid parameters" />
        <div className="p-6">
          <Card>
            <CardContent className="py-12 text-center">
              <p className="text-muted-foreground">Invalid colony parameters</p>
              <Link to="/pi" className="text-primary hover:underline mt-2 block">
                ← Back to PI Overview
              </Link>
            </CardContent>
          </Card>
        </div>
      </div>
    )
  }

  const colony = data?.colony
  const planetConfig = colony ? PLANET_CONFIG[colony.planet_type.toLowerCase()] || PLANET_CONFIG.barren : PLANET_CONFIG.barren
  const PlanetIcon = planetConfig.icon

  return (
    <div>
      <Header
        title={colony ? `${colony.planet_type} Colony` : 'Colony Detail'}
        subtitle={colony?.solar_system_name || 'Loading...'}
      />

      <div className="p-6 space-y-6">
        {/* Back link */}
        <Link
          to="/pi"
          className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to PI Overview
        </Link>

        {isLoading ? (
          <ColonyDetailSkeleton />
        ) : isError || !data ? (
          <Card>
            <CardContent className="py-12 text-center">
              <Globe2 className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-lg font-medium mb-2">Failed to Load Colony</h3>
              <p className="text-muted-foreground">Could not fetch colony details.</p>
            </CardContent>
          </Card>
        ) : (
          <>
            {/* Colony Summary */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <Card>
                <CardContent className="pt-4">
                  <div className="flex items-center gap-3">
                    <div className={cn('p-2 rounded-lg', planetConfig.bg)}>
                      <PlanetIcon className={cn('h-5 w-5', planetConfig.color)} />
                    </div>
                    <div>
                      <div className="text-lg font-bold capitalize">{colony?.planet_type}</div>
                      <div className="text-xs text-muted-foreground">Planet Type</div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="pt-4">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-blue-500/20">
                      <Package className="h-5 w-5 text-blue-400" />
                    </div>
                    <div>
                      <div className="text-lg font-bold">{data.pins.length}</div>
                      <div className="text-xs text-muted-foreground">Total Pins</div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="pt-4">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-green-500/20">
                      <Drill className="h-5 w-5 text-green-400" />
                    </div>
                    <div>
                      <div className="text-lg font-bold">{categorizedPins.extractors.length}</div>
                      <div className="text-xs text-muted-foreground">Extractors</div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card className={expiredExtractors.length > 0 ? 'border-red-500/50' : ''}>
                <CardContent className="pt-4">
                  <div className="flex items-center gap-3">
                    <div className={cn(
                      'p-2 rounded-lg',
                      expiredExtractors.length > 0 ? 'bg-red-500/20' : 'bg-yellow-500/20'
                    )}>
                      <AlertTriangle className={cn(
                        'h-5 w-5',
                        expiredExtractors.length > 0 ? 'text-red-400' : 'text-yellow-400'
                      )} />
                    </div>
                    <div>
                      <div className="text-lg font-bold">{expiredExtractors.length}</div>
                      <div className="text-xs text-muted-foreground">Expired</div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Extractors */}
            {categorizedPins.extractors.length > 0 && (
              <div>
                <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">
                  <Drill className="h-5 w-5 text-green-400" />
                  Extractors ({categorizedPins.extractors.length})
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {categorizedPins.extractors.map((pin) => (
                    <PinCard key={pin.pin_id} pin={pin} />
                  ))}
                </div>
              </div>
            )}

            {/* Factories */}
            {categorizedPins.factories.length > 0 && (
              <div>
                <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">
                  <Factory className="h-5 w-5 text-yellow-400" />
                  Factories ({categorizedPins.factories.length})
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {categorizedPins.factories.map((pin) => (
                    <PinCard key={pin.pin_id} pin={pin} />
                  ))}
                </div>
              </div>
            )}

            {/* Storage & Launchpads */}
            {categorizedPins.storage.length > 0 && (
              <div>
                <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">
                  <Warehouse className="h-5 w-5 text-cyan-400" />
                  Storage & Launchpads ({categorizedPins.storage.length})
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {categorizedPins.storage.map((pin) => (
                    <PinCard key={pin.pin_id} pin={pin} />
                  ))}
                </div>
              </div>
            )}

            {/* Other */}
            {categorizedPins.other.length > 0 && (
              <div>
                <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">
                  <Package className="h-5 w-5 text-gray-400" />
                  Other ({categorizedPins.other.length})
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {categorizedPins.other.map((pin) => (
                    <PinCard key={pin.pin_id} pin={pin} />
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
