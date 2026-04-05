import type { Meta, StoryObj } from '@storybook/react';
import { SignalsTab } from './SignalsTab';
import { fn } from '@storybook/test';
import {
  mockFuelTrends,
  mockManipulationAlerts,
  mockSupercapTimers,
} from '../../../.storybook/mocks/data/war-economy';

const meta: Meta<typeof SignalsTab> = {
  title: 'Economy & Market/War Economy/SignalsTab',
  component: SignalsTab,
  tags: ['autodocs'],
  parameters: {
    layout: 'padded',
  },
};

export default meta;
type Story = StoryObj<typeof SignalsTab>;

/**
 * Default: Fuel isotope trends with sparklines, manipulation
 * alerts with severity badges, and supercap construction timers.
 * Capital intelligence section with alliance breakdown.
 */
export const Default: Story = {
  args: {
    selectedRegion: 10000002,
    onRegionChange: fn(),
    fuelTrends: mockFuelTrends,
    manipulationAlerts: mockManipulationAlerts,
    supercapTimers: mockSupercapTimers,
    capitalAlliances: null,
    expandedAlliances: new Set<number>(),
    onToggleAlliance: fn(),
    loading: false,
  },
};

/** Loading state: shows skeleton placeholder. */
export const Loading: Story = {
  args: {
    selectedRegion: 10000002,
    onRegionChange: fn(),
    fuelTrends: null,
    manipulationAlerts: null,
    supercapTimers: null,
    capitalAlliances: null,
    expandedAlliances: new Set<number>(),
    onToggleAlliance: fn(),
    loading: true,
  },
};

/** Stable markets: no manipulation alerts, no supercap timers. */
export const StableMarkets: Story = {
  args: {
    selectedRegion: 10000002,
    onRegionChange: fn(),
    fuelTrends: mockFuelTrends,
    manipulationAlerts: { region_id: 10000002, count: 0, alerts: [] },
    supercapTimers: { count: 0, timers: [] },
    capitalAlliances: null,
    expandedAlliances: new Set<number>(),
    onToggleAlliance: fn(),
    loading: false,
  },
};
