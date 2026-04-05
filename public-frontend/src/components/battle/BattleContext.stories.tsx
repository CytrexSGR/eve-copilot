import type { Meta, StoryObj } from '@storybook/react';
import { BattleContext } from './BattleContext';
import { mockWarSummary } from '../../../.storybook/mocks/data/battles';

const meta: Meta<typeof BattleContext> = {
  title: 'Intel & Battle/Battle Report/BattleContext',
  component: BattleContext,
  tags: ['autodocs'],
  parameters: {
    layout: 'padded',
  },
};

export default meta;
type Story = StoryObj<typeof BattleContext>;

export const Default: Story = {
  args: {
    battleKills: 47,
    battleISK: 32_500_000_000,
    battleCapitalKills: 8,
    warSummary: mockWarSummary,
  },
};

export const MajorBattle: Story = {
  args: {
    battleKills: 120,
    battleISK: 180_000_000_000,
    battleCapitalKills: 15,
    warSummary: mockWarSummary,
  },
};

export const MinorSkirmish: Story = {
  args: {
    battleKills: 5,
    battleISK: 500_000_000,
    battleCapitalKills: 0,
    warSummary: mockWarSummary,
  },
};

export const NoWarSummary: Story = {
  args: {
    battleKills: 47,
    battleISK: 32_500_000_000,
    battleCapitalKills: 8,
    warSummary: null,
  },
};
