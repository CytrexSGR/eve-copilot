import type { Meta, StoryObj } from '@storybook/react';
import { PIChainPlanner } from './PIChainPlanner';

const meta: Meta<typeof PIChainPlanner> = {
  title: 'Production/PI Chain/PIChainPlanner',
  component: PIChainPlanner,
  tags: ['autodocs'],
  parameters: {
    layout: 'padded',
  },
};

export default meta;
type Story = StoryObj<typeof PIChainPlanner>;

/**
 * Default: Tabbed view with "My Plans" (plan list with status filters,
 * create form) and "Chain Browser" (DAG visualization).
 * Fetches PI plans list via MSW.
 */
export const Default: Story = {
  args: {},
};
