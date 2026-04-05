import type { Meta, StoryObj } from '@storybook/react';
import { PIChainBrowser } from './PIChainBrowser';
import { fn } from '@storybook/test';

const meta: Meta<typeof PIChainBrowser> = {
  title: 'Production/PI Chain/PIChainBrowser',
  component: PIChainBrowser,
  tags: ['autodocs'],
  parameters: {
    layout: 'padded',
  },
};

export default meta;
type Story = StoryObj<typeof PIChainBrowser>;

/**
 * Default: Interactive SVG DAG showing P4 production chains.
 * P4 product selector at top, DAG graph with Bezier edges,
 * clickable nodes for cart, and cart panel on the right.
 * Fetches PI schematics and profitability via MSW.
 */
export const Default: Story = {
  args: {
    onPlanCreated: fn(),
  },
};
