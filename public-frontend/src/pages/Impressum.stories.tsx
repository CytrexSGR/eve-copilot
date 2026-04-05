import type { Meta, StoryObj } from '@storybook/react';
import { Impressum } from './Impressum';

const meta: Meta<typeof Impressum> = {
  title: 'Pages/Impressum',
  component: Impressum,
  tags: ['autodocs'],
};
export default meta;
type Story = StoryObj<typeof Impressum>;

export const Default: Story = {};
