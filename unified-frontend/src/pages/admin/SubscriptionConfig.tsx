import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import {
  ArrowLeft,
  Power,
  LogIn,
  Wallet,
  User,
  AlertTriangle,
  CheckCircle
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { subscriptionAdminApi } from '@/api/subscriptionAdmin'

interface ConfigItem {
  key: string
  label: string
  description: string
  icon: React.ElementType
  dangerous?: boolean
}

const CONFIG_ITEMS: ConfigItem[] = [
  {
    key: 'subscription_enabled',
    label: 'Paywall Active',
    description: 'When enabled, premium features require an active subscription',
    icon: Power,
    dangerous: true,
  },
  {
    key: 'login_enabled',
    label: 'Login Enabled',
    description: 'Show login button on public frontend',
    icon: LogIn,
  },
  {
    key: 'wallet_poll_enabled',
    label: 'Payment Polling',
    description: 'Automatically check for incoming ISK payments every 5 minutes',
    icon: Wallet,
  },
]

export default function SubscriptionConfig() {
  const queryClient = useQueryClient()

  const { data: config, isLoading } = useQuery({
    queryKey: ['subscription-config'],
    queryFn: subscriptionAdminApi.getConfig,
  })

  const updateMutation = useMutation({
    mutationFn: ({ key, value }: { key: string; value: string }) =>
      subscriptionAdminApi.updateConfig(key, { value }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['subscription-config'] })
    },
  })

  const toggleConfig = (key: string, currentValue: string) => {
    const newValue = currentValue === 'true' ? 'false' : 'true'
    updateMutation.mutate({ key, value: newValue })
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link to="/admin/subscriptions">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back
          </Button>
        </Link>
        <div>
          <h1 className="text-2xl font-bold">System Configuration</h1>
          <p className="text-muted-foreground">Control subscription system features</p>
        </div>
      </div>

      {/* Warning */}
      <Card className="border-yellow-500 border-l-4">
        <CardContent className="flex items-start gap-3 p-4">
          <AlertTriangle className="h-5 w-5 text-yellow-500 mt-0.5" />
          <div>
            <p className="font-medium">Production Settings</p>
            <p className="text-sm text-muted-foreground">
              Changes take effect immediately. Be careful when enabling the paywall.
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Config Toggles */}
      <div className="space-y-4">
        {CONFIG_ITEMS.map((item) => {
          const Icon = item.icon
          const value = config?.[item.key as keyof typeof config] ?? 'false'
          const isEnabled = value === 'true'

          return (
            <Card key={item.key} className={item.dangerous && isEnabled ? 'border-red-500' : ''}>
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div className="flex items-start gap-4">
                    <div className={`p-2 rounded-lg ${isEnabled ? 'bg-green-500/20' : 'bg-muted'}`}>
                      <Icon className={`h-5 w-5 ${isEnabled ? 'text-green-500' : 'text-muted-foreground'}`} />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="font-medium">{item.label}</h3>
                        <Badge variant={isEnabled ? 'default' : 'secondary'}>
                          {isEnabled ? 'Enabled' : 'Disabled'}
                        </Badge>
                        {item.dangerous && (
                          <Badge variant="destructive" className="text-xs">
                            Production
                          </Badge>
                        )}
                      </div>
                      <p className="text-sm text-muted-foreground mt-1">
                        {item.description}
                      </p>
                    </div>
                  </div>

                  {isLoading ? (
                    <Skeleton className="h-10 w-24" />
                  ) : (
                    <Button
                      variant={isEnabled ? 'destructive' : 'default'}
                      onClick={() => toggleConfig(item.key, value)}
                      disabled={updateMutation.isPending}
                    >
                      {isEnabled ? 'Disable' : 'Enable'}
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>

      {/* Billing Character */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <User className="h-5 w-5" />
            Billing Character
          </CardTitle>
          <CardDescription>
            Character that receives ISK payments
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <Skeleton className="h-6 w-48" />
          ) : config?.billing_character_id ? (
            <div className="flex items-center gap-2">
              <CheckCircle className="h-5 w-5 text-green-500" />
              <span className="font-medium">Character ID: {config.billing_character_id}</span>
            </div>
          ) : (
            <div className="flex items-center gap-2 text-yellow-500">
              <AlertTriangle className="h-5 w-5" />
              <span>Not configured - set via database</span>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Current Status Summary */}
      <Card>
        <CardHeader>
          <CardTitle>Current Status</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <StatusItem
              label="Paywall"
              enabled={config?.subscription_enabled === 'true'}
              enabledText="Users must pay for premium features"
              disabledText="All features are free"
            />
            <StatusItem
              label="Login"
              enabled={config?.login_enabled === 'true'}
              enabledText="Users can log in via EVE SSO"
              disabledText="Login button hidden"
            />
            <StatusItem
              label="Payments"
              enabled={config?.wallet_poll_enabled === 'true'}
              enabledText="Checking wallet every 5 min"
              disabledText="Manual payment matching only"
            />
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

function StatusItem({
  label,
  enabled,
  enabledText,
  disabledText
}: {
  label: string
  enabled: boolean
  enabledText: string
  disabledText: string
}) {
  return (
    <div className={`p-4 rounded-lg ${enabled ? 'bg-green-500/10' : 'bg-muted'}`}>
      <div className="flex items-center gap-2 mb-1">
        {enabled ? (
          <CheckCircle className="h-4 w-4 text-green-500" />
        ) : (
          <Power className="h-4 w-4 text-muted-foreground" />
        )}
        <span className="font-medium">{label}</span>
      </div>
      <p className="text-sm text-muted-foreground">
        {enabled ? enabledText : disabledText}
      </p>
    </div>
  )
}
