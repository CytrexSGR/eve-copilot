import type { Meta, StoryObj } from '@storybook/react';
import { CollapsibleStats } from './CollapsibleStats';
import { mockDrakeStats } from '../../../.storybook/mocks/data/fittings';

const meta: Meta<typeof CollapsibleStats> = {
  title: 'Fittings & Navigation/Fittings/CollapsibleStats',
  component: CollapsibleStats,
  tags: ['autodocs'],
};
export default meta;
type Story = StoryObj<typeof CollapsibleStats>;

export const Default: Story = {
  args: {
    stats: mockDrakeStats,
    loading: false,
    hasShip: true,
  },
};

export const Loading: Story = {
  args: {
    stats: null,
    loading: true,
    hasShip: true,
  },
};

export const NoShip: Story = {
  args: {
    stats: null,
    loading: false,
    hasShip: false,
  },
};

export const NullStats: Story = {
  args: {
    stats: null,
    loading: false,
    hasShip: true,
  },
};
