import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { Header } from '@/components/layout/Header'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { piApi, type EmpirePlanDetail, type EmpirePlanAssignment } from '@/api/pi'
import { cn, formatISK } from '@/lib/utils'
import { ArrowLeft, Plus, Play, Pause, CheckCircle, Users, Globe2, Factory, Pickaxe, Loader2, Truck } from 'lucide-react'
import { LogisticsDashboard } from '@/components/pi/LogisticsDashboard'

/**
 * Empire plan status type
 */
type EmpirePlanStatus = 'planning' | 'active' | 'paused' | 'completed'

/**
 * Status badge configuration
 */
const STATUS_CONFIG: Record<EmpirePlanStatus, { label: string; color: string; bg: string }> = {
  planning: { label: 'Planning', color: 'text-blue-400', bg: 'bg-blue-500/20' },
  active: { label: 'Active', color: 'text-green-400', bg: 'bg-green-500/20' },
  paused: { label: 'Paused', color: 'text-yellow-400', bg: 'bg-yellow-500/20' },
  completed: { label: 'Completed', color: 'text-gray-400', bg: 'bg-gray-500/20' },
}

/**
 * Character role configuration
 */
const ROLE_CONFIG: Record<string, { label: string; icon: typeof Factory; color: string }> = {
  extractor: { label: 'Extractor', icon: Pickaxe, color: 'text-amber-400' },
  factory: { label: 'Factory', icon: Factory, color: 'text-blue-400' },
  hybrid: { label: 'Hybrid', icon: Globe2, color: 'text-purple-400' },
}

/**
 * Get item icon URL
 */
function getItemIconUrl(typeId: number, size: 32 | 64 = 32): string {
  return `https://images.evetech.net/types/${typeId}/icon?size=${size}`
}

/**
 * Format date to readable string
 */
function formatDate(dateStr: string): string {
  const date = new Date(dateStr)
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

/**
 * Loading skeleton component
 */
function DetailSkeleton() {
  return (
    <div className="space-y-6">
      {/* Header skeleton */}
      <div className="flex items-center gap-4">
        <Skeleton className="h-16 w-16 rounded-lg" />
        <div className="flex-1">
          <Skeleton className="h-6 w-48 mb-2" />
          <Skeleton className="h-4 w-32" />
        </div>
        <Skeleton className="h-8 w-24" />
      </div>

      {/* Configuration skeleton */}
      <Card>
        <CardHeader>
          <Skeleton className="h-5 w-32" />
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i}>
                <Skeleton className="h-4 w-20 mb-2" />
                <Skeleton className="h-6 w-16" />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Assignments skeleton */}
      <Card>
        <CardHeader>
          <Skeleton className="h-5 w-40" />
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="flex items-center gap-4">
                <Skeleton className="h-10 w-10 rounded-full" />
                <Skeleton className="h-5 flex-1" />
                <Skeleton className="h-6 w-20" />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

/**
 * Error state component
 */
function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="py-12 text-center">
      <div className="text-red-400 mb-4">
        <Globe2 className="h-12 w-12 mx-auto" />
      </div>
      <h3 className="text-lg font-medium mb-2">Error Loading Plan</h3>
      <p className="text-muted-foreground mb-4">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="px-4 py-2 rounded-lg bg-secondary hover:bg-secondary/80 text-sm"
        >
          Try Again
        </button>
      )}
    </div>
  )
}

/**
 * Plan header with status badge and actions
 */
function PlanHeader({
  plan,
  onStatusChange,
  isUpdating,
}: {
  plan: EmpirePlanDetail
  onStatusChange: (status: EmpirePlanStatus) => void
  isUpdating: boolean
}) {
  const statusConfig = STATUS_CONFIG[plan.status] || STATUS_CONFIG.planning

  return (
    <div className="flex items-start gap-4 flex-wrap">
      {/* Product icon and name */}
      <img
        src={getItemIconUrl(plan.target_product.id, 64)}
        alt={plan.target_product.name}
        className="w-16 h-16 rounded-lg border border-border"
        onError={(e: React.SyntheticEvent<HTMLImageElement>) => {
          e.currentTarget.style.display = 'none'
        }}
      />
      <div className="flex-1 min-w-[200px]">
        <h2 className="text-xl font-semibold">{plan.name}</h2>
        <div className="flex items-center gap-3 mt-1">
          <span className="text-muted-foreground">{plan.target_product.name}</span>
          <Badge className={cn('text-xs', statusConfig.bg, statusConfig.color)}>
            {statusConfig.label}
          </Badge>
        </div>
        <div className="text-sm text-muted-foreground mt-1">
          Created {formatDate(plan.created_at)}
        </div>
      </div>

      {/* Status action buttons */}
      <div className="flex items-center gap-2">
        {plan.status === 'planning' && (
          <button
            onClick={() => onStatusChange('active')}
            disabled={isUpdating}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-green-500/20 text-green-400 hover:bg-green-500/30 disabled:opacity-50 text-sm"
          >
            {isUpdating ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Play className="h-4 w-4" />
            )}
            Activate
          </button>
        )}
        {plan.status === 'active' && (
          <button
            onClick={() => onStatusChange('paused')}
            disabled={isUpdating}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-yellow-500/20 text-yellow-400 hover:bg-yellow-500/30 disabled:opacity-50 text-sm"
          >
            {isUpdating ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Pause className="h-4 w-4" />
            )}
            Pause
          </button>
        )}
        {plan.status === 'paused' && (
          <>
            <button
              onClick={() => onStatusChange('active')}
              disabled={isUpdating}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-green-500/20 text-green-400 hover:bg-green-500/30 disabled:opacity-50 text-sm"
            >
              {isUpdating ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Play className="h-4 w-4" />
              )}
              Resume
            </button>
            <button
              onClick={() => onStatusChange('completed')}
              disabled={isUpdating}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-secondary text-muted-foreground hover:bg-secondary/80 disabled:opacity-50 text-sm"
            >
              {isUpdating ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <CheckCircle className="h-4 w-4" />
              )}
              Complete
            </button>
          </>
        )}
      </div>
    </div>
  )
}

/**
 * Configuration display card
 */
function ConfigurationCard({ plan }: { plan: EmpirePlanDetail }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-lg">Configuration</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div>
            <div className="text-sm text-muted-foreground">Total Planets</div>
            <div className="text-lg font-medium">{plan.configuration.total_planets}</div>
          </div>
          <div>
            <div className="text-sm text-muted-foreground">Extraction</div>
            <div className="text-lg font-medium">{plan.configuration.extraction_planets}</div>
          </div>
          <div>
            <div className="text-sm text-muted-foreground">Factory</div>
            <div className="text-lg font-medium">{plan.configuration.factory_planets}</div>
          </div>
          <div>
            <div className="text-sm text-muted-foreground">POCO Tax</div>
            <div className="text-lg font-medium">{plan.configuration.poco_tax_rate}%</div>
          </div>
          <div>
            <div className="text-sm text-muted-foreground">Est. Monthly Profit</div>
            <div className="text-lg font-medium text-green-400">
              {plan.estimated_monthly_profit
                ? formatISK(plan.estimated_monthly_profit)
                : 'N/A'}
            </div>
          </div>
        </div>
        {plan.home_system && (
          <div className="mt-4 pt-4 border-t border-border">
            <div className="text-sm text-muted-foreground">Home System</div>
            <div className="font-medium">{plan.home_system.name}</div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

/**
 * Character assignment row
 */
function AssignmentRow({ assignment }: { assignment: EmpirePlanAssignment }) {
  const roleConfig = ROLE_CONFIG[assignment.role] || ROLE_CONFIG.hybrid
  const RoleIcon = roleConfig.icon

  return (
    <div className="flex items-center gap-4 p-4 rounded-lg bg-secondary/30 border border-border">
      <div className="w-10 h-10 rounded-full bg-secondary flex items-center justify-center">
        <Users className="h-5 w-5 text-muted-foreground" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="font-medium truncate">{assignment.character_name}</div>
        <div className="text-sm text-muted-foreground">
          {assignment.planets.length} planet{assignment.planets.length !== 1 ? 's' : ''} assigned
        </div>
      </div>
      <Badge
        className={cn(
          'flex items-center gap-1.5',
          assignment.role === 'extractor' && 'bg-amber-500/20 text-amber-400',
          assignment.role === 'factory' && 'bg-blue-500/20 text-blue-400',
          assignment.role === 'hybrid' && 'bg-purple-500/20 text-purple-400'
        )}
      >
        <RoleIcon className="h-3 w-3" />
        {roleConfig.label}
      </Badge>
    </div>
  )
}

/**
 * Character assignments card
 */
function AssignmentsCard({
  assignments,
  planId,
}: {
  assignments: EmpirePlanAssignment[]
  planId: number
}) {
  const navigate = useNavigate()

  const handleAddCharacter = () => {
    // Navigate to add character (could be a modal or separate page)
    navigate(`/pi/empire/plans/${planId}/add-character`)
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">Character Assignments</CardTitle>
          <button
            onClick={handleAddCharacter}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-primary/20 text-primary hover:bg-primary/30 text-sm"
          >
            <Plus className="h-4 w-4" />
            Add Character
          </button>
        </div>
      </CardHeader>
      <CardContent>
        {assignments.length === 0 ? (
          <div className="py-8 text-center">
            <Users className="h-10 w-10 text-muted-foreground mx-auto mb-3" />
            <h4 className="font-medium mb-1">No Characters Assigned</h4>
            <p className="text-sm text-muted-foreground mb-4">
              Add characters to start coordinating your PI empire.
            </p>
            <button
              onClick={handleAddCharacter}
              className="px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 text-sm"
            >
              Add First Character
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            {assignments.map((assignment) => (
              <AssignmentRow key={assignment.id} assignment={assignment} />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

/**
 * Main PI Empire Plan Detail Page
 */
function PIEmpirePlanDetail() {
  const { planId } = useParams<{ planId: string }>()
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  const planIdNum = planId ? parseInt(planId, 10) : 0

  // Fetch plan details
  const {
    data: plan,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ['pi', 'empire', 'plans', planIdNum],
    queryFn: () => piApi.getEmpirePlan(planIdNum),
    enabled: planIdNum > 0,
    staleTime: 30 * 1000,
  })

  // Status update mutation
  const statusMutation = useMutation({
    mutationFn: (status: EmpirePlanStatus) =>
      piApi.updatePlanStatus(planIdNum, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pi', 'empire', 'plans', planIdNum] })
      queryClient.invalidateQueries({ queryKey: ['pi', 'empire', 'plans'] })
    },
  })

  const handleStatusChange = (status: EmpirePlanStatus) => {
    statusMutation.mutate(status)
  }

  // Handle invalid planId
  if (!planIdNum) {
    return (
      <div className="p-6">
        <ErrorState message="Invalid plan ID" />
      </div>
    )
  }

  return (
    <div>
      <Header
        title="Empire Plan Details"
        subtitle="View and manage your PI empire plan"
      />

      <div className="p-6 space-y-6">
        {/* Navigation row */}
        <div className="flex items-center justify-between">
          <Link
            to="/pi/empire/plans"
            className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Plans
          </Link>
          <button
            onClick={() => navigate('/pi/planets/finder')}
            className="flex items-center gap-2 px-4 py-2 bg-[#21262d] hover:bg-[#30363d] text-[#e6edf3] rounded-lg transition-colors text-sm"
          >
            <Globe2 className="h-4 w-4" />
            Find Planets
          </button>
        </div>

        {/* Content */}
        {isLoading ? (
          <DetailSkeleton />
        ) : isError ? (
          <ErrorState
            message={error?.message || 'Failed to load plan details'}
            onRetry={() => refetch()}
          />
        ) : plan ? (
          <div className="space-y-6">
            {/* Plan header with status and actions */}
            <PlanHeader
              plan={plan}
              onStatusChange={handleStatusChange}
              isUpdating={statusMutation.isPending}
            />

            {/* Configuration */}
            <ConfigurationCard plan={plan} />

            {/* Character assignments */}
            <AssignmentsCard
              assignments={plan.assignments}
              planId={planIdNum}
            />

            {/* Logistics Planning - only show for active/paused plans */}
            {plan.status !== 'planning' && (
              <div className="space-y-4">
                <div className="flex items-center gap-2">
                  <Truck className="h-5 w-5 text-[#8b949e]" />
                  <h2 className="text-xl font-semibold text-[#e6edf3]">Logistics Planning</h2>
                </div>
                <LogisticsDashboard planId={planIdNum} frequencyHours={48} />
              </div>
            )}

            {/* Status update error */}
            {statusMutation.isError && (
              <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
                Failed to update plan status. Please try again.
              </div>
            )}
          </div>
        ) : (
          <ErrorState message="Plan not found" />
        )}
      </div>
    </div>
  )
}

export default PIEmpirePlanDetail
export { PIEmpirePlanDetail }
