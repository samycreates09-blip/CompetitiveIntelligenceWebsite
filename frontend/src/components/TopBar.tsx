export function TopBar() {
  return (
    <header className="topbar">
      <div className="brand">
        <span className="brand-mark">BOOST</span>
        <span className="brand-sep" aria-hidden="true">|</span>
        <span className="brand-subtitle">Competitive Intelligence</span>
      </div>
      <div className="topbar-right">
        <span className="demo-badge">Synthetic demo data</span>
        <div className="user-chip">
          <span className="user-avatar" aria-hidden="true">S</span>
          <span className="user-name">Sam</span>
        </div>
      </div>
    </header>
  );
}
