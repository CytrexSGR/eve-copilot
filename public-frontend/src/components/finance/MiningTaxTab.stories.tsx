import type { Meta, StoryObj } from '@storybook/react';
import { MiningTaxTab } from './MiningTaxTab';
import { financeHandlers } from '../../../.storybook/mocks/handlers/finance';

const meta: Meta<typeof MiningTaxTab> = {
  title: 'Corporation Tools/Finance/MiningTaxTab',
  component: MiningTaxTab,
  tags: ['autodocs'],
  parameters: {
    msw: { handlers: financeHandlers },
  },
};
export default meta;
type Story = StoryObj<typeof MiningTaxTab>;

export const Default: Story = {
  args: {
    corpId: 98378388,
  },
};
