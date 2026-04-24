import { ChartSkeleton } from "@/components/chart-skeleton";

export default function StoryLoading() {
  return (
    <>
      <nav className="breadcrumb" aria-label="Ruta">
        <span className="muted">Cargando historia…</span>
      </nav>
      <div className="card">
        <div className="skeleton-title" />
        <div className="skeleton-line skeleton-line--wide" />
        <div className="skeleton-line" />
        <ChartSkeleton />
      </div>
    </>
  );
}
