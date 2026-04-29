import HourCard from "../components/HourCard";

export default function Dashboard() {
  return (
    <div>
      <h1>Today's Summary</h1>

      <HourCard
        hour="9 AM - 10 AM"
        title="Coding Session"
        summary="Worked on frontend UI and project structure."
      />

      <HourCard
        hour="10 AM - 11 AM"
        title="Research Session"
        summary="Explored Gemini API integration."
      />
    </div>
  );
}
