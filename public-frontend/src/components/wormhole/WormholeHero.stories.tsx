import type { Meta, StoryObj } from '@storybook/react';
import { WormholeHero } from './WormholeHero';
import {
  mockWormholeSummary,
  mockWormholeSummaryLow,
} from '../../../.storybook/mocks/data/wormhole';

const meta: Meta<typeof WormholeHero> = {
  title: 'Intel & Battle/Wormhole/WormholeHero',
  component: WormholeHero,
  tags: ['autodocs'],
  parameters: {
    layout: 'padded',
  },
};

export default meta;
type Story = StoryObj<typeof WormholeHero>;

export const Default: Story = {
  args: {
    summary: mockWormholeSummary,
    lastUpdated: new Date(),
    loading: false,
  },
};

export const LowActivity: Story = {
  args: {
    summary: mockWormholeSummaryLow,
    lastUpdated: new Date(),
    loading: false,
  },
};

export const Loading: Story = {
  args: {
    summary: null,
    lastUpdated: new Date(),
    loading: true,
  },
};

export const NoSummary: Story = {
  args: {
    summary: null,
    lastUpdated: new Date(),
    loading: false,
  },
};
