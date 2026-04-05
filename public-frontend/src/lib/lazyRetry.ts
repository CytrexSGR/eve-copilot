import { lazy, type ComponentType } from 'react';

/**
 * Wrapper around React.lazy() that retries failed dynamic imports.
 * Handles chunk loading failures after deployments (stale chunk hashes).
 */
export function lazyRetry<T extends ComponentType<unknown>>(
  factory: () => Promise<{ default: T }>,
  retries = 2,
): React.LazyExoticComponent<T> {
  return lazy(() => retryImport(factory, retries));
}

async function retryImport<T extends ComponentType<unknown>>(
  factory: () => Promise<{ default: T }>,
  retries: number,
): Promise<{ default: T }> {
  try {
    return await factory();
  } catch (error) {
    if (retries <= 0) throw error;

    // Wait briefly before retrying (exponential backoff)
    await new Promise(r => setTimeout(r, 1000 * (3 - retries)));

    return retryImport(factory, retries - 1);
  }
}
