import type { Meta, StoryObj } from '@storybook/react';
import { BattleKillFeed } from './BattleKillFeed';
import { mockKills } from '../../../.storybook/mocks/data/battles';

const meta: Meta<typeof BattleKillFeed> = {
  title: 'Intel & Battle/Battle Report/BattleKillFeed',
  component: BattleKillFeed,
  tags: ['autodocs'],
  parameters: {
    layout: 'padded',
  },
};

export default meta;
type Story = StoryObj<typeof BattleKillFeed>;

export const Default: Story = {
  args: {
    kills: mockKills,
    totalKills: 47,
  },
};

export const Empty: Story = {
  args: {
    kills: [],
    totalKills: 47,
  },
};

export const SingleKill: Story = {
  args: {
    kills: [mockKills[0]],
    totalKills: 1,
  },
};
