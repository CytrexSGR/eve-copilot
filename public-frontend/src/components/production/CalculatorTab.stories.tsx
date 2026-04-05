import type { Meta, StoryObj } from '@storybook/react';
import { CalculatorTab } from './CalculatorTab';
import { fn } from '@storybook/test';

const meta: Meta<typeof CalculatorTab> = {
  title: 'Production/Projects/CalculatorTab',
  component: CalculatorTab,
  tags: ['autodocs'],
  parameters: {
    layout: 'padded',
  },
};

export default meta;
type Story = StoryObj<typeof CalculatorTab>;

/**
 * Drake blueprint: shows BOM, financial analysis, production time,
 * and facility comparison button. Fetches simulation data via MSW.
 */
export const Drake: Story = {
  args: {
    selectedItem: { typeID: 24698, typeName: 'Drake', groupName: 'Battlecruiser' },
    onNavigateToMaterial: fn(),
  },
};

/** Rifter blueprint: cheaper T1 frigate for comparison. */
export const Rifter: Story = {
  args: {
    selectedItem: { typeID: 587, typeName: 'Rifter', groupName: 'Frigate' },
    onNavigateToMaterial: fn(),
  },
};

/** Without navigation callback: material names are not clickable. */
export const WithoutNavigation: Story = {
  args: {
    selectedItem: { typeID: 24698, typeName: 'Drake', groupName: 'Battlecruiser' },
  },
};
