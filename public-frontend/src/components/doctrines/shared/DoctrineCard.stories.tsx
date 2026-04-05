import type { Meta, StoryObj } from '@storybook/react';
import { DoctrineCard } from './DoctrineCard';

const meta: Meta<typeof DoctrineCard> = {
  title: 'Doctrines/DoctrineCard',
  component: DoctrineCard,
  parameters: { layout: 'padded' },
};
export default meta;
type Story = StoryObj<typeof DoctrineCard>;

export const Default: Story = {
  args: {
    name: 'Muninn Fleet',
    rank: 1,
    metrics: {
      iskEfficiency: 1.87,
      kdRatio: 2.4,
      winRate: 68,
      survivalRate: 72,
    },
    color: '#ff4444',
  },
};

export const SecondRank: Story = {
  args: {
    name: 'Eagle Fleet',
    rank: 2,
    metrics: {
      iskEfficiency: 1.45,
      kdRatio: 1.8,
      winRate: 55,
      survivalRate: 65,
    },
    color: '#00d4ff',
  },
};

export const PoorPerformance: Story = {
  args: {
    name: 'Ferox Fleet',
    rank: 5,
    metrics: {
      iskEfficiency: 0.6,
      kdRatio: 0.8,
      winRate: 32,
      survivalRate: 45,
    },
    color: '#a855f7',
  },
};
