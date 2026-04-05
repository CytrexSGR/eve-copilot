import type { Meta, StoryObj } from '@storybook/react';
import { TheraRouterTab } from './TheraRouterTab';

/**
 * TheraRouterTab is a large data-fetching component (~700 lines) that provides
 * Thera route calculation with system presets, quick-select buttons, and route
 * visualization. It fetches data internally via wormholeApi.
 *
 * MSW handlers mock the /api/wormhole/thera/routes endpoint.
 */
const meta: Meta<typeof TheraRouterTab> = {
  title: 'Intel & Battle/Wormhole/TheraRouterTab',
  component: TheraRouterTab,
  tags: ['autodocs'],
  parameters: {
    layout: 'padded',
  },
};

export default meta;
type Story = StoryObj<typeof TheraRouterTab>;

export const Default: Story = {};
