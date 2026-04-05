import type { Meta, StoryObj } from '@storybook/react';
import { RefreshIndicator } from './RefreshIndicator';

const meta: Meta<typeof RefreshIndicator> = {
  title: 'Shared UI/RefreshIndicator',
  component: RefreshIndicator,
  tags: ['autodocs'],
  parameters: {
    layout: 'padded',
  },
  argTypes: {
    autoRefreshSeconds: {
      control: { type: 'range', min: 10, max: 300, step: 10 },
    },
  },
};

export default meta;
type Story = StoryObj<typeof RefreshIndicator>;

export const JustUpdated: Story = {
  args: {
    lastUpdated: new Date(),
    autoRefreshSeconds: 60,
  },
};

export const UpdatedMinutesAgo: Story = {
  args: {
    lastUpdated: new Date(Date.now() - 5 * 60 * 1000),
    autoRefreshSeconds: 60,
  },
};

export const UpdatedHoursAgo: Story = {
  args: {
    lastUpdated: new Date(Date.now() - 2 * 60 * 60 * 1000),
    autoRefreshSeconds: 300,
  },
};

export const FastRefresh: Story = {
  args: {
    lastUpdated: new Date(),
    autoRefreshSeconds: 10,
  },
};

export const SlowRefresh: Story = {
  args: {
    lastUpdated: new Date(Date.now() - 30 * 1000),
    autoRefreshSeconds: 300,
  },
};
