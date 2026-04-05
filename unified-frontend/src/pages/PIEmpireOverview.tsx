import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Header } from '@/components/layout/Header'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { useCharacterContext } from '@/contexts/CharacterContext'
import { piApi, PIExtractorStatus, PIAlert } from '@/api/pi'
import { cn } from '@/lib/utils'
import { MaterialFlowDiagram } from '@/components/pi/MaterialFlowDiagram'
import {
  ArrowLeft,
  RefreshCw,
  AlertTriangle,
  CheckCircle,
  Clock,
  Globe2,
  Factory,
  Pickaxe,
  Users,
} from 'lucide-react'

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

function getStatusIcon(status: string) {
  switch (status) {
    case 'active':
      return <CheckCircle className="w-4 h-4 text-green-400" />
    case 'expiring':
      return <Clock className="w-4 h-4 text-yellow-400" />
    case 'stopped':
      return <AlertTriangle className="w-4 h-4 text-red-400" />
    default:
      return null
  }
}

function AlertBanner({ alerts }: { alerts: PIAlert[] }) {
  if (alerts.length === 0) return null

  const criticalCount = alerts.filter(a => a.severity === 'critical').length
  const warningCount = alerts.filter(a => a.severity === 'warning').length

  return (
    <Card className={cn(
      'border',
      criticalCount > 0 ? 'bg-red-500/10 border-red-500/30' : 'bg-yellow-500/10 border-yellow-500/30'
    )}>
      <CardContent className="p-4">
        <div className="flex items-center gap-3">
          <AlertTriangle className={cn(
            'w-5 h-5',
            criticalCount > 0 ? 'text-red-400' : 'text-yellow-400'
          )} />
          <div className="flex-1">
            <p className="font-medium text-[#e6edf3]">
              {criticalCount > 0 && `${criticalCount} critical`}
              {criticalCount > 0 && warningCount > 0 && ', '}
              {warningCount > 0 && `${warningCount} warning${warningCount > 1 ? 's' : ''}`}
            </p>
            <p className="text-sm text-[#8b949e]">
              {alerts[0].message}
              {alerts.length > 1 && ` (+${alerts.length - 1} more)`}
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

function CharacterCard({
  character
}: {
  character: { character_id: number; character_name: string; colonies: number; extractors: number; factories: number }
}) {
  return (
    <Card className="bg-[#161b22] border-[#30363d]">
      <CardHeader className="pb-2">
        <CardTitle className="text-lg flex items-center gap-2">
          <Users className="w-4 h-4 text-[#8b949e]" />
          {character.character_name}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-3 gap-4 text-center">
          <div>
            <div className="text-2xl font-bold text-[#e6edf3]">{character.colonies}</div>
            <div className="text-xs text-[#8b949e] flex items-center justify-center gap-1">
              <Globe2 className="w-3 h-3" /> Colonies
            </div>
          </div>
          <div>
            <div className="text-2xl font-bold text-green-400">{character.extractors}</div>
            <div className="text-xs text-[#8b949e] flex items-center justify-center gap-1">
              <Pickaxe className="w-3 h-3" /> Extractors
            </div>
          </div>
          <div>
            <div className="text-2xl font-bold text-blue-400">{character.factories}</div>
            <div className="text-xs text-[#8b949e] flex items-center justify-center gap-1">
              <Factory className="w-3 h-3" /> Factories
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

function ExtractorTable({ extractors }: { extractors: PIExtractorStatus[] }) {
  return (
    <Card className="bg-[#161b22] border-[#30363d]">
      <CardHeader>
        <CardTitle className="text-lg">Extractors ({extractors.length})</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[#30363d]">
                <th className="text-left py-2 px-3 text-[#8b949e]">Character</th>
                <th className="text-left py-2 px-3 text-[#8b949e]">Planet</th>
                <th className="text-left py-2 px-3 text-[#8b949e]">Product</th>
                <th className="text-left py-2 px-3 text-[#8b949e]">Output/h</th>
                <th className="text-left py-2 px-3 text-[#8b949e]">Status</th>
                <th className="text-right py-2 px-3 text-[#8b949e]">Time Left</th>
              </tr>
            </thead>
            <tbody>
              {extractors.map((ext, idx) => (
                <tr key={idx} className="border-b border-[#30363d]/50 hover:bg-[#21262d]">
                  <td className="py-2 px-3 text-[#e6edf3]">{ext.character_name}</td>
                  <td className="py-2 px-3">
                    <div className="flex items-center gap-2">
                      <span className="text-[#e6edf3]">{ext.planet_name}</span>
                      <Badge className={cn('text-xs border', PLANET_TYPE_COLORS[ext.planet_type] || 'bg-gray-500/20')}>
                        {ext.planet_type}
                      </Badge>
                    </div>
                  </td>
                  <td className="py-2 px-3 text-[#e6edf3]">{ext.product_name}</td>
                  <td className="py-2 px-3 text-[#8b949e]">
                    {ext.qty_per_cycle && ext.cycle_time
                      ? Math.round((ext.qty_per_cycle * 3600) / ext.cycle_time).toLocaleString()
                      : '-'}
                  </td>
                  <td className="py-2 px-3">
                    <div className="flex items-center gap-1">
                      {getStatusIcon(ext.status)}
                      <span className={cn(
                        ext.status === 'active' && 'text-green-400',
                        ext.status === 'expiring' && 'text-yellow-400',
                        ext.status === 'stopped' && 'text-red-400',
                      )}>
                        {ext.status}
                      </span>
                    </div>
                  </td>
                  <td className="py-2 px-3 text-right">
                    {ext.hours_remaining !== null ? (
                      <span className={cn(
                        ext.hours_remaining > 12 && 'text-green-400',
                        ext.hours_remaining <= 12 && ext.hours_remaining > 0 && 'text-yellow-400',
                        ext.hours_remaining <= 0 && 'text-red-400',
                      )}>
                        {ext.hours_remaining > 0 ? `${ext.hours_remaining.toFixed(1)}h` : 'Stopped'}
                      </span>
                    ) : (
                      <span className="text-[#6e7681]">-</span>
                    )}
                  </td>
                </tr>
              ))}
              {extractors.length === 0 && (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-[#8b949e]">
                    No extractors found. Sync your colonies to see extractor data.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  )
}

export default function PIEmpireOverview() {
  const { characters } = useCharacterContext()
  const queryClient = useQueryClient()

  const characterIds = characters.map(c => c.character_id)

  const { data, isLoading, error } = useQuery({
    queryKey: ['pi', 'multi-character', 'detail', characterIds],
    queryFn: () => piApi.getMultiCharacterDetail(characterIds),
    enabled: characterIds.length > 0,
    refetchInterval: 60000, // Refresh every minute
  })

  const syncMutation = useMutation({
    mutationFn: () => piApi.syncMultiCharacterColonies(characterIds),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pi', 'multi-character'] })
    },
  })

  return (
    <div>
      <Header
        title="PI Empire Overview"
        subtitle={`${characterIds.length} characters, monitoring all colonies`}
      />

      <div className="p-6 space-y-6">
        {/* Navigation */}
        <div className="flex items-center justify-between">
          <Link
            to="/pi/empire"
            className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Empire Dashboard
          </Link>
          <button
            onClick={() => syncMutation.mutate()}
            disabled={syncMutation.isPending}
            className="flex items-center gap-2 px-4 py-2 bg-[#238636] hover:bg-[#2ea043] disabled:opacity-50 text-white rounded-lg transition-colors"
          >
            <RefreshCw className={cn('w-4 h-4', syncMutation.isPending && 'animate-spin')} />
            {syncMutation.isPending ? 'Syncing...' : 'Sync All'}
          </button>
        </div>

        {isLoading ? (
          <div className="space-y-4">
            <Skeleton className="h-20 w-full" />
            <div className="grid grid-cols-3 gap-4">
              {[1, 2, 3].map(i => <Skeleton key={i} className="h-32" />)}
            </div>
            <Skeleton className="h-64 w-full" />
          </div>
        ) : error ? (
          <div className="text-red-400 p-4 bg-red-500/10 rounded-lg">
            Error loading PI data: {String(error)}
          </div>
        ) : data ? (
          <>
            {/* Alerts */}
            <AlertBanner alerts={data.alerts} />

            {/* Character Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {data.summary.characters.map(char => (
                <CharacterCard key={char.character_id} character={char} />
              ))}
            </div>

            {/* Summary Stats */}
            <Card className="bg-[#161b22] border-[#30363d]">
              <CardContent className="p-4">
                <div className="grid grid-cols-4 gap-4 text-center">
                  <div>
                    <div className="text-3xl font-bold text-[#e6edf3]">{data.summary.total_colonies}</div>
                    <div className="text-sm text-[#8b949e]">Total Colonies</div>
                  </div>
                  <div>
                    <div className="text-3xl font-bold text-green-400">{data.summary.total_extractors}</div>
                    <div className="text-sm text-[#8b949e]">Extractors</div>
                  </div>
                  <div>
                    <div className="text-3xl font-bold text-blue-400">{data.summary.total_factories}</div>
                    <div className="text-sm text-[#8b949e]">Factories</div>
                  </div>
                  <div>
                    <div className="text-3xl font-bold text-yellow-400">{data.alerts.length}</div>
                    <div className="text-sm text-[#8b949e]">Alerts</div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Material Flow Diagram */}
            <MaterialFlowDiagram characters={data.summary.characters} />

            {/* Extractor Table */}
            <ExtractorTable extractors={data.extractors} />
          </>
        ) : null}
      </div>
    </div>
  )
}
