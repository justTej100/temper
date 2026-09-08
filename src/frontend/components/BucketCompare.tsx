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
    <section className="section">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Probability comparison</p>
          <h2>Model and market buckets</h2>
        </div>
      </div>
      <p className="section-intro">
        “Difference” is model probability minus market probability. It is a disagreement measure,
        not expected profit or a recommendation.
      </p>
      <div className="table-scroll" tabIndex={0}>
        <table>
          <caption className="sr-only">Model probabilities compared with Polymarket probabilities by temperature bucket</caption>
          <thead>
            <tr>
              <th scope="col">Temperature bucket</th>
              <th scope="col">Market probability</th>
              <th scope="col">Model probability</th>
              <th scope="col">Difference</th>
            </tr>
          </thead>
          <tbody>
            {buckets.map((b) => {
              const edge = b.edge;
              const hot = edge !== null && Math.abs(edge) >= 0.08;
              return (
                <tr key={b.id}>
                  <th scope="row">{b.label}</th>
                  <td>{pct(b.yes_price)}</td>
                  <td>
                    {b.model_prob !== null ? pct(b.model_prob) : "—"}
                  </td>
                  <td>
                    {edge !== null ? (
                      <span className={hot ? "difference notable" : "difference"}>
                        <span aria-hidden="true">{edge >= 0 ? "↑" : "↓"}</span>
                        {edge >= 0 ? "+" : ""}{pct(edge)}
                        {hot && <span className="sr-only">, notable disagreement</span>}
                      </span>
                    ) : "—"}
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
