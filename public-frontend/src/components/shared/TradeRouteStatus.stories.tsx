import type { Meta, StoryObj } from '@storybook/react';
import { TradeRouteStatus } from './TradeRouteStatus';
import {
  mockTradeRouteDangerous,
  mockTradeRouteSafe,
} from '../../../.storybook/mocks/data/alliances';

const meta: Meta<typeof TradeRouteStatus> = {
  title: 'Intel & Battle/Alliance Views/TradeRouteStatus',
  component: TradeRouteStatus,
  tags: ['autodocs'],
  parameters: {
    layout: 'padded',
  },
  argTypes: {
    onSystemClick: { action: 'systemClicked' },
  },
};

export default meta;
type Story = StoryObj<typeof TradeRouteStatus>;

export const Default: Story = {
  args: {
    route: mockTradeRouteDangerous,
    perspective: 'threat',
  },
};

export const SafeRoute: Story = {
  args: {
    route: mockTradeRouteSafe,
    perspective: 'threat',
  },
};

export const LogisticsPerspective: Story = {
  args: {
    route: mockTradeRouteDangerous,
    perspective: 'logistics',
  },
};

export const Compact: Story = {
  args: {
    route: mockTradeRouteDangerous,
    perspective: 'threat',
    compact: true,
  },
};

export const SafeLogistics: Story = {
  args: {
    route: mockTradeRouteSafe,
    perspective: 'logistics',
    compact: false,
  },
};
