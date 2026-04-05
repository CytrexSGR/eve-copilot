/**
 * Centralized ESI API agent for all EVE API calls
 * Ensures consistent headers and User-Agent across all requests
 */

const ESI_BASE_URL = 'https://esi.evetech.net/latest';
const USER_AGENT = 'EVE Online Interactive Map (https://github.com/ectkirk/ectmap)';
const X_COMPATIBILITY_DATE = '2025-11-06';

interface ESIRequestOptions {
  endpoint: string;
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE';
  headers?: Record<string, string>;
  body?: unknown;
}

export class ESIAgent {
  /**
   * Make a request to the ESI API
   */
  static async request<T>(options: ESIRequestOptions): Promise<T> {
    const { endpoint, method = 'GET', headers = {}, body } = options;

    const url = endpoint.startsWith('http') ? endpoint : `${ESI_BASE_URL}${endpoint}`;

    const requestHeaders: Record<string, string> = {
      'User-Agent': USER_AGENT,
      'X-Compatibility-Date': X_COMPATIBILITY_DATE,
      'Accept-Language': 'en',
      ...headers,
    };

    const requestOptions: RequestInit = {
      method,
      headers: requestHeaders,
    };

    if (body && method !== 'GET') {
      requestOptions.body = JSON.stringify(body);
      requestHeaders['Content-Type'] = 'application/json';
    }

    const response = await fetch(url, requestOptions);

    if (!response.ok) {
      throw new Error(`ESI request failed: ${response.status} ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Get faction warfare systems
   */
  static async getFactionWarfareSystems(): Promise<
    Array<{
      contested: 'captured' | 'contested' | 'uncontested' | 'vulnerable';
      occupier_faction_id: number;
      owner_faction_id: number;
      solar_system_id: number;
      victory_points: number;
      victory_points_threshold: number;
    }>
  > {
    return this.request({
      endpoint: '/fw/systems/',
    });
  }

  /**
   * Get sovereignty map
   */
  static async getSovereigntyMap(): Promise<
    Array<{
      alliance_id?: number;
      corporation_id?: number;
      faction_id?: number;
      system_id: number;
    }>
  > {
    return this.request({
      endpoint: '/sovereignty/map/',
    });
  }

  /**
   * Resolve IDs to names
   */
  static async getNames(ids: number[]): Promise<
    Array<{
      category: string;
      id: number;
      name: string;
    }>
  > {
    return this.request({
      endpoint: '/universe/names/',
      method: 'POST',
      body: ids,
    });
  }
}
