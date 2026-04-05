import type { Meta, StoryObj } from '@storybook/react';
import { LandingFeatures } from './LandingFeatures';

const meta: Meta<typeof LandingFeatures> = {
  title: 'Home/LandingFeatures',
  component: LandingFeatures,
  parameters: { layout: 'padded' },
};
export default meta;
type Story = StoryObj<typeof LandingFeatures>;

export const Default: Story = {};
