import type { Meta, StoryObj } from '@storybook/react';
import { LandingHero } from './LandingHero';

const meta: Meta<typeof LandingHero> = {
  title: 'Home/LandingHero',
  component: LandingHero,
  parameters: { layout: 'fullscreen' },
};
export default meta;
type Story = StoryObj<typeof LandingHero>;

export const Default: Story = {};
