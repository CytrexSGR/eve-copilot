import { useState } from 'react';
import type { Meta, StoryObj } from '@storybook/react';
import { WormholeTabNav } from './WormholeTabNav';
import type { WormholeTabId } from '../../types/wormhole';

const meta: Meta<typeof WormholeTabNav> = {
  title: 'Intel & Battle/Wormhole/WormholeTabNav',
  component: WormholeTabNav,
  tags: ['autodocs'],
  parameters: {
    layout: 'padded',
  },
};

export default meta;
type Story = StoryObj<typeof WormholeTabNav>;

export const Default: Story = {
  args: {
    activeTab: 'residents',
    onTabChange: () => {},
  },
};

export const HuntersActive: Story = {
  args: {
    activeTab: 'hunters',
    onTabChange: () => {},
  },
};

export const MarketActive: Story = {
  args: {
    activeTab: 'market',
    onTabChange: () => {},
  },
};

export const TheraRouterActive: Story = {
  args: {
    activeTab: 'thera-router',
    onTabChange: () => {},
  },
};

/** Interactive demo with working tab switching */
export const Interactive: Story = {
  render: () => {
    const [activeTab, setActiveTab] = useState<WormholeTabId>('residents');
    return <WormholeTabNav activeTab={activeTab} onTabChange={setActiveTab} />;
  },
};
