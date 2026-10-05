export type PriceSeries = {
  label: string;
  color: string;
  values: Array<{ date: string; value: number | null }>;
};

type PriceHistoryChartProps = {
  series: PriceSeries[];
};

const WIDTH = 720;
const HEIGHT = 220;
const PADDING = { top: 16, right: 24, bottom: 36, left: 58 };

export function PriceHistoryChart({ series }: PriceHistoryChartProps) {
  const values = series.flatMap((line) => line.values.filter((point) => point.value != null));
  if (values.length === 0) return null;

  const min = Math.min(...values.map((point) => point.value as number));
  const max = Math.max(...values.map((point) => point.value as number));
  const range = max - min || Math.max(max * 0.1, 1);
  const yMin = Math.max(0, min - range * 0.15);
  const yMax = max + range * 0.15;
  const allDates = [...new Set(values.map((point) => point.date))].sort();
  const innerWidth = WIDTH - PADDING.left - PADDING.right;
  const innerHeight = HEIGHT - PADDING.top - PADDING.bottom;
  const xFor = (date: string) => {
    const index = allDates.indexOf(date);
    return PADDING.left + (allDates.length <= 1 ? innerWidth / 2 : (index / (allDates.length - 1)) * innerWidth);
  };
  const yFor = (value: number) => PADDING.top + ((yMax - value) / (yMax - yMin)) * innerHeight;
  const ticks = [0, 1, 2, 3].map((index) => yMin + ((yMax - yMin) * index) / 3);

  return (
    <div className="price-chart-wrap" role="img" aria-label="Price history chart">
      <svg className="price-chart" viewBox={`0 0 ${WIDTH} ${HEIGHT}`} preserveAspectRatio="none">
        {ticks.map((tick) => (
          <g key={tick}>
            <line x1={PADDING.left} x2={WIDTH - PADDING.right} y1={yFor(tick)} y2={yFor(tick)} className="chart-gridline" />
            <text x={PADDING.left - 8} y={yFor(tick) + 4} textAnchor="end" className="chart-axis-label">${tick.toFixed(0)}</text>
          </g>
        ))}
        {allDates.map((date, index) => (index === 0 || index === allDates.length - 1 || index === Math.floor(allDates.length / 2)) ? (
          <text key={date} x={xFor(date)} y={HEIGHT - 8} textAnchor="middle" className="chart-axis-label">{date.slice(5)}</text>
        ) : null)}
        {series.map((line) => {
          const points = line.values
            .filter((point): point is { date: string; value: number } => point.value != null)
            .map((point) => `${xFor(point.date)},${yFor(point.value)}`)
            .join(' ');
          return (
            <g key={line.label}>
              {line.values.filter((point) => point.value != null).length > 1 ? (
                <polyline points={points} fill="none" stroke={line.color} strokeWidth="3" strokeLinejoin="round" strokeLinecap="round" />
              ) : null}
              {line.values.filter((point) => point.value != null).map((point) => (
                <circle key={`${line.label}-${point.date}`} cx={xFor(point.date)} cy={yFor(point.value as number)} r="4" fill={line.color} />
              ))}
            </g>
          );
        })}
      </svg>
      <div className="chart-legend">
        {series.map((line) => (
          <span key={line.label}><i style={{ backgroundColor: line.color }} />{line.label}</span>
        ))}
      </div>
    </div>
  );
}