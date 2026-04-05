import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Header } from '@/components/layout/Header'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { cn, formatISK } from '@/lib/utils'
import { getReactions, getProfitableReactions } from '@/api/reactions'
import type { ReactionFormula, ProfitableReaction, ReactionType } from '@/types/reactions'
import {
  Search,
  FlaskConical,
  TrendingUp,
  ArrowUpDown,
  ChevronUp,
  ChevronDown,
  ToggleLeft,
  ToggleRight,
  Filter,
} from 'lucide-react'
import { ProfitabilityChart } from '@/components/reactions/ProfitabilityChart'

/**
 * Get item icon URL
 */
function getItemIconUrl(typeId: number, size: 32 | 64 = 32): string {
  return `https://images.evetech.net/types/${typeId}/icon?size=${size}`
}

/**
 * Get category badge style
 */
function getCategoryStyle(category: string | undefined) {
  switch (category?.toLowerCase()) {
    case 'simple':
      return 'bg-blue-500/20 text-blue-400 border-blue-500/30'
    case 'complex':
      return 'bg-purple-500/20 text-purple-400 border-purple-500/30'
    case 'composite':
      return 'bg-orange-500/20 text-orange-400 border-orange-500/30'
    case 'biochemical':
      return 'bg-green-500/20 text-green-400 border-green-500/30'
    default:
      return 'bg-gray-500/20 text-gray-400 border-gray-500/30'
  }
}

/**
 * Format ROI percentage
 */
function formatROI(roi: number): string {
  if (roi >= 1000) {
    return `${(roi / 1000).toFixed(1)}K%`
  }
  return `${roi.toFixed(1)}%`
}

/**
 * Format time duration in seconds to readable format
 */
function formatTime(seconds: number): string {
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  if (hours > 0) {
    return `${hours}h ${minutes}m`
  }
  return `${minutes}m`
}

type SortField = 'name' | 'category' | 'output' | 'profit_per_run' | 'profit_per_hour' | 'roi_percent'
type SortDirection = 'asc' | 'desc'

/**
 * Sortable table header
 */
function SortableHeader({
  label,
  field,
  currentField,
  direction,
  onSort,
  align = 'left',
}: {
  label: string
  field: SortField
  currentField: SortField
  direction: SortDirection
  onSort: (field: SortField) => void
  align?: 'left' | 'right'
}) {
  const isActive = currentField === field
  return (
    <th
      onClick={() => onSort(field)}
      className={cn(
        'py-3 px-4 font-medium text-muted-foreground cursor-pointer hover:text-foreground transition-colors',
        align === 'right' && 'text-right'
      )}
    >
      <div className={cn('flex items-center gap-1', align === 'right' && 'justify-end')}>
        {label}
        {isActive ? (
          direction === 'desc' ? (
            <ChevronDown className="h-4 w-4" />
          ) : (
            <ChevronUp className="h-4 w-4" />
          )
        ) : (
          <ArrowUpDown className="h-4 w-4 opacity-30" />
        )}
      </div>
    </th>
  )
}

/**
 * Reaction row for "All Reactions" view
 */
function ReactionRow({ reaction }: { reaction: ReactionFormula }) {
  return (
    <tr className="border-b border-border hover:bg-secondary/30 transition-colors">
      <td className="py-3 px-4">
        <Link
          to={`/reactions/${reaction.reaction_type_id}`}
          className="flex items-center gap-3 hover:underline"
        >
          <img
            src={getItemIconUrl(reaction.product_type_id)}
            alt={reaction.reaction_name}
            className="w-8 h-8 rounded-lg border border-border"
            loading="lazy"
            onError={(e) => {
              e.currentTarget.style.display = 'none'
            }}
          />
          <div>
            <div className="font-medium">{reaction.reaction_name}</div>
            <div className="text-xs text-muted-foreground">{reaction.product_name}</div>
          </div>
        </Link>
      </td>
      <td className="py-3 px-4">
        <Badge variant="outline" className={cn('text-xs', getCategoryStyle(reaction.reaction_category))}>
          {reaction.reaction_category || 'Unknown'}
        </Badge>
      </td>
      <td className="py-3 px-4 text-right font-mono">
        {reaction.product_quantity.toLocaleString()}
      </td>
      <td className="py-3 px-4 text-right text-muted-foreground">
        {formatTime(reaction.reaction_time)}
      </td>
      <td className="py-3 px-4 text-right text-muted-foreground">
        {reaction.inputs.length}
      </td>
    </tr>
  )
}

/**
 * Profitable reaction row
 */
function ProfitableReactionRow({ reaction }: { reaction: ProfitableReaction }) {
  const isProfitable = reaction.profit_per_run > 0

  return (
    <tr className="border-b border-border hover:bg-secondary/30 transition-colors">
      <td className="py-3 px-4">
        <Link
          to={`/reactions/${reaction.reaction_type_id}`}
          className="flex items-center gap-3 hover:underline"
        >
          <img
            src={getItemIconUrl(reaction.reaction_type_id)}
            alt={reaction.reaction_name}
            className="w-8 h-8 rounded-lg border border-border"
            loading="lazy"
            onError={(e) => {
              e.currentTarget.style.display = 'none'
            }}
          />
          <div>
            <div className="font-medium">{reaction.reaction_name}</div>
            <div className="text-xs text-muted-foreground">{reaction.product_name}</div>
          </div>
        </Link>
      </td>
      <td className="py-3 px-4 text-right">
        <span className={cn('font-mono', isProfitable ? 'text-green-400' : 'text-red-400')}>
          {formatISK(reaction.profit_per_run)}
        </span>
      </td>
      <td className="py-3 px-4 text-right">
        <span className={cn('font-mono', isProfitable ? 'text-green-400' : 'text-red-400')}>
          {formatISK(reaction.profit_per_hour)}
        </span>
      </td>
      <td className="py-3 px-4 text-right">
        <span className={cn('font-mono font-bold', isProfitable ? 'text-green-400' : 'text-red-400')}>
          {formatROI(reaction.roi_percent)}
        </span>
      </td>
      <td className="py-3 px-4 text-right text-muted-foreground">
        {reaction.runs_per_hour.toFixed(1)}/h
      </td>
    </tr>
  )
}

/**
 * Loading skeleton
 */
function TableSkeleton() {
  return (
    <div className="space-y-2">
      {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
        <div key={i} className="flex items-center gap-4 p-3">
          <Skeleton className="h-8 w-8 rounded-lg" />
          <Skeleton className="h-5 flex-1" />
          <Skeleton className="h-5 w-20" />
          <Skeleton className="h-5 w-20" />
          <Skeleton className="h-5 w-20" />
        </div>
      ))}
    </div>
  )
}

/**
 * Category filter buttons
 */
const CATEGORIES: { value: ReactionType; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'simple', label: 'Simple' },
  { value: 'complex', label: 'Complex' },
  { value: 'composite', label: 'Composite' },
  { value: 'biochemical', label: 'Biochemical' },
]

/**
 * Main Reactions Browser page
 */
export function ReactionsBrowser() {
  // State
  const [searchQuery, setSearchQuery] = useState('')
  const [categoryFilter, setCategoryFilter] = useState<ReactionType>('all')
  const [showProfitable, setShowProfitable] = useState(false)
  const [sortField, setSortField] = useState<SortField>('name')
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc')

  // Fetch all reactions
  const {
    data: allReactions,
    isLoading: isLoadingAll,
    error: errorAll,
  } = useQuery({
    queryKey: ['reactions', categoryFilter],
    queryFn: () => getReactions(categoryFilter),
    enabled: !showProfitable,
    staleTime: 5 * 60 * 1000,
  })

  // Fetch profitable reactions
  const {
    data: profitableReactions,
    isLoading: isLoadingProfitable,
    error: errorProfitable,
  } = useQuery({
    queryKey: ['reactions-profitable', categoryFilter],
    queryFn: () => getProfitableReactions(200, categoryFilter),
    enabled: showProfitable,
    staleTime: 5 * 60 * 1000,
  })

  const isLoading = showProfitable ? isLoadingProfitable : isLoadingAll
  const error = showProfitable ? errorProfitable : errorAll

  // Filter and sort reactions
  const filteredReactions = useMemo(() => {
    if (showProfitable) {
      if (!profitableReactions) return []
      let filtered = profitableReactions

      // Apply search filter
      if (searchQuery) {
        const query = searchQuery.toLowerCase()
        filtered = filtered.filter(
          (r) =>
            r.reaction_name.toLowerCase().includes(query) ||
            r.product_name.toLowerCase().includes(query)
        )
      }

      // Sort
      return [...filtered].sort((a, b) => {
        let comparison = 0
        switch (sortField) {
          case 'name':
            comparison = a.reaction_name.localeCompare(b.reaction_name)
            break
          case 'profit_per_run':
            comparison = a.profit_per_run - b.profit_per_run
            break
          case 'profit_per_hour':
            comparison = a.profit_per_hour - b.profit_per_hour
            break
          case 'roi_percent':
            comparison = a.roi_percent - b.roi_percent
            break
          default:
            comparison = a.reaction_name.localeCompare(b.reaction_name)
        }
        return sortDirection === 'desc' ? -comparison : comparison
      })
    } else {
      if (!allReactions) return []
      let filtered = allReactions

      // Apply search filter
      if (searchQuery) {
        const query = searchQuery.toLowerCase()
        filtered = filtered.filter(
          (r) =>
            r.reaction_name.toLowerCase().includes(query) ||
            r.product_name.toLowerCase().includes(query)
        )
      }

      // Sort
      return [...filtered].sort((a, b) => {
        let comparison = 0
        switch (sortField) {
          case 'name':
            comparison = a.reaction_name.localeCompare(b.reaction_name)
            break
          case 'category':
            comparison = (a.reaction_category || '').localeCompare(b.reaction_category || '')
            break
          case 'output':
            comparison = a.product_quantity - b.product_quantity
            break
          default:
            comparison = a.reaction_name.localeCompare(b.reaction_name)
        }
        return sortDirection === 'desc' ? -comparison : comparison
      })
    }
  }, [allReactions, profitableReactions, showProfitable, searchQuery, sortField, sortDirection])

  // Handle sort
  const handleSort = (field: SortField) => {
    if (field === sortField) {
      setSortDirection(sortDirection === 'desc' ? 'asc' : 'desc')
    } else {
      setSortField(field)
      setSortDirection('desc')
    }
  }

  // Reset sort when switching views
  const handleViewToggle = () => {
    setShowProfitable(!showProfitable)
    setSortField(showProfitable ? 'name' : 'roi_percent')
    setSortDirection('desc')
  }

  return (
    <div>
      <Header title="Reactions Browser" subtitle="Browse all 112 reactions with profitability analysis" />

      <div className="p-6 space-y-6">
        {/* Controls Row */}
        <div className="flex flex-col sm:flex-row gap-4">
          {/* Search */}
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search reactions..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className={cn(
                'w-full pl-10 pr-4 py-2.5 rounded-lg',
                'bg-[#161b22] border border-[#30363d]',
                'text-[#e6edf3] placeholder:text-[#8b949e]',
                'focus:outline-none focus:ring-2 focus:ring-[#58a6ff] focus:border-transparent',
                'transition-colors'
              )}
            />
          </div>

          {/* View Toggle */}
          <button
            onClick={handleViewToggle}
            className={cn(
              'flex items-center gap-2 px-4 py-2.5 rounded-lg border transition-colors',
              showProfitable
                ? 'bg-green-500/20 border-green-500/30 text-green-400'
                : 'bg-[#21262d] border-[#30363d] text-[#e6edf3] hover:bg-[#30363d]'
            )}
          >
            {showProfitable ? (
              <ToggleRight className="h-5 w-5" />
            ) : (
              <ToggleLeft className="h-5 w-5" />
            )}
            {showProfitable ? 'Profitable View' : 'All Reactions'}
          </button>
        </div>

        {/* Category Filter */}
        <div className="flex items-center gap-2 flex-wrap">
          <Filter className="h-4 w-4 text-muted-foreground" />
          <span className="text-sm text-muted-foreground mr-2">Category:</span>
          {CATEGORIES.map((cat) => (
            <button
              key={cat.value}
              onClick={() => setCategoryFilter(cat.value)}
              className={cn(
                'px-3 py-1.5 text-sm rounded-lg border transition-colors',
                categoryFilter === cat.value
                  ? 'bg-[#58a6ff]/20 border-[#58a6ff]/50 text-[#58a6ff]'
                  : 'bg-[#21262d] border-[#30363d] text-[#8b949e] hover:text-[#e6edf3] hover:bg-[#30363d]'
              )}
            >
              {cat.label}
            </button>
          ))}
        </div>

        {/* Summary Stats */}
        {showProfitable && profitableReactions && (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <Card>
              <CardContent className="pt-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-green-500/20">
                    <TrendingUp className="h-5 w-5 text-green-400" />
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground">Profitable Reactions</div>
                    <div className="text-xl font-bold">
                      {profitableReactions.filter((r) => r.profit_per_run > 0).length}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-blue-500/20">
                    <FlaskConical className="h-5 w-5 text-blue-400" />
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground">Best ROI</div>
                    <div className="text-xl font-bold text-green-400">
                      {profitableReactions[0] ? formatROI(profitableReactions[0].roi_percent) : 'N/A'}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-purple-500/20">
                    <FlaskConical className="h-5 w-5 text-purple-400" />
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground">Best ISK/Hour</div>
                    <div className="text-xl font-bold text-green-400">
                      {profitableReactions[0] ? formatISK(
                        Math.max(...profitableReactions.map((r) => r.profit_per_hour))
                      ) : 'N/A'}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Profitability Chart - Only in Profitable View */}
        {showProfitable && profitableReactions && profitableReactions.length > 0 && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <ProfitabilityChart reactions={profitableReactions} metric="profit_per_hour" />
            <ProfitabilityChart reactions={profitableReactions} metric="roi_percent" />
          </div>
        )}

        {/* Reactions Table */}
        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-lg flex items-center gap-2">
                <FlaskConical className="h-5 w-5" />
                {showProfitable ? 'Profitable Reactions' : 'All Reactions'}
              </CardTitle>
              <span className="text-sm text-muted-foreground">
                {filteredReactions.length} reactions
              </span>
            </div>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <TableSkeleton />
            ) : error ? (
              <div className="py-12 text-center">
                <div className="text-red-400 mb-2">Failed to load reactions</div>
                <div className="text-sm text-muted-foreground">
                  {error instanceof Error ? error.message : 'Unknown error'}
                </div>
              </div>
            ) : filteredReactions.length === 0 ? (
              <div className="py-12 text-center">
                <FlaskConical className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                <h3 className="text-lg font-medium mb-2">No Reactions Found</h3>
                <p className="text-muted-foreground">
                  {searchQuery
                    ? `No reactions match "${searchQuery}"`
                    : 'No reactions available for this category'}
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-border">
                      {showProfitable ? (
                        <>
                          <SortableHeader
                            label="Reaction"
                            field="name"
                            currentField={sortField}
                            direction={sortDirection}
                            onSort={handleSort}
                          />
                          <SortableHeader
                            label="Profit/Run"
                            field="profit_per_run"
                            currentField={sortField}
                            direction={sortDirection}
                            onSort={handleSort}
                            align="right"
                          />
                          <SortableHeader
                            label="Profit/Hour"
                            field="profit_per_hour"
                            currentField={sortField}
                            direction={sortDirection}
                            onSort={handleSort}
                            align="right"
                          />
                          <SortableHeader
                            label="ROI"
                            field="roi_percent"
                            currentField={sortField}
                            direction={sortDirection}
                            onSort={handleSort}
                            align="right"
                          />
                          <th className="py-3 px-4 text-right font-medium text-muted-foreground">
                            Runs
                          </th>
                        </>
                      ) : (
                        <>
                          <SortableHeader
                            label="Reaction"
                            field="name"
                            currentField={sortField}
                            direction={sortDirection}
                            onSort={handleSort}
                          />
                          <SortableHeader
                            label="Category"
                            field="category"
                            currentField={sortField}
                            direction={sortDirection}
                            onSort={handleSort}
                          />
                          <SortableHeader
                            label="Output"
                            field="output"
                            currentField={sortField}
                            direction={sortDirection}
                            onSort={handleSort}
                            align="right"
                          />
                          <th className="py-3 px-4 text-right font-medium text-muted-foreground">
                            Time
                          </th>
                          <th className="py-3 px-4 text-right font-medium text-muted-foreground">
                            Inputs
                          </th>
                        </>
                      )}
                    </tr>
                  </thead>
                  <tbody>
                    {showProfitable
                      ? (filteredReactions as ProfitableReaction[]).map((reaction) => (
                          <ProfitableReactionRow key={reaction.reaction_type_id} reaction={reaction} />
                        ))
                      : (filteredReactions as ReactionFormula[]).map((reaction) => (
                          <ReactionRow key={reaction.reaction_type_id} reaction={reaction} />
                        ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

export default ReactionsBrowser
