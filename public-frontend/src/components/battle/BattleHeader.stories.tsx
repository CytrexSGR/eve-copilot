import type { Meta, StoryObj } from '@storybook/react';
import { BattleHeader } from './BattleHeader';
import {
  mockBattleInfo,
  mockBattleInfoModerate,
  mockSystemDanger,
  mockSystemDangerSafe,
  mockCapitalShipsLost,
} from '../../../.storybook/mocks/data/battles';

const meta: Meta<typeof BattleHeader> = {
  title: 'Intel & Battle/Battle Report/BattleHeader',
  component: BattleHeader,
  tags: ['autodocs'],
  parameters: {
    layout: 'padded',
  },
  argTypes: {
    onBack: { action: 'onBack' },
  },
};

export default meta;
type Story = StoryObj<typeof BattleHeader>;

export const Default: Story = {
  args: {
    battle: mockBattleInfo,
    systemDanger: mockSystemDanger,
    capitalShipsLost: mockCapitalShipsLost,
    onBack: () => {},
  },
};

export const ModerateBattle: Story = {
  args: {
    battle: mockBattleInfoModerate,
    systemDanger: mockSystemDangerSafe,
    capitalShipsLost: [],
    onBack: () => {},
  },
};

export const NoDangerNoCapitals: Story = {
  args: {
    battle: mockBattleInfo,
    systemDanger: null,
    capitalShipsLost: [],
    onBack: () => {},
  },
};

export const WithSovereignty: Story = {
  args: {
    battle: {
      ...mockBattleInfo,
      security: -0.4,
    },
    systemDanger: {
      ...mockSystemDanger,
      sov_alliance_name: 'Fraternity.',
      sov_alliance_id: 99003581,
    },
    capitalShipsLost: mockCapitalShipsLost,
    onBack: () => {},
  },
};
