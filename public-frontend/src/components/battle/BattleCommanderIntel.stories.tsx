import type { Meta, StoryObj } from '@storybook/react';
import { BattleCommanderIntel } from './BattleCommanderIntel';
import {
  mockCommanderIntel,
  mockKills,
  mockSystemDanger,
  mockSystemDangerSafe,
} from '../../../.storybook/mocks/data/battles';

const meta: Meta<typeof BattleCommanderIntel> = {
  title: 'Intel & Battle/Battle Report/BattleCommanderIntel',
  component: BattleCommanderIntel,
  tags: ['autodocs'],
  parameters: {
    layout: 'padded',
  },
};

export default meta;
type Story = StoryObj<typeof BattleCommanderIntel>;

export const Default: Story = {
  args: {
    commanderIntel: mockCommanderIntel,
    recentKills: mockKills,
    systemDanger: mockSystemDanger,
  },
};

export const SafeSystem: Story = {
  args: {
    commanderIntel: mockCommanderIntel,
    recentKills: mockKills,
    systemDanger: mockSystemDangerSafe,
  },
};

export const NoDanger: Story = {
  args: {
    commanderIntel: mockCommanderIntel,
    recentKills: [],
    systemDanger: null,
  },
};
