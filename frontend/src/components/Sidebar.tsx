type NavItem<K extends string> = { key: K; label: string };

type SidebarProps<K extends string> = {
  items: readonly NavItem<K>[];
  activeKey: K;
  onSelect: (key: K) => void;
};

export function Sidebar<K extends string>({ items, activeKey, onSelect }: SidebarProps<K>) {
  return (
    <aside className="sidebar">
      <nav className="sidebar-nav" aria-label="Primary navigation">
        {items.map((item) => (
          <button
            key={item.key}
            type="button"
            className={item.key === activeKey ? 'sidebar-link active' : 'sidebar-link'}
            aria-current={item.key === activeKey ? 'page' : undefined}
            onClick={() => onSelect(item.key)}
          >
            {item.label}
          </button>
        ))}
      </nav>
    </aside>
  );
}
