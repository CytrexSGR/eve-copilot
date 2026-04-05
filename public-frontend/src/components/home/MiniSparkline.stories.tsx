import type { Meta, StoryObj } from '@storybook/react';
import { MiniSparkline } from './MiniSparkline';

const meta: Meta<typeof MiniSparkline> = {
  title: 'Home/MiniSparkline',
  component: MiniSparkline,
  parameters: { layout: 'centered' },
};
export default meta;
type Story = StoryObj<typeof MiniSparkline>;

export const RisingTrend: Story = {
  args: {
    data: [10, 12, 15, 14, 18, 22, 25, 28, 30],
    width: 100,
    height: 30,
  },
};

export const FallingTrend: Story = {
  args: {
    data: [30, 28, 25, 22, 18, 15, 14, 12, 10],
    width: 100,
    height: 30,
  },
};

export const Flat: Story = {
  args: {
    data: [20, 21, 19, 20, 21, 20, 19, 20, 21],
    width: 100,
    height: 30,
  },
};

export const CustomColor: Story = {
  args: {
    data: [5, 10, 8, 15, 12, 20, 18, 25],
    width: 80,
    height: 24,
    color: '#a855f7',
    showTrend: false,
  },
};

export const InsufficientData: Story = {
  args: {
    data: [10],
    width: 60,
    height: 20,
  },
};
