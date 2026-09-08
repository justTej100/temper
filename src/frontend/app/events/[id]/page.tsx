"use client";

import { useParams } from "next/navigation";
import TemperatureEvent, {
  type TemperatureMarketData,
} from "@/components/TemperatureEvent";

const eventsById: Record<
  string,
  { location: string; date: string; markets: TemperatureMarketData[] }
> = {
  "1": {
    location: "Dallas, TX",
    date: "September 9",
    markets: [
      {
        id: "below-89",
        label: "89°F or below",
        probability: 8,
        history: [
          { time: "10:00", probability: 15 },
          { time: "12:00", probability: 12 },
          { time: "14:00", probability: 10 },
          { time: "16:00", probability: 8 },
        ],
      },
      {
        id: "90-91",
        label: "90–91°F",
        probability: 24,
        history: [
          { time: "10:00", probability: 20 },
          { time: "12:00", probability: 22 },
          { time: "14:00", probability: 25 },
          { time: "16:00", probability: 24 },
        ],
      },
    ],
  },
};

export default function EventPage() {
  const params = useParams<{ id: string }>();
  const event = eventsById[params.id];

  if (!event) {
    return <p>No event found for id &quot;{params.id}&quot;.</p>;
  }

  return (
    <TemperatureEvent
      location={event.location}
      date={event.date}
      markets={event.markets}
    />
  );
}