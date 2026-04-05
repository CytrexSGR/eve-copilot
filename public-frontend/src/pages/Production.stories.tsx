import { createElement } from 'react';
import type { Meta, StoryObj } from '@storybook/react-vite';
import type { Decorator } from '@storybook/react-vite';
import { MemoryRouter } from 'react-router-dom';
import { Production } from './Production';
import { handlers } from '../../.storybook/mocks/handlers';

/**
 * Decorator that provides a MemoryRouter with search params pre-set,
 * allowing the Production page to start on a specific tab with an item selected.
 */
function withProductionRouter(tab: string = 'economics', typeId?: number): Decorator {
  const search = typeId ? `?tab=${tab}&typeId=${typeId}` : `?tab=${tab}`;
  return (Story) =>
    createElement(
      MemoryRouter,
      { initialEntries: [`/production${search}`] },
      createElement(Story)
    );
}

const meta: Meta<typeof Production> = {
  title: 'Production/ProductionPage',
  component: Production,
  tags: ['autodocs'],
  parameters: {
    msw: { handlers },
    layout: 'fullscreen',
  },
};

export default meta;
type Story = StoryObj<typeof Production>;

/**
 * Default view — Economics tab with manufacturing opportunities loaded.
 * No item pre-selected; user can search for an item in the search bar.
 */
export const EconomicsTab: Story = {
  decorators: [withProductionRouter('economics')],
};

/**
 * Planner tab with Drake pre-selected — shows the material chain tree
 * with build/buy toggles and Jita prices in the shopping list.
 */
export const PlannerWithDrake: Story = {
  decorators: [withProductionRouter('planner', 24698)],
};

/**
 * Calculator tab with Drake pre-selected — shows production simulation,
 * BOM, financial analysis, and facility comparison.
 */
export const CalculatorWithDrake: Story = {
  decorators: [withProductionRouter('calculator', 24698)],
};
