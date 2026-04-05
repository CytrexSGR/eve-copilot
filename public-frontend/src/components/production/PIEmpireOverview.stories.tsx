import type { Meta, StoryObj } from '@storybook/react';
import { PIEmpireOverview } from './PIEmpireOverview';

const meta: Meta<typeof PIEmpireOverview> = {
  title: 'Production/PI Chain/PIEmpireOverview',
  component: PIEmpireOverview,
  tags: ['autodocs'],
  parameters: {
    layout: 'padded',
  },
};

export default meta;
type Story = StoryObj<typeof PIEmpireOverview>;

/**
 * Default: Multi-character PI empire analysis showing:
 * - P4 feasibility selector sorted by feasibility percentage
 * - SVG DAG with availability status overlay (available/factory/missing)
 * - Empire sidebar with character stats and P4 profitability
 * Fetches empire analysis and PI schematics via MSW.
 */
export const Default: Story = {
  args: {},
};
