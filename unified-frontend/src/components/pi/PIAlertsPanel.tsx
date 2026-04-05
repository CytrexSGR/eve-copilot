import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { piApi, PIAlertLog } from '@/api/pi'
import { cn } from '@/lib/utils'
import { AlertTriangle, CheckCircle, Clock, Bell, BellOff } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'

interface PIAlertsPanelProps {
  characterId?: number
  limit?: number
  showConfig?: boolean
}

const ALERT_TYPE_LABELS: Record<string, string> = {
  extractor_depleting: 'Extractor Depleting',
  extractor_stopped: 'Extractor Stopped',
  storage_full: 'Storage Full',
  storage_almost_full: 'Storage Almost Full',
  factory_idle: 'Factory Idle',
  pickup_reminder: 'Pickup Reminder',
}

const ALERT_TYPE_ICONS: Record<string, typeof AlertTriangle> = {
  extractor_depleting: Clock,
  extractor_stopped: AlertTriangle,
  storage_full: AlertTriangle,
  storage_almost_full: Clock,
  factory_idle: AlertTriangle,
  pickup_reminder: Bell,
}

function AlertItem({ alert, onMarkRead }: { alert: PIAlertLog; onMarkRead: (id: number) => void }) {
  const Icon = ALERT_TYPE_ICONS[alert.alert_type] || AlertTriangle
  const isCritical = alert.severity === 'critical'

  return (
    <div
      className={cn(
        'p-3 rounded-lg border transition-colors',
        isCritical
          ? 'bg-red-500/10 border-red-500/30'
          : 'bg-yellow-500/10 border-yellow-500/30',
        alert.is_read && 'opacity-60'
      )}
    >
      <div className="flex items-start gap-3">
        <Icon
          className={cn(
            'w-5 h-5 mt-0.5 shrink-0',
            isCritical ? 'text-red-400' : 'text-yellow-400'
          )}
        />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <Badge
              className={cn(
                'text-xs',
                isCritical
                  ? 'bg-red-500/20 text-red-400'
                  : 'bg-yellow-500/20 text-yellow-400'
              )}
            >
              {ALERT_TYPE_LABELS[alert.alert_type] || alert.alert_type}
            </Badge>
            {!alert.is_read && (
              <Badge className="bg-blue-500/20 text-blue-400 text-xs">New</Badge>
            )}
          </div>
          <p className="text-sm text-[#e6edf3]">{alert.message}</p>
          {alert.details?.hours_remaining !== undefined && (
            <p className="text-xs text-[#8b949e] mt-1">
              {alert.details.hours_remaining > 0
                ? `${(alert.details.hours_remaining as number).toFixed(1)}h remaining`
                : 'Stopped'}
            </p>
          )}
          <p className="text-xs text-[#6e7681] mt-1">
            {formatDistanceToNow(new Date(alert.created_at), { addSuffix: true })}
          </p>
        </div>
        {!alert.is_read && (
          <button
            onClick={() => onMarkRead(alert.id)}
            className="p-1 hover:bg-[#30363d] rounded"
            title="Mark as read"
          >
            <CheckCircle className="w-4 h-4 text-[#8b949e]" />
          </button>
        )}
      </div>
    </div>
  )
}

export function PIAlertsPanel({ characterId, limit = 20, showConfig = false }: PIAlertsPanelProps) {
  const queryClient = useQueryClient()

  const { data: alerts, isLoading } = useQuery({
    queryKey: ['pi', 'alerts', characterId, limit],
    queryFn: () => piApi.getAlerts(characterId, false, limit),
    refetchInterval: 60000, // Refresh every minute
  })

  const markReadMutation = useMutation({
    mutationFn: (alertIds: number[]) => piApi.markAlertsRead(alertIds),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pi', 'alerts'] })
    },
  })

  const handleMarkRead = (alertId: number) => {
    markReadMutation.mutate([alertId])
  }

  const handleMarkAllRead = () => {
    if (alerts && alerts.length > 0) {
      const unreadIds = alerts.filter(a => !a.is_read).map(a => a.id)
      if (unreadIds.length > 0) {
        markReadMutation.mutate(unreadIds)
      }
    }
  }

  const unreadCount = alerts?.filter(a => !a.is_read).length || 0
  const criticalCount = alerts?.filter(a => a.severity === 'critical' && !a.is_read).length || 0

  return (
    <Card className="bg-[#161b22] border-[#30363d]">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Bell className="w-5 h-5 text-[#8b949e]" />
            <CardTitle className="text-lg">PI Alerts</CardTitle>
            {unreadCount > 0 && (
              <Badge
                className={cn(
                  'text-xs',
                  criticalCount > 0
                    ? 'bg-red-500/20 text-red-400'
                    : 'bg-yellow-500/20 text-yellow-400'
                )}
              >
                {unreadCount} unread
              </Badge>
            )}
          </div>
          {unreadCount > 0 && (
            <button
              onClick={handleMarkAllRead}
              className="text-xs text-[#8b949e] hover:text-[#e6edf3] transition-colors"
            >
              Mark all read
            </button>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-3">
            {[1, 2, 3].map(i => (
              <Skeleton key={i} className="h-20 w-full" />
            ))}
          </div>
        ) : !alerts || alerts.length === 0 ? (
          <div className="py-8 text-center">
            <BellOff className="w-10 h-10 text-[#6e7681] mx-auto mb-3" />
            <p className="text-[#8b949e]">No alerts</p>
            <p className="text-xs text-[#6e7681] mt-1">
              Your PI colonies are running smoothly
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {alerts.map(alert => (
              <AlertItem
                key={alert.id}
                alert={alert}
                onMarkRead={handleMarkRead}
              />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
