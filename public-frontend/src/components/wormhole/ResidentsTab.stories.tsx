import type { Meta, StoryObj } from '@storybook/react';
import { ResidentsTab } from './ResidentsTab';
import {
  mockThreats,
  mockEvictions,
} from '../../../.storybook/mocks/data/wormhole';

const meta: Meta<typeof ResidentsTab> = {
  title: 'Intel & Battle/Wormhole/ResidentsTab',
  component: ResidentsTab,
  tags: ['autodocs'],
  parameters: {
    layout: 'padded',
  },
  argTypes: {
    onClassChange: { action: 'classChanged' },
    onSystemSearch: { action: 'systemSearched' },
  },
};

export default meta;
type Story = StoryObj<typeof ResidentsTab>;

export const Default: Story = {
  args: {
    threats: mockThreats,
    evictions: mockEvictions,
    selectedClass: null,
    onClassChange: () => {},
    onSystemSearch: () => {},
  },
};

export const Class5Selected: Story = {
  args: {
    threats: mockThreats,
    evictions: mockEvictions,
    selectedClass: 5,
    onClassChange: () => {},
    onSystemSearch: () => {},
  },
};

export const NoData: Story = {
  args: {
    threats: [],
    evictions: [],
    selectedClass: null,
    onClassChange: () => {},
    onSystemSearch: () => {},
  },
};
