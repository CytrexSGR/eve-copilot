import type { Meta, StoryObj } from '@storybook/react';
import { BuybackTab } from './BuybackTab';
import { financeHandlers } from '../../../.storybook/mocks/handlers/finance';

const meta: Meta<typeof BuybackTab> = {
  title: 'Corporation Tools/Finance/BuybackTab',
  component: BuybackTab,
  tags: ['autodocs'],
  parameters: {
    msw: { handlers: financeHandlers },
  },
};
export default meta;
type Story = StoryObj<typeof BuybackTab>;

export const Default: Story = {
  args: {
    corpId: 98378388,
  },
};
