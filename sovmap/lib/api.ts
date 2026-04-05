// API helper that respects Next.js basePath
const BASE_PATH = '/ectmap';

export function apiUrl(path: string): string {
  // Remove leading slash if present
  const cleanPath = path.startsWith('/') ? path.slice(1) : path;
  return `${BASE_PATH}/${cleanPath}`;
}

export async function apiFetch(path: string, options?: RequestInit): Promise<Response> {
  return fetch(apiUrl(path), options);
}
