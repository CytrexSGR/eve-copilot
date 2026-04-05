import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Header } from '@/components/layout/Header'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { piApi, type EmpirePlanListItem } from '@/api/pi'
import { cn } from '@/lib/utils'
import {
  ArrowLeft,
  Plus,
  Trash2,
  Globe2,
  Users,
  Calendar,
} from 'lucide-react'
import { Link } from 'react-router-dom'

/**
 * Empire plan status type
 */
type EmpirePlanStatus = 'planning' | 'active' | 'paused' | 'completed'

/**
 * Status badge colors
 */
const STATUS_CONFIG: Record<EmpirePlanStatus, { label: string; color: string; bg: string }> = {
  planning: { label: 'Planning', color: 'text-blue-400', bg: 'bg-blue-500/20' },
  active: { label: 'Active', color: 'text-green-400', bg: 'bg-green-500/20' },
  paused: { label: 'Paused', color: 'text-yellow-400', bg: 'bg-yellow-500/20' },
  completed: { label: 'Completed', color: 'text-gray-400', bg: 'bg-gray-500/20' },
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
 * Status filter buttons component
 */
function StatusFilterButtons({
  currentFilter,
  onFilterChange,
}: {
  currentFilter: EmpirePlanStatus | ''
  onFilterChange: (filter: EmpirePlanStatus | '') => void
}) {
  const filters: Array<{ value: EmpirePlanStatus | ''; label: string }> = [
    { value: '', label: 'All' },
    { value: 'planning', label: 'Planning' },
    { value: 'active', label: 'Active' },
    { value: 'paused', label: 'Paused' },
    { value: 'completed', label: 'Completed' },
  ]

  return (
    <div className="flex items-center gap-2">
      {filters.map((filter) => {
        const isActive = currentFilter === filter.value
        const statusConfig = filter.value ? STATUS_CONFIG[filter.value] : null

        return (
          <button
            key={filter.value}
            onClick={() => onFilterChange(filter.value)}
            className={cn(
              'px-3 py-1.5 rounded-lg text-sm font-medium transition-colors',
              isActive
                ? statusConfig
                  ? cn(statusConfig.bg, statusConfig.color)
                  : 'bg-primary text-primary-foreground'
                : 'bg-secondary/50 text-muted-foreground hover:bg-secondary hover:text-foreground'
            )}
          >
            {filter.label}
          </button>
        )
      })}
    </div>
  )
}

/**
 * Loading skeleton for table
 */
function TableSkeleton() {
  return (
    <div className="p-6 space-y-4">
      {[1, 2, 3].map((i) => (
        <div key={i} className="flex items-center gap-4">
          <Skeleton className="h-10 w-10 rounded-lg" />
          <Skeleton className="h-5 flex-1" />
          <Skeleton className="h-5 w-20" />
          <Skeleton className="h-5 w-20" />
          <Skeleton className="h-5 w-16" />
        </div>
      ))}
    </div>
  )
}

/**
 * Empty state component
 */
function EmptyState({ onCreateClick }: { onCreateClick: () => void }) {
  return (
    <div className="py-12 text-center">
      <Globe2 className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
      <h3 className="text-lg font-medium mb-2">No Empire Plans</h3>
      <p className="text-muted-foreground mb-4">
        Create your first empire plan to coordinate multi-character PI production.
      </p>
      <button
        onClick={onCreateClick}
        className="px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 text-sm"
      >
        Create Empire Plan
      </button>
    </div>
  )
}

/**
 * Plan row component
 */
function PlanRow({
  plan,
  onView,
  onDelete,
  isDeleting,
}: {
  plan: EmpirePlanListItem
  onView: () => void
  onDelete: () => void
  isDeleting: boolean
}) {
  const statusConfig = STATUS_CONFIG[plan.status] || STATUS_CONFIG.planning

  return (
    <tr className="border-b border-border hover:bg-secondary/30 transition-colors">
      <td className="p-4">
        <button
          onClick={onView}
          className="flex items-center gap-3 text-left hover:text-primary transition-colors"
        >
          <img
            src={getItemIconUrl(plan.target_product_id, 64)}
            alt={plan.target_product_name || 'Product'}
            className="w-10 h-10 rounded-lg border border-border"
            onError={(e: React.SyntheticEvent<HTMLImageElement>) => {
              e.currentTarget.style.display = 'none'
            }}
          />
          <div>
            <div className="font-medium">{plan.name}</div>
            <div className="text-xs text-muted-foreground">
              {plan.target_product_name || 'No target product'}
            </div>
          </div>
        </button>
      </td>
      <td className="p-4">
        <Badge className={cn('text-xs', statusConfig.bg, statusConfig.color)}>
          {statusConfig.label}
        </Badge>
      </td>
      <td className="p-4">
        <div className="flex items-center gap-2 text-muted-foreground">
          <Users className="h-4 w-4" />
          <span className="text-sm">{plan.assignment_count} characters</span>
        </div>
      </td>
      <td className="p-4">
        <div className="flex items-center gap-2 text-muted-foreground">
          <Calendar className="h-4 w-4" />
          <span className="text-sm">{formatDate(plan.created_at)}</span>
        </div>
      </td>
      <td className="p-4 text-right">
        <div className="flex items-center justify-end gap-2">
          <button
            onClick={onView}
            className="px-3 py-1 rounded text-sm bg-secondary hover:bg-secondary/80"
          >
            View
          </button>
          <button
            onClick={onDelete}
            disabled={isDeleting}
            className="p-2 rounded text-red-400 hover:bg-red-500/20 disabled:opacity-50"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      </td>
    </tr>
  )
}

/**
 * Main PI Empire Plans Page
 */
function PIEmpirePlans() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [statusFilter, setStatusFilter] = useState<EmpirePlanStatus | ''>('')

  // Fetch empire plans
  const { data: plans, isLoading } = useQuery({
    queryKey: ['pi', 'empire', 'plans', statusFilter],
    queryFn: () => piApi.listEmpirePlans(statusFilter || undefined),
    staleTime: 30 * 1000,
  })

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (planId: number) => piApi.deleteEmpirePlan(planId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pi', 'empire', 'plans'] })
    },
  })

  const handleDelete = (plan: EmpirePlanListItem) => {
    if (confirm(`Delete empire plan "${plan.name}"? This action cannot be undone.`)) {
      deleteMutation.mutate(plan.plan_id)
    }
  }

  const handleView = (plan: EmpirePlanListItem) => {
    navigate(`/pi/empire/plans/${plan.plan_id}`)
  }

  const handleNewPlan = () => {
    navigate('/pi/empire/plans/new')
  }

  return (
    <div>
      <Header title="Empire Plans" subtitle="Multi-character PI production coordination" />

      <div className="p-6 space-y-6">
        {/* Back link */}
        <Link
          to="/pi/empire"
          className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Empire Dashboard
        </Link>

        {/* Actions row */}
        <div className="flex items-center justify-between flex-wrap gap-4">
          <button
            onClick={handleNewPlan}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 text-sm"
          >
            <Plus className="h-4 w-4" />
            New Plan
          </button>

          <StatusFilterButtons
            currentFilter={statusFilter}
            onFilterChange={setStatusFilter}
          />
        </div>

        {/* Plans Table */}
        <Card>
          <CardContent className="p-0">
            {isLoading ? (
              <TableSkeleton />
            ) : !plans || plans.length === 0 ? (
              <EmptyState onCreateClick={handleNewPlan} />
            ) : (
              <table className="w-full">
                <thead>
                  <tr className="border-b border-border">
                    <th className="text-left p-4 text-sm font-medium text-muted-foreground">
                      Plan
                    </th>
                    <th className="text-left p-4 text-sm font-medium text-muted-foreground">
                      Status
                    </th>
                    <th className="text-left p-4 text-sm font-medium text-muted-foreground">
                      Assignments
                    </th>
                    <th className="text-left p-4 text-sm font-medium text-muted-foreground">
                      Created
                    </th>
                    <th className="text-right p-4 text-sm font-medium text-muted-foreground">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {plans.map((plan) => (
                    <PlanRow
                      key={plan.plan_id}
                      plan={plan}
                      onView={() => handleView(plan)}
                      onDelete={() => handleDelete(plan)}
                      isDeleting={deleteMutation.isPending}
                    />
                  ))}
                </tbody>
              </table>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

export default PIEmpirePlans
export { PIEmpirePlans }
