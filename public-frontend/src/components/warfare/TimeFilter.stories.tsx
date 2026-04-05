import type { Meta, StoryObj } from '@storybook/react';
import { TimeFilter } from './TimeFilter';
import { fn } from '@storybook/test';

const meta: Meta<typeof TimeFilter> = {
  title: 'Warfare/TimeFilter',
  component: TimeFilter,
  parameters: { layout: 'centered' },
};
export default meta;
type Story = StoryObj<typeof TimeFilter>;

export const OneHour: Story = {
  args: {
    value: 60,
    onChange: fn(),
  },
};

export const TenMinutes: Story = {
  args: {
    value: 10,
    onChange: fn(),
  },
};

export const SevenDays: Story = {
  args: {
    value: 10080,
    onChange: fn(),
  },
};

export const CustomOptions: Story = {
  args: {
    value: 30,
    onChange: fn(),
    options: [
      { label: '30m', minutes: 30 },
      { label: '2h', minutes: 120 },
      { label: '6h', minutes: 360 },
    ],
  },
};
