import type { Meta, StoryObj } from '@storybook/react';
import { DoctrinesSection } from './DoctrinesSection';

const meta: Meta<typeof DoctrinesSection> = {
  title: 'Battlefield/DoctrinesSection',
  component: DoctrinesSection,
  parameters: { layout: 'padded' },
};
export default meta;
type Story = StoryObj<typeof DoctrinesSection>;

export const Default: Story = {
  args: {
    timeframeMinutes: 1440,
  },
};

export const OneHour: Story = {
  args: {
    timeframeMinutes: 60,
  },
};

export const SevenDays: Story = {
  args: {
    timeframeMinutes: 10080,
  },
};
