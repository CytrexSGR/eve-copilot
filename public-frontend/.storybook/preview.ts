import { createElement } from 'react';
import type { Preview, Decorator } from '@storybook/react-vite';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { initialize, mswLoader } from 'msw-storybook-addon';
import { AuthContext } from '../src/context/AuthContext';
import type { AuthState } from '../src/context/AuthContext';
import type { AccountInfo, TierInfo, OrgPlan } from '../src/types/auth';

import '../src/index.css';
import '../src/App.css';

// Initialize MSW
initialize({
  onUnhandledRequest: 'bypass',
});

// ---------------------------------------------------------------------------
// Mock auth data factory
// ---------------------------------------------------------------------------

const mockAccount: AccountInfo = {
  account_id: 1,
  primary_character_id: 1117367444,
  primary_character_name: 'Cytrex',
  tier: 'coalition',
  subscription_id: 1,
  expires_at: '2027-01-01T00:00:00Z',
  corporation_id: 98378388,
  alliance_id: 99003581,
  characters: [
    { character_id: 1117367444, character_name: 'Cytrex', is_primary: true },
  ],
  created_at: '2024-01-01T00:00:00Z',
  last_login: '2026-02-20T00:00:00Z',
};

const TIER_MAP: Record<string, TierInfo> = {
  free: { tier: 'free', subscription_id: null, expires_at: null },
  pilot: { tier: 'pilot', subscription_id: 1, expires_at: '2027-01-01T00:00:00Z' },
  corp: { tier: 'corporation', subscription_id: 2, expires_at: '2027-01-01T00:00:00Z' },
  coalition: { tier: 'coalition', subscription_id: 3, expires_at: '2027-01-01T00:00:00Z' },
};

const MODULES_BY_TIER: Record<string, string[]> = {
  free: [],
  pilot: ['intel', 'market'],
  corp: ['intel', 'market', 'production', 'fittings'],
  coalition: ['intel', 'market', 'production', 'fittings', 'navigation', 'shopping', 'corp'],
};

function buildAuthState(tier: string, loggedIn: boolean): AuthState {
  const tierInfo = TIER_MAP[tier] ?? TIER_MAP.free;
  const orgPlan: OrgPlan | null =
    tier === 'corp' || tier === 'coalition'
      ? {
          type: 'alliance',
          plan: tier === 'coalition' ? 'coalition' : 'corporation',
          has_seat: true,
          heavy_seats: 50,
          seats_used: 12,
          expires_at: '2027-01-01T00:00:00Z',
        }
      : null;

  return {
    isLoading: false,
    isLoggedIn: loggedIn,
    account: loggedIn ? { ...mockAccount, tier: tierInfo.tier } : null,
    tierInfo: loggedIn ? tierInfo : null,
    activeModules: loggedIn ? (MODULES_BY_TIER[tier] ?? []) : [],
    orgPlan: loggedIn ? orgPlan : null,
    login: async () => {},
    logout: async () => {},
    refresh: async () => {},
  };
}

// ---------------------------------------------------------------------------
// Decorators
// ---------------------------------------------------------------------------

/**
 * Wraps every story with AuthContext.Provider using toolbar-controlled values.
 */
const withAuth: Decorator = (Story, context) => {
  const tier: string = (context.globals['tier'] as string) ?? 'coalition';
  const loggedIn: boolean = (context.globals['loggedIn'] as boolean) ?? true;
  const authState = buildAuthState(tier, loggedIn);

  return createElement(
    AuthContext.Provider,
    { value: authState },
    createElement(Story)
  );
};

/**
 * Wraps every story with a fresh QueryClientProvider (retry: false, staleTime: Infinity).
 */
const withQuery: Decorator = (Story) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        staleTime: Infinity,
      },
    },
  });

  return createElement(
    QueryClientProvider,
    { client: queryClient },
    createElement(Story)
  );
};

/**
 * Wraps every story with MemoryRouter from react-router-dom.
 */
const withRouter: Decorator = (Story) => {
  return createElement(
    MemoryRouter,
    { initialEntries: ['/'] },
    createElement(Story)
  );
};

// ---------------------------------------------------------------------------
// Preview configuration
// ---------------------------------------------------------------------------

const preview: Preview = {
  decorators: [withAuth, withQuery, withRouter],
  loaders: [mswLoader],

  globalTypes: {
    tier: {
      description: 'Subscription tier for AuthContext',
      toolbar: {
        title: 'Tier',
        icon: 'shield',
        items: [
          { value: 'free', title: 'Free' },
          { value: 'pilot', title: 'Pilot' },
          { value: 'corp', title: 'Corporation' },
          { value: 'coalition', title: 'Coalition' },
        ],
        dynamicTitle: true,
      },
    },
    loggedIn: {
      description: 'Whether the user is logged in',
      toolbar: {
        title: 'Logged In',
        icon: 'user',
        items: [
          { value: true, title: 'Logged In' },
          { value: false, title: 'Logged Out' },
        ],
        dynamicTitle: true,
      },
    },
  },

  initialGlobals: {
    tier: 'coalition',
    loggedIn: true,
  },

  parameters: {
    controls: {
      matchers: {
        color: /(background|color)$/i,
        date: /Date$/i,
      },
    },
    backgrounds: {
      default: 'eve-dark',
      values: [
        { name: 'eve-dark', value: '#0d1117' },
        { name: 'eve-darker', value: '#010409' },
        { name: 'white', value: '#ffffff' },
      ],
    },
    a11y: {
      test: 'todo',
    },
  },
};

export default preview;
