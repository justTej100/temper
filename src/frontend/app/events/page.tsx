import TemperatureEvent from "@/components/TemperatureEvent";

const markets = [
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
  {
    id: "92-93",
    label: "92–93°F",
    probability: 38,
    history: [
      { time: "10:00", probability: 30 },
      { time: "12:00", probability: 34 },
      { time: "14:00", probability: 40 },
      { time: "16:00", probability: 38 },
    ],
  },
  {
    id: "94-95",
    label: "94–95°F",
    probability: 22,
    history: [
      { time: "10:00", probability: 25 },
      { time: "12:00", probability: 24 },
      { time: "14:00", probability: 20 },
      { time: "16:00", probability: 22 },
    ],
  },
  {
    id: "96-plus",
    label: "96°F or above",
    probability: 8,
    history: [
      { time: "10:00", probability: 10 },
      { time: "12:00", probability: 8 },
      { time: "14:00", probability: 5 },
      { time: "16:00", probability: 8 },
    ],
  },
];

export default function Page() {
  return (
    <TemperatureEvent
      location="Dallas, TX"
      date="September 9"
      markets={markets}
    />
  );
}