import type { Meta, StoryObj } from '@storybook/react';
import { ConfidenceBadge } from './ConfidenceBadge';

const meta: Meta<typeof ConfidenceBadge> = {
  title: 'Economy & Market/War Economy/ConfidenceBadge',
  component: ConfidenceBadge,
  tags: ['autodocs'],
  parameters: {
    layout: 'centered',
  },
};

export default meta;
type Story = StoryObj<typeof ConfidenceBadge>;

/** HIGH confidence (70%+): strong data backing. */
export const High: Story = {
  args: { score: 85 },
};

/** MEDIUM confidence (40-69%): moderate data quality. */
export const Medium: Story = {
  args: { score: 55 },
};

/** LOW confidence (<40%): limited data available. */
export const Low: Story = {
  args: { score: 25 },
};

/** Edge case: exact threshold (70%). */
export const ExactHighThreshold: Story = {
  args: { score: 70 },
};
