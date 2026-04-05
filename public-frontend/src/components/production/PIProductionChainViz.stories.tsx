import type { Meta, StoryObj } from '@storybook/react';
import { PIProductionChainViz } from './PIProductionChainViz';
import type { ChainItem, Connection } from './PIProductionChainViz';

const sampleColumns: Record<number, ChainItem[]> = {
  0: [
    { name: 'Aqueous Liquids' },
    { name: 'Base Metals' },
    { name: 'Noble Metals' },
  ],
  1: [
    { name: 'Water' },
    { name: 'Reactive Metals' },
    { name: 'Precious Metals' },
  ],
  2: [
    { name: 'Coolant', subtitle: 'Water + Electrolytes' },
    { name: 'Mechanical Parts', subtitle: 'Reactive Metals + Precious Metals' },
  ],
  3: [
    { name: 'Robotics', subtitle: 'Mechanical Parts + Consumer Electronics' },
  ],
};

const sampleConnections: Connection[] = [
  { from: 'Aqueous Liquids', fromTier: 0, to: 'Water', toTier: 1 },
  { from: 'Base Metals', fromTier: 0, to: 'Reactive Metals', toTier: 1 },
  { from: 'Noble Metals', fromTier: 0, to: 'Precious Metals', toTier: 1 },
  { from: 'Water', fromTier: 1, to: 'Coolant', toTier: 2 },
  { from: 'Reactive Metals', fromTier: 1, to: 'Mechanical Parts', toTier: 2 },
  { from: 'Precious Metals', fromTier: 1, to: 'Mechanical Parts', toTier: 2 },
  { from: 'Mechanical Parts', fromTier: 2, to: 'Robotics', toTier: 3 },
];

const sampleTypeIds: Record<string, number> = {
  'Aqueous Liquids': 2268,
  'Base Metals': 2267,
  'Noble Metals': 2270,
  'Water': 3645,
  'Reactive Metals': 3646,
  'Precious Metals': 3647,
  'Coolant': 9832,
  'Mechanical Parts': 9834,
  'Robotics': 9848,
};

const meta: Meta<typeof PIProductionChainViz> = {
  title: 'Production/PI Chain/PIProductionChainViz',
  component: PIProductionChainViz,
  tags: ['autodocs'],
  parameters: {
    layout: 'padded',
  },
};

export default meta;
type Story = StoryObj<typeof PIProductionChainViz>;

/**
 * Robotics production chain: P0 raw resources through P1, P2, to P3.
 * Hover items to highlight connected chain. Bezier connection lines
 * between tier columns.
 */
export const RoboticsChain: Story = {
  args: {
    tierColumns: sampleColumns,
    connections: sampleConnections,
    chainTypeIds: sampleTypeIds,
    title: 'Robotics Production Chain',
    finalProduct: { name: 'Robotics', tier: 3 },
    p0PlanetMap: {
      'Aqueous Liquids': ['temperate', 'oceanic'],
      'Base Metals': ['lava', 'barren'],
      'Noble Metals': ['barren', 'plasma'],
    },
  },
};

/** Minimal chain: only two tiers with a single connection. */
export const MinimalChain: Story = {
  args: {
    tierColumns: {
      0: [{ name: 'Aqueous Liquids' }],
      1: [{ name: 'Water' }],
    },
    connections: [
      { from: 'Aqueous Liquids', fromTier: 0, to: 'Water', toTier: 1 },
    ],
    title: 'Simple P0 to P1',
  },
};
