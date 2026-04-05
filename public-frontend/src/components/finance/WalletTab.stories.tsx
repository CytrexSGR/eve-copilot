import type { Meta, StoryObj } from '@storybook/react';
import { WalletTab } from './WalletTab';
import { financeHandlers } from '../../../.storybook/mocks/handlers/finance';

const meta: Meta<typeof WalletTab> = {
  title: 'Corporation Tools/Finance/WalletTab',
  component: WalletTab,
  tags: ['autodocs'],
  parameters: {
    msw: { handlers: financeHandlers },
  },
};
export default meta;
type Story = StoryObj<typeof WalletTab>;

export const Default: Story = {
  args: {
    corpId: 98378388,
  },
};
