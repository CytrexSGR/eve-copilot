// unified-frontend/src/api/market.ts

import { apiClient } from './client'
import type {
  WalletJournal,
  WalletTransactions,
  UndercutReport,
  HeatmapResponse,
  PortfolioHistory,
  NotificationSettings,
  TradingPnLReport,
  MarginAlert,
  TradingSummary,
  VelocityReport,
  CompetitionReport,
  AlertsResponse,
  AlertConfig,
  GoalsResponse,
  TradingGoal,
  RiskSummary,
  ConcentrationRisk,
  LiquidityRisk,
  TradingHistory,
  AggregatedOrdersResponse,
  TradingOpportunitiesResponse,
  ArbitrageRoutesResponse,
  TradingOpportunitiesV2Response,
  SimulationResult,
  AllocationRequest,
  AllocationResult,
} from '@/types/market'

export const marketApi = {
  // Wallet Journal
  getWalletJournal: async (characterId: number, page = 1): Promise<WalletJournal> => {
    const response = await apiClient.get<WalletJournal>(
      `/character/${characterId}/wallet/journal`,
      { params: { page } }
    )
    return response.data
  },

  // Wallet Transactions
  getWalletTransactions: async (
    characterId: number,
    fromId?: number
  ): Promise<WalletTransactions> => {
    const response = await apiClient.get<WalletTransactions>(
      `/character/${characterId}/wallet/transactions`,
      { params: fromId ? { from_id: fromId } : undefined }
    )
    return response.data
  },

  // Orders with undercut status
  getOrderUndercuts: async (characterId: number): Promise<UndercutReport> => {
    const response = await apiClient.get<UndercutReport>(
      `/character/${characterId}/orders/undercuts`
    )
    return response.data
  },

  // Price Heatmap
  getPriceHeatmap: async (typeIds: number[]): Promise<HeatmapResponse> => {
    const response = await apiClient.get<HeatmapResponse>('/market/heatmap', {
      params: { type_ids: typeIds.join(',') },
    })
    return response.data
  },

  getCategoryHeatmap: async (
    categoryId: number,
    limit = 20
  ): Promise<HeatmapResponse> => {
    const response = await apiClient.get<HeatmapResponse>(
      `/market/heatmap/category/${categoryId}`,
      { params: { limit } }
    )
    return response.data
  },

  getPortfolioHeatmap: async (
    characterId: number,
    limit = 20
  ): Promise<HeatmapResponse> => {
    const response = await apiClient.get<HeatmapResponse>(
      `/market/heatmap/portfolio/${characterId}`,
      { params: { limit } }
    )
    return response.data
  },

  // Portfolio History
  getPortfolioHistory: async (
    characterId: number,
    days = 30
  ): Promise<PortfolioHistory> => {
    const response = await apiClient.get<PortfolioHistory>(
      `/portfolio/${characterId}/history`,
      { params: { days } }
    )
    return response.data
  },

  // Notification Settings
  getNotificationSettings: async (): Promise<NotificationSettings> => {
    const response = await apiClient.get<NotificationSettings>(
      '/settings/notifications'
    )
    return response.data
  },

  updateNotificationSettings: async (
    settings: Partial<NotificationSettings>
  ): Promise<NotificationSettings> => {
    const response = await apiClient.put<NotificationSettings>(
      '/settings/notifications',
      settings
    )
    return response.data
  },

  testNotification: async (): Promise<{ success: boolean; message: string }> => {
    const response = await apiClient.post<{ success: boolean; message: string }>(
      '/settings/notifications/test'
    )
    return response.data
  },

  // Trading Analytics

  /**
   * Get P&L report for character's trading activity
   */
  getTradingPnL: async (
    characterId: number,
    options?: { includeCorp?: boolean; days?: number }
  ): Promise<TradingPnLReport> => {
    const response = await apiClient.get<TradingPnLReport>(
      `/trading/${characterId}/pnl`,
      {
        params: {
          include_corp: options?.includeCorp ?? true,
          days: options?.days ?? 30,
        },
      }
    )
    return response.data
  },

  /**
   * Get margin alerts for items with low or negative margins
   */
  getMarginAlerts: async (
    characterId: number,
    threshold = 10.0
  ): Promise<MarginAlert[]> => {
    const response = await apiClient.get<MarginAlert[]>(
      `/trading/${characterId}/margin-alerts`,
      { params: { threshold } }
    )
    return response.data
  },

  /**
   * Get quick trading summary for dashboard
   */
  getTradingSummary: async (
    characterId: number,
    includeCorp = true
  ): Promise<TradingSummary> => {
    const response = await apiClient.get<TradingSummary>(
      `/trading/${characterId}/summary`,
      { params: { include_corp: includeCorp } }
    )
    return response.data
  },

  /**
   * Get velocity analysis for traded items
   * Classifies items as fast movers, slow movers, or dead stock
   */
  getVelocityReport: async (
    characterId: number,
    includeCorp = true
  ): Promise<VelocityReport> => {
    const response = await apiClient.get<VelocityReport>(
      `/trading/${characterId}/velocity`,
      { params: { include_corp: includeCorp } }
    )
    return response.data
  },

  /**
   * Get competition analysis for active orders
   * Shows position vs competitors and price gaps
   */
  getCompetitionReport: async (
    characterId: number,
    includeCorp = true
  ): Promise<CompetitionReport> => {
    const response = await apiClient.get<CompetitionReport>(
      `/trading/${characterId}/competition`,
      { params: { include_corp: includeCorp } }
    )
    return response.data
  },

  // Trading Alerts

  /**
   * Get trading alerts for a character
   */
  getAlerts: async (
    characterId: number,
    options?: { limit?: number; unreadOnly?: boolean; alertType?: string }
  ): Promise<AlertsResponse> => {
    const response = await apiClient.get<AlertsResponse>(
      `/alerts/${characterId}`,
      {
        params: {
          limit: options?.limit ?? 50,
          unread_only: options?.unreadOnly ?? false,
          alert_type: options?.alertType,
        },
      }
    )
    return response.data
  },

  /**
   * Mark alerts as read
   */
  markAlertsRead: async (
    characterId: number,
    alertIds?: number[]
  ): Promise<{ marked_count: number }> => {
    const response = await apiClient.post<{ marked_count: number }>(
      `/alerts/${characterId}/mark-read`,
      alertIds ?? null
    )
    return response.data
  },

  /**
   * Get alert configuration
   */
  getAlertConfig: async (characterId: number): Promise<AlertConfig> => {
    const response = await apiClient.get<AlertConfig>(
      `/alerts/${characterId}/config`
    )
    return response.data
  },

  /**
   * Update alert configuration
   */
  updateAlertConfig: async (
    characterId: number,
    config: Partial<AlertConfig>
  ): Promise<AlertConfig> => {
    const response = await apiClient.put<AlertConfig>(
      `/alerts/${characterId}/config`,
      config
    )
    return response.data
  },

  /**
   * Test Discord webhook by sending a test message
   */
  testDiscordWebhook: async (
    characterId: number
  ): Promise<{ success: boolean; message: string }> => {
    const response = await apiClient.post<{ success: boolean; message: string }>(
      `/alerts/${characterId}/test-discord`
    )
    return response.data
  },

  // Trading Goals

  /**
   * Get trading goals with progress
   */
  getGoals: async (
    characterId: number,
    options?: { activeOnly?: boolean; goalType?: string }
  ): Promise<GoalsResponse> => {
    const response = await apiClient.get<GoalsResponse>(
      `/goals/${characterId}`,
      {
        params: {
          active_only: options?.activeOnly ?? true,
          goal_type: options?.goalType,
        },
      }
    )
    return response.data
  },

  /**
   * Create a new trading goal
   */
  createGoal: async (
    characterId: number,
    goal: {
      goal_type: 'daily' | 'weekly' | 'monthly'
      target_type: 'profit' | 'volume' | 'trades' | 'roi'
      target_value: number
      type_id?: number
      type_name?: string
      notify_on_progress?: boolean
      notify_on_completion?: boolean
    }
  ): Promise<TradingGoal> => {
    const response = await apiClient.post<TradingGoal>(
      `/goals/${characterId}`,
      goal
    )
    return response.data
  },

  /**
   * Delete a trading goal
   */
  deleteGoal: async (
    characterId: number,
    goalId: number
  ): Promise<{ deleted: boolean }> => {
    const response = await apiClient.delete<{ deleted: boolean }>(
      `/goals/${characterId}/${goalId}`
    )
    return response.data
  },

  /**
   * Deactivate a trading goal
   */
  deactivateGoal: async (
    characterId: number,
    goalId: number
  ): Promise<{ deactivated: boolean }> => {
    const response = await apiClient.post<{ deactivated: boolean }>(
      `/goals/${characterId}/${goalId}/deactivate`
    )
    return response.data
  },

  // Risk Management

  /**
   * Get comprehensive risk summary for portfolio
   */
  getRiskSummary: async (
    characterId: number,
    options?: { includeCorp?: boolean; concentrationThreshold?: number; liquidityThreshold?: number }
  ): Promise<RiskSummary> => {
    const response = await apiClient.get<RiskSummary>(
      `/risk/${characterId}/summary`,
      {
        params: {
          include_corp: options?.includeCorp ?? true,
          concentration_threshold: options?.concentrationThreshold ?? 10,
          liquidity_threshold: options?.liquidityThreshold ?? 7,
        },
      }
    )
    return response.data
  },

  /**
   * Get detailed concentration analysis
   */
  getConcentrationDetails: async (
    characterId: number,
    includeCorp = true
  ): Promise<ConcentrationRisk[]> => {
    const response = await apiClient.get<ConcentrationRisk[]>(
      `/risk/${characterId}/concentration`,
      { params: { include_corp: includeCorp } }
    )
    return response.data
  },

  /**
   * Get detailed liquidity analysis
   */
  getLiquidityDetails: async (
    characterId: number,
    includeCorp = true
  ): Promise<LiquidityRisk[]> => {
    const response = await apiClient.get<LiquidityRisk[]>(
      `/risk/${characterId}/liquidity`,
      { params: { include_corp: includeCorp } }
    )
    return response.data
  },

  // Trading History

  /**
   * Get comprehensive trading history with pattern analysis
   */
  getTradingHistory: async (
    characterId: number,
    options?: { days?: number; includeCorp?: boolean }
  ): Promise<TradingHistory> => {
    const response = await apiClient.get<TradingHistory>(
      `/history/${characterId}`,
      {
        params: {
          days: options?.days ?? 30,
          include_corp: options?.includeCorp ?? true,
        },
      }
    )
    return response.data
  },

  // ============================================
  // Multi-Account Orders
  // ============================================

  /**
   * Get aggregated orders across all characters
   */
  getAggregatedOrders: async (
    characterIds?: number[],
    orderType?: 'buy' | 'sell'
  ): Promise<AggregatedOrdersResponse> => {
    const params = new URLSearchParams()
    if (characterIds?.length) {
      characterIds.forEach(id => params.append('character_ids', id.toString()))
    }
    if (orderType) {
      params.set('order_type', orderType)
    }
    const response = await apiClient.get<AggregatedOrdersResponse>(
      `/orders/aggregated?${params.toString()}`
    )
    return response.data
  },

  // ============================================
  // Station Trading
  // ============================================

  /**
   * Get station trading opportunities in a region
   */
  getTradingOpportunities: async (
    regionId: number = 10000002,
    options?: {
      minMarginPercent?: number
      minDailyVolume?: number
      minProfitPerTrade?: number
      maxCapitalRequired?: number
      limit?: number
    }
  ): Promise<TradingOpportunitiesResponse> => {
    const response = await apiClient.get<TradingOpportunitiesResponse>(
      '/trading/opportunities',
      {
        params: {
          region_id: regionId,
          min_margin_percent: options?.minMarginPercent ?? 5.0,
          min_daily_volume: options?.minDailyVolume ?? 100,
          min_profit_per_trade: options?.minProfitPerTrade ?? 1000000,
          max_capital_required: options?.maxCapitalRequired,
          limit: options?.limit ?? 50,
        },
      }
    )
    return response.data
  },

  // ============================================
  // Arbitrage Routes
  // ============================================

  /**
   * Get profitable arbitrage routes from a starting region
   */
  getArbitrageRoutes: async (
    startRegion: number = 10000002,
    options?: {
      maxJumps?: number
      minProfitPerTrip?: number
      cargoCapacity?: number
      collateralLimit?: number
      // V2 filters
      turnover?: string
      maxCompetition?: string
      maxDaysToSell?: number
      minVolume?: number
    }
  ): Promise<ArbitrageRoutesResponse> => {
    const response = await apiClient.get<ArbitrageRoutesResponse>(
      '/market/routes',
      {
        params: {
          start_region: startRegion,
          max_jumps: options?.maxJumps ?? 15,
          min_profit_per_trip: options?.minProfitPerTrip ?? 10000000,
          cargo_capacity: options?.cargoCapacity ?? 60000,
          collateral_limit: options?.collateralLimit,
          // V2 filters
          turnover: options?.turnover || undefined,
          max_competition: options?.maxCompetition || undefined,
          max_days_to_sell: options?.maxDaysToSell || undefined,
          min_volume: options?.minVolume || undefined,
        },
      }
    )
    return response.data
  },

  // ============================================
  // Station Trading V2
  // ============================================

  /**
   * Get trading opportunities with MER categories and risk metrics
   */
  getTradingOpportunitiesV2: async (
    regionId: number = 10000002,
    options?: {
      primaryIndex?: string
      subIndices?: string[]
      minCapital?: number
      maxCapital?: number
      minVolume?: number
      maxDaysToSell?: number
      minMargin?: number
      turnover?: string  // 'instant', 'fast', 'moderate', 'slow'
      maxCompetition?: string  // 'low', 'medium', 'high', 'extreme'
      sortBy?: 'daily_potential' | 'margin' | 'profit_per_unit' | 'days_to_sell' | 'risk_score' | 'volume'
      limit?: number
    }
  ): Promise<TradingOpportunitiesV2Response> => {
    const params = new URLSearchParams()
    params.set('region_id', regionId.toString())

    if (options?.primaryIndex) params.set('primary_index', options.primaryIndex)
    if (options?.subIndices?.length) params.set('sub_indices', options.subIndices.join(','))
    if (options?.minCapital) params.set('min_capital', options.minCapital.toString())
    if (options?.maxCapital) params.set('max_capital', options.maxCapital.toString())
    if (options?.minVolume !== undefined) params.set('min_volume', options.minVolume.toString())
    if (options?.maxDaysToSell) params.set('max_days_to_sell', options.maxDaysToSell.toString())
    if (options?.minMargin) params.set('min_margin', options.minMargin.toString())
    if (options?.turnover) params.set('turnover', options.turnover)
    if (options?.maxCompetition) params.set('max_competition', options.maxCompetition)
    if (options?.sortBy) params.set('sort_by', options.sortBy)
    if (options?.limit) params.set('limit', options.limit.toString())

    const response = await apiClient.get<TradingOpportunitiesV2Response>(
      `/trading/opportunities/v2?${params.toString()}`
    )
    return response.data
  },

  /**
   * Simulate investment in a specific item
   */
  simulateInvestment: async (
    typeId: number,
    investment: number,
    regionId: number = 10000002
  ): Promise<SimulationResult> => {
    const response = await apiClient.get<SimulationResult>(
      `/trading/simulate`,
      {
        params: {
          type_id: typeId,
          region_id: regionId,
          investment
        }
      }
    )
    return response.data
  },

  /**
   * Allocate capital across multiple items
   */
  allocateCapital: async (
    request: AllocationRequest
  ): Promise<AllocationResult> => {
    const response = await apiClient.post<AllocationResult>(
      `/trading/allocate`,
      request
    )
    return response.data
  },
}
