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
    <section className="model-evaluation">
      <h3>Rolling-origin evaluation</h3>
      <p className="section-intro">
        Models are tested on past forecast horizons. Lower mean absolute error (MAE) ranks first.
      </p>
      <div className="table-scroll" tabIndex={0}>
        <table>
          <caption className="sr-only">Backtest errors by candidate model, measured in degrees Celsius</caption>
          <thead>
            <tr>
              <th scope="col">Model</th>
              <th scope="col">MAE</th>
              <th scope="col">Bias</th>
              <th scope="col">RMSE</th>
              <th scope="col">Selection</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((m) => (
              <tr key={m.model_type}>
                <th scope="row">{m.model_type.replaceAll("_", " ")}</th>
                <td>{m.mae != null ? `${m.mae.toFixed(2)}°C` : "—"}</td>
                <td>{m.bias != null ? `${m.bias.toFixed(2)}°C` : "—"}</td>
                <td>{m.rmse != null ? `${m.rmse.toFixed(2)}°C` : "—"}</td>
                <td>
                  {(m.is_best || m.model_type === bestModel) && (
                    <span className="status ready">
                      <span aria-hidden="true">✓</span> Selected
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
