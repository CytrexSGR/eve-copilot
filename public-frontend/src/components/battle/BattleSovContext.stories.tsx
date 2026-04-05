import type { Meta, StoryObj } from '@storybook/react';
import { BattleSovContext } from './BattleSovContext';
import { mockStrategicContext, mockStrategicContextEmpty } from '../../../.storybook/mocks/data/battles';

const meta: Meta<typeof BattleSovContext> = {
  title: 'Intel & Battle/Battle Report/BattleSovContext',
  component: BattleSovContext,
  tags: ['autodocs'],
  parameters: {
    layout: 'padded',
  },
};

export default meta;
type Story = StoryObj<typeof BattleSovContext>;

export const Default: Story = {
  args: {
    context: mockStrategicContext,
  },
};

export const NoCampaigns: Story = {
  args: {
    context: mockStrategicContextEmpty,
  },
};

export const NoContext: Story = {
  args: {
    context: null,
  },
};

export const MultipleCampaigns: Story = {
  args: {
    context: {
      battle_id: 102977,
      system_sov: { alliance_id: 99003581, alliance_name: 'Fraternity.' },
      active_campaigns: [
        { system_name: 'M-OEE8', structure_type: 'IHUB', defender: 'Fraternity.', score: 42, adm: 3.2 },
        { system_name: 'EC-P8R', structure_type: 'TCU', defender: 'Fraternity.', score: 65, adm: 4.1 },
        { system_name: 'X47L-Q', structure_type: 'IHUB', defender: 'Ranger Regiment', score: 28, adm: 1.8 },
      ],
      constellation_campaigns: 2,
      strategic_note: 'Constellation under heavy pressure',
    },
  },
};
