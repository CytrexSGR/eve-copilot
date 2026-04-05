// unified-frontend/src/components/capital/StructureTimersTab.tsx

import { useState, useEffect, useCallback } from 'react'
import { getUpcomingTimers, updateTimer, deleteTimer } from '@/api/capital'
import type { StructureTimer, TimerSummary, Urgency } from '@/types/capital'

type ConfirmAction = { type: 'delete'; timerId: number } | { type: 'result'; timerId: number; result: string } | null

const URGENCY_COLORS: Record<Urgency, { bg: string; text: string; border: string }> = {
  critical: { bg: 'bg-red-900/50', text: 'text-red-300', border: 'border-red-500' },
  urgent: { bg: 'bg-orange-900/50', text: 'text-orange-300', border: 'border-orange-500' },
  upcoming: { bg: 'bg-yellow-900/50', text: 'text-yellow-300', border: 'border-yellow-500' },
  planned: { bg: 'bg-gray-800', text: 'text-gray-300', border: 'border-gray-600' },
}

const CATEGORY_ICONS: Record<string, string> = {
  tcu: '🏴',
  ihub: '🏛️',
  poco: '📦',
  pos: '🗼',
  ansiblex: '🌀',
  cyno_beacon: '📡',
  cyno_jammer: '🚫',
}

export default function StructureTimersTab() {
  const [timers, setTimers] = useState<StructureTimer[]>([])
  const [summary, setSummary] = useState<TimerSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [hoursFilter, setHoursFilter] = useState(72)
  const [categoryFilter, setCategoryFilter] = useState<string>('all')
  const [isUpdating, setIsUpdating] = useState(false)
  const [pendingConfirm, setPendingConfirm] = useState<ConfirmAction>(null)

  const loadTimers = useCallback(async () => {
    try {
      const data = await getUpcomingTimers(
        hoursFilter,
        categoryFilter === 'all' ? undefined : categoryFilter
      )
      setTimers(data.timers)
      setSummary(data.summary)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load timers')
    } finally {
      setLoading(false)
    }
  }, [hoursFilter, categoryFilter])

  useEffect(() => {
    loadTimers()
  }, [loadTimers])

  // Note: Countdown shows static values from API until refresh.
  // Real-time countdown would require WebSocket or timer_end recalculation.

  const formatCountdown = (hoursUntil: number) => {
    if (hoursUntil < 0) return 'EXPIRED'

    const totalMinutes = hoursUntil * 60
    const hours = Math.floor(totalMinutes / 60)
    const minutes = Math.floor(totalMinutes % 60)
    const seconds = Math.floor((totalMinutes * 60) % 60)

    if (hours > 24) {
      const days = Math.floor(hours / 24)
      return `${days}d ${hours % 24}h`
    }
    return `${hours}h ${minutes}m ${seconds}s`
  }

  const handleMarkResult = async (timerId: number, result: string) => {
    setIsUpdating(true)
    setError(null)
    try {
      await updateTimer(timerId, { result })
      loadTimers()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update timer')
    } finally {
      setIsUpdating(false)
      setPendingConfirm(null)
    }
  }

  const handleDelete = async (timerId: number) => {
    setIsUpdating(true)
    setError(null)
    try {
      await deleteTimer(timerId)
      loadTimers()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete timer')
    } finally {
      setIsUpdating(false)
      setPendingConfirm(null)
    }
  }

  const handleConfirmAction = () => {
    if (!pendingConfirm) return
    if (pendingConfirm.type === 'delete') {
      handleDelete(pendingConfirm.timerId)
    } else if (pendingConfirm.type === 'result') {
      handleMarkResult(pendingConfirm.timerId, pendingConfirm.result)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-400">Loading structure timers...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-900/50 border border-red-500 rounded p-4 text-red-300">
        {error}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div className={`rounded-lg p-4 ${URGENCY_COLORS.critical.bg} border ${URGENCY_COLORS.critical.border}`}>
            <div className="text-3xl font-bold text-red-400">{summary.critical}</div>
            <div className="text-gray-400 text-sm">Critical (&lt;1h)</div>
          </div>
          <div className={`rounded-lg p-4 ${URGENCY_COLORS.urgent.bg} border ${URGENCY_COLORS.urgent.border}`}>
            <div className="text-3xl font-bold text-orange-400">{summary.urgent}</div>
            <div className="text-gray-400 text-sm">Urgent (&lt;3h)</div>
          </div>
          <div className={`rounded-lg p-4 ${URGENCY_COLORS.upcoming.bg} border ${URGENCY_COLORS.upcoming.border}`}>
            <div className="text-3xl font-bold text-yellow-400">{summary.upcoming}</div>
            <div className="text-gray-400 text-sm">Upcoming (&lt;24h)</div>
          </div>
          <div className="bg-gray-800 rounded-lg p-4 border border-gray-600">
            <div className="text-3xl font-bold text-gray-400">{summary.planned}</div>
            <div className="text-gray-400 text-sm">Planned</div>
          </div>
          <div className="bg-gray-800 rounded-lg p-4 border border-gray-600">
            <div className="text-3xl font-bold text-white">{summary.total}</div>
            <div className="text-gray-400 text-sm">Total Active</div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="bg-gray-800 rounded-lg p-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm text-gray-400 mb-1">Time Window</label>
            <select
              value={hoursFilter}
              onChange={e => setHoursFilter(Number(e.target.value))}
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
            >
              <option value={12}>Next 12 hours</option>
              <option value={24}>Next 24 hours</option>
              <option value={48}>Next 48 hours</option>
              <option value={72}>Next 72 hours</option>
              <option value={168}>Next 7 days</option>
            </select>
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">Structure Type</label>
            <select
              value={categoryFilter}
              onChange={e => setCategoryFilter(e.target.value)}
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
            >
              <option value="all">All Types</option>
              <option value="tcu">TCU</option>
              <option value="ihub">iHub</option>
              <option value="poco">POCO</option>
              <option value="pos">POS</option>
              <option value="ansiblex">Ansiblex</option>
              <option value="cyno_beacon">Cyno Beacon</option>
              <option value="cyno_jammer">Cyno Jammer</option>
            </select>
          </div>
          <div className="flex items-end">
            <button
              onClick={() => loadTimers()}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded"
            >
              Refresh
            </button>
          </div>
        </div>
      </div>

      {/* Timer List */}
      <div className="space-y-3">
        {timers.map(timer => {
          const colors = URGENCY_COLORS[timer.urgency]
          return (
            <div
              key={timer.id}
              className={`${colors.bg} border ${colors.border} rounded-lg p-4`}
            >
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-xl">{CATEGORY_ICONS[timer.category] || '🏗️'}</span>
                    <span className={`text-lg font-semibold ${colors.text}`}>
                      {timer.structure_name}
                    </span>
                    {timer.cyno_jammed && (
                      <span className="bg-red-600 text-white px-2 py-0.5 rounded text-xs">
                        JAMMED
                      </span>
                    )}
                  </div>
                  <div className="text-gray-400 text-sm mt-1">
                    {timer.system_name} • {timer.region_name}
                    {timer.owner_alliance_name && ` • ${timer.owner_alliance_name}`}
                  </div>
                  <div className="text-gray-500 text-xs mt-1">
                    {timer.timer_type.toUpperCase()} timer • {timer.category.toUpperCase()}
                    {timer.notes && ` • ${timer.notes}`}
                  </div>
                </div>
                <div className="text-right">
                  <div className={`text-2xl font-mono font-bold ${colors.text}`}>
                    {formatCountdown(timer.hours_until)}
                  </div>
                  <div className="text-gray-500 text-xs">
                    {new Date(timer.timer_end).toLocaleString()}
                  </div>
                  <div className="mt-2 flex gap-1">
                    {pendingConfirm?.timerId === timer.id ? (
                      <>
                        <span className="text-xs text-gray-400 px-1 py-1">
                          {pendingConfirm.type === 'delete' ? 'Delete?' : `Mark ${pendingConfirm.type === 'result' ? pendingConfirm.result : ''}?`}
                        </span>
                        <button
                          onClick={handleConfirmAction}
                          disabled={isUpdating}
                          className="bg-green-700 hover:bg-green-600 disabled:opacity-50 disabled:cursor-not-allowed text-white px-2 py-1 rounded text-xs"
                        >
                          {isUpdating ? '...' : 'Yes'}
                        </button>
                        <button
                          onClick={() => setPendingConfirm(null)}
                          disabled={isUpdating}
                          className="bg-gray-700 hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed text-white px-2 py-1 rounded text-xs"
                        >
                          No
                        </button>
                      </>
                    ) : (
                      <>
                        <button
                          onClick={() => setPendingConfirm({ type: 'result', timerId: timer.id, result: 'defended' })}
                          disabled={isUpdating}
                          className="bg-green-700 hover:bg-green-600 disabled:opacity-50 disabled:cursor-not-allowed text-white px-2 py-1 rounded text-xs"
                        >
                          Defended
                        </button>
                        <button
                          onClick={() => setPendingConfirm({ type: 'result', timerId: timer.id, result: 'destroyed' })}
                          disabled={isUpdating}
                          className="bg-red-700 hover:bg-red-600 disabled:opacity-50 disabled:cursor-not-allowed text-white px-2 py-1 rounded text-xs"
                        >
                          Lost
                        </button>
                        <button
                          onClick={() => setPendingConfirm({ type: 'delete', timerId: timer.id })}
                          disabled={isUpdating}
                          className="bg-gray-700 hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed text-white px-2 py-1 rounded text-xs"
                        >
                          ×
                        </button>
                      </>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {timers.length === 0 && (
        <div className="bg-gray-800 rounded-lg p-8 text-center">
          <div className="text-gray-400">No upcoming timers found</div>
          <div className="text-gray-500 text-sm mt-2">
            Timers can be added via the API or imported from ESI
          </div>
        </div>
      )}
    </div>
  )
}
