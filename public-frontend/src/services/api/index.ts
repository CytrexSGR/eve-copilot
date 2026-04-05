// Domain-specific API modules re-export
// This file provides backwards compatibility for imports from '../services/api'

// Battle domain: battleApi, warApi, and battle-related types
export * from './battles';

// Economy domain: doctrineApi, warEconomyApi, and economy-related types
export * from './economy';

// Reports domain: reportsApi and report-related functions
export * from './reports';

// Fingerprints domain: fingerprintApi, counterDoctrineApi
export * from './fingerprints';

// Wormhole domain: wormholeApi for J-Space intelligence
export * from './wormhole';

// Re-export default axios instances for direct use if needed
export { default as battleApiClient } from './battles';
export { default as economyApiClient } from './economy';
export { default as reportsApiClient } from './reports';
export { default as wormholeApiClient } from './wormhole';

// Default export for backwards compatibility (using battles api client)
import battleApiClient from './battles';
export default battleApiClient;
