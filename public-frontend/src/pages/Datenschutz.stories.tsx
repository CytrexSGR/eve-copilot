import type { Meta, StoryObj } from '@storybook/react';
import { Datenschutz } from './Datenschutz';

const meta: Meta<typeof Datenschutz> = {
  title: 'Pages/Datenschutz',
  component: Datenschutz,
  tags: ['autodocs'],
};
export default meta;
type Story = StoryObj<typeof Datenschutz>;

export const Default: Story = {};
