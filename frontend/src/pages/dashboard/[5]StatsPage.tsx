import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import "../../styles/dashboard/[5]StatsPage.css";

import dogPet from "../../assets/Dogs/005.png";

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

function todayISO() {
  return new Date().toISOString().slice(0, 10);
}

function getToken() {
  return (
    localStorage.getItem("accessToken") || localStorage.getItem("token") || ""
  );
}

export default function StatsPage() {
  const [stats, setStats] = useState<ApiStat[]>([]);
  const [date, setDate] = useState(todayISO());
  const [loading, setLoading] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [selectedHour, setSelectedHour] = useState<HourPoint | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [flowerModal, setFlowerModal] = useState(false);

  useEffect(() => {
    async function loadStats() {
      setLoading(true);

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

        setStats([
          {
            category: "study",
            category_display: "Study",
            total_minutes: 45,
            time_range: "01:00 PM - 02:00 PM",
            start_time: "2026-04-29T13:00:00-04:00",
            end_time: "2026-04-29T14:00:00-04:00",
            activity_count: 2,
            titles: ["Reading Django docs", "Working on serializers"],
            notes: ["Reviewed DRF serializer structure"],
          },
          {
            category: "work",
            category_display: "Work",
            total_minutes: 30,
            time_range: "02:00 PM - 03:00 PM",
            start_time: "2026-04-29T14:00:00-04:00",
            end_time: "2026-04-29T15:00:00-04:00",
            activity_count: 1,
            titles: ["Fixed stats endpoint"],
            notes: [],
          },
        ]);
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
    const totalMinutes =
      stats.reduce((sum, item) => sum + item.total_minutes, 0) || 1;

    stats.forEach((item) => {
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
      percent: Math.round((value.minutes / totalMinutes) * 100),
    }));
  }, [stats]);

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

  return (
    <motion.div
      className="stats-page"
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <nav className="stats-nav">
        <Link to="/dashboard" className="stats-logo">
          Journalise
        </Link>

        <div className="stats-nav-icons">
          <Link to="/dashboard" className="icon-btn">
            ⌂
          </Link>
          <button className="icon-btn" onClick={() => setMenuOpen(!menuOpen)}>
            ☰
          </button>

          <AnimatePresence>
            {menuOpen && (
              <motion.div
                className="menu-dropdown"
                initial={{ opacity: 0, y: -8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
              >
                <Link to="/stats">My Stats</Link>
                <Link to="/account">My Account</Link>
                <Link to="/journal-history">Journal History</Link>
                <Link to="/logout">Logout</Link>
              </motion.div>
            )}
          </AnimatePresence>
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
            <div className="pie-chart">
              <div className="pie-center">Today</div>
            </div>

            <div className="legend">
              {breakdown.map((item) => (
                <motion.button
                  key={item.category}
                  whileHover={{ x: 5 }}
                  onClick={() => setSelectedCategory(item.category)}
                  className={selectedCategory === item.category ? "active" : ""}
                >
                  <span />
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
            onClick={() => (window.location.href = "/pet-room")}
          >
            <div className="speech">Great day!</div>
            <img src={dogPet} alt="Teacher pet dog" />
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
                ×
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
