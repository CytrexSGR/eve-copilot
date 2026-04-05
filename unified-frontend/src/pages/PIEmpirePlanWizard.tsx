import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Header } from '@/components/layout/Header'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { piApi, type P4EmpireProfitability, type EmpirePlanCreate } from '@/api/pi'
import { cn } from '@/lib/utils'
import {
  ArrowLeft,
  ArrowRight,
  Check,
  Loader2,
  Package,
  Settings,
  FileCheck,
} from 'lucide-react'
import { Link } from 'react-router-dom'

/**
 * Wizard step type
 */
type WizardStep = 1 | 2 | 3

/**
 * Step configuration
 */
const STEPS = [
  { number: 1, label: 'Select Product', icon: Package },
  { number: 2, label: 'Configure', icon: Settings },
  { number: 3, label: 'Confirm', icon: FileCheck },
] as const

/**
 * Get item icon URL
 */
function getItemIconUrl(typeId: number, size: 32 | 64 = 32): string {
  return `https://images.evetech.net/types/${typeId}/icon?size=${size}`
}

/**
 * Format ISK value
 */
function formatISK(value: number): string {
  if (value >= 1_000_000_000) {
    return `${(value / 1_000_000_000).toFixed(2)}B`
  }
  if (value >= 1_000_000) {
    return `${(value / 1_000_000).toFixed(2)}M`
  }
  if (value >= 1_000) {
    return `${(value / 1_000).toFixed(2)}K`
  }
  return value.toFixed(0)
}

/**
 * Step progress indicator component
 */
function StepIndicator({
  currentStep,
  onStepClick,
}: {
  currentStep: WizardStep
  onStepClick?: (step: WizardStep) => void
}) {
  return (
    <div className="flex items-center justify-center gap-4 mb-8">
      {STEPS.map((step, index) => {
        const isActive = step.number === currentStep
        const isCompleted = step.number < currentStep
        const canClick = step.number < currentStep && onStepClick

        return (
          <div key={step.number} className="flex items-center">
            {/* Step circle */}
            <button
              onClick={() => canClick && onStepClick(step.number as WizardStep)}
              disabled={!canClick}
              className={cn(
                'flex items-center justify-center w-10 h-10 rounded-full border-2 transition-colors',
                isCompleted && 'bg-green-500/20 border-green-500 text-green-400',
                isActive && 'bg-primary/20 border-primary text-primary',
                !isActive && !isCompleted && 'bg-secondary/50 border-border text-muted-foreground',
                canClick && 'cursor-pointer hover:border-primary/60'
              )}
            >
              {isCompleted ? (
                <Check className="h-5 w-5" />
              ) : (
                <step.icon className="h-5 w-5" />
              )}
            </button>

            {/* Step label */}
            <span
              className={cn(
                'ml-2 text-sm font-medium',
                isActive && 'text-foreground',
                !isActive && 'text-muted-foreground'
              )}
            >
              {step.label}
            </span>

            {/* Connector line */}
            {index < STEPS.length - 1 && (
              <div
                className={cn(
                  'w-12 h-0.5 mx-4',
                  step.number < currentStep ? 'bg-green-500' : 'bg-border'
                )}
              />
            )}
          </div>
        )
      })}
    </div>
  )
}

/**
 * Step 1: Select Product
 */
function SelectProductStep({
  selectedProduct,
  onSelect,
}: {
  selectedProduct: P4EmpireProfitability | null
  onSelect: (product: P4EmpireProfitability) => void
}) {
  const { data: profitabilityData, isLoading } = useQuery({
    queryKey: ['pi', 'empire', 'profitability'],
    queryFn: () => piApi.getEmpireProfitability(),
    staleTime: 60 * 1000,
  })

  if (isLoading) {
    return (
      <div className="space-y-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="flex items-center gap-4 p-4">
            <Skeleton className="h-12 w-12 rounded-lg" />
            <div className="flex-1">
              <Skeleton className="h-5 w-48 mb-2" />
              <Skeleton className="h-4 w-32" />
            </div>
            <Skeleton className="h-5 w-20" />
          </div>
        ))}
      </div>
    )
  }

  const products = profitabilityData?.products || []

  if (products.length === 0) {
    return (
      <div className="py-12 text-center">
        <Package className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
        <h3 className="text-lg font-medium mb-2">No Products Available</h3>
        <p className="text-muted-foreground">
          Unable to load P4 product profitability data.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      <p className="text-sm text-muted-foreground mb-4">
        Select a P4 product to produce. Products are sorted by monthly profit.
      </p>
      <div className="space-y-2 max-h-[400px] overflow-y-auto pr-2">
        {products.map((product) => {
          const isSelected = selectedProduct?.type_id === product.type_id
          return (
            <button
              key={product.type_id}
              onClick={() => onSelect(product)}
              className={cn(
                'w-full flex items-center gap-4 p-4 rounded-lg border transition-colors text-left',
                isSelected
                  ? 'border-primary bg-primary/10'
                  : 'border-border bg-secondary/30 hover:bg-secondary/50 hover:border-border/80'
              )}
            >
              <img
                src={getItemIconUrl(product.type_id, 64)}
                alt={product.type_name}
                className="w-12 h-12 rounded-lg border border-border"
                onError={(e: React.SyntheticEvent<HTMLImageElement>) => {
                  e.currentTarget.style.display = 'none'
                }}
              />
              <div className="flex-1">
                <div className="font-medium">{product.type_name}</div>
                <div className="flex items-center gap-4 text-sm text-muted-foreground">
                  <span>Tier {product.tier}</span>
                  <span>{product.p0_count} P0 inputs</span>
                  <span
                    className={cn(
                      'px-2 py-0.5 rounded text-xs',
                      product.complexity === 'low' && 'bg-green-500/20 text-green-400',
                      product.complexity === 'medium' && 'bg-yellow-500/20 text-yellow-400',
                      product.complexity === 'high' && 'bg-red-500/20 text-red-400'
                    )}
                  >
                    {product.complexity} complexity
                  </span>
                </div>
              </div>
              <div className="text-right">
                <div className="font-medium text-green-400">
                  {formatISK(product.monthly_profit)}/mo
                </div>
                <div className="text-sm text-muted-foreground">
                  {product.roi_percent.toFixed(1)}% ROI
                </div>
              </div>
              {isSelected && (
                <Check className="h-5 w-5 text-primary" />
              )}
            </button>
          )
        })}
      </div>
    </div>
  )
}

/**
 * Step 2: Configure Plan
 */
function ConfigureStep({
  config,
  onChange,
}: {
  config: {
    name: string
    totalPlanets: number
    pocoTaxRate: number
  }
  onChange: (updates: Partial<typeof config>) => void
}) {
  return (
    <div className="space-y-6">
      <p className="text-sm text-muted-foreground mb-4">
        Configure your empire plan settings.
      </p>

      {/* Plan Name */}
      <div className="space-y-2">
        <label htmlFor="plan-name" className="text-sm font-medium">
          Plan Name
        </label>
        <Input
          id="plan-name"
          value={config.name}
          onChange={(e) => onChange({ name: e.target.value })}
          placeholder="Enter a name for your plan"
          className="w-full"
        />
        <p className="text-xs text-muted-foreground">
          Give your plan a descriptive name to identify it later.
        </p>
      </div>

      {/* Total Planets */}
      <div className="space-y-2">
        <label htmlFor="total-planets" className="text-sm font-medium">
          Total Planets
        </label>
        <Input
          id="total-planets"
          type="number"
          min={1}
          max={30}
          value={config.totalPlanets}
          onChange={(e) => onChange({ totalPlanets: parseInt(e.target.value) || 1 })}
          className="w-full"
        />
        <p className="text-xs text-muted-foreground">
          Total number of planets across all characters (1-30). Each character can have up to 6 planets.
        </p>
      </div>

      {/* POCO Tax Rate */}
      <div className="space-y-2">
        <label htmlFor="poco-tax" className="text-sm font-medium">
          POCO Tax Rate (%)
        </label>
        <Input
          id="poco-tax"
          type="number"
          min={0}
          max={100}
          step={0.5}
          value={config.pocoTaxRate}
          onChange={(e) => onChange({ pocoTaxRate: parseFloat(e.target.value) || 0 })}
          className="w-full"
        />
        <p className="text-xs text-muted-foreground">
          Player-Owned Customs Office tax rate. Affects import/export costs.
        </p>
      </div>

      {/* Configuration Summary */}
      <Card className="bg-secondary/30">
        <CardContent className="p-4">
          <div className="text-sm font-medium mb-2">Configuration Summary</div>
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div className="text-muted-foreground">Characters Needed:</div>
            <div>{Math.ceil(config.totalPlanets / 6)}</div>
            <div className="text-muted-foreground">Planets per Character:</div>
            <div>{Math.min(config.totalPlanets, 6)}</div>
            <div className="text-muted-foreground">Effective Tax:</div>
            <div>{config.pocoTaxRate}%</div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

/**
 * Step 3: Confirm and Create
 */
function ConfirmStep({
  selectedProduct,
  config,
}: {
  selectedProduct: P4EmpireProfitability
  config: {
    name: string
    totalPlanets: number
    pocoTaxRate: number
  }
}) {
  return (
    <div className="space-y-6">
      <p className="text-sm text-muted-foreground mb-4">
        Review your plan configuration before creating.
      </p>

      {/* Product Summary */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-lg">Target Product</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-4">
            <img
              src={getItemIconUrl(selectedProduct.type_id, 64)}
              alt={selectedProduct.type_name}
              className="w-16 h-16 rounded-lg border border-border"
              onError={(e: React.SyntheticEvent<HTMLImageElement>) => {
                e.currentTarget.style.display = 'none'
              }}
            />
            <div className="flex-1">
              <div className="text-lg font-medium">{selectedProduct.type_name}</div>
              <div className="flex items-center gap-4 text-sm text-muted-foreground">
                <span>Tier {selectedProduct.tier}</span>
                <span>{selectedProduct.p0_count} P0 inputs</span>
                <span
                  className={cn(
                    'px-2 py-0.5 rounded text-xs',
                    selectedProduct.complexity === 'low' && 'bg-green-500/20 text-green-400',
                    selectedProduct.complexity === 'medium' && 'bg-yellow-500/20 text-yellow-400',
                    selectedProduct.complexity === 'high' && 'bg-red-500/20 text-red-400'
                  )}
                >
                  {selectedProduct.complexity} complexity
                </span>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Plan Configuration */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-lg">Plan Configuration</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="text-sm text-muted-foreground">Plan Name</div>
              <div className="font-medium">{config.name || '(Not set)'}</div>
            </div>
            <div>
              <div className="text-sm text-muted-foreground">Total Planets</div>
              <div className="font-medium">{config.totalPlanets}</div>
            </div>
            <div>
              <div className="text-sm text-muted-foreground">Characters Needed</div>
              <div className="font-medium">{Math.ceil(config.totalPlanets / 6)}</div>
            </div>
            <div>
              <div className="text-sm text-muted-foreground">POCO Tax Rate</div>
              <div className="font-medium">{config.pocoTaxRate}%</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Estimated Profits */}
      <Card className="border-green-500/30 bg-green-500/5">
        <CardHeader className="pb-2">
          <CardTitle className="text-lg text-green-400">Estimated Profits</CardTitle>
          <CardDescription>Based on current market prices</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="text-sm text-muted-foreground">Monthly Revenue</div>
              <div className="text-xl font-medium">
                {formatISK(selectedProduct.monthly_revenue)}
              </div>
            </div>
            <div>
              <div className="text-sm text-muted-foreground">Monthly Profit</div>
              <div className="text-xl font-medium text-green-400">
                {formatISK(selectedProduct.monthly_profit)}
              </div>
            </div>
            <div>
              <div className="text-sm text-muted-foreground">Profit per Planet</div>
              <div className="font-medium">
                {formatISK(selectedProduct.profit_per_planet)}
              </div>
            </div>
            <div>
              <div className="text-sm text-muted-foreground">ROI</div>
              <div className="font-medium">{selectedProduct.roi_percent.toFixed(1)}%</div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

/**
 * Main PI Empire Plan Wizard Page
 */
function PIEmpirePlanWizard() {
  const navigate = useNavigate()
  const [currentStep, setCurrentStep] = useState<WizardStep>(1)
  const [selectedProduct, setSelectedProduct] = useState<P4EmpireProfitability | null>(null)
  const [config, setConfig] = useState({
    name: '',
    totalPlanets: 6,
    pocoTaxRate: 10,
  })

  // Create mutation
  const createMutation = useMutation({
    mutationFn: (plan: EmpirePlanCreate) => piApi.createEmpirePlan(plan),
    onSuccess: (data) => {
      navigate(`/pi/empire/plans/${data.plan_id}`)
    },
  })

  const handleNext = () => {
    if (currentStep === 1 && selectedProduct) {
      // Auto-populate plan name from product
      if (!config.name) {
        setConfig((prev) => ({
          ...prev,
          name: `${selectedProduct.type_name} Empire`,
        }))
      }
      setCurrentStep(2)
    } else if (currentStep === 2 && config.name && config.totalPlanets > 0) {
      setCurrentStep(3)
    } else if (currentStep === 3 && selectedProduct) {
      // Create the plan
      createMutation.mutate({
        name: config.name,
        target_product_id: selectedProduct.type_id,
        target_product_name: selectedProduct.type_name,
        total_planets: config.totalPlanets,
        poco_tax_rate: config.pocoTaxRate,
      })
    }
  }

  const handleBack = () => {
    if (currentStep > 1) {
      setCurrentStep((prev) => (prev - 1) as WizardStep)
    }
  }

  const canProceed =
    (currentStep === 1 && selectedProduct !== null) ||
    (currentStep === 2 && config.name.trim() !== '' && config.totalPlanets > 0) ||
    (currentStep === 3 && selectedProduct !== null)

  return (
    <div>
      <Header title="New Empire Plan" subtitle="Create a multi-character PI production plan" />

      <div className="p-6 space-y-6 max-w-3xl mx-auto">
        {/* Back link */}
        <Link
          to="/pi/empire/plans"
          className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Plans
        </Link>

        {/* Step indicator */}
        <StepIndicator
          currentStep={currentStep}
          onStepClick={(step) => {
            if (step < currentStep) setCurrentStep(step)
          }}
        />

        {/* Step content */}
        <Card>
          <CardHeader>
            <CardTitle>
              {currentStep === 1 && 'Select Target Product'}
              {currentStep === 2 && 'Configure Plan'}
              {currentStep === 3 && 'Review & Create'}
            </CardTitle>
            <CardDescription>
              {currentStep === 1 && 'Choose a P4 product to produce in your empire'}
              {currentStep === 2 && 'Set up your plan parameters'}
              {currentStep === 3 && 'Confirm your plan details'}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {currentStep === 1 && (
              <SelectProductStep
                selectedProduct={selectedProduct}
                onSelect={setSelectedProduct}
              />
            )}
            {currentStep === 2 && (
              <ConfigureStep
                config={config}
                onChange={(updates) => setConfig((prev) => ({ ...prev, ...updates }))}
              />
            )}
            {currentStep === 3 && selectedProduct && (
              <ConfirmStep selectedProduct={selectedProduct} config={config} />
            )}
          </CardContent>
        </Card>

        {/* Navigation buttons */}
        <div className="flex items-center justify-between">
          <button
            onClick={handleBack}
            disabled={currentStep === 1}
            className={cn(
              'flex items-center gap-2 px-4 py-2 rounded-lg text-sm transition-colors',
              currentStep === 1
                ? 'text-muted-foreground cursor-not-allowed'
                : 'bg-secondary hover:bg-secondary/80'
            )}
          >
            <ArrowLeft className="h-4 w-4" />
            Back
          </button>

          <button
            onClick={handleNext}
            disabled={!canProceed || createMutation.isPending}
            className={cn(
              'flex items-center gap-2 px-4 py-2 rounded-lg text-sm transition-colors',
              canProceed && !createMutation.isPending
                ? 'bg-primary text-primary-foreground hover:bg-primary/90'
                : 'bg-secondary text-muted-foreground cursor-not-allowed'
            )}
          >
            {createMutation.isPending ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Creating...
              </>
            ) : currentStep === 3 ? (
              <>
                <Check className="h-4 w-4" />
                Create Plan
              </>
            ) : (
              <>
                Next
                <ArrowRight className="h-4 w-4" />
              </>
            )}
          </button>
        </div>

        {/* Error message */}
        {createMutation.isError && (
          <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
            Failed to create plan. Please try again.
          </div>
        )}
      </div>
    </div>
  )
}

export default PIEmpirePlanWizard
export { PIEmpirePlanWizard }
