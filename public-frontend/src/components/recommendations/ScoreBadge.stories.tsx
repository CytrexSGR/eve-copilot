import type { Meta, StoryObj } from '@storybook/react';
import { ScoreBadge } from './ScoreBadge';

const meta: Meta<typeof ScoreBadge> = {
  title: 'Recommendations/ScoreBadge',
  component: ScoreBadge,
  parameters: { layout: 'centered' },
};
export default meta;
type Story = StoryObj<typeof ScoreBadge>;

export const High: Story = {
  args: { score: 85 },
};

export const Medium: Story = {
  args: { score: 55 },
};

export const Low: Story = {
  args: { score: 20 },
};

export const Perfect: Story = {
  args: { score: 100 },
};

export const Zero: Story = {
  args: { score: 0 },
};
