import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  getReactions,
  getReactionById,
  getReactionProfitability,
  getProfitableReactions
} from '../reactions'

// Mock axios
vi.mock('axios', () => ({
  default: {
    create: () => ({
      get: vi.fn(),
      interceptors: {
        response: { use: vi.fn() }
      }
    })
  }
}))

// Mock apiClient
vi.mock('../client', () => ({
  apiClient: {
    get: vi.fn()
  }
}))

import { apiClient } from '../client'

describe('reactions API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('fetches all reactions', async () => {
    const mockReactions = [{ reaction_type_id: 1, reaction_name: 'Test Reaction' }]
    vi.mocked(apiClient.get).mockResolvedValue({ data: mockReactions })

    const result = await getReactions()
    expect(result).toHaveLength(1)
    expect(result[0].reaction_name).toBe('Test Reaction')
    expect(apiClient.get).toHaveBeenCalledWith('/reactions', { params: {} })
  })

  it('fetches reactions filtered by type', async () => {
    const mockReactions = [{ reaction_type_id: 2, reaction_name: 'Complex Reaction', reaction_category: 'complex' }]
    vi.mocked(apiClient.get).mockResolvedValue({ data: mockReactions })

    const result = await getReactions('complex')
    expect(result).toHaveLength(1)
    expect(apiClient.get).toHaveBeenCalledWith('/reactions', { params: { reaction_type: 'complex' } })
  })

  it('fetches reaction profitability', async () => {
    const mockProfitability = {
      reaction_type_id: 1,
      reaction_name: 'Test Reaction',
      product_name: 'Test Product',
      input_cost: 1000000,
      output_value: 2000000,
      profit_per_run: 1000000,
      profit_per_hour: 1000000,
      roi_percent: 15.5,
      reaction_time: 3600,
      runs_per_hour: 1.0
    }
    vi.mocked(apiClient.get).mockResolvedValue({ data: mockProfitability })

    const result = await getReactionProfitability(1)
    expect(result.profit_per_hour).toBe(1000000)
    expect(result.roi_percent).toBe(15.5)
    expect(apiClient.get).toHaveBeenCalledWith('/reactions/1/profit', {
      params: { region_id: 10000002 }
    })
  })

  it('fetches reaction profitability with custom region', async () => {
    const mockProfitability = {
      reaction_type_id: 1,
      reaction_name: 'Test Reaction',
      product_name: 'Test Product',
      input_cost: 1000000,
      output_value: 1800000,
      profit_per_run: 800000,
      profit_per_hour: 800000,
      roi_percent: 12.0,
      reaction_time: 3600,
      runs_per_hour: 1.0
    }
    vi.mocked(apiClient.get).mockResolvedValue({ data: mockProfitability })

    await getReactionProfitability(1, 10000043)
    expect(apiClient.get).toHaveBeenCalledWith('/reactions/1/profit', {
      params: { region_id: 10000043 }
    })
  })

  it('fetches reaction by ID', async () => {
    const mockReaction = {
      reaction_type_id: 42,
      reaction_name: 'Ferrofluid Reaction',
      product_type_id: 16670,
      product_name: 'Ferrofluid',
      product_quantity: 200,
      reaction_time: 3600,
      reaction_category: 'simple',
      inputs: [
        { input_type_id: 16634, input_name: 'Hydrocarbons', quantity: 100 }
      ]
    }
    vi.mocked(apiClient.get).mockResolvedValue({ data: mockReaction })

    const result = await getReactionById(42)
    expect(result.reaction_type_id).toBe(42)
    expect(result.reaction_name).toBe('Ferrofluid Reaction')
    expect(apiClient.get).toHaveBeenCalledWith('/reactions/42')
  })

  it('fetches profitable reactions', async () => {
    const mockProfitable = [
      { reaction_type_id: 1, reaction_name: 'Profitable Reaction 1', profit_per_hour: 5000000, rank: 1 },
      { reaction_type_id: 2, reaction_name: 'Profitable Reaction 2', profit_per_hour: 4000000, rank: 2 }
    ]
    vi.mocked(apiClient.get).mockResolvedValue({ data: mockProfitable })

    const result = await getProfitableReactions(10)
    expect(result).toHaveLength(2)
    expect(result[0].rank).toBe(1)
    expect(apiClient.get).toHaveBeenCalledWith('/reactions/profitable', {
      params: { limit: 10, region_id: 10000002 }
    })
  })

  it('fetches profitable reactions with type filter', async () => {
    const mockProfitable = [
      { reaction_type_id: 1, reaction_name: 'Complex Reaction', reaction_category: 'complex', rank: 1 }
    ]
    vi.mocked(apiClient.get).mockResolvedValue({ data: mockProfitable })

    await getProfitableReactions(20, 'complex', 10000043)
    expect(apiClient.get).toHaveBeenCalledWith('/reactions/profitable', {
      params: { limit: 20, region_id: 10000043, reaction_type: 'complex' }
    })
  })
})
