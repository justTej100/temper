import type { Bucket } from "@/lib/types";

function pct(v: number) {
  return `${Math.round(v * 100)}%`;
}

export function BucketCompare({ buckets }: { buckets: Bucket[] }) {
  if (!buckets.length) {
    return (
      <p className="text-sm text-muted">No Polymarket buckets yet — sync markets first.</p>
    );
  }

  return (
    <section className="py-6">
      <h2 className="text-xl font-semibold">Model vs Polymarket</h2>
      <p className="mt-1 text-sm text-muted">
        Model probability from residual-aware normal CDF over °C buckets. Edge = model − market.
      </p>
      <div className="mt-4 overflow-hidden rounded-lg border border-border">
        <table className="w-full text-left text-sm">
          <thead className="bg-surface-2 text-xs uppercase tracking-wide text-muted">
            <tr>
              <th className="px-4 py-3">Bucket</th>
              <th className="px-4 py-3">Market</th>
              <th className="px-4 py-3">Model</th>
              <th className="px-4 py-3">Edge</th>
            </tr>
          </thead>
          <tbody>
            {buckets.map((b) => {
              const edge = b.edge;
              const hot = edge !== null && Math.abs(edge) >= 0.08;
              return (
                <tr key={b.id} className="border-t border-border">
                  <td className="px-4 py-3 font-medium">{b.label}</td>
                  <td className="px-4 py-3">{pct(b.yes_price)}</td>
                  <td className="px-4 py-3">
                    {b.model_prob !== null ? pct(b.model_prob) : "—"}
                  </td>
                  <td className={`px-4 py-3 ${hot ? "font-semibold text-accent" : ""}`}>
                    {edge !== null ? `${edge >= 0 ? "+" : ""}${pct(edge)}` : "—"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
