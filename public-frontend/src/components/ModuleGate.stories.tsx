import type { Meta, StoryObj } from '@storybook/react';
import { ModuleGate } from './ModuleGate';

const meta: Meta<typeof ModuleGate> = {
  title: 'Shared UI/ModuleGate',
  component: ModuleGate,
  tags: ['autodocs'],
  parameters: {
    layout: 'padded',
  },
};

export default meta;
type Story = StoryObj<typeof ModuleGate>;

export const Default: Story = {
  args: {
    module: 'intel',
    children: (
      <div style={{ padding: '1rem', background: 'rgba(0, 212, 255, 0.1)', borderRadius: '8px', color: '#fff' }}>
        Intel Module Content — War intelligence feeds, battle analysis, and sovereignty tracking.
      </div>
    ),
  },
};

export const MarketModule: Story = {
  args: {
    module: 'market',
    children: (
      <div style={{ padding: '1rem', background: 'rgba(0, 255, 136, 0.1)', borderRadius: '8px', color: '#fff' }}>
        Market Module Content — Real-time price data, arbitrage finder, and trade route optimizer.
      </div>
    ),
  },
};

export const ProductionModule: Story = {
  args: {
    module: 'production',
    preview: true,
    children: (
      <div style={{ padding: '1rem', background: 'rgba(255, 136, 0, 0.1)', borderRadius: '8px', color: '#fff' }}>
        Production Module Content — Blueprint management, ME/TE calculation, PI chain optimization.
      </div>
    ),
  },
};

export const WithSeatRequired: Story = {
  args: {
    module: 'corp',
    seatRequired: true,
    children: (
      <div style={{ padding: '1rem', background: 'rgba(255, 68, 68, 0.1)', borderRadius: '8px', color: '#fff' }}>
        Corporation Module Content — Requires an active corporation seat to access.
      </div>
    ),
  },
};

export const WithFallback: Story = {
  args: {
    module: 'navigation',
    fallback: (
      <div style={{ padding: '1rem', background: 'rgba(255, 255, 255, 0.05)', borderRadius: '8px', color: 'rgba(255,255,255,0.4)', textAlign: 'center' }}>
        Navigation module requires a Pilot subscription. Upgrade to access route planning and Thera connections.
      </div>
    ),
    children: (
      <div style={{ padding: '1rem', background: 'rgba(0, 212, 255, 0.1)', borderRadius: '8px', color: '#fff' }}>
        Navigation Module Content — Thera router, route planner, and jump bridge network.
      </div>
    ),
  },
};
