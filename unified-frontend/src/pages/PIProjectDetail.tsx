import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Header } from '@/components/layout/Header'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import {
  piApi,
  type PIAssignment,
  type PIProjectStatus,
  type MakeOrBuyResult,
  type PIColony,
} from '@/api/pi'
import { useCharacters } from '@/hooks/useCharacters'
import { cn } from '@/lib/utils'
import {
  ArrowLeft,
  Factory,
  RefreshCw,
  Loader2,
  Wand2,
  Target,
  ShoppingCart,
} from 'lucide-react'

/**
 * Status badge colors
 */
const STATUS_CONFIG: Record<PIProjectStatus, { label: string; color: string; bg: string }> = {
  active: { label: 'Active', color: 'text-green-400', bg: 'bg-green-500/20' },
  planning: { label: 'Planning', color: 'text-blue-400', bg: 'bg-blue-500/20' },
  paused: { label: 'Paused', color: 'text-yellow-400', bg: 'bg-yellow-500/20' },
  completed: { label: 'Completed', color: 'text-gray-400', bg: 'bg-gray-500/20' },
}

/**
 * Tier badge colors
 */
const TIER_CONFIG: Record<number, { label: string; color: string; bg: string }> = {
  0: { label: 'P0', color: 'text-gray-400', bg: 'bg-gray-500/20' },
  1: { label: 'P1', color: 'text-blue-400', bg: 'bg-blue-500/20' },
  2: { label: 'P2', color: 'text-green-400', bg: 'bg-green-500/20' },
  3: { label: 'P3', color: 'text-purple-400', bg: 'bg-purple-500/20' },
  4: { label: 'P4', color: 'text-yellow-400', bg: 'bg-yellow-500/20' },
}

/**
 * Get item icon URL
 */
function getItemIconUrl(typeId: number, size: 32 | 64 = 32): string {
  return `https://images.evetech.net/types/${typeId}/icon?size=${size}`
}

/**
 * Colony select for assignment
 */
function ColonySelect({
  assignment,
  colonies,
  onSelect,
  disabled,
}: {
  assignment: PIAssignment
  colonies: PIColony[]
  onSelect: (colonyId: number | null) => void
  disabled?: boolean
}) {
  return (
    <select
      value={assignment.colony_id ?? ''}
      onChange={(e) => onSelect(e.target.value ? Number(e.target.value) : null)}
      disabled={disabled}
      className="w-full px-2 py-1 rounded bg-secondary/50 border border-border text-sm disabled:opacity-50"
    >
      <option value="">-- Select Colony --</option>
      {colonies.map((colony) => (
        <option key={colony.id} value={colony.id}>
          {colony.solar_system_name} / {colony.planet_type}
        </option>
      ))}
    </select>
  )
}

/**
 * Main PI Project Detail Page
 */
export function PIProjectDetail() {
  const { projectId } = useParams<{ projectId: string }>()
  const queryClient = useQueryClient()
  const { data: charactersData } = useCharacters()
  const characters = charactersData?.characters ?? []

  const [isSyncing, setIsSyncing] = useState(false)

  // Fetch project detail
  const { data: projectDetail, isLoading: isLoadingProject } = useQuery({
    queryKey: ['pi', 'project', projectId],
    queryFn: () => piApi.getProject(Number(projectId)),
    enabled: !!projectId,
    staleTime: 30 * 1000,
  })

  // Fetch assignments
  const { data: assignments, isLoading: isLoadingAssignments } = useQuery({
    queryKey: ['pi', 'project', projectId, 'assignments'],
    queryFn: () => piApi.getAssignments(Number(projectId)),
    enabled: !!projectId,
    staleTime: 30 * 1000,
  })

  // Fetch colonies for assignment dropdown
  const characterId = projectDetail?.project.character_id
  const { data: colonies } = useQuery({
    queryKey: ['pi', 'colonies', characterId],
    queryFn: () => piApi.getColonies(characterId!),
    enabled: !!characterId,
  })

  // Fetch make-or-buy for all materials
  const materialTypeIds = assignments?.map((a) => a.material_type_id) ?? []
  const makeOrBuyQueries = useQuery({
    queryKey: ['pi', 'make-or-buy-batch', materialTypeIds],
    queryFn: async () => {
      const results: Record<number, MakeOrBuyResult> = {}
      // Fetch in parallel
      await Promise.all(
        materialTypeIds.map(async (typeId) => {
          try {
            const result = await piApi.analyzeMakeOrBuy(typeId)
            results[typeId] = result
          } catch {
            // Skip failed ones
          }
        })
      )
      return results
    },
    enabled: materialTypeIds.length > 0,
    staleTime: 5 * 60 * 1000,
  })

  // Update assignment mutation
  const updateAssignmentMutation = useMutation({
    mutationFn: ({ materialTypeId, colonyId }: { materialTypeId: number; colonyId: number | null }) =>
      piApi.updateAssignment(Number(projectId), materialTypeId, colonyId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pi', 'project', projectId, 'assignments'] })
    },
  })

  // Auto-assign mutation
  const autoAssignMutation = useMutation({
    mutationFn: () => piApi.autoAssign(Number(projectId)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pi', 'project', projectId, 'assignments'] })
    },
  })

  // Status update mutation
  const updateStatusMutation = useMutation({
    mutationFn: (status: PIProjectStatus) => piApi.updateProjectStatus(Number(projectId), status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pi', 'project', projectId] })
      queryClient.invalidateQueries({ queryKey: ['pi', 'projects'] })
    },
  })

  const handleSync = async () => {
    setIsSyncing(true)
    try {
      await piApi.syncProject(Number(projectId))
      queryClient.invalidateQueries({ queryKey: ['pi', 'project', projectId] })
    } finally {
      setIsSyncing(false)
    }
  }

  const project = projectDetail?.project
  const isLoading = isLoadingProject || isLoadingAssignments
  const makeOrBuyData = makeOrBuyQueries.data ?? {}

  // Calculate stats
  const assignedCount = assignments?.filter((a) => a.colony_id !== null).length ?? 0
  const totalMaterials = assignments?.length ?? 0

  return (
    <div>
      <Header
        title={project?.name ?? 'Project Detail'}
        subtitle={project ? `Target: ${project.target_product_type_id ? 'P' + (projectDetail?.colonies?.[0]?.expected_output_type_id ?? '') : 'None'}` : ''}
      />

      <div className="p-6 space-y-6">
        {/* Back link */}
        <Link
          to="/pi/projects"
          className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Projects
        </Link>

        {isLoading ? (
          <div className="space-y-4">
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-64 w-full" />
          </div>
        ) : !project ? (
          <Card>
            <CardContent className="py-12 text-center">
              <Factory className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-lg font-medium mb-2">Project Not Found</h3>
              <p className="text-muted-foreground">
                This project does not exist or has been deleted.
              </p>
            </CardContent>
          </Card>
        ) : (
          <>
            {/* Summary Card */}
            <Card>
              <CardContent className="py-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className="p-3 rounded-lg bg-primary/20">
                      <Target className="h-6 w-6 text-primary" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{project.name}</span>
                        <Badge className={cn('text-xs', STATUS_CONFIG[project.status].bg, STATUS_CONFIG[project.status].color)}>
                          {STATUS_CONFIG[project.status].label}
                        </Badge>
                      </div>
                      <div className="text-sm text-muted-foreground">
                        {characters.find((c) => c.character_id === project.character_id)?.character_name ?? 'Unknown'} •{' '}
                        Materials: {assignedCount}/{totalMaterials} assigned
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {/* Status dropdown */}
                    <select
                      value={project.status}
                      onChange={(e) => updateStatusMutation.mutate(e.target.value as PIProjectStatus)}
                      className="px-3 py-2 rounded-lg bg-secondary/50 border border-border text-sm"
                    >
                      <option value="planning">Planning</option>
                      <option value="active">Active</option>
                      <option value="paused">Paused</option>
                      <option value="completed">Completed</option>
                    </select>

                    <button
                      onClick={() => autoAssignMutation.mutate()}
                      disabled={autoAssignMutation.isPending}
                      className="flex items-center gap-2 px-3 py-2 rounded-lg bg-secondary hover:bg-secondary/80 text-sm"
                    >
                      {autoAssignMutation.isPending ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Wand2 className="h-4 w-4" />
                      )}
                      Auto-Assign
                    </button>

                    <button
                      onClick={handleSync}
                      disabled={isSyncing}
                      className="flex items-center gap-2 px-3 py-2 rounded-lg bg-secondary hover:bg-secondary/80 text-sm"
                    >
                      {isSyncing ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <RefreshCw className="h-4 w-4" />
                      )}
                      Sync
                    </button>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Assignments Table */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Factory className="h-5 w-5" />
                  Material Assignments
                </CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                {!assignments || assignments.length === 0 ? (
                  <div className="py-12 text-center">
                    <p className="text-muted-foreground">
                      No materials in this project. Click "Auto-Assign" to generate the production chain.
                    </p>
                  </div>
                ) : (
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-border">
                        <th className="text-left p-4 text-sm font-medium text-muted-foreground">Material</th>
                        <th className="text-left p-4 text-sm font-medium text-muted-foreground">Tier</th>
                        <th className="text-left p-4 text-sm font-medium text-muted-foreground">Decision</th>
                        <th className="text-left p-4 text-sm font-medium text-muted-foreground">Colony</th>
                        <th className="text-left p-4 text-sm font-medium text-muted-foreground">Output</th>
                      </tr>
                    </thead>
                    <tbody>
                      {assignments.map((assignment) => {
                        const tierConfig = TIER_CONFIG[assignment.tier] || TIER_CONFIG[0]
                        const makeOrBuy = makeOrBuyData[assignment.material_type_id]
                        const isBuy = makeOrBuy?.recommendation === 'BUY'

                        return (
                          <tr
                            key={assignment.id}
                            className="border-b border-border hover:bg-secondary/30"
                          >
                            <td className="p-4">
                              <div className="flex items-center gap-2">
                                <img
                                  src={getItemIconUrl(assignment.material_type_id)}
                                  alt=""
                                  className="w-6 h-6 rounded"
                                  onError={(e: React.SyntheticEvent<HTMLImageElement>) => {
                                    e.currentTarget.style.display = 'none'
                                  }}
                                />
                                <span>{assignment.material_name ?? `Type ${assignment.material_type_id}`}</span>
                              </div>
                            </td>
                            <td className="p-4">
                              <Badge className={cn('text-xs', tierConfig.bg, tierConfig.color)}>
                                {tierConfig.label}
                              </Badge>
                            </td>
                            <td className="p-4">
                              {makeOrBuy ? (
                                <div className="flex items-center gap-2">
                                  <Badge
                                    className={cn(
                                      'text-xs',
                                      isBuy
                                        ? 'bg-orange-500/20 text-orange-400'
                                        : 'bg-green-500/20 text-green-400'
                                    )}
                                  >
                                    {isBuy ? <ShoppingCart className="h-3 w-3 mr-1" /> : <Factory className="h-3 w-3 mr-1" />}
                                    {makeOrBuy.recommendation}
                                  </Badge>
                                  {isBuy && makeOrBuy.savings_percent > 0 && (
                                    <span className="text-xs text-orange-400">
                                      -{makeOrBuy.savings_percent.toFixed(0)}%
                                    </span>
                                  )}
                                </div>
                              ) : (
                                <span className="text-muted-foreground">-</span>
                              )}
                            </td>
                            <td className="p-4">
                              {isBuy ? (
                                <span className="text-muted-foreground text-sm">Not needed (BUY)</span>
                              ) : (
                                <ColonySelect
                                  assignment={assignment}
                                  colonies={colonies ?? []}
                                  onSelect={(colonyId) =>
                                    updateAssignmentMutation.mutate({
                                      materialTypeId: assignment.material_type_id,
                                      colonyId,
                                    })
                                  }
                                  disabled={updateAssignmentMutation.isPending}
                                />
                              )}
                            </td>
                            <td className="p-4">
                              {assignment.output_percentage !== null ? (
                                <span
                                  className={cn(
                                    'font-mono text-sm',
                                    assignment.output_percentage >= 100
                                      ? 'text-green-400'
                                      : assignment.output_percentage >= 50
                                      ? 'text-yellow-400'
                                      : 'text-red-400'
                                  )}
                                >
                                  {assignment.output_percentage}%
                                </span>
                              ) : (
                                <span className="text-muted-foreground">-</span>
                              )}
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                )}
              </CardContent>
            </Card>
          </>
        )}
      </div>
    </div>
  )
}
