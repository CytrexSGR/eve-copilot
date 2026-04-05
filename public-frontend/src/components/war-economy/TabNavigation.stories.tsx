import type { Meta, StoryObj } from '@storybook/react';
import { TabNavigation } from './TabNavigation';
import { fn } from '@storybook/test';

const meta: Meta<typeof TabNavigation> = {
  title: 'Economy & Market/War Economy/TabNavigation',
  component: TabNavigation,
  tags: ['autodocs'],
  parameters: {
    layout: 'padded',
  },
  args: {
    onTabChange: fn(),
  },
};

export default meta;
type Story = StoryObj<typeof TabNavigation>;

/** Combat tab active. */
export const CombatActive: Story = {
  args: {
    activeTab: 'combat',
  },
};

/** Trading tab active. */
export const TradingActive: Story = {
  args: {
    activeTab: 'trading',
  },
};

/** Routes tab active. */
export const RoutesActive: Story = {
  args: {
    activeTab: 'routes',
  },
};

/** Signals tab active. */
export const SignalsActive: Story = {
  args: {
    activeTab: 'signals',
  },
};

/** Intel tab active. */
export const IntelActive: Story = {
  args: {
    activeTab: 'intel',
  },
};
