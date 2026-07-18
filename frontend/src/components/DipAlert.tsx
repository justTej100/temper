export function DipAlert({
  date,
  price,
}: {
  date: string;
  price: number;
}) {
  const formatted = new Date(date).toLocaleDateString("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
  });

  return (
    <div className="rounded-lg border border-success/40 bg-success/10 px-5 py-4 text-success">
      <strong>Predicted next dip:</strong> {formatted} at{" "}
      <strong>${price.toFixed(2)}</strong>
    </div>
  );
}

export function NoDipBanner() {
  return (
    <div className="rounded-lg border border-info/40 bg-info/10 px-5 py-4 text-info">
      No significant price dip predicted in the next 30 days.
    </div>
  );
}
