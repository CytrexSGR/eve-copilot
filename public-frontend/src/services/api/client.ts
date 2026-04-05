import axios, { type AxiosInstance } from 'axios';

function addCharacterInterceptor(instance: AxiosInstance): AxiosInstance {
  instance.interceptors.request.use((config) => {
    const activeChar = localStorage.getItem('eve_active_char');
    if (activeChar) {
      config.headers['X-Character-Id'] = activeChar;
    }
    return config;
  });
  return instance;
}

/** Create an API client with character context interceptor. */
export function createApiClient(baseURL: string, timeout = 30_000): AxiosInstance {
  return addCharacterInterceptor(
    axios.create({ baseURL, timeout, withCredentials: true })
  );
}

export const api = createApiClient('/api');
