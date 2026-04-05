import type { Meta, StoryObj } from '@storybook/react';
import { WormholeTicker } from './WormholeTicker';
import {
  mockThreats,
  mockEvictions,
} from '../../../.storybook/mocks/data/wormhole';

const meta: Meta<typeof WormholeTicker> = {
  title: 'Intel & Battle/Wormhole/WormholeTicker',
  component: WormholeTicker,
  tags: ['autodocs'],
  parameters: {
    layout: 'padded',
  },
};

export default meta;
type Story = StoryObj<typeof WormholeTicker>;

export const Default: Story = {
  args: {
    threats: mockThreats,
    evictions: mockEvictions,
  },
};

export const ThreatsOnly: Story = {
  args: {
    threats: mockThreats,
    evictions: [],
  },
};

export const EvictionsOnly: Story = {
  args: {
    threats: [],
    evictions: mockEvictions,
  },
};

export const Empty: Story = {
  args: {
    threats: [],
    evictions: [],
  },
};

export const SingleThreat: Story = {
  args: {
    threats: [mockThreats[0]],
    evictions: [],
  },
};
