import type { Meta, StoryObj } from '@storybook/react';
import { EveImage, AllianceLogo, CorpLogo, CharacterPortrait, ShipRender, ShipIcon } from './EveImage';

const meta: Meta<typeof EveImage> = {
  title: 'Shared UI/EveImage',
  component: EveImage,
  tags: ['autodocs'],
  parameters: {
    layout: 'padded',
  },
  argTypes: {
    type: {
      control: 'select',
      options: ['alliance', 'corporation', 'character', 'type'],
    },
    variant: {
      control: 'select',
      options: ['logo', 'portrait', 'render', 'icon'],
    },
    size: {
      control: 'select',
      options: [32, 64, 128, 256, 512],
    },
    eager: { control: 'boolean' },
  },
};

export default meta;
type Story = StoryObj<typeof EveImage>;

// Well-known EVE Online entity IDs
const FRATERNITY_ALLIANCE_ID = 99003581;
const CORP_ID = 98378388; // Fraternity University
const CYTREX_CHARACTER_ID = 1117367444;
const DRAKE_TYPE_ID = 24698;
const GOLEM_TYPE_ID = 28710;
const MUNINN_TYPE_ID = 12015;

export const Default: Story = {
  args: {
    id: FRATERNITY_ALLIANCE_ID,
    type: 'alliance',
    size: 64,
  },
};

export const AllianceLogoSmall: Story = {
  render: () => (
    <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
      <AllianceLogo id={FRATERNITY_ALLIANCE_ID} size={32} />
      <span style={{ color: '#fff', fontSize: '0.85rem' }}>Fraternity.</span>
    </div>
  ),
};

export const AllianceLogoLarge: Story = {
  render: () => <AllianceLogo id={FRATERNITY_ALLIANCE_ID} size={128} />,
};

export const CorporationLogo: Story = {
  render: () => (
    <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
      <CorpLogo id={CORP_ID} size={64} />
      <div>
        <div style={{ color: '#fff', fontWeight: 700 }}>Fraternity University</div>
        <div style={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.75rem' }}>Training Corp</div>
      </div>
    </div>
  ),
};

export const CharacterPortraitStory: Story = {
  name: 'Character Portrait',
  render: () => (
    <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
      <CharacterPortrait id={CYTREX_CHARACTER_ID} size={64} style={{ borderRadius: '50%' }} />
      <div>
        <div style={{ color: '#fff', fontWeight: 700 }}>Cytrex</div>
        <div style={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.75rem' }}>63.1M SP</div>
      </div>
    </div>
  ),
};

export const ShipRenderStory: Story = {
  name: 'Ship Render',
  render: () => (
    <div style={{ display: 'flex', gap: '2rem', alignItems: 'flex-end' }}>
      <div style={{ textAlign: 'center' }}>
        <ShipRender id={DRAKE_TYPE_ID} size={128} />
        <div style={{ color: '#fff', fontSize: '0.75rem', marginTop: '0.5rem' }}>Drake</div>
      </div>
      <div style={{ textAlign: 'center' }}>
        <ShipRender id={GOLEM_TYPE_ID} size={128} />
        <div style={{ color: '#fff', fontSize: '0.75rem', marginTop: '0.5rem' }}>Golem</div>
      </div>
      <div style={{ textAlign: 'center' }}>
        <ShipRender id={MUNINN_TYPE_ID} size={128} />
        <div style={{ color: '#fff', fontSize: '0.75rem', marginTop: '0.5rem' }}>Muninn</div>
      </div>
    </div>
  ),
};

export const ShipIconStory: Story = {
  name: 'Ship Icon',
  render: () => (
    <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
      <ShipIcon id={DRAKE_TYPE_ID} size={32} />
      <ShipIcon id={GOLEM_TYPE_ID} size={32} />
      <ShipIcon id={MUNINN_TYPE_ID} size={32} />
    </div>
  ),
};

export const AllSizes: Story = {
  render: () => (
    <div style={{ display: 'flex', gap: '1rem', alignItems: 'flex-end' }}>
      {([32, 64, 128, 256] as const).map((size) => (
        <div key={size} style={{ textAlign: 'center' }}>
          <EveImage id={FRATERNITY_ALLIANCE_ID} type="alliance" size={size} />
          <div style={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.65rem', marginTop: '0.25rem' }}>
            {size}px
          </div>
        </div>
      ))}
    </div>
  ),
};

export const BrokenImage: Story = {
  args: {
    id: 999999999,
    type: 'alliance',
    size: 64,
  },
};
