import type { Meta, StoryObj } from '@storybook/react';
import { LiveMapView } from './LiveMapView';

const meta: Meta<typeof LiveMapView> = {
  title: 'Intel & Battle/Alliance Views/LiveMapView',
  component: LiveMapView,
  tags: ['autodocs'],
  parameters: {
    layout: 'fullscreen',
  },
};

export default meta;
type Story = StoryObj<typeof LiveMapView>;

export const Alliance: Story = {
  args: {
    entityType: 'alliance',
    entityId: 99003581,
    days: 7,
  },
};

export const Corporation: Story = {
  args: {
    entityType: 'corporation',
    entityId: 98378388,
    days: 7,
  },
};

export const PowerBloc: Story = {
  args: {
    entityType: 'powerbloc',
    entityId: 99003581,
    days: 30,
  },
};
