import type { Meta, StoryObj } from '@storybook/react';
import { PlannerTab } from './PlannerTab';
import { fn } from '@storybook/test';
import { handlers } from '../../../.storybook/mocks/handlers';

const meta: Meta<typeof PlannerTab> = {
  title: 'Production/Projects/PlannerTab',
  component: PlannerTab,
  tags: ['autodocs'],
  parameters: {
    msw: { handlers },
    layout: 'padded',
  },
};

export default meta;
type Story = StoryObj<typeof PlannerTab>;

/**
 * Drake production chain: interactive tree with build/buy toggles,
 * collapsible nodes, quantity multiplier, and shopping list with
 * Jita prices. Fetches material chain data via MSW.
 */
export const Drake: Story = {
  args: {
    selectedItem: { typeID: 24698, typeName: 'Drake', groupName: 'Battlecruiser' },
    onNavigateToMaterial: fn(),
  },
};

/** Without navigation callback: material names not clickable. */
export const WithoutNavigation: Story = {
  args: {
    selectedItem: { typeID: 24698, typeName: 'Drake', groupName: 'Battlecruiser' },
  },
};

/** Project context: shows saved buy/make decisions. */
export const InProjectContext: Story = {
  args: {
    selectedItem: { typeID: 24698, typeName: 'Drake', groupName: 'Battlecruiser' },
    onNavigateToMaterial: fn(),
    projectItemId: 42,
    onDecisionsChanged: fn(),
  },
};

/**
 * Make-or-Buy decision variant — same Drake chain but intended for
 * demonstrating the toggle between BUILD (default) and BUY for
 * raw minerals. Click the build/buy toggle on any material row.
 */
export const MakeOrBuyDrake: Story = {
  args: {
    selectedItem: { typeID: 24698, typeName: 'Drake', groupName: 'Battlecruiser' },
    onNavigateToMaterial: fn(),
  },
};

/**
 * Deep chain with sub-components — Tengu (T3 Strategic Cruiser).
 * Multi-level tree: Tengu > Fullerene Intercalated Sheets > Fulleroferrocene > raw gas.
 * Exercises nested collapsible nodes and make-or-buy decisions at every level.
 * The MSW handler returns mockDeepMaterialChain for typeId 29984.
 */
export const DeepChain: Story = {
  args: {
    selectedItem: { typeID: 29984, typeName: 'Tengu', groupName: 'Strategic Cruiser' },
    onNavigateToMaterial: fn(),
  },
};
