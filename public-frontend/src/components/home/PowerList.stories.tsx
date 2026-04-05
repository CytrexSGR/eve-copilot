import type { Meta, StoryObj } from '@storybook/react';
import { PowerList } from './PowerList';

const meta: Meta<typeof PowerList> = {
  title: 'Home/PowerList',
  component: PowerList,
  parameters: { layout: 'padded' },
  decorators: [(Story) => (
    <div style={{ maxWidth: 400 }}><Story /></div>
  )],
};
export default meta;
type Story = StoryObj<typeof PowerList>;

const risingEntries = [
  {
    name: 'Fraternity.',
    alliance_id: 99003581,
    kills: 8552,
    losses: 5200,
    efficiency: 62.2,
    pilots: 4900,
    isk_destroyed: 2_500_000_000_000,
    isk_lost: 1_200_000_000_000,
    trend_24h: 15,
    history_7d: [100, 120, 130, 145, 160, 175, 190],
  },
  {
    name: 'Goonswarm Federation',
    alliance_id: 1354830081,
    kills: 6200,
    losses: 4800,
    efficiency: 56.4,
    pilots: 12000,
    isk_destroyed: 1_800_000_000_000,
    trend_24h: 8,
    history_7d: [80, 85, 90, 95, 100, 105, 110],
  },
];

const fallingEntries = [
  {
    name: 'TEST Alliance',
    alliance_id: 498125261,
    kills: 1200,
    losses: 2800,
    efficiency: 30.0,
    pilots: 3500,
    trend_24h: -22,
    history_7d: [200, 180, 160, 140, 120, 100, 80],
  },
  {
    name: 'Circle-Of-Two',
    alliance_id: 99005338,
    kills: 400,
    losses: 900,
    efficiency: 31.8,
    pilots: 800,
    trend_24h: -35,
    history_7d: [150, 130, 110, 90, 70, 50, 30],
  },
];

export const Rising: Story = {
  args: {
    entries: risingEntries,
    type: 'rising',
  },
};

export const Falling: Story = {
  args: {
    entries: fallingEntries,
    type: 'falling',
  },
};

export const Empty: Story = {
  args: {
    entries: [],
    type: 'rising',
  },
};
