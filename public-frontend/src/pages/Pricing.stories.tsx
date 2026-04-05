import type { Meta, StoryObj } from '@storybook/react';
import { Pricing } from './Pricing';

const meta: Meta<typeof Pricing> = {
  title: 'Pages/Pricing',
  component: Pricing,
  tags: ['autodocs'],
};
export default meta;
type Story = StoryObj<typeof Pricing>;

export const Default: Story = {};
