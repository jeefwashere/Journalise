type Props = {
  hour: string;
  title: string;
  summary: string;
};

export default function HourCard({ hour, title, summary }: Props) {
  return (
    <div
      style={{
        background: "#1e293b",
        padding: "20px",
        borderRadius: "16px",
        marginBottom: "16px",
      }}
    >
      <p>{hour}</p>
      <h3>{title}</h3>
      <p>{summary}</p>
    </div>
  );
}
