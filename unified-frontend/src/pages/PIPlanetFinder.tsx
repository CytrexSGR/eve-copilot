import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { piApi, PlanetRecommendation, PlanetSearchParams } from '@/api/pi'
import { cn } from '@/lib/utils'
import { Search, MapPin, Shield, Star, ChevronDown, ChevronUp } from 'lucide-react'

const PLANET_TYPES = [
  'barren', 'gas', 'ice', 'lava', 'oceanic', 'plasma', 'storm', 'temperate'
]

const PLANET_TYPE_COLORS: Record<string, string> = {
  barren: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
  gas: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30',
  ice: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  lava: 'bg-red-500/20 text-red-400 border-red-500/30',
  oceanic: 'bg-teal-500/20 text-teal-400 border-teal-500/30',
  plasma: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
  storm: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
  temperate: 'bg-green-500/20 text-green-400 border-green-500/30',
}

function getSecurityColor(security: number): string {
  if (security >= 0.5) return 'text-green-400'
  if (security >= 0.0) return 'text-yellow-400'
  return 'text-red-400'
}

function PlanetCard({ planet }: { planet: PlanetRecommendation }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <Card className="bg-[#161b22] border-[#30363d]">
      <CardContent className="p-4">
        <div className="flex justify-between items-start">
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <h3 className="font-medium text-[#e6edf3]">{planet.planet_name}</h3>
              <Badge className={cn('border text-xs', PLANET_TYPE_COLORS[planet.planet_type])}>
                {planet.planet_type}
              </Badge>
            </div>
            <div className="flex items-center gap-4 mt-2 text-sm text-[#8b949e]">
              <span className="flex items-center gap-1">
                <MapPin className="w-3 h-3" />
                {planet.system_name}
              </span>
              <span className="flex items-center gap-1">
                <Shield className={cn('w-3 h-3', getSecurityColor(planet.security))} />
                {planet.security.toFixed(2)}
              </span>
              <span>{planet.jumps_from_home} jump{planet.jumps_from_home !== 1 ? 's' : ''}</span>
            </div>
            <p className="text-xs text-[#6e7681] mt-1">{planet.reason}</p>
          </div>
          <div className="flex flex-col items-end gap-2">
            <div className="flex items-center gap-1">
              <Star className="w-4 h-4 text-yellow-400" />
              <span className="text-lg font-bold text-[#e6edf3]">
                {planet.recommendation_score.toFixed(1)}
              </span>
            </div>
            <button
              onClick={() => setExpanded(!expanded)}
              className="text-[#8b949e] hover:text-[#e6edf3] text-xs flex items-center gap-1"
            >
              Resources
              {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
            </button>
          </div>
        </div>

        {expanded && (
          <div className="mt-3 pt-3 border-t border-[#30363d]">
            <p className="text-xs text-[#8b949e] mb-2">Available P0 Resources:</p>
            <div className="flex flex-wrap gap-1">
              {planet.resources.map((resource) => (
                <Badge key={resource} variant="outline" className="text-xs">
                  {resource}
                </Badge>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export default function PIPlanetFinder() {
  const [searchParams, setSearchParams] = useState<PlanetSearchParams>({
    system_name: 'Isikemi',
    jump_range: 5,
  })
  const [inputSystem, setInputSystem] = useState('Isikemi')

  const { data, isLoading, error } = useQuery({
    queryKey: ['planet-recommendations', searchParams],
    queryFn: () => piApi.recommendPlanets(searchParams),
    enabled: !!searchParams.system_name,
  })

  const handleSearch = () => {
    setSearchParams({
      ...searchParams,
      system_name: inputSystem,
    })
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-[#e6edf3]">Planet Finder</h1>
        <p className="text-[#8b949e]">Find optimal planets for PI extraction near your home system</p>
      </div>

      {/* Search Form */}
      <Card className="bg-[#161b22] border-[#30363d]">
        <CardContent className="p-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium text-[#e6edf3] mb-1">
                Center System
              </label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={inputSystem}
                  onChange={(e) => setInputSystem(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                  placeholder="e.g., Isikemi"
                  className="flex-1 px-3 py-2 bg-[#0d1117] border border-[#30363d] rounded-lg text-[#e6edf3] focus:outline-none focus:border-[#58a6ff]"
                />
                <button
                  onClick={handleSearch}
                  className="px-4 py-2 bg-[#238636] hover:bg-[#2ea043] text-white rounded-lg"
                >
                  <Search className="w-4 h-4" />
                </button>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-[#e6edf3] mb-1">
                Jump Range
              </label>
              <select
                value={searchParams.jump_range}
                onChange={(e) => setSearchParams({ ...searchParams, jump_range: parseInt(e.target.value) })}
                className="w-full px-3 py-2 bg-[#0d1117] border border-[#30363d] rounded-lg text-[#e6edf3] focus:outline-none focus:border-[#58a6ff]"
              >
                {[1, 2, 3, 5, 7, 10, 15].map((n) => (
                  <option key={n} value={n}>{n} jump{n !== 1 ? 's' : ''}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-[#e6edf3] mb-1">
                Planet Type
              </label>
              <select
                value={searchParams.planet_type || ''}
                onChange={(e) => setSearchParams({ ...searchParams, planet_type: e.target.value || undefined })}
                className="w-full px-3 py-2 bg-[#0d1117] border border-[#30363d] rounded-lg text-[#e6edf3] focus:outline-none focus:border-[#58a6ff]"
              >
                <option value="">All Types</option>
                {PLANET_TYPES.map((type) => (
                  <option key={type} value={type}>{type.charAt(0).toUpperCase() + type.slice(1)}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-[#e6edf3] mb-1">
                Min Security
              </label>
              <select
                value={searchParams.min_security ?? -1}
                onChange={(e) => setSearchParams({ ...searchParams, min_security: parseFloat(e.target.value) })}
                className="w-full px-3 py-2 bg-[#0d1117] border border-[#30363d] rounded-lg text-[#e6edf3] focus:outline-none focus:border-[#58a6ff]"
              >
                <option value={-1}>Any</option>
                <option value={0}>Low-sec+ (0.0+)</option>
                <option value={0.5}>High-sec (0.5+)</option>
              </select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Results */}
      {isLoading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-24 w-full" />
          ))}
        </div>
      ) : error ? (
        <div className="text-red-400 p-4 bg-red-500/10 rounded-lg">
          Error: {String(error)}
        </div>
      ) : data ? (
        <>
          {/* Stats */}
          <div className="flex items-center justify-between">
            <div className="text-[#8b949e]">
              Found <span className="text-[#e6edf3] font-medium">{data.planets_found}</span> planets
              in <span className="text-[#e6edf3] font-medium">{data.systems_searched}</span> systems
              within <span className="text-[#e6edf3] font-medium">{data.search_radius}</span> jumps
              of <span className="text-[#e6edf3] font-medium">{data.search_center}</span>
            </div>

            {/* Type distribution */}
            <div className="flex gap-2">
              {Object.entries(data.by_planet_type).map(([type, count]) => (
                <Badge key={type} className={cn('border', PLANET_TYPE_COLORS[type])}>
                  {type}: {count}
                </Badge>
              ))}
            </div>
          </div>

          {/* Planet List */}
          <div className="space-y-3">
            {data.recommendations.map((planet) => (
              <PlanetCard key={planet.planet_id} planet={planet} />
            ))}

            {data.recommendations.length === 0 && (
              <div className="text-center py-12 text-[#8b949e]">
                <p className="text-lg">No planets found</p>
                <p className="text-sm mt-2">Try expanding your search radius or removing filters</p>
              </div>
            )}
          </div>
        </>
      ) : null}
    </div>
  )
}
