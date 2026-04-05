import type { Meta, StoryObj } from '@storybook/react';
import { FittingNameDialog } from './FittingNameDialog';
import { fn } from '@storybook/test';

const meta: Meta<typeof FittingNameDialog> = {
  title: 'Fittings & Navigation/Fittings/FittingNameDialog',
  component: FittingNameDialog,
  tags: ['autodocs'],
  args: {
    onClose: fn(),
    onSave: fn(),
  },
};
export default meta;
type Story = StoryObj<typeof FittingNameDialog>;

export const NewFitting: Story = {
  args: {
    open: true,
    initialName: '',
    saving: false,
    editingFittingId: null,
  },
};

export const WithInitialName: Story = {
  args: {
    open: true,
    initialName: 'Drake PvE L4',
    saving: false,
    editingFittingId: null,
  },
};

export const EditingExistingFitting: Story = {
  args: {
    open: true,
    initialName: 'Drake Shield Tank V2',
    saving: false,
    editingFittingId: 2001,
  },
};

export const SavingState: Story = {
  args: {
    open: true,
    initialName: 'My Fitting',
    saving: true,
    editingFittingId: null,
  },
};

export const Closed: Story = {
  args: {
    open: false,
    initialName: 'Test',
    saving: false,
    editingFittingId: null,
  },
};
