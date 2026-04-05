/**
 * EveImage - Optimized image component for EVE Online assets
 *
 * Features:
 * - Lazy loading by default
 * - Automatic error handling (hides broken images)
 * - Preconnect hint already in index.html
 */

import type { ImgHTMLAttributes } from 'react';

const EVE_IMAGE_BASE = 'https://images.evetech.net';

type ImageType = 'alliance' | 'corporation' | 'character' | 'type';
type ImageVariant = 'logo' | 'portrait' | 'render' | 'icon';

interface EveImageProps extends Omit<ImgHTMLAttributes<HTMLImageElement>, 'src' | 'id'> {
  /** Entity ID (alliance_id, corporation_id, character_id, or type_id) */
  id: number;
  /** Type of entity */
  type: ImageType;
  /** Image variant (default: logo for alliance/corp, portrait for character, render for type) */
  variant?: ImageVariant;
  /** Image size in pixels (default: 32) */
  size?: 32 | 64 | 128 | 256 | 512;
  /** Disable lazy loading (for above-the-fold images) */
  eager?: boolean;
}

function getDefaultVariant(type: ImageType): ImageVariant {
  switch (type) {
    case 'alliance':
    case 'corporation':
      return 'logo';
    case 'character':
      return 'portrait';
    case 'type':
      return 'render';
  }
}

function buildUrl(type: ImageType, id: number, variant: ImageVariant, size: number): string {
  const plural = type === 'type' ? 'types' : `${type}s`;
  return `${EVE_IMAGE_BASE}/${plural}/${id}/${variant}?size=${size}`;
}

export function EveImage({
  id,
  type,
  variant,
  size = 32,
  eager = false,
  style,
  onError,
  ...props
}: EveImageProps) {
  const actualVariant = variant || getDefaultVariant(type);
  const src = buildUrl(type, id, actualVariant, size);

  return (
    <img
      src={src}
      loading={eager ? 'eager' : 'lazy'}
      decoding="async"
      style={{
        width: size,
        height: size,
        ...style,
      }}
      onError={(e) => {
        // Hide broken images
        e.currentTarget.style.display = 'none';
        onError?.(e);
      }}
      {...props}
    />
  );
}

// Convenience exports for common use cases
export const AllianceLogo = (props: Omit<EveImageProps, 'type'>) => (
  <EveImage type="alliance" {...props} />
);

export const CorpLogo = (props: Omit<EveImageProps, 'type'>) => (
  <EveImage type="corporation" {...props} />
);

export const CharacterPortrait = (props: Omit<EveImageProps, 'type'>) => (
  <EveImage type="character" variant="portrait" {...props} />
);

export const ShipRender = (props: Omit<EveImageProps, 'type'>) => (
  <EveImage type="type" variant="render" {...props} />
);

export const ShipIcon = (props: Omit<EveImageProps, 'type'>) => (
  <EveImage type="type" variant="icon" {...props} />
);

export default EveImage;
