import { Link } from 'react-router-dom';

interface AllianceLinkProps {
  allianceId: number;
  name: string;
  showLogo?: boolean;
  logoSize?: number;
  style?: React.CSSProperties;
}

/**
 * Clickable alliance name that links to the alliance detail page.
 * Use this component wherever an alliance name is displayed.
 */
export function AllianceLink({ allianceId, name, showLogo = false, logoSize = 20, style }: AllianceLinkProps) {
  return (
    <Link
      to={`/alliance/${allianceId}`}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '0.5rem',
        color: 'inherit',
        textDecoration: 'none',
        ...style
      }}
      title={`View ${name} intelligence`}
    >
      {showLogo && (
        <img
          src={`https://images.evetech.net/alliances/${allianceId}/logo?size=32`}
          alt=""
          loading="lazy"
          decoding="async"
          style={{ width: logoSize, height: logoSize, borderRadius: 4, flexShrink: 0 }}
          onError={(e) => { e.currentTarget.style.display = 'none'; }}
        />
      )}
      <span style={{
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        whiteSpace: 'nowrap',
        borderBottom: '1px dotted currentColor'
      }}>
        {name}
      </span>
    </Link>
  );
}

export default AllianceLink;
