import type { Meta, StoryObj } from '@storybook/react';
import { BattleAttackerLoadouts } from './BattleAttackerLoadouts';
import { mockAttackerLoadouts } from '../../../.storybook/mocks/data/battles';

const meta: Meta<typeof BattleAttackerLoadouts> = {
  title: 'Intel & Battle/Battle Report/BattleAttackerLoadouts',
  component: BattleAttackerLoadouts,
  tags: ['autodocs'],
  parameters: {
    layout: 'padded',
  },
};

export default meta;
type Story = StoryObj<typeof BattleAttackerLoadouts>;

export const Default: Story = {
  args: {
    data: mockAttackerLoadouts,
  },
};

export const NoData: Story = {
  args: {
    data: null,
  },
};

export const SingleAlliance: Story = {
  args: {
    data: {
      battle_id: 102977,
      alliances: [mockAttackerLoadouts.alliances[0]],
    },
  },
};
