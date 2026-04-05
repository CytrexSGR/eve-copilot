import type { Meta, StoryObj } from '@storybook/react';
import { TrendIndicator } from './TrendIndicator';

const meta: Meta<typeof TrendIndicator> = {
  title: 'Doctrines/TrendIndicator',
  component: TrendIndicator,
  parameters: { layout: 'centered' },
};
export default meta;
type Story = StoryObj<typeof TrendIndicator>;

export const Rising: Story = {
  args: {
    change: 23,
    label: '7d',
  },
};

export const Declining: Story = {
  args: {
    change: -15,
    label: '7d',
  },
};

export const Stable: Story = {
  args: {
    change: 2,
    label: '30d',
  },
};

export const SharpRise: Story = {
  args: {
    change: 85,
    label: '24h',
  },
};
