import { http, HttpResponse } from 'msw';
import { mockAccount, mockTierInfo, mockModules } from '../data/auth';

/**
 * MSW handlers for auth-related API endpoints.
 * These intercept requests in Storybook to provide mock data.
 */
export const authHandlers = [
  // GET /api/auth/public/account — returns logged-in account info
  http.get('/api/auth/public/account', () => {
    return HttpResponse.json(mockAccount);
  }),

  // GET /api/tier/my-tier — returns current subscription tier
  http.get('/api/tier/my-tier', () => {
    return HttpResponse.json(mockTierInfo);
  }),

  // GET /api/tier/modules/active — returns active module list
  http.get('/api/tier/modules/active', () => {
    return HttpResponse.json(mockModules);
  }),

  // POST /api/auth/public/logout — mock logout
  http.post('/api/auth/public/logout', () => {
    return HttpResponse.json({ success: true });
  }),
];
