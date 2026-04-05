import type { Meta, StoryObj } from '@storybook/react';
import { TradeRoutesSummary } from './TradeRoutesSummary';
import type { TradeRoutes } from '../../types/reports';
import { fn } from '@storybook/test';

const mockReport: TradeRoutes = {
  period: '24h',
  global: {
    total_routes: 12,
    dangerous_routes: 4,
    avg_danger_score: 3.8,
    gate_camps_detected: 7,
  },
  routes: [],
};

const meta: Meta<typeof TradeRoutesSummary> = {
  title: 'Economy & Market/Supply Chain/TradeRoutesSummary',
  component: TradeRoutesSummary,
  tags: ['autodocs'],
  parameters: {
    layout: 'padded',
  },
  args: {
    onTimeChange: fn(),
  },
};

export default meta;
type Story = StoryObj<typeof TradeRoutesSummary>;

/**
 * Default: shows Trade Route Intelligence header with global stats
 * (routes analyzed, dangerous, gate camps, avg danger score)
 * and time period selector.
 */
export const Default: Story = {
  args: {
    report: mockReport,
    selectedMinutes: 1440,
    lastUpdated: new Date(),
  },
};

/** 1-hour view: shorter time period selected. */
export const OneHourView: Story = {
  args: {
    report: {
      ...mockReport,
      global: {
        total_routes: 12,
        dangerous_routes: 2,
        avg_danger_score: 2.1,
        gate_camps_detected: 3,
      },
    },
    selectedMinutes: 60,
    lastUpdated: new Date(),
  },
};
