import type { Meta, StoryObj } from '@storybook/react';
import { SrpStatsTab } from './SrpStatsTab';
import { financeHandlers } from '../../../.storybook/mocks/handlers/finance';

const meta: Meta<typeof SrpStatsTab> = {
  title: 'Corporation Tools/SRP/SrpStatsTab',
  component: SrpStatsTab,
  tags: ['autodocs'],
  parameters: {
    msw: { handlers: financeHandlers },
  },
};
export default meta;
type Story = StoryObj<typeof SrpStatsTab>;

export const Default: Story = {
  args: {
    corpId: 98378388,
  },
};
