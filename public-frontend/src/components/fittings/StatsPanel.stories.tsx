import type { Meta, StoryObj } from '@storybook/react';
import { StatsPanel } from './StatsPanel';
import { mockDrakeStats } from '../../../.storybook/mocks/data/fittings';

const meta: Meta<typeof StatsPanel> = {
  title: 'Fittings & Navigation/Fittings/StatsPanel',
  component: StatsPanel,
  tags: ['autodocs'],
};
export default meta;
type Story = StoryObj<typeof StatsPanel>;

export const DrakePvE: Story = {
  args: {
    stats: mockDrakeStats,
    loading: false,
  },
};

export const Loading: Story = {
  args: {
    stats: null,
    loading: true,
  },
};

export const NoStats: Story = {
  args: {
    stats: null,
    loading: false,
  },
};
