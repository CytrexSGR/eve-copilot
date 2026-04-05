import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { piApi } from '@/api/pi'
import {
  Truck,
  Clock,
  MapPin,
  ArrowRight,
  Package,
  Building2,
  Route,
} from 'lucide-react'

interface LogisticsDashboardProps {
  planId: number
  frequencyHours?: number
}

function formatTime(minutes: number): string {
  if (minutes < 60) return `${minutes}min`
  const hours = Math.floor(minutes / 60)
  const mins = minutes % 60
  return mins > 0 ? `${hours}h ${mins}min` : `${hours}h`
}

function formatVolume(m3: number): string {
  if (m3 >= 1000) return `${(m3 / 1000).toFixed(1)}k m³`
  return `${m3.toFixed(0)} m³`
}

export function LogisticsDashboard({ planId, frequencyHours = 48 }: LogisticsDashboardProps) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['pi', 'empire', 'logistics', planId, frequencyHours],
    queryFn: () => piApi.getEmpireLogistics(planId, frequencyHours),
    enabled: planId > 0,
  })

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-48 w-full" />
        <Skeleton className="h-32 w-full" />
      </div>
    )
  }

  if (error) {
    return (
      <Card className="bg-red-500/10 border-red-500/30">
        <CardContent className="p-4 text-red-400">
          Error loading logistics: {String(error)}
        </CardContent>
      </Card>
    )
  }

  if (!data) return null

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="bg-[#161b22] border-[#30363d]">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <Clock className="w-8 h-8 text-blue-400" />
              <div>
                <div className="text-2xl font-bold text-[#e6edf3]">
                  {formatTime(data.pickup_schedule.total_time_minutes)}
                </div>
                <div className="text-xs text-[#8b949e]">Per Pickup Run</div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-[#161b22] border-[#30363d]">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <Route className="w-8 h-8 text-purple-400" />
              <div>
                <div className="text-2xl font-bold text-[#e6edf3]">
                  {data.pickup_schedule.total_jumps}
                </div>
                <div className="text-xs text-[#8b949e]">Total Jumps</div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-[#161b22] border-[#30363d]">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <Package className="w-8 h-8 text-yellow-400" />
              <div>
                <div className="text-2xl font-bold text-[#e6edf3]">
                  {formatVolume(data.pickup_schedule.total_cargo_volume_m3)}
                </div>
                <div className="text-xs text-[#8b949e]">Cargo Volume</div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-[#161b22] border-[#30363d]">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <Truck className="w-8 h-8 text-green-400" />
              <div>
                <div className="text-2xl font-bold text-[#e6edf3]">
                  {data.estimated_weekly_trips}
                </div>
                <div className="text-xs text-[#8b949e]">Trips/Week ({data.estimated_weekly_time_hours}h)</div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Pickup Route */}
      <Card className="bg-[#161b22] border-[#30363d]">
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <MapPin className="w-5 h-5 text-[#8b949e]" />
            Pickup Route
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {data.pickup_schedule.route.map((stop, idx) => (
              <div
                key={idx}
                className="flex items-center gap-4 p-3 bg-[#0d1117] rounded-lg"
              >
                <div className="w-8 h-8 rounded-full bg-[#238636] flex items-center justify-center text-white font-bold">
                  {idx + 1}
                </div>
                <div className="flex-1">
                  <div className="font-medium text-[#e6edf3]">
                    {stop.system_name}
                  </div>
                  <div className="text-sm text-[#8b949e]">
                    {stop.character_name} • {stop.planets} planet{stop.planets > 1 ? 's' : ''}
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-sm text-[#e6edf3]">{formatTime(stop.estimated_time_minutes)}</div>
                  <div className="text-xs text-[#8b949e]">{formatVolume(stop.materials_volume_m3)}</div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Transfers */}
      {data.transfers.length > 0 && (
        <Card className="bg-[#161b22] border-[#30363d]">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <ArrowRight className="w-5 h-5 text-[#8b949e]" />
              Cross-Character Transfers
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {data.transfers.map((transfer) => (
                <div
                  key={transfer.id}
                  className="flex items-center gap-4 p-3 bg-[#0d1117] rounded-lg"
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-[#e6edf3]">{transfer.from_character_name}</span>
                      <ArrowRight className="w-4 h-4 text-[#8b949e]" />
                      <span className="font-medium text-[#e6edf3]">{transfer.to_character_name}</span>
                    </div>
                    <div className="text-sm text-[#8b949e]">
                      {transfer.materials.map(m => m.type_name).join(', ')}
                    </div>
                  </div>
                  <Badge className="bg-blue-500/20 text-blue-400 border-blue-500/30">
                    {transfer.method}
                  </Badge>
                  <div className="text-right">
                    <div className="text-sm text-[#e6edf3]">{formatVolume(transfer.total_volume_m3)}</div>
                    <div className="text-xs text-[#8b949e]">every {transfer.frequency_hours}h</div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Hub Station */}
      <Card className="bg-[#161b22] border-[#30363d]">
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Building2 className="w-5 h-5 text-[#8b949e]" />
            Hub Station
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-4 p-3 bg-[#0d1117] rounded-lg">
            <Building2 className="w-10 h-10 text-yellow-400" />
            <div className="flex-1">
              <div className="font-medium text-[#e6edf3]">{data.hub_station.station_name}</div>
              <div className="text-sm text-[#8b949e]">
                {data.hub_station.system_name} ({data.hub_station.security.toFixed(2)} sec)
              </div>
            </div>
            <div className="text-right">
              <div className="text-sm text-green-400">
                ~{data.hub_station.avg_jumps_to_colonies.toFixed(1)} avg jumps
              </div>
              <div className="text-xs text-[#8b949e]">{data.hub_station.reason}</div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
