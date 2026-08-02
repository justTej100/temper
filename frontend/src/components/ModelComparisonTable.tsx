import type { ModelComparison } from "@/lib/types";

export function ModelComparisonTable({
  models,
  bestModel,
}: {
  models: ModelComparison[];
  bestModel: string | null;
}) {
  if (!models.length) return null;
  const sorted = [...models].sort((a, b) => (a.mae ?? 99) - (b.mae ?? 99));

  return (
    <section className="py-6">
      <h2 className="text-xl font-semibold">Model Bakeoff</h2>
      <p className="mt-1 text-sm text-muted">
        Same train/test split. Lower MAE wins.
      </p>
      <div className="mt-4 overflow-hidden rounded-lg border border-border">
        <table className="w-full text-left text-sm">
          <thead className="bg-surface-2 text-xs uppercase tracking-wide text-muted">
            <tr>
              <th className="px-4 py-3">Model</th>
              <th className="px-4 py-3">MAE</th>
              <th className="px-4 py-3">MAPE</th>
              <th className="px-4 py-3">RMSE</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody>
            {sorted.map((m) => (
              <tr key={m.model_type} className="border-t border-border">
                <td className="px-4 py-3 font-medium uppercase">{m.model_type}</td>
                <td className="px-4 py-3">{m.mae?.toFixed(2) ?? "—"}</td>
                <td className="px-4 py-3">{m.mape?.toFixed(1) ?? "—"}</td>
                <td className="px-4 py-3">{m.rmse?.toFixed(2) ?? "—"}</td>
                <td className="px-4 py-3">
                  {(m.is_best || m.model_type === bestModel) && (
                    <span className="rounded-full bg-accent px-2 py-0.5 text-xs font-bold text-black">
                      BEST
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
