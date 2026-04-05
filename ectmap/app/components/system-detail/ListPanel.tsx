'use client';

// Base interface that all list items must satisfy
interface ListItem {
  _key: number;
}

interface ListPanelProps<T extends ListItem> {
  title: string;
  items: T[];
  onClose: () => void;
  onSelectItem: (item: T) => void;
  getItemName: (item: T) => string;
  getItemSubtitle?: (item: T) => string;
}

export default function ListPanel<T extends ListItem>({
  title,
  items,
  onClose,
  onSelectItem,
  getItemName,
  getItemSubtitle,
}: ListPanelProps<T>) {
  return (
    <div className="absolute top-1/2 right-4 transform -translate-y-1/2 bg-gray-900 border border-gray-700 rounded-lg shadow-lg max-w-md w-80 overflow-hidden max-h-[90vh] overflow-y-auto detail-panel-scroll">
      <div className="bg-gray-800 px-4 py-3 flex justify-between items-center border-b border-gray-700 sticky top-0 z-10">
        <h3 className="text-white font-semibold text-lg">
          {title} ({items.length})
        </h3>
        <button onClick={onClose} className="text-gray-400 hover:text-white text-xl">
          ×
        </button>
      </div>
      <div className="p-2">
        {items.map((item) => (
          <button
            key={item._key}
            onClick={() => onSelectItem(item)}
            className="w-full text-left px-4 py-3 hover:bg-gray-800 rounded transition-colors border-b border-gray-800 last:border-b-0"
          >
            <div className="text-white font-medium">{getItemName(item)}</div>
            {getItemSubtitle && (
              <div className="text-gray-400 text-sm mt-1">{getItemSubtitle(item)}</div>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}
