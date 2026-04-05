import type { Meta, StoryObj } from '@storybook/react';
import { Sparkline, IsotopeSparkline } from './Sparkline';

// ---------------------------------------------------------------------------
// Sparkline
// ---------------------------------------------------------------------------

const meta: Meta<typeof Sparkline> = {
  title: 'Shared UI/Sparkline',
  component: Sparkline,
  tags: ['autodocs'],
  parameters: {
    layout: 'padded',
  },
  argTypes: {
    color: { control: 'color' },
    fillColor: { control: 'color' },
    strokeWidth: { control: { type: 'range', min: 0.5, max: 4, step: 0.5 } },
    showArea: { control: 'boolean' },
    width: { control: { type: 'range', min: 60, max: 300, step: 10 } },
    height: { control: { type: 'range', min: 20, max: 80, step: 5 } },
  },
};

export default meta;
type Story = StoryObj<typeof Sparkline>;

// Realistic EVE Online kill activity data (7-day hourly buckets)
const risingData = [12, 15, 18, 14, 22, 28, 35, 42, 38, 45, 52, 48, 55, 60];
const fallingData = [60, 55, 48, 52, 45, 38, 42, 35, 28, 22, 18, 14, 15, 12];
const flatData = [30, 32, 28, 31, 29, 33, 30, 31, 29, 32, 30, 28, 31, 30];
const volatileData = [10, 45, 12, 55, 8, 60, 15, 48, 5, 52, 20, 42, 10, 50];

export const Default: Story = {
  args: {
    data: risingData,
    width: 120,
    height: 32,
  },
};

export const RisingTrend: Story = {
  args: {
    data: risingData,
    color: 'auto',
    width: 150,
    height: 40,
  },
};

export const FallingTrend: Story = {
  args: {
    data: fallingData,
    color: 'auto',
    width: 150,
    height: 40,
  },
};

export const FlatTrend: Story = {
  args: {
    data: flatData,
    color: 'auto',
    width: 150,
    height: 40,
  },
};

export const VolatileData: Story = {
  args: {
    data: volatileData,
    color: '#ff8800',
    width: 150,
    height: 40,
  },
};

export const CustomColors: Story = {
  args: {
    data: risingData,
    color: '#00d4ff',
    fillColor: '#00d4ff',
    width: 200,
    height: 50,
    strokeWidth: 2,
  },
};

export const NoArea: Story = {
  args: {
    data: risingData,
    showArea: false,
    width: 150,
    height: 40,
  },
};

export const InsufficientData: Story = {
  args: {
    data: [42],
    width: 100,
    height: 30,
  },
};

export const EmptyData: Story = {
  args: {
    data: [],
    width: 100,
    height: 30,
  },
};

// ---------------------------------------------------------------------------
// IsotopeSparkline
// ---------------------------------------------------------------------------

const now = new Date();
const isotopeSnapshots = Array.from({ length: 24 }, (_, i) => ({
  delta_percent: Math.random() * 15,
  timestamp: new Date(now.getTime() - (23 - i) * 3600000).toISOString(),
}));

const highDeltaSnapshots = Array.from({ length: 24 }, (_, i) => ({
  delta_percent: 8 + Math.random() * 7,
  timestamp: new Date(now.getTime() - (23 - i) * 3600000).toISOString(),
}));

const lowDeltaSnapshots = Array.from({ length: 24 }, (_, i) => ({
  delta_percent: 1 + Math.random() * 3,
  timestamp: new Date(now.getTime() - (23 - i) * 3600000).toISOString(),
}));

export const IsotopeDefault: StoryObj<typeof IsotopeSparkline> = {
  render: () => (
    <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
      <span style={{ color: '#fff', fontSize: '0.8rem' }}>Isotope Delta:</span>
      <IsotopeSparkline snapshots={isotopeSnapshots} />
    </div>
  ),
};

export const IsotopeHighDelta: StoryObj<typeof IsotopeSparkline> = {
  render: () => (
    <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
      <span style={{ color: '#ff4444', fontSize: '0.8rem' }}>Critical:</span>
      <IsotopeSparkline snapshots={highDeltaSnapshots} />
    </div>
  ),
};

export const IsotopeLowDelta: StoryObj<typeof IsotopeSparkline> = {
  render: () => (
    <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
      <span style={{ color: '#00ff88', fontSize: '0.8rem' }}>Stable:</span>
      <IsotopeSparkline snapshots={lowDeltaSnapshots} />
    </div>
  ),
};
