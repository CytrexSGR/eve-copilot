/**
 * Shared entity abstraction for deduplicated view components.
 *
 * All intelligence views (Offensive, Defensive, Capitals, Geography) share
 * identical panel rendering — only the data fetcher and entity ID differ.
 */

export type EntityType = 'alliance' | 'corporation' | 'powerbloc';

export interface EntityViewProps {
  entityType: EntityType;
  entityId: number;
  days: number;
}

export type EntityFetcher<T> = (entityId: number, days: number) => Promise<T>;

export type FetcherMap<T> = Record<EntityType, EntityFetcher<T>>;
