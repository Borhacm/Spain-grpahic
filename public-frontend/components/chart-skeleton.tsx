export function ChartSkeleton() {
  return (
    <div className="chart-skeleton" aria-hidden>
      <div className="chart-skeleton__shimmer" />
      <div className="chart-skeleton__bars">
        <span />
        <span />
        <span />
        <span />
        <span />
        <span />
        <span />
        <span />
      </div>
    </div>
  );
}
