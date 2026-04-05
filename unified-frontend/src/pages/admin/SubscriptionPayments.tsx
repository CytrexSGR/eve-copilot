import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  CreditCard,
  ArrowLeft,
  CheckCircle,
  Clock,
  XCircle,
  AlertTriangle,
  User,
  Package
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { subscriptionAdminApi } from '@/api/subscriptionAdmin'
import { formatISK } from '@/lib/utils'
import type { Payment, Product, Customer } from '@/types/subscription'

const STATUS_CONFIG = {
  pending: { label: 'Pending', color: 'bg-yellow-500', icon: Clock },
  matched: { label: 'Matched', color: 'bg-blue-500', icon: CheckCircle },
  processed: { label: 'Processed', color: 'bg-green-500', icon: CheckCircle },
  failed: { label: 'Failed', color: 'bg-red-500', icon: XCircle },
}

export default function SubscriptionPayments() {
  const queryClient = useQueryClient()
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [matchingPayment, setMatchingPayment] = useState<Payment | null>(null)

  const { data: payments, isLoading } = useQuery({
    queryKey: ['subscription-payments', statusFilter],
    queryFn: () => subscriptionAdminApi.getPayments(
      statusFilter === 'all' ? undefined : statusFilter,
      200
    ),
  })

  const { data: products } = useQuery({
    queryKey: ['subscription-products'],
    queryFn: subscriptionAdminApi.getProducts,
  })

  const { data: customers } = useQuery({
    queryKey: ['subscription-customers'],
    queryFn: () => subscriptionAdminApi.getCustomers(500, 0),
  })

  const matchMutation = useMutation({
    mutationFn: ({ paymentId, customerId, productId }: {
      paymentId: number
      customerId: number
      productId: number
    }) => subscriptionAdminApi.matchPayment(paymentId, {
      customer_id: customerId,
      product_id: productId
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['subscription-payments'] })
      queryClient.invalidateQueries({ queryKey: ['subscription-stats'] })
      setMatchingPayment(null)
    },
  })

  const pendingCount = payments?.filter(p => p.status === 'pending').length ?? 0

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link to="/admin/subscriptions">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back
            </Button>
          </Link>
          <div>
            <h1 className="text-2xl font-bold">Payments</h1>
            <p className="text-muted-foreground">
              {pendingCount > 0 && (
                <span className="text-yellow-500 font-medium">{pendingCount} pending · </span>
              )}
              Review and match incoming ISK payments
            </p>
          </div>
        </div>

        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="Filter status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All</SelectItem>
            <SelectItem value="pending">Pending</SelectItem>
            <SelectItem value="matched">Matched</SelectItem>
            <SelectItem value="processed">Processed</SelectItem>
            <SelectItem value="failed">Failed</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Payments List */}
      {isLoading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <Card key={i}>
              <CardContent className="p-4">
                <Skeleton className="h-6 w-full" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <div className="space-y-3">
          {payments?.map((payment) => {
            const statusConfig = STATUS_CONFIG[payment.status]
            const StatusIcon = statusConfig.icon

            return (
              <Card
                key={payment.id}
                className={payment.status === 'pending' ? 'border-yellow-500 border-l-4' : ''}
              >
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className={`p-2 rounded-full ${statusConfig.color} bg-opacity-20`}>
                        <StatusIcon className={`h-5 w-5 ${statusConfig.color.replace('bg-', 'text-')}`} />
                      </div>

                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-medium">
                            {payment.from_character_name || `Character ${payment.from_character_id}`}
                          </span>
                          <Badge variant="outline">{statusConfig.label}</Badge>
                        </div>
                        <div className="text-sm text-muted-foreground">
                          {new Date(payment.received_at).toLocaleString()} ·
                          Ref: {payment.journal_ref_id}
                          {payment.payment_code && (
                            <span className="ml-2 text-blue-500">Code: {payment.payment_code}</span>
                          )}
                        </div>
                        {payment.notes && (
                          <div className="text-sm text-yellow-600 mt-1">
                            <AlertTriangle className="h-3 w-3 inline mr-1" />
                            {payment.notes}
                          </div>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center gap-4">
                      <div className="text-right">
                        <p className="text-xl font-bold text-green-500">
                          {formatISK(payment.amount)}
                        </p>
                        {payment.reason && (
                          <p className="text-xs text-muted-foreground max-w-[200px] truncate">
                            "{payment.reason}"
                          </p>
                        )}
                      </div>

                      {payment.status === 'pending' && (
                        <Button
                          variant="outline"
                          onClick={() => setMatchingPayment(payment)}
                        >
                          Match
                        </Button>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            )
          })}

          {payments?.length === 0 && (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <CreditCard className="h-12 w-12 text-muted-foreground mb-4" />
                <p className="text-muted-foreground">No payments found</p>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* Match Dialog */}
      <Dialog open={!!matchingPayment} onOpenChange={() => setMatchingPayment(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Match Payment</DialogTitle>
          </DialogHeader>
          {matchingPayment && (
            <PaymentMatchForm
              payment={matchingPayment}
              products={products ?? []}
              customers={customers ?? []}
              onMatch={(customerId, productId) =>
                matchMutation.mutate({
                  paymentId: matchingPayment.id,
                  customerId,
                  productId
                })
              }
              isLoading={matchMutation.isPending}
            />
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}

function PaymentMatchForm({
  payment,
  products,
  customers,
  onMatch,
  isLoading,
}: {
  payment: Payment
  products: Product[]
  customers: Customer[]
  onMatch: (customerId: number, productId: number) => void
  isLoading: boolean
}) {
  const [customerId, setCustomerId] = useState<string>(
    payment.from_character_id.toString()
  )
  const [productId, setProductId] = useState<string>('')

  // Find product matching the amount
  const matchingProduct = products.find(p => p.price_isk === payment.amount)

  return (
    <div className="space-y-4">
      <div className="p-4 bg-muted rounded-lg">
        <p className="text-sm text-muted-foreground">Payment Details</p>
        <p className="font-medium">{payment.from_character_name}</p>
        <p className="text-xl font-bold text-green-500">{formatISK(payment.amount)}</p>
        {payment.reason && (
          <p className="text-sm text-muted-foreground">"{payment.reason}"</p>
        )}
      </div>

      {matchingProduct && (
        <div className="p-3 bg-green-500/10 border border-green-500/30 rounded-lg">
          <p className="text-sm text-green-600">
            <CheckCircle className="h-4 w-4 inline mr-1" />
            Price matches "{matchingProduct.name}"
          </p>
        </div>
      )}

      <div>
        <label className="text-sm font-medium flex items-center gap-2">
          <User className="h-4 w-4" />
          Customer
        </label>
        <Select value={customerId} onValueChange={setCustomerId}>
          <SelectTrigger>
            <SelectValue placeholder="Select customer" />
          </SelectTrigger>
          <SelectContent>
            {customers.map((c) => (
              <SelectItem key={c.character_id} value={c.character_id.toString()}>
                {c.character_name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div>
        <label className="text-sm font-medium flex items-center gap-2">
          <Package className="h-4 w-4" />
          Product
        </label>
        <Select
          value={productId || matchingProduct?.id.toString() || ''}
          onValueChange={setProductId}
        >
          <SelectTrigger>
            <SelectValue placeholder="Select product" />
          </SelectTrigger>
          <SelectContent>
            {products.filter(p => p.is_active).map((p) => (
              <SelectItem key={p.id} value={p.id.toString()}>
                {p.name} ({formatISK(p.price_isk)})
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <Button
        className="w-full"
        onClick={() => onMatch(
          parseInt(customerId),
          parseInt(productId || matchingProduct?.id.toString() || '0')
        )}
        disabled={isLoading || !customerId || (!productId && !matchingProduct)}
      >
        {isLoading ? 'Matching...' : 'Match & Activate Subscription'}
      </Button>
    </div>
  )
}
