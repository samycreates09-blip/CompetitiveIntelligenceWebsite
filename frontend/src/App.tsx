import { useMemo, useState } from 'react';
import { Sidebar } from './components/Sidebar';
import { TopBar } from './components/TopBar';
import OverviewPage from './pages/OverviewPage';
import PlansPage from './pages/PlansPage';
import DevicesPage from './pages/DevicesPage';
import PromotionsPage from './pages/PromotionsPage';
import ChangesPage from './pages/ChangesPage';
import ChatPage from './pages/ChatPage';

const navItems = [
  { key: 'overview', label: 'Overview' },
  { key: 'plans', label: 'Plans' },
  { key: 'devices', label: 'Devices' },
  { key: 'promotions', label: 'Promotions' },
  { key: 'changes', label: 'Changes' },
  { key: 'chat', label: 'Ask AI' },
] as const;

type PageKey = (typeof navItems)[number]['key'];

export default function App() {
  const [activePage, setActivePage] = useState<PageKey>('overview');

  const pageContent = useMemo(() => {
    switch (activePage) {
      case 'overview':
        return <OverviewPage />;
      case 'plans':
        return <PlansPage />;
      case 'devices':
        return <DevicesPage />;
      case 'promotions':
        return <PromotionsPage />;
      case 'changes':
        return <ChangesPage />;
      case 'chat':
        return <ChatPage />;
      default:
        return <OverviewPage />;
    }
  }, [activePage]);

  return (
    <div className="app-shell">
      <TopBar />
      <Sidebar items={navItems} activeKey={activePage} onSelect={setActivePage} />
      <main className="main-content">
        <div className="page-container">{pageContent}</div>
      </main>
    </div>
  );
}
