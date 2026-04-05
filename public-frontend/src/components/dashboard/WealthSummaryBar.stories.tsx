import { createElement } from 'react';
import type { Meta, StoryObj, Decorator } from '@storybook/react';
import { WealthSummaryBar } from './WealthSummaryBar';
import { PilotIntelContext } from '../../context/PilotIntelContext';
import type { PilotIntelState } from '../../types/pilot-intel';

const mockPilotIntel: PilotIntelState = {
  isLoading: false,
  refresh: async () => {},
  profile: {
    characters: [],
    portfolioSummary: null,
    orders: null,
    lastUpdated: null,
  },
  derived: {
    totalWallet: 3_080_000_000,
    totalAssetValue: 5_200_000_000,
    totalSellOrderValue: 1_450_000_000,
    totalBuyEscrow: 680_000_000,
    totalNetWorth: 5_210_000_000,
    activeIndustryJobs: 3,
    completingSoonJobs: [],
    outbidCount: 2,
    skillMap: new Map(),
    primaryCharacter: null,
  },
};

const withPilotIntel: Decorator = (Story) =>
  createElement(PilotIntelContext.Provider, { value: mockPilotIntel }, createElement(Story));

const meta: Meta<typeof WealthSummaryBar> = {
  title: 'Characters & Account/Dashboard/WealthSummaryBar',
  component: WealthSummaryBar,
  tags: ['autodocs'],
  decorators: [withPilotIntel],
};
export default meta;
type Story = StoryObj<typeof WealthSummaryBar>;

export const Default: Story = {};

export const Wealthy: Story = {
  decorators: [
    (Story) =>
      createElement(
        PilotIntelContext.Provider,
        {
          value: {
            ...mockPilotIntel,
            derived: {
              ...mockPilotIntel.derived,
              totalWallet: 48_000_000_000,
              totalSellOrderValue: 12_000_000_000,
              totalBuyEscrow: 5_000_000_000,
              totalNetWorth: 65_000_000_000,
            },
          },
        },
        createElement(Story),
      ),
  ],
};
