// src/services/api.ts - Backwards compatibility re-exports
// All API functions are now organized in domain-specific modules under ./api/
// This file re-exports everything for backwards compatibility with existing imports.

export * from './api/index';
export { default } from './api/index';
