import type { Meta, StoryObj } from '@storybook/react';
import { LandingCTA } from './LandingCTA';

const meta: Meta<typeof LandingCTA> = {
  title: 'Home/LandingCTA',
  component: LandingCTA,
  parameters: { layout: 'padded' },
};
export default meta;
type Story = StoryObj<typeof LandingCTA>;

export const Default: Story = {};
