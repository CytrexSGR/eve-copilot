import type { Meta, StoryObj } from '@storybook/react';
import { DonutChart } from './DonutChart';

const meta: Meta<typeof DonutChart> = {
  title: 'BattleReport/DonutChart',
  component: DonutChart,
  parameters: { layout: 'centered' },
};
export default meta;
type Story = StoryObj<typeof DonutChart>;

export const Default: Story = {
  args: {
    data: [
      { label: 'Shield', value: 45, color: '#00d4ff' },
      { label: 'Armor', value: 35, color: '#ff8800' },
      { label: 'Hull', value: 20, color: '#8b949e' },
    ],
    size: 120,
  },
};

export const TwoSegments: Story = {
  args: {
    data: [
      { label: 'Wins', value: 72, color: '#3fb950' },
      { label: 'Losses', value: 28, color: '#f85149' },
    ],
    size: 150,
  },
};

export const Large: Story = {
  args: {
    data: [
      { label: 'Frigates', value: 120, color: '#00d4ff' },
      { label: 'Cruisers', value: 80, color: '#ff8800' },
      { label: 'Battleships', value: 45, color: '#a855f7' },
      { label: 'Capitals', value: 12, color: '#ff4444' },
    ],
    size: 200,
  },
};

export const EmptyData: Story = {
  args: {
    data: [],
    size: 120,
  },
};
