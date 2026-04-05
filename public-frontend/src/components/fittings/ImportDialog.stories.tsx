import type { Meta, StoryObj } from '@storybook/react';
import { ImportDialog } from './ImportDialog';
import { fittingsHandlers } from '../../../.storybook/mocks/handlers/fittings';
import { fn } from '@storybook/test';

const meta: Meta<typeof ImportDialog> = {
  title: 'Fittings & Navigation/Fittings/ImportDialog',
  component: ImportDialog,
  tags: ['autodocs'],
  parameters: {
    msw: { handlers: fittingsHandlers },
  },
  args: {
    onClose: fn(),
  },
};
export default meta;
type Story = StoryObj<typeof ImportDialog>;

export const PasteStep: Story = {
  args: {
    open: true,
  },
};

export const Closed: Story = {
  args: {
    open: false,
  },
};
