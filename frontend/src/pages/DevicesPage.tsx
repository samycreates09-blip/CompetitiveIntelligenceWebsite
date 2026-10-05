import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { DataState } from '../components/DataState';
import { PageHeader } from '../components/PageHeader';
import { PriceHistoryChart } from '../components/PriceHistoryChart';
import { api } from '../lib/api';
import { formatCurrency, formatDate } from '../lib/format';

export default function DevicesPage() {
  const [competitorId, setCompetitorId] = useState('all');
  const [manufacturer, setManufacturer] = useState('all');
  const [deviceType, setDeviceType] = useState('all');
  const [selectedDeviceId, setSelectedDeviceId] = useState<number | null>(null);
  const [fromDate, setFromDate] = useState('');
  const [toDate, setToDate] = useState('');

  const devicesQuery = useQuery({ queryKey: ['devices'], queryFn: () => api.getDevices() });
  const detailQuery = useQuery({
    queryKey: ['device', selectedDeviceId],
    queryFn: () => api.getDevice(selectedDeviceId as number),
    enabled: selectedDeviceId !== null,
  });
  const historyQuery = useQuery({
    queryKey: ['device-history', selectedDeviceId, fromDate, toDate],
    queryFn: () => api.getDeviceHistory(selectedDeviceId as number, {
      from_date: fromDate || undefined,
      to_date: toDate || undefined,
      order: 'asc',
    }),
    enabled: selectedDeviceId !== null,
  });

  const devices = devicesQuery.data ?? [];
  const manufacturers = [...new Set(devices.map((device) => device.manufacturer))].sort();
  const deviceTypes = [...new Set(devices.map((device) => device.device_type))].sort();
  const filteredDevices = useMemo(() => devices.filter((device) =>
    (competitorId === 'all' || device.competitor_id === Number(competitorId)) &&
    (manufacturer === 'all' || device.manufacturer === manufacturer) &&
    (deviceType === 'all' || device.device_type === deviceType),
  ), [devices, competitorId, manufacturer, deviceType]);

  if (devicesQuery.isPending) return <DataState status="loading" message="Loading device catalog" detail="Retrieving devices from the competitor API." />;
  if (devicesQuery.isError) return <DataState status="error" message="Device catalog unavailable" detail="The devices endpoint could not be reached." />;

  const competitors = [...new Map(devices.map((device) => [device.competitor_id, device.competitor_name])).entries()];
  const history = historyQuery.data ?? [];

  return (
    <div className="dashboard-page">
      <PageHeader eyebrow="Devices" title="Device pricing & history" note="Select a catalog item to inspect its captured price timeline." />
      <section className="filter-bar" aria-label="Device filters">
        <label>Competitor
          <select value={competitorId} onChange={(event) => setCompetitorId(event.target.value)}>
            <option value="all">All competitors</option>
            {competitors.map(([id, name]) => <option key={id} value={id}>{name}</option>)}
          </select>
        </label>
        <label>Manufacturer
          <select value={manufacturer} onChange={(event) => setManufacturer(event.target.value)}>
            <option value="all">All manufacturers</option>
            {manufacturers.map((value) => <option key={value}>{value}</option>)}
          </select>
        </label>
        <label>Device type
          <select value={deviceType} onChange={(event) => setDeviceType(event.target.value)}>
            <option value="all">All types</option>
            {deviceTypes.map((value) => <option key={value}>{value}</option>)}
          </select>
        </label>
        <span className="filter-count">{filteredDevices.length} devices</span>
      </section>

      {filteredDevices.length === 0 ? <DataState status="empty" message="No devices match these filters" /> : (
        <section className="device-catalog-grid" aria-label="Device catalog">
          {filteredDevices.map((device) => (
            <button
              key={device.device_id}
              type="button"
              className={`device-catalog-card${selectedDeviceId === device.device_id ? ' selected' : ''}`}
              aria-pressed={selectedDeviceId === device.device_id}
              onClick={() => setSelectedDeviceId(device.device_id)}
            >
              <span className="catalog-topline"><span>{device.competitor_name}</span><span className="catalog-id">#{device.device_id}</span></span>
              <strong>{device.model_name}</strong>
              <span>{device.manufacturer} · {device.device_type}</span>
              <small>{[device.storage_variant, device.color].filter(Boolean).join(' · ') || 'Configuration not specified'}</small>
            </button>
          ))}
        </section>
      )}

      {selectedDeviceId !== null ? (
        <section className="panel history-panel" aria-label="Selected device details">
          {detailQuery.isPending ? <DataState status="loading" message="Loading device details" /> : null}
          {detailQuery.isError ? <DataState status="error" message="Device details unavailable" /> : null}
          {detailQuery.isSuccess ? (
            <>
              <div className="panel-header device-detail-heading">
                <div>
                  <p className="plan-competitor">{detailQuery.data.competitor_name}</p>
                  <h3>{detailQuery.data.model_name}</h3>
                  <p className="subtle-copy">{detailQuery.data.manufacturer} · {detailQuery.data.device_type} · {[detailQuery.data.storage_variant, detailQuery.data.color].filter(Boolean).join(' · ')}</p>
                </div>
                <button type="button" className="secondary-button" onClick={() => setSelectedDeviceId(null)}>Close details</button>
              </div>
              <div className="panel-header history-subheader">
                <div><h4>Observed price history</h4><p className="subtle-copy">Snapshot date and effective date are shown separately.</p></div>
                <div className="date-filters">
                  <label>From<input type="date" value={fromDate} onChange={(event) => setFromDate(event.target.value)} /></label>
                  <label>To<input type="date" value={toDate} onChange={(event) => setToDate(event.target.value)} /></label>
                </div>
              </div>
              {historyQuery.isPending ? <DataState status="loading" message="Loading price history" /> : null}
              {historyQuery.isError ? <DataState status="error" message="Price history unavailable" detail="Try another date range or device." /> : null}
              {historyQuery.isSuccess && history.length === 0 ? <DataState status="empty" message="No price history in this date range" /> : null}
              {historyQuery.isSuccess && history.length > 0 ? (
                <>
                  <PriceHistoryChart series={[
                    { label: 'Retail price', color: '#60a5fa', values: history.map((entry) => ({ date: entry.source_snapshot_date, value: entry.retail_price_usd })) },
                    { label: 'Promo price', color: '#c084fc', values: history.map((entry) => ({ date: entry.source_snapshot_date, value: entry.promo_price_usd })) },
                  ]} />
                  <div className="table-scroll">
                    <table className="data-table">
                      <thead><tr><th>Snapshot</th><th>Effective</th><th>Retail</th><th>Promo</th><th>Promotion / financing terms</th></tr></thead>
                      <tbody>{history.map((entry) => (
                        <tr key={`${entry.source_snapshot_date}-${entry.captured_at}`}>
                          <td>{formatDate(entry.source_snapshot_date)}</td><td>{formatDate(entry.effective_date)}</td>
                          <td>{formatCurrency(entry.retail_price_usd)}</td><td>{formatCurrency(entry.promo_price_usd)}</td>
                          <td>{[entry.promotion_terms, entry.financing_terms].filter(Boolean).join(' · ') || '—'}</td>
                        </tr>
                      ))}</tbody>
                    </table>
                  </div>
                </>
              ) : null}
            </>
          ) : null}
        </section>
      ) : null}
    </div>
  );
}
