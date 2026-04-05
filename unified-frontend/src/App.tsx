import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { lazy } from 'react'
import { Layout } from '@/components/layout/Layout'
import { CharacterProvider } from '@/contexts/CharacterContext'
import { AccountGroupProvider } from '@/contexts/AccountGroupContext'
import { SettingsProvider } from '@/contexts/SettingsContext'
import { CopilotProvider } from '@/contexts/CopilotContext'
import { Dashboard } from '@/pages/Dashboard'
import { CharacterDetail } from '@/pages/CharacterDetail'
import { Assets } from '@/pages/Assets'
import { Industry } from '@/pages/Industry'
import { BlueprintBrowser } from '@/pages/BlueprintBrowser'
import { ManufacturingOpportunities } from '@/pages/ManufacturingOpportunities'
import { PlanetaryIndustry } from '@/pages/PlanetaryIndustry'
import { PIColonyDetail } from '@/pages/PIColonyDetail'
import { PIProfitability } from '@/pages/PIProfitability'
import { PIProductionChain } from '@/pages/PIProductionChain'
import { PIMakeOrBuy } from '@/pages/PIMakeOrBuy'
import { PIProjects } from '@/pages/PIProjects'
import { PIProjectDetail } from '@/pages/PIProjectDetail'
const PIEmpireDashboard = lazy(() => import('./pages/PIEmpireDashboard'))
const PIEmpirePlans = lazy(() => import('./pages/PIEmpirePlans'))
const PIEmpirePlanWizard = lazy(() => import('./pages/PIEmpirePlanWizard'))
const PIEmpirePlanDetail = lazy(() => import('./pages/PIEmpirePlanDetail'))
const PIPlanetFinder = lazy(() => import('./pages/PIPlanetFinder'))
const PIEmpireOverview = lazy(() => import('./pages/PIEmpireOverview'))
const ReactionsBrowser = lazy(() => import('./pages/ReactionsBrowser'))
const ReactionDetail = lazy(() => import('./pages/ReactionDetail'))
const FittingsBrowser = lazy(() => import('./pages/FittingsBrowser'))
const FittingDetail = lazy(() => import('./pages/FittingDetail'))
const FittingEditor = lazy(() => import('./pages/FittingEditor'))
const CapitalDashboard = lazy(() => import('./pages/CapitalDashboard'))
const SubscriptionDashboard = lazy(() => import('./pages/admin/SubscriptionDashboard'))
const SubscriptionProducts = lazy(() => import('./pages/admin/SubscriptionProducts'))
const SubscriptionPayments = lazy(() => import('./pages/admin/SubscriptionPayments'))
const SubscriptionConfig = lazy(() => import('./pages/admin/SubscriptionConfig'))
const MultiAccountOrders = lazy(() => import('./pages/market/MultiAccountOrders'))
const StationTradingV2 = lazy(() => import('./pages/market/StationTradingV2'))
const ArbitragePlanner = lazy(() => import('./pages/market/ArbitragePlanner'))
import { MarketDashboard } from '@/pages/market/MarketDashboard'
import { MarketOrders } from '@/pages/market/MarketOrders'
import { Transactions } from '@/pages/market/Transactions'
import { ProfitLoss } from '@/pages/market/ProfitLoss'
import { VelocityAnalysis } from '@/pages/market/VelocityAnalysis'
import { CompetitionTracker } from '@/pages/market/CompetitionTracker'
import { TradingAlerts } from '@/pages/market/TradingAlerts'
import TradingGoals from '@/pages/market/TradingGoals'
import RiskManagement from '@/pages/market/RiskManagement'
import TradingHistoryPage from '@/pages/market/TradingHistory'
import { PriceHeatmap } from '@/pages/market/PriceHeatmap'
import { Settings } from '@/pages/Settings'
import { SkillBrowser } from '@/pages/SkillBrowser'
import { SkillQueue } from '@/pages/SkillQueue'
import { ShipMastery } from '@/pages/ShipMastery'
import { SkillPlanner } from '@/pages/SkillPlanner'
import Copilot from '@/pages/Copilot'
import { AuthCallback } from '@/pages/AuthCallback'
import { FloatingWidget } from '@/components/copilot/FloatingWidget'
import { CommandPalette } from '@/components/shared/CommandPalette'

function App() {
  return (
    <BrowserRouter>
      <SettingsProvider>
        <CharacterProvider>
          <AccountGroupProvider>
            <CopilotProvider>
            <Routes>
            {/* Auth callback route - outside layout */}
            <Route path="/auth/callback" element={<AuthCallback />} />
            <Route element={<Layout />}>
              <Route path="/" element={<Dashboard />} />
              <Route path="/characters" element={<Dashboard />} />
              <Route path="/character/:characterId" element={<CharacterDetail />} />
              <Route path="/assets" element={<Assets />} />
              <Route path="/industry" element={<Industry />} />
              <Route path="/blueprints" element={<BlueprintBrowser />} />
              <Route path="/opportunities" element={<ManufacturingOpportunities />} />
              <Route path="/pi" element={<PlanetaryIndustry />} />
              <Route path="/pi/colony/:characterId/:planetId" element={<PIColonyDetail />} />
              <Route path="/pi/profitability" element={<PIProfitability />} />
              <Route path="/pi/chain/:typeId" element={<PIProductionChain />} />
              <Route path="/pi/make-or-buy" element={<PIMakeOrBuy />} />
              <Route path="/pi/projects" element={<PIProjects />} />
              <Route path="/pi/projects/:projectId" element={<PIProjectDetail />} />
              <Route path="/pi/empire" element={<PIEmpireDashboard />} />
              <Route path="/pi/empire/plans" element={<PIEmpirePlans />} />
              <Route path="/pi/empire/plans/new" element={<PIEmpirePlanWizard />} />
              <Route path="/pi/empire/plans/:planId" element={<PIEmpirePlanDetail />} />
              <Route path="/pi/planets/finder" element={<PIPlanetFinder />} />
              <Route path="/pi/empire/overview" element={<PIEmpireOverview />} />
              <Route path="/reactions" element={<ReactionsBrowser />} />
              <Route path="/reactions/:reactionTypeId" element={<ReactionDetail />} />
              <Route path="/capital" element={<CapitalDashboard />} />
              <Route path="/market" element={<MarketDashboard />} />
              <Route path="/market/orders" element={<MultiAccountOrders />} />
              <Route path="/market/transactions" element={<Transactions />} />
              <Route path="/market/pnl" element={<ProfitLoss />} />
              <Route path="/market/velocity" element={<VelocityAnalysis />} />
              <Route path="/market/competition" element={<CompetitionTracker />} />
              <Route path="/market/alerts" element={<TradingAlerts />} />
              <Route path="/market/goals" element={<TradingGoals />} />
              <Route path="/market/risk" element={<RiskManagement />} />
              <Route path="/market/history" element={<TradingHistoryPage />} />
              <Route path="/market/prices" element={<PriceHeatmap />} />
              <Route path="/market/multi-account" element={<MultiAccountOrders />} />
              <Route path="/market/station-trading" element={<Navigate to="/market/station-trading-v2" replace />} />
              <Route path="/market/station-trading-v2" element={<StationTradingV2 />} />
              <Route path="/market/arbitrage" element={<ArbitragePlanner />} />
              <Route path="/settings" element={<Settings />} />
              <Route path="/fittings" element={<FittingsBrowser />} />
              <Route path="/fittings/new" element={<FittingEditor />} />
              <Route path="/fittings/esi/:fittingId" element={<FittingDetail />} />
              <Route path="/fittings/custom/:fittingId" element={<FittingDetail />} />
              <Route path="/skills" element={<SkillBrowser />} />
              <Route path="/skills/queue" element={<SkillQueue />} />
              <Route path="/skills/mastery" element={<ShipMastery />} />
              <Route path="/skills/planner" element={<SkillPlanner />} />
              <Route path="/copilot" element={<Copilot />} />
              {/* Admin Routes */}
              <Route path="/admin/subscriptions" element={<SubscriptionDashboard />} />
              <Route path="/admin/subscriptions/products" element={<SubscriptionProducts />} />
              <Route path="/admin/subscriptions/payments" element={<SubscriptionPayments />} />
              <Route path="/admin/subscriptions/config" element={<SubscriptionConfig />} />
            </Route>
          </Routes>
            <FloatingWidget />
              <CommandPalette />
            </CopilotProvider>
          </AccountGroupProvider>
        </CharacterProvider>
      </SettingsProvider>
    </BrowserRouter>
  )
}

export default App
