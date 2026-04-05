import type { Meta, StoryObj } from '@storybook/react';
import { BattleSidesPanel } from './BattleSidesPanel';
import {
  mockBattleSides,
  mockCommanderIntel,
  mockParticipants,
} from '../../../.storybook/mocks/data/battles';

const meta: Meta<typeof BattleSidesPanel> = {
  title: 'Intel & Battle/Battle Report/BattleSidesPanel',
  component: BattleSidesPanel,
  tags: ['autodocs'],
  parameters: {
    layout: 'padded',
  },
};

export default meta;
type Story = StoryObj<typeof BattleSidesPanel>;

export const Default: Story = {
  args: {
    battleSides: mockBattleSides,
    participants: mockParticipants,
    commanderIntel: mockCommanderIntel,
  },
};

export const NoParticipants: Story = {
  args: {
    battleSides: mockBattleSides,
    participants: null,
    commanderIntel: null,
  },
};

export const NoData: Story = {
  args: {
    battleSides: null,
    participants: null,
    commanderIntel: null,
  },
};
