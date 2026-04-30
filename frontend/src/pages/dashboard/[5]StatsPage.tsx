import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import "../../styles/dashboard/[5]StatsPage.css";

import { useUserPet } from "../../hooks/useUserPet";
import { getPetImage } from "../../utils/petDisplay";

import flowerStudy from "../../assets/Flowers/6.png";
import flowerWork from "../../assets/Flowers/7.png";
import flowerBreak from "../../assets/Flowers/8.png";
import flowerCommunication from "../../assets/Flowers/4.png";
import flowerOther from "../../assets/Flowers/5.png";

interface ApiStat {
  category: string;
  category_display: string;
  total_minutes: number;
  time_range: string;
  start_time: string;
  end_time: string;
  activity_count: number;
  titles: string[];
  notes: string[];
}

interface HourPoint {
  hour: string;
  percent: number;
  minutes: number;
  app: string;
  summary: string;
  raw: ApiStat[];
}

const API_BASE_URL = "/api";

const flowerMap: Record<string, string> = {
  study: flowerStudy,
  work: flowerWork,
  break: flowerBreak,
  communication: flowerCommunication,
  other: flowerOther,
};

const categoryColors: Record<string, string> = {
  study: "#9ee3d8",
  work: "#d8c5f2",
  break: "#ffe29a",
  entertainment: "#ffe29a",
  communication: "#ffaaa0",
  other: "#aeddf2",
};

const fallbackPieColors = [
  "#9ee3d8",
  "#ffe29a",
  "#d8c5f2",
  "#ffaaa0",
  "#aeddf2",
  "#b7eadf",
];

function todayISO() {
  return new Date().toISOString().slice(0, 10);
}

function getToken() {
  return (
    localStorage.getItem("accessToken") || localStorage.getItem("token") || ""
  );
}

export default function StatsPage() {
  const navigate = useNavigate();
  const [stats, setStats] = useState<ApiStat[]>([]);
  const [date, setDate] = useState(todayISO());
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [selectedHour, setSelectedHour] = useState<HourPoint | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [flowerModal, setFlowerModal] = useState(false);
  const userPet = useUserPet();

  useEffect(() => {
    async function loadStats() {
      setLoading(true);
      setError("");

      try {
        const token = getToken();

        const response = await fetch(`${API_BASE_URL}/stats/?date=${date}`, {
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
        });

        if (!response.ok) {
          throw new Error("Could not load stats");
        }

        const data: ApiStat[] = await response.json();
        setStats(data);
      } catch (error) {
        console.error(error);
        setStats([]);
        setError("Could not load stats from the backend.");
      } finally {
        setLoading(false);
      }
    }

    loadStats();
  }, [date]);

  const hourlyPoints = useMemo<HourPoint[]>(() => {
    const grouped = new Map<string, ApiStat[]>();

    stats.forEach((item) => {
      const key = item.time_range;
      grouped.set(key, [...(grouped.get(key) || []), item]);
    });

    return Array.from(grouped.entries()).map(([hour, rows]) => {
      const minutes = rows.reduce((sum, row) => sum + row.total_minutes, 0);
      const percent = Math.min(100, Math.round((minutes / 60) * 100));
      const titles = rows.flatMap((row) => row.titles || []);
      const notes = rows.flatMap((row) => row.notes || []);

      return {
        hour,
        minutes,
        percent,
        app: titles[0] || rows[0]?.category_display || "Activity",
        summary: notes[0] || titles.join(", ") || "No summary yet.",
        raw: rows,
      };
    });
  }, [stats]);

  const breakdown = useMemo(() => {
    const totals = new Map<string, { label: string; minutes: number }>();
    const totalMinutes = stats.reduce(
      (sum, item) => sum + Math.max(0, item.total_minutes),
      0,
    );

    stats.forEach((item) => {
      if (item.total_minutes <= 0) return;

      const existing = totals.get(item.category);
      totals.set(item.category, {
        label: item.category_display,
        minutes: (existing?.minutes || 0) + item.total_minutes,
      });
    });

    return Array.from(totals.entries()).map(([category, value]) => ({
      category,
      label: value.label,
      minutes: value.minutes,
      percent:
        totalMinutes > 0
          ? Math.round((value.minutes / totalMinutes) * 100)
          : 0,
    }));
  }, [stats]);

  const coloredBreakdown = useMemo(
    () =>
      breakdown.map((item, index) => ({
        ...item,
        color:
          categoryColors[item.category] ||
          fallbackPieColors[index % fallbackPieColors.length],
      })),
    [breakdown],
  );

  const pieBackground = useMemo(() => {
    const totalMinutes = coloredBreakdown.reduce(
      (sum, item) => sum + item.minutes,
      0,
    );

    if (totalMinutes <= 0) {
      return "#fff8eb";
    }

    let cursor = 0;
    const segments = coloredBreakdown.map((item, index) => {
      const start = cursor;
      const size = (item.minutes / totalMinutes) * 100;
      const end = index === coloredBreakdown.length - 1 ? 100 : cursor + size;
      cursor = end;

      return `${item.color} ${start.toFixed(2)}% ${end.toFixed(2)}%`;
    });

    return `conic-gradient(${segments.join(", ")})`;
  }, [coloredBreakdown]);

  const topHours = [...hourlyPoints]
    .sort((a, b) => b.percent - a.percent)
    .slice(0, 3);

  const flowerCount = stats.reduce(
    (sum, item) => sum + Math.max(1, Math.round(item.total_minutes / 15)),
    0,
  );

  const chartPoints = hourlyPoints
    .map((point, index) => {
      const x = 50 + index * 95;
      const y = 205 - point.percent * 1.55;
      return `${x},${y}`;
    })
    .join(" ");

  const handleLogout = () => {
    localStorage.removeItem("accessToken");
    localStorage.removeItem("token");
    localStorage.removeItem("journaliseIsAuthenticated");
    localStorage.removeItem("journaliseHomeState");
    navigate("/login");
  };

  return (
    <motion.div
      className="stats-page"
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <nav className="stats-nav">
        <Link to="/home" className="stats-logo">
          Journalise
        </Link>

        <div className="stats-nav-links">
          <Link to="/stats">Stats</Link>
          <Link to="/journal">Journal</Link>
          <Link to="/account">My Account</Link>
          <button type="button" onClick={handleLogout}>
            Log Out
          </button>
        </div>
      </nav>

      <main className="stats-content">
        <section className="stats-panel">
          <div className="panel-header">
            <div>
              <h2>
                <span>📈</span> Hourly Trends
              </h2>
              <p>How your day flowed</p>
            </div>

            <input
              className="date-picker"
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
            />
          </div>

          {loading && <p className="loading-text">Loading your day...</p>}
          {error && <p className="loading-text">{error}</p>}

          <div className="line-chart-wrap">
            <div className="y-labels">
              <span>High</span>
              <span>Med</span>
              <span>Low</span>
            </div>

            <svg viewBox="0 0 720 240" className="line-chart">
              {hourlyPoints.length > 0 && (
                <>
                  <polyline
                    points={`50,220 ${chartPoints} 680,220`}
                    className="chart-fill"
                  />
                  <polyline points={chartPoints} className="chart-line" />
                </>
              )}

              {hourlyPoints.map((point, index) => {
                const x = 50 + index * 95;
                const y = 205 - point.percent * 1.55;

                return (
                  <g key={point.hour} onClick={() => setSelectedHour(point)}>
                    <circle cx={x} cy={y} r="7" className="chart-dot" />
                    <text x={x - 38} y="235" className="x-label">
                      {point.hour.split(" - ")[0]}
                    </text>
                    <title>{`${point.hour} • ${point.percent}% • ${point.app} • ${point.summary}`}</title>
                  </g>
                );
              })}
            </svg>
          </div>

          <motion.div className="top-hours-card" whileHover={{ y: -3 }}>
            <h3>Top 3 Productive Hours</h3>

            {topHours.length === 0 && <p>No activity for this date yet.</p>}

            {topHours.map((row) => (
              <motion.button
                key={row.hour}
                className="hour-row"
                whileHover={{ x: 5 }}
                onClick={() => setSelectedHour(row)}
              >
                <span>{row.hour}</span>
                <div className="progress">
                  <div style={{ width: `${row.percent}%` }} />
                </div>
                <strong>{row.percent}%</strong>
              </motion.button>
            ))}
          </motion.div>
        </section>

        <section className="stats-panel right-panel">
          <div className="panel-header">
            <div>
              <h2>
                <span>◔</span> Breakdown
              </h2>
              <p>Where your time went</p>
            </div>

            <input
              className="date-picker"
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
            />
          </div>

          <div className="breakdown-area">
            <div
              className={`pie-chart ${coloredBreakdown.length === 0 ? "empty" : ""}`}
              style={
                coloredBreakdown.length > 0
                  ? { background: pieBackground }
                  : undefined
              }
            >
              <div className="pie-center">
                {coloredBreakdown.length === 0 ? "No data" : "Today"}
              </div>
            </div>

            <div className="legend">
              {coloredBreakdown.length === 0 && (
                <p className="empty-breakdown">No activity for this date yet.</p>
              )}

              {coloredBreakdown.map((item) => (
                <motion.button
                  key={item.category}
                  whileHover={{ x: 5 }}
                  onClick={() => setSelectedCategory(item.category)}
                  className={selectedCategory === item.category ? "active" : ""}
                >
                  <span style={{ background: item.color }} />
                  {item.label}
                  <strong>{item.percent}%</strong>
                </motion.button>
              ))}
            </div>
          </div>

          <motion.div
            className="flowers-card"
            whileHover={{ y: -4 }}
            onClick={() => setFlowerModal(true)}
          >
            <h3>Flowers Garden</h3>

            <div className="garden">
              {stats.map((item, index) => (
                <img
                  key={`${item.category}-${index}`}
                  src={flowerMap[item.category] || flowerOther}
                  alt={item.category_display}
                  title={`${item.category_display}: ${item.total_minutes} minutes`}
                />
              ))}
            </div>

            <div className="flower-info">
              <strong>{flowerCount}</strong>
              <span>flowers today</span>
              <p>Flowers bloom from your tracked work sessions.</p>
            </div>
          </motion.div>

          <motion.div
            className="teacher-pet"
            whileHover={{ y: -8, rotate: 2 }}
          >
            <img
              src={getPetImage(userPet.petTypeIndex, userPet.assetLevel, 5)}
              alt={`${userPet.petName}, ${userPet.petLabel}`}
            />
          </motion.div>
        </section>
      </main>

      <AnimatePresence>
        {selectedHour && (
          <motion.div
            className="modal-backdrop"
            onClick={() => setSelectedHour(null)}
          >
            <motion.div
              className="sketch-modal"
              onClick={(e) => e.stopPropagation()}
              initial={{ opacity: 0, y: 24, scale: 0.94 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 24, scale: 0.94 }}
            >
              <button
                className="close-btn"
                onClick={() => setSelectedHour(null)}
              >
                ×
              </button>

              <h2>{selectedHour.hour}</h2>
              <p>
                <strong>Productivity:</strong> {selectedHour.percent}%
              </p>
              <p>
                <strong>Minutes tracked:</strong> {selectedHour.minutes}
              </p>
              <p>
                <strong>Summary:</strong> {selectedHour.summary}
              </p>

              <h3>Tasks</h3>
              <ul>
                {selectedHour.raw
                  .flatMap((item) => item.titles)
                  .map((title) => (
                    <li key={title}>{title}</li>
                  ))}
              </ul>
            </motion.div>
          </motion.div>
        )}

        {flowerModal && (
          <motion.div
            className="modal-backdrop"
            onClick={() => setFlowerModal(false)}
          >
            <motion.div
              className="sketch-modal"
              onClick={(e) => e.stopPropagation()}
              initial={{ opacity: 0, y: 24, scale: 0.94 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 24, scale: 0.94 }}
            >
              <button
                className="close-btn"
                onClick={() => setFlowerModal(false)}
              >
            
              </button>
              <h2>Reward Garden</h2>
              <p>
                You earned <strong>{flowerCount} flowers</strong> today.
              </p>
              <p>
                Each flower represents activity from your tracked categories.
              </p>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
