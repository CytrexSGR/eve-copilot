// unified-frontend/src/pages/market/TradingAlerts.tsx

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Header } from '@/components/layout/Header'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Checkbox } from '@/components/ui/checkbox'
import { useCharacterContext } from '@/contexts/CharacterContext'
import { marketApi } from '@/api/market'
import { cn } from '@/lib/utils'
import {
  Bell,
  BellOff,
  AlertTriangle,
  AlertCircle,
  Info,
  CheckCircle2,
  Settings,
  Send,
  Clock,
  Eye,
  EyeOff,
  Webhook,
} from 'lucide-react'
import type { AlertEntry, AlertConfig } from '@/types/market'

function formatTimeAgo(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / (1000 * 60))
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

  if (diffMins < 1) return 'just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  return `${diffDays}d ago`
}

function SeverityBadge({ severity }: { severity: string }) {
  const config = {
    critical: { label: 'Critical', className: 'bg-red-500/20 text-red-400 border-red-500/50', icon: AlertCircle },
    warning: { label: 'Warning', className: 'bg-amber-500/20 text-amber-400 border-amber-500/50', icon: AlertTriangle },
    info: { label: 'Info', className: 'bg-blue-500/20 text-blue-400 border-blue-500/50', icon: Info },
  }[severity] ?? { label: severity, className: 'bg-gray-500/20 text-gray-400', icon: Info }

  const Icon = config.icon

  return (
    <Badge variant="outline" className={cn('flex items-center gap-1', config.className)}>
      <Icon className="h-3 w-3" />
      {config.label}
    </Badge>
  )
}

function AlertCard({ alert, onMarkRead }: { alert: AlertEntry; onMarkRead: (id: number) => void }) {
  const timeAgo = formatTimeAgo(alert.created_at)

  return (
    <div
      className={cn(
        "p-4 rounded-lg border transition-colors",
        alert.is_read
          ? "bg-muted/20 border-border/50"
          : "bg-card border-border hover:bg-muted/50"
      )}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            <SeverityBadge severity={alert.severity} />
            <Badge variant="secondary" className="text-xs">
              {alert.alert_type.replace(/_/g, ' ')}
            </Badge>
            {alert.discord_sent && (
              <Badge variant="outline" className="text-xs text-purple-400 border-purple-500/50">
                Discord
              </Badge>
            )}
          </div>
          <p className={cn("text-sm", alert.is_read ? "text-muted-foreground" : "text-foreground")}>
            {alert.message}
          </p>
          {alert.type_name && (
            <p className="text-xs text-muted-foreground mt-1">
              Item: {alert.type_name}
            </p>
          )}
          <div className="flex items-center gap-2 mt-2 text-xs text-muted-foreground">
            <Clock className="h-3 w-3" />
            {timeAgo}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {!alert.is_read && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onMarkRead(alert.id)}
              className="text-muted-foreground hover:text-foreground"
            >
              <Eye className="h-4 w-4" />
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}

function ConfigSection({
  config,
  onUpdate,
  onTestWebhook,
  isUpdating,
  isTesting,
}: {
  config: AlertConfig
  onUpdate: (updates: Partial<AlertConfig>) => void
  onTestWebhook: () => void
  isUpdating: boolean
  isTesting: boolean
}) {
  const [localWebhook, setLocalWebhook] = useState(config.discord_webhook_url || '')

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg flex items-center gap-2">
          <Settings className="h-5 w-5" />
          Alert Configuration
        </CardTitle>
        <CardDescription>
          Configure Discord notifications and alert preferences
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Discord Webhook */}
        <div className="space-y-4">
          <div className="flex items-center gap-2 text-sm font-medium">
            <Webhook className="h-4 w-4 text-purple-400" />
            Discord Integration
          </div>

          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <div className="text-sm font-medium">Enable Discord Notifications</div>
              <p className="text-xs text-muted-foreground">
                Receive alerts via Discord webhook
              </p>
            </div>
            <Checkbox
              checked={config.discord_enabled}
              onCheckedChange={(checked: boolean) => onUpdate({ discord_enabled: checked })}
            />
          </div>

          <div className="space-y-2">
            <div className="text-sm font-medium">Webhook URL</div>
            <div className="flex gap-2">
              <Input
                type="url"
                placeholder="https://discord.com/api/webhooks/..."
                value={localWebhook}
                onChange={(e) => setLocalWebhook(e.target.value)}
                className="flex-1"
              />
              <Button
                variant="outline"
                onClick={() => onUpdate({ discord_webhook_url: localWebhook })}
                disabled={isUpdating || localWebhook === config.discord_webhook_url}
              >
                Save
              </Button>
              <Button
                variant="secondary"
                onClick={onTestWebhook}
                disabled={isTesting || !config.discord_webhook_url}
              >
                <Send className="h-4 w-4 mr-1" />
                Test
              </Button>
            </div>
          </div>
        </div>

        {/* Alert Types */}
        <div className="space-y-4 pt-4 border-t">
          <div className="text-sm font-medium">Alert Types</div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
              <div className="space-y-0.5">
                <div className="text-sm">Margin Alerts</div>
                <p className="text-xs text-muted-foreground">Low margin warnings</p>
              </div>
              <Checkbox
                checked={config.alert_undercut_enabled}
                onCheckedChange={(checked: boolean) => onUpdate({ alert_undercut_enabled: checked })}
              />
            </div>

            <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
              <div className="space-y-0.5">
                <div className="text-sm">Velocity Alerts</div>
                <p className="text-xs text-muted-foreground">Slow movers, dead stock</p>
              </div>
              <Checkbox
                checked={config.alert_velocity_enabled}
                onCheckedChange={(checked: boolean) => onUpdate({ alert_velocity_enabled: checked })}
              />
            </div>

            <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
              <div className="space-y-0.5">
                <div className="text-sm">Goal Alerts</div>
                <p className="text-xs text-muted-foreground">Target achievements</p>
              </div>
              <Checkbox
                checked={config.alert_goals_enabled}
                onCheckedChange={(checked: boolean) => onUpdate({ alert_goals_enabled: checked })}
              />
            </div>
          </div>
        </div>

        {/* Thresholds */}
        <div className="space-y-4 pt-4 border-t">
          <div className="text-sm font-medium">Thresholds</div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <div className="text-sm">Margin Alert Threshold (%)</div>
              <Input
                type="number"
                min={0}
                max={100}
                step={0.5}
                value={config.alert_margin_threshold}
                onChange={(e) => onUpdate({ alert_margin_threshold: parseFloat(e.target.value) })}
              />
              <p className="text-xs text-muted-foreground">
                Alert when margin falls below this percentage
              </p>
            </div>

            <div className="space-y-2">
              <div className="text-sm">Minimum Alert Interval (minutes)</div>
              <Input
                type="number"
                min={1}
                max={1440}
                value={config.min_alert_interval_minutes}
                onChange={(e) => onUpdate({ min_alert_interval_minutes: parseInt(e.target.value) })}
              />
              <p className="text-xs text-muted-foreground">
                Prevent notification spam
              </p>
            </div>
          </div>
        </div>

        {/* Quiet Hours */}
        <div className="space-y-4 pt-4 border-t">
          <div className="text-sm font-medium">Quiet Hours (UTC)</div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <div className="text-sm">Start Hour</div>
              <Input
                type="number"
                min={0}
                max={23}
                placeholder="e.g., 22"
                value={config.quiet_hours_start ?? ''}
                onChange={(e) => onUpdate({ quiet_hours_start: e.target.value ? parseInt(e.target.value) : null })}
              />
            </div>

            <div className="space-y-2">
              <div className="text-sm">End Hour</div>
              <Input
                type="number"
                min={0}
                max={23}
                placeholder="e.g., 8"
                value={config.quiet_hours_end ?? ''}
                onChange={(e) => onUpdate({ quiet_hours_end: e.target.value ? parseInt(e.target.value) : null })}
              />
            </div>
          </div>
          <p className="text-xs text-muted-foreground">
            No Discord notifications during these hours
          </p>
        </div>
      </CardContent>
    </Card>
  )
}

export function TradingAlerts() {
  const { selectedCharacter } = useCharacterContext()
  const characterId = selectedCharacter?.character_id
  const queryClient = useQueryClient()
  const [showUnreadOnly, setShowUnreadOnly] = useState(false)
  const [showConfig, setShowConfig] = useState(false)

  const { data: alertsData, isLoading: alertsLoading, refetch, isFetching } = useQuery({
    queryKey: ['alerts', characterId, showUnreadOnly],
    queryFn: () => marketApi.getAlerts(characterId!, { unreadOnly: showUnreadOnly }),
    enabled: !!characterId,
    refetchInterval: 60000, // Refresh every minute
  })

  const { data: config, isLoading: configLoading } = useQuery({
    queryKey: ['alertConfig', characterId],
    queryFn: () => marketApi.getAlertConfig(characterId!),
    enabled: !!characterId && showConfig,
  })

  const markReadMutation = useMutation({
    mutationFn: (alertIds?: number[]) => marketApi.markAlertsRead(characterId!, alertIds),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts', characterId] })
    },
  })

  const updateConfigMutation = useMutation({
    mutationFn: (updates: Partial<AlertConfig>) =>
      marketApi.updateAlertConfig(characterId!, updates),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alertConfig', characterId] })
    },
  })

  const testWebhookMutation = useMutation({
    mutationFn: () => marketApi.testDiscordWebhook(characterId!),
  })

  if (!characterId) {
    return (
      <div className="p-6">
        <Header title="Trading Alerts" subtitle="Select a character to view alerts" />
      </div>
    )
  }

  const alerts = alertsData?.alerts ?? []
  const unreadCount = alertsData?.unread_count ?? 0
  const criticalCount = alertsData?.critical_count ?? 0
  const warningCount = alertsData?.warning_count ?? 0

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <Header
          title="Trading Alerts"
          subtitle="Monitor margin alerts, velocity warnings, and more"
          onRefresh={() => refetch()}
          isRefreshing={isFetching}
        />
        <div className="flex items-center gap-2">
          <Button
            variant={showConfig ? "default" : "outline"}
            size="sm"
            onClick={() => setShowConfig(!showConfig)}
          >
            <Settings className="h-4 w-4 mr-1" />
            Settings
          </Button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="border-l-4 border-l-blue-500">
          <CardContent className="pt-4">
            <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
              <Bell className="h-4 w-4" />
              Unread Alerts
            </div>
            <div className="text-2xl font-bold">
              {alertsLoading ? '...' : unreadCount}
            </div>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-red-500">
          <CardContent className="pt-4">
            <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
              <AlertCircle className="h-4 w-4 text-red-500" />
              Critical
            </div>
            <div className="text-2xl font-bold text-red-500">
              {alertsLoading ? '...' : criticalCount}
            </div>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-amber-500">
          <CardContent className="pt-4">
            <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
              <AlertTriangle className="h-4 w-4 text-amber-500" />
              Warnings
            </div>
            <div className="text-2xl font-bold text-amber-500">
              {alertsLoading ? '...' : warningCount}
            </div>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-green-500">
          <CardContent className="pt-4">
            <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
              <CheckCircle2 className="h-4 w-4 text-green-500" />
              Discord
            </div>
            <div className="text-2xl font-bold text-green-500">
              {configLoading ? '...' : config?.discord_enabled ? 'Enabled' : 'Disabled'}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Configuration Section */}
      {showConfig && config && (
        <ConfigSection
          config={config}
          onUpdate={(updates) => updateConfigMutation.mutate(updates)}
          onTestWebhook={() => testWebhookMutation.mutate()}
          isUpdating={updateConfigMutation.isPending}
          isTesting={testWebhookMutation.isPending}
        />
      )}

      {/* Alerts List */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-lg flex items-center gap-2">
                <Bell className="h-5 w-5" />
                Recent Alerts
              </CardTitle>
              <CardDescription>
                {alerts.length} alerts in the last 7 days
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowUnreadOnly(!showUnreadOnly)}
                className={showUnreadOnly ? 'bg-muted' : ''}
              >
                {showUnreadOnly ? (
                  <>
                    <Eye className="h-4 w-4 mr-1" />
                    Unread Only
                  </>
                ) : (
                  <>
                    <EyeOff className="h-4 w-4 mr-1" />
                    Show All
                  </>
                )}
              </Button>
              {unreadCount > 0 && (
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => markReadMutation.mutate(undefined)}
                  disabled={markReadMutation.isPending}
                >
                  <CheckCircle2 className="h-4 w-4 mr-1" />
                  Mark All Read
                </Button>
              )}
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {alertsLoading ? (
            <div className="text-center py-8 text-muted-foreground">
              Loading alerts...
            </div>
          ) : alerts.length === 0 ? (
            <div className="text-center py-12">
              <BellOff className="h-12 w-12 mx-auto text-muted-foreground/50 mb-4" />
              <p className="text-muted-foreground">
                {showUnreadOnly ? 'No unread alerts' : 'No alerts yet'}
              </p>
              <p className="text-sm text-muted-foreground mt-1">
                Alerts will appear here when margins drop or items need attention
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {alerts.map((alert) => (
                <AlertCard
                  key={alert.id}
                  alert={alert}
                  onMarkRead={(id) => markReadMutation.mutate([id])}
                />
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Webhook Test Result */}
      {testWebhookMutation.isSuccess && (
        <Card className={testWebhookMutation.data.success ? 'border-green-500/50' : 'border-red-500/50'}>
          <CardContent className="py-4">
            <div className="flex items-center gap-2">
              {testWebhookMutation.data.success ? (
                <CheckCircle2 className="h-5 w-5 text-green-500" />
              ) : (
                <AlertCircle className="h-5 w-5 text-red-500" />
              )}
              <span>{testWebhookMutation.data.message}</span>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
