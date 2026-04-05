import type { Meta, StoryObj } from '@storybook/react';
import { TopEnemiesSection } from './TopEnemiesSection';

const meta: Meta<typeof TopEnemiesSection> = {
  title: 'WarfareIntel/TopEnemiesSection',
  component: TopEnemiesSection,
  parameters: { layout: 'padded' },
};
export default meta;
type Story = StoryObj<typeof TopEnemiesSection>;

export const Default: Story = {
  args: {
    enemies: [
      { alliance_id: 1354830081, alliance_name: 'Goonswarm Federation', ticker: 'CONDI', kills: 2450, isk_destroyed: 850_000_000_000, efficiency_vs_them: 62 },
      { alliance_id: 99010079, alliance_name: 'Brave Collective', ticker: 'BRAVE', kills: 1200, isk_destroyed: 320_000_000_000, efficiency_vs_them: 55 },
      { alliance_id: 99003581, alliance_name: 'Fraternity.', ticker: 'FRT', kills: 980, isk_destroyed: 280_000_000_000, efficiency_vs_them: 48 },
    ],
    timeframeLabel: '7d',
    loading: false,
  },
};

export const Loading: Story = {
  args: {
    enemies: [],
    timeframeLabel: '7d',
    loading: true,
  },
};

export const Empty: Story = {
  args: {
    enemies: [],
    timeframeLabel: '24h',
    loading: false,
  },
};
