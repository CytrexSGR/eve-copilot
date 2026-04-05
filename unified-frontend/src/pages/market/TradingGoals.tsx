// unified-frontend/src/pages/market/TradingGoals.tsx

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useCharacterContext } from '@/contexts/CharacterContext'
import { marketApi } from '@/api/market'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Target,
  Plus,
  Trash2,
  TrendingUp,
  Package,
  BarChart3,
  Percent,
  CheckCircle,
  Clock,
  AlertTriangle,
} from 'lucide-react'
import type { GoalProgress, GoalsResponse } from '@/types/market'

const formatISK = (value: number): string => {
  if (Math.abs(value) >= 1e9) return `${(value / 1e9).toFixed(2)}B`
  if (Math.abs(value) >= 1e6) return `${(value / 1e6).toFixed(2)}M`
  if (Math.abs(value) >= 1e3) return `${(value / 1e3).toFixed(1)}K`
  return value.toFixed(0)
}

const goalTypeLabels: Record<string, string> = {
  daily: 'Daily',
  weekly: 'Weekly',
  monthly: 'Monthly',
}

const targetTypeLabels: Record<string, string> = {
  profit: 'Profit',
  volume: 'Volume',
  trades: 'Trades',
  roi: 'ROI',
}

const targetTypeIcons: Record<string, React.ReactNode> = {
  profit: <TrendingUp className="h-4 w-4" />,
  volume: <Package className="h-4 w-4" />,
  trades: <BarChart3 className="h-4 w-4" />,
  roi: <Percent className="h-4 w-4" />,
}

interface GoalCardProps {
  progress: GoalProgress
  onDelete: (goalId: number) => void
  onDeactivate: (goalId: number) => void
}

function GoalCard({ progress, onDelete, onDeactivate }: GoalCardProps) {
  const { goal, progress_percent, remaining, days_remaining, on_track, projected_value } = progress
  const progressClamped = Math.min(100, Math.max(0, progress_percent))

  const formatValue = (value: number, type: string): string => {
    if (type === 'roi') return `${value.toFixed(1)}%`
    if (type === 'trades') return value.toFixed(0)
    return formatISK(value)
  }

  return (
    <Card className={goal.is_achieved ? 'border-green-500/50 bg-green-500/5' : ''}>
      <CardContent className="p-4">
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-2">
            {targetTypeIcons[goal.target_type]}
            <span className="font-medium">
              {goalTypeLabels[goal.goal_type]} {targetTypeLabels[goal.target_type]}
            </span>
            {goal.type_name && (
              <span className="text-xs text-muted-foreground">({goal.type_name})</span>
            )}
          </div>
          <div className="flex items-center gap-1">
            {goal.is_achieved ? (
              <CheckCircle className="h-5 w-5 text-green-500" />
            ) : on_track ? (
              <Clock className="h-5 w-5 text-blue-500" />
            ) : (
              <AlertTriangle className="h-5 w-5 text-yellow-500" />
            )}
          </div>
        </div>

        {/* Progress bar */}
        <div className="mb-3">
          <div className="flex justify-between text-sm mb-1">
            <span>{formatValue(goal.current_value, goal.target_type)}</span>
            <span className="text-muted-foreground">
              / {formatValue(goal.target_value, goal.target_type)}
            </span>
          </div>
          <div className="h-2 bg-muted rounded-full overflow-hidden">
            <div
              className={`h-full transition-all ${
                goal.is_achieved
                  ? 'bg-green-500'
                  : on_track
                  ? 'bg-blue-500'
                  : 'bg-yellow-500'
              }`}
              style={{ width: `${progressClamped}%` }}
            />
          </div>
          <div className="flex justify-between text-xs text-muted-foreground mt-1">
            <span>{progressClamped.toFixed(1)}% complete</span>
            {!goal.is_achieved && (
              <span>
                {days_remaining} day{days_remaining !== 1 ? 's' : ''} left
              </span>
            )}
          </div>
        </div>

        {/* Stats */}
        {!goal.is_achieved && (
          <div className="grid grid-cols-2 gap-2 text-sm mb-3">
            <div>
              <span className="text-muted-foreground">Remaining: </span>
              <span className={remaining > 0 ? 'text-yellow-500' : 'text-green-500'}>
                {formatValue(Math.max(0, remaining), goal.target_type)}
              </span>
            </div>
            <div>
              <span className="text-muted-foreground">Projected: </span>
              <span className={projected_value >= goal.target_value ? 'text-green-500' : 'text-yellow-500'}>
                {formatValue(projected_value, goal.target_type)}
              </span>
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="flex justify-end gap-2">
          {!goal.is_achieved && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onDeactivate(goal.id)}
              className="text-muted-foreground hover:text-foreground"
            >
              Deactivate
            </Button>
          )}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onDelete(goal.id)}
            className="text-red-500 hover:text-red-600 hover:bg-red-500/10"
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

interface CreateGoalFormProps {
  characterId: number
  onSuccess: () => void
}

function CreateGoalForm({ characterId, onSuccess }: CreateGoalFormProps) {
  const [goalType, setGoalType] = useState<'daily' | 'weekly' | 'monthly'>('daily')
  const [targetType, setTargetType] = useState<'profit' | 'volume' | 'trades' | 'roi'>('profit')
  const [targetValue, setTargetValue] = useState('')
  const [notifyProgress, setNotifyProgress] = useState(true)
  const [notifyCompletion, setNotifyCompletion] = useState(true)

  const queryClient = useQueryClient()

  const createMutation = useMutation({
    mutationFn: () =>
      marketApi.createGoal(characterId, {
        goal_type: goalType,
        target_type: targetType,
        target_value: parseFloat(targetValue),
        notify_on_progress: notifyProgress,
        notify_on_completion: notifyCompletion,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['goals', characterId] })
      setTargetValue('')
      onSuccess()
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!targetValue || parseFloat(targetValue) <= 0) return
    createMutation.mutate()
  }

  const getPlaceholder = () => {
    switch (targetType) {
      case 'profit':
        return 'e.g., 100000000 (100M ISK)'
      case 'volume':
        return 'e.g., 1000 units'
      case 'trades':
        return 'e.g., 50 trades'
      case 'roi':
        return 'e.g., 10 (10%)'
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="text-sm font-medium mb-2 block">Period</label>
          <div className="flex gap-2">
            {(['daily', 'weekly', 'monthly'] as const).map((type) => (
              <Button
                key={type}
                type="button"
                variant={goalType === type ? 'default' : 'outline'}
                size="sm"
                onClick={() => setGoalType(type)}
              >
                {goalTypeLabels[type]}
              </Button>
            ))}
          </div>
        </div>
        <div>
          <label className="text-sm font-medium mb-2 block">Target Type</label>
          <div className="flex gap-2">
            {(['profit', 'volume', 'trades', 'roi'] as const).map((type) => (
              <Button
                key={type}
                type="button"
                variant={targetType === type ? 'default' : 'outline'}
                size="sm"
                onClick={() => setTargetType(type)}
                title={targetTypeLabels[type]}
              >
                {targetTypeIcons[type]}
              </Button>
            ))}
          </div>
        </div>
      </div>

      <div>
        <label className="text-sm font-medium mb-2 block">
          Target Value ({targetTypeLabels[targetType]})
        </label>
        <Input
          type="number"
          value={targetValue}
          onChange={(e) => setTargetValue(e.target.value)}
          placeholder={getPlaceholder()}
          min="0"
          step="any"
        />
      </div>

      <div className="flex gap-6">
        <div className="flex items-center gap-2">
          <Checkbox
            id="notify-progress"
            checked={notifyProgress}
            onCheckedChange={(checked: boolean) => setNotifyProgress(checked)}
          />
          <label htmlFor="notify-progress" className="text-sm">
            Notify at milestones
          </label>
        </div>
        <div className="flex items-center gap-2">
          <Checkbox
            id="notify-completion"
            checked={notifyCompletion}
            onCheckedChange={(checked: boolean) => setNotifyCompletion(checked)}
          />
          <label htmlFor="notify-completion" className="text-sm">
            Notify on completion
          </label>
        </div>
      </div>

      <Button type="submit" disabled={createMutation.isPending || !targetValue}>
        {createMutation.isPending ? 'Creating...' : 'Create Goal'}
      </Button>
    </form>
  )
}

export default function TradingGoals() {
  const { selectedCharacter } = useCharacterContext()
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [showInactive, setShowInactive] = useState(false)
  const queryClient = useQueryClient()

  const characterId = selectedCharacter?.character_id

  const { data, isLoading, error } = useQuery<GoalsResponse>({
    queryKey: ['goals', characterId, showInactive],
    queryFn: () => marketApi.getGoals(characterId!, { activeOnly: !showInactive }),
    enabled: !!characterId,
    refetchInterval: 60000, // Refresh every minute
  })

  const deleteMutation = useMutation({
    mutationFn: (goalId: number) => marketApi.deleteGoal(characterId!, goalId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['goals', characterId] })
    },
  })

  const deactivateMutation = useMutation({
    mutationFn: (goalId: number) => marketApi.deactivateGoal(characterId!, goalId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['goals', characterId] })
    },
  })

  if (!characterId) {
    return (
      <div className="p-6">
        <Card>
          <CardContent className="p-6 text-center text-muted-foreground">
            Please select a character to view trading goals.
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Target className="h-8 w-8 text-primary" />
          <div>
            <h1 className="text-2xl font-bold">Trading Goals</h1>
            <p className="text-muted-foreground">
              Set and track your trading targets
            </p>
          </div>
        </div>
        <Button onClick={() => setShowCreateForm(!showCreateForm)}>
          <Plus className="h-4 w-4 mr-2" />
          New Goal
        </Button>
      </div>

      {/* Create Form */}
      {showCreateForm && (
        <Card>
          <CardHeader>
            <CardTitle>Create New Goal</CardTitle>
          </CardHeader>
          <CardContent>
            <CreateGoalForm
              characterId={characterId}
              onSuccess={() => setShowCreateForm(false)}
            />
          </CardContent>
        </Card>
      )}

      {/* Achievement Stats */}
      {data && (
        <div className="grid grid-cols-4 gap-4">
          <Card>
            <CardContent className="p-4 text-center">
              <div className="text-2xl font-bold text-green-500">
                {data.completed_today}
              </div>
              <div className="text-sm text-muted-foreground">Completed Today</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 text-center">
              <div className="text-2xl font-bold text-blue-500">
                {data.completed_this_week}
              </div>
              <div className="text-sm text-muted-foreground">This Week</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 text-center">
              <div className="text-2xl font-bold text-purple-500">
                {data.completed_this_month}
              </div>
              <div className="text-sm text-muted-foreground">This Month</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 text-center">
              <div className="text-2xl font-bold text-yellow-500">
                {data.total_achievements}
              </div>
              <div className="text-sm text-muted-foreground">Total Achievements</div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Filter */}
      <div className="flex items-center gap-2">
        <Checkbox
          id="show-inactive"
          checked={showInactive}
          onCheckedChange={(checked: boolean) => setShowInactive(checked)}
        />
        <label htmlFor="show-inactive" className="text-sm">
          Show inactive goals
        </label>
      </div>

      {/* Goals List */}
      {isLoading ? (
        <Card>
          <CardContent className="p-6 text-center text-muted-foreground">
            Loading goals...
          </CardContent>
        </Card>
      ) : error ? (
        <Card>
          <CardContent className="p-6 text-center text-red-500">
            Error loading goals: {(error as Error).message}
          </CardContent>
        </Card>
      ) : data?.active_goals.length === 0 ? (
        <Card>
          <CardContent className="p-6 text-center text-muted-foreground">
            No goals found. Create one to start tracking your progress!
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {data?.active_goals.map((progress) => (
            <GoalCard
              key={progress.goal.id}
              progress={progress}
              onDelete={(goalId) => deleteMutation.mutate(goalId)}
              onDeactivate={(goalId) => deactivateMutation.mutate(goalId)}
            />
          ))}
        </div>
      )}
    </div>
  )
}
