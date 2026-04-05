import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Users,
  CreditCard,
  Package,
  AlertTriangle,
  TrendingUp,
  Clock,
  RefreshCw,
  Settings,
  ShoppingCart
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { subscriptionAdminApi } from '@/api/subscriptionAdmin'
import { formatISK } from '@/lib/utils'

export default function SubscriptionDashboard() {
  const { data: stats, isLoading: statsLoading, refetch: refetchStats } = useQuery({
    queryKey: ['subscription-stats'],
    queryFn: subscriptionAdminApi.getStats,
    refetchInterval: 60000, // Refresh every minute
  })

  const { data: config, isLoading: configLoading } = useQuery({
    queryKey: ['subscription-config'],
    queryFn: subscriptionAdminApi.getConfig,
  })

  const { data: pendingPayments } = useQuery({
    queryKey: ['subscription-payments', 'pending'],
    queryFn: () => subscriptionAdminApi.getPayments('pending', 10),
  })

  const isLoading = statsLoading || configLoading

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Subscription Management</h1>
          <p className="text-muted-foreground">Manage products, payments, and subscriptions</p>
        </div>
        <Button variant="outline" size="sm" onClick={() => refetchStats()}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* System Status */}
      <div className="flex gap-2">
        <Badge variant={config?.subscription_enabled === 'true' ? 'default' : 'secondary'}>
          Paywall: {config?.subscription_enabled === 'true' ? 'Active' : 'Disabled'}
        </Badge>
        <Badge variant={config?.login_enabled === 'true' ? 'default' : 'secondary'}>
          Login: {config?.login_enabled === 'true' ? 'Enabled' : 'Disabled'}
        </Badge>
        <Badge variant={config?.wallet_poll_enabled === 'true' ? 'default' : 'secondary'}>
          Payments: {config?.wallet_poll_enabled === 'true' ? 'Polling' : 'Disabled'}
        </Badge>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatsCard
          title="Total Customers"
          value={stats?.total_customers ?? 0}
          icon={Users}
          loading={isLoading}
        />
        <StatsCard
          title="Active Subscriptions"
          value={stats?.active_subscriptions ?? 0}
          icon={CreditCard}
          loading={isLoading}
        />
        <StatsCard
          title="Active Products"
          value={stats?.active_products ?? 0}
          icon={Package}
          loading={isLoading}
        />
        <StatsCard
          title="Pending Payments"
          value={stats?.pending_payments ?? 0}
          icon={Clock}
          loading={isLoading}
          highlight={stats?.pending_payments ? stats.pending_payments > 0 : false}
        />
      </div>

      {/* Revenue Card */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5" />
            Revenue
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-muted-foreground">Last 30 Days</p>
              {isLoading ? <Skeleton className="h-8 w-32" /> : (
                <p className="text-2xl font-bold text-green-500">
                  {formatISK(stats?.revenue_30d_isk ?? 0)}
                </p>
              )}
            </div>
            <div>
              <p className="text-sm text-muted-foreground">All Time</p>
              {isLoading ? <Skeleton className="h-8 w-32" /> : (
                <p className="text-2xl font-bold">
                  {formatISK(stats?.total_revenue_isk ?? 0)}
                </p>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Link to="/admin/subscriptions/products">
          <Card className="hover:bg-accent cursor-pointer transition-colors">
            <CardContent className="flex items-center gap-4 p-6">
              <ShoppingCart className="h-8 w-8 text-blue-500" />
              <div>
                <p className="font-medium">Manage Products</p>
                <p className="text-sm text-muted-foreground">Create, edit, or disable products</p>
              </div>
            </CardContent>
          </Card>
        </Link>

        <Link to="/admin/subscriptions/payments">
          <Card className="hover:bg-accent cursor-pointer transition-colors">
            <CardContent className="flex items-center gap-4 p-6">
              <CreditCard className="h-8 w-8 text-green-500" />
              <div>
                <p className="font-medium">Review Payments</p>
                <p className="text-sm text-muted-foreground">
                  {pendingPayments?.length ?? 0} pending payments
                </p>
              </div>
            </CardContent>
          </Card>
        </Link>

        <Link to="/admin/subscriptions/config">
          <Card className="hover:bg-accent cursor-pointer transition-colors">
            <CardContent className="flex items-center gap-4 p-6">
              <Settings className="h-8 w-8 text-gray-500" />
              <div>
                <p className="font-medium">System Config</p>
                <p className="text-sm text-muted-foreground">Kill-switches and settings</p>
              </div>
            </CardContent>
          </Card>
        </Link>
      </div>

      {/* Pending Payments Alert */}
      {pendingPayments && pendingPayments.length > 0 && (
        <Card className="border-yellow-500 border-l-4">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-yellow-600">
              <AlertTriangle className="h-5 w-5" />
              Payments Requiring Review
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {pendingPayments.slice(0, 5).map((payment) => (
                <div key={payment.id} className="flex justify-between items-center p-2 bg-muted rounded">
                  <div>
                    <span className="font-medium">{payment.from_character_name}</span>
                    <span className="text-muted-foreground ml-2">
                      {formatISK(payment.amount)}
                    </span>
                  </div>
                  <span className="text-sm text-muted-foreground">
                    {payment.notes || 'No match found'}
                  </span>
                </div>
              ))}
            </div>
            {pendingPayments.length > 5 && (
              <Link to="/admin/subscriptions/payments" className="text-sm text-blue-500 mt-2 block">
                View all {pendingPayments.length} pending payments →
              </Link>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}

// Stats Card Component
function StatsCard({
  title,
  value,
  icon: Icon,
  loading,
  highlight
}: {
  title: string
  value: number
  icon: React.ElementType
  loading: boolean
  highlight?: boolean
}) {
  return (
    <Card className={highlight ? 'border-yellow-500 border-l-4' : ''}>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {title}
        </CardTitle>
        <Icon className={`h-4 w-4 ${highlight ? 'text-yellow-500' : 'text-muted-foreground'}`} />
      </CardHeader>
      <CardContent>
        {loading ? (
          <Skeleton className="h-8 w-16" />
        ) : (
          <p className={`text-2xl font-bold ${highlight ? 'text-yellow-500' : ''}`}>
            {value.toLocaleString()}
          </p>
        )}
      </CardContent>
    </Card>
  )
}
