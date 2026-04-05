import { api } from './client';
import type {
  ShoppingList, ShoppingItem, CargoSummary, TransportShip,
  FreightRoute, FreightCalculation, RegionalComparison,
} from '../../types/shopping';

export const shoppingApi = {
  getLists: async (characterId?: number): Promise<ShoppingList[]> => {
    const params = characterId ? { character_id: characterId } : {};
    const { data } = await api.get('/shopping/lists', { params });
    return Array.isArray(data) ? data : data.lists || [];
  },

  createList: async (name: string, characterId?: number): Promise<ShoppingList> => {
    const { data } = await api.post('/shopping/lists', { name, character_id: characterId });
    return data;
  },

  getList: async (listId: number): Promise<ShoppingList> => {
    const { data } = await api.get(`/shopping/lists/${listId}`);
    return data;
  },

  deleteList: async (listId: number): Promise<void> => {
    await api.delete(`/shopping/lists/${listId}`);
  },

  getItems: async (listId: number): Promise<ShoppingItem[]> => {
    const { data } = await api.get(`/shopping/lists/${listId}/items`);
    return Array.isArray(data) ? data : data.items || [];
  },

  addItem: async (listId: number, typeId: number, quantity: number): Promise<ShoppingItem> => {
    const { data } = await api.post(`/shopping/lists/${listId}/items`, {
      type_id: typeId, quantity,
    });
    return data;
  },

  deleteItem: async (listId: number, itemId: number): Promise<void> => {
    await api.delete(`/shopping/lists/${listId}/items/${itemId}`);
  },

  markPurchased: async (listId: number, itemId: number, purchased: boolean): Promise<void> => {
    await api.patch(`/shopping/lists/${listId}/items/${itemId}`, { purchased });
  },

  getRegionalComparison: async (listId: number): Promise<RegionalComparison> => {
    const { data } = await api.get(`/shopping/lists/${listId}/regional-comparison`);
    return data;
  },

  exportList: async (listId: number, format: 'eve' | 'csv' = 'eve'): Promise<string> => {
    const { data } = await api.get(`/shopping/lists/${listId}/export`, {
      params: { format },
    });
    return data;
  },

  getCargoSummary: async (listId: number): Promise<CargoSummary> => {
    const { data } = await api.get(`/shopping/lists/${listId}/cargo-summary`);
    return data;
  },

  getTransportOptions: async (listId: number): Promise<TransportShip[]> => {
    const { data } = await api.get(`/shopping/lists/${listId}/transport-options`);
    return Array.isArray(data) ? data : data.options || [];
  },

  addProduction: async (listId: number, typeId: number, me = 0, runs = 1) => {
    const { data } = await api.post(
      `/shopping/lists/${listId}/add-production/${typeId}`,
      null,
      { params: { me, runs } },
    );
    return data;
  },

  addDoctrine: async (listId: number, doctrineId: number, quantity = 30) => {
    const { data } = await api.post(
      `/shopping/lists/${listId}/add-doctrine/${doctrineId}`,
      null,
      { params: { quantity } },
    );
    return data;
  },
};

export const freightApi = {
  getRoutes: async (activeOnly = true): Promise<{ routes: FreightRoute[]; count: number }> => {
    const { data } = await api.get('/shopping/freight/routes', {
      params: { active_only: activeOnly },
    });
    return data;
  },

  searchRoutes: async (startId: number, endId: number): Promise<{ routes: FreightRoute[]; count: number }> => {
    const { data } = await api.get('/shopping/freight/routes/search', {
      params: { start_system_id: startId, end_system_id: endId },
    });
    return data;
  },

  calculate: async (routeId: number, volumeM3: number, collateralIsk: number): Promise<FreightCalculation> => {
    const { data } = await api.post('/shopping/freight/calculate', {
      route_id: routeId, volume_m3: volumeM3, collateral_isk: collateralIsk,
    });
    return data;
  },
};
