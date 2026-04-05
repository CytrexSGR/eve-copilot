import { authHandlers } from './handlers/auth';
import { battleHandlers } from './handlers/battles';
import { allianceHandlers } from './handlers/alliances';
import { wormholeHandlers } from './handlers/wormhole';
import { marketHandlers } from './handlers/market';
import { productionHandlers } from './handlers/production';
import { warEconomyHandlers } from './handlers/war-economy';
import { fittingsHandlers } from './handlers/fittings';
import { financeHandlers } from './handlers/finance';

/**
 * Combined MSW handler exports.
 * Import this in stories that need MSW request interception.
 *
 * Usage in a story:
 *   import { handlers } from '../../.storybook/mocks/handlers';
 *
 *   export default {
 *     parameters: {
 *       msw: { handlers },
 *     },
 *   };
 */
export const handlers = [
  ...authHandlers,
  ...battleHandlers,
  ...allianceHandlers,
  ...wormholeHandlers,
  ...marketHandlers,
  ...productionHandlers,
  ...warEconomyHandlers,
  ...fittingsHandlers,
  ...financeHandlers,
];
