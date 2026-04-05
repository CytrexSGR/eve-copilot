import type { Meta, StoryObj } from '@storybook/react';
import { VettingTab } from './VettingTab';
import { financeHandlers } from '../../../.storybook/mocks/handlers/finance';

const meta: Meta<typeof VettingTab> = {
  title: 'Corporation Tools/HR/VettingTab',
  component: VettingTab,
  tags: ['autodocs'],
  parameters: {
    msw: { handlers: financeHandlers },
  },
};
export default meta;
type Story = StoryObj<typeof VettingTab>;

export const Default: Story = {
  args: {
    corpId: 98378388,
  },
};
