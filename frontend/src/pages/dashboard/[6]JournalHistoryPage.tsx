import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import api from "../../api/api";
import "../../styles/dashboard/[6]JournalHistoryPage.css";

type CategoryType = string;

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

interface JournalCategory {
  category: CategoryType;
  category_display: string;
  total_minutes: number;
  activity_count: number;
  titles: string[];
  notes: string[];
}

interface JournalHour {
  time_range: string;
  start_time: string;
  end_time: string;
  categories: JournalCategory[];
}

const colors: Record<string, string> = {
  study: "#9fe4f2",
  other: "#d8d8d8",
  work: "#d7c2ff",
  break: "#ffe89b",
  entertainment: "#ffe89b",
  communication: "#ffb8c7",
};

function todayISO() {
  return new Date().toISOString().slice(0, 10);
}

export default function JournalHistoryPage() {
  const navigate = useNavigate();
  const [openEntry, setOpenEntry] = useState<number | null>(0);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("all");
  const [showAi, setShowAi] = useState(true);
  const [date, setDate] = useState(todayISO());
  const [stats, setStats] = useState<ApiStat[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const paperWrapRef = useRef<HTMLElement | null>(null);
  const entryRefs = useRef<Record<string, HTMLDivElement | null>>({});
  const [timelinePositions, setTimelinePositions] = useState<Record<string, number>>({});

  useEffect(() => {
    async function loadJournalHistory() {
      setLoading(true);
      setError("");

      try {
        const response = await api.get<ApiStat[]>("stats/", {
          params: { date },
        });

        setStats(response.data);
      } catch (requestError: any) {
        setStats([]);
        setError(
          requestError.response?.data?.detail ||
            "Could not load journal history from the backend."
        );
      } finally {
        setLoading(false);
      }
    }

    loadJournalHistory();
  }, [date]);

  const journalHours = useMemo<JournalHour[]>(() => {
    const grouped = new Map<string, ApiStat[]>();

    stats.forEach((row) => {
      grouped.set(row.time_range, [...(grouped.get(row.time_range) || []), row]);
    });

    return Array.from(grouped.entries()).map(([timeRange, rows]) => ({
      time_range: timeRange,
      start_time: rows[0]?.start_time || "",
      end_time: rows[0]?.end_time || "",
      categories: rows.map((row) => ({
        category: row.category,
        category_display: row.category_display,
        total_minutes: row.total_minutes,
        activity_count: row.activity_count,
        titles: row.titles || [],
        notes: row.notes || [],
      })),
    }));
  }, [stats]);

  const filtered = useMemo(() => {
    return journalHours.filter((hour) => {
      const matchesFilter =
        filter === "all" ||
        hour.categories.some((c) => c.category === filter);

      const text = JSON.stringify(hour).toLowerCase();
      const matchesSearch = text.includes(search.toLowerCase());

      return matchesFilter && matchesSearch;
    });
  }, [journalHours, search, filter]);

  const aiReflection = useMemo(() => {
    if (journalHours.length === 0) {
      return "No activity has been tracked for this date yet.";
    }

    const totals = new Map<string, number>();

    journalHours.forEach((hour) => {
      hour.categories.forEach((category) => {
        totals.set(
          category.category_display,
          (totals.get(category.category_display) || 0) + category.total_minutes
        );
      });
    });

    const [topCategory, topMinutes] = Array.from(totals.entries()).sort(
      (a, b) => b[1] - a[1]
    )[0];

    return `You logged ${journalHours.length} active hour${
      journalHours.length === 1 ? "" : "s"
    } on this date. Most of your tracked time went to ${topCategory} with ${topMinutes} minutes.`;
  }, [journalHours]);

  function buildSummary(hour: JournalHour) {
    const total = hour.categories.reduce(
      (sum, c) => sum + c.total_minutes,
      0
    );

    const apps = hour.categories.flatMap((c) => c.titles).join(", ");

    return `During this hour, you spent ${total} minutes across ${
      hour.categories.length
    } activity type${
      hour.categories.length > 1 ? "s" : ""
    }. Most of your activity happened in ${apps}.`;
  }

  useLayoutEffect(() => {
    const updateTimelinePositions = () => {
      const nextPositions: Record<string, number> = {};

      filtered.forEach((hour) => {
        const entry = entryRefs.current[hour.time_range];

        if (!entry) {
          return;
        }

        const entryRect = entry.getBoundingClientRect();
        nextPositions[hour.time_range] = entryRect.bottom;
      });

      setTimelinePositions(nextPositions);
    };

    updateTimelinePositions();

    const resizeObserver = new ResizeObserver(updateTimelinePositions);

    if (paperWrapRef.current) {
      resizeObserver.observe(paperWrapRef.current);
    }

    filtered.forEach((hour) => {
      const entry = entryRefs.current[hour.time_range];

      if (entry) {
        resizeObserver.observe(entry);
      }
    });

    window.addEventListener("resize", updateTimelinePositions);
    window.addEventListener("scroll", updateTimelinePositions, { passive: true });
    const animationFrame = requestAnimationFrame(updateTimelinePositions);

    return () => {
      resizeObserver.disconnect();
      window.removeEventListener("resize", updateTimelinePositions);
      window.removeEventListener("scroll", updateTimelinePositions);
      cancelAnimationFrame(animationFrame);
    };
  }, [filtered, openEntry, showAi, loading, error]);

  const handleTimelineJump = (hour: JournalHour, index: number) => {
    setOpenEntry(index);
    entryRefs.current[hour.time_range]?.scrollIntoView({
      behavior: "smooth",
      block: "center",
    });
  };

  const handleLogout = () => {
    localStorage.removeItem("accessToken");
    localStorage.removeItem("token");
    localStorage.removeItem("journaliseIsAuthenticated");
    localStorage.removeItem("journaliseHomeState");
    navigate("/login");
  };

  return (
    <motion.div
      className="journal-page"
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <nav className="journal-nav">
        <Link to="/home" className="journal-logo">
          Journalise
        </Link>

        <div className="journal-nav-links">
          <Link to="/stats">Stats</Link>
          <Link to="/journal">Journal</Link>
          <Link to="/account">My Account</Link>
          <button type="button" onClick={handleLogout}>
            Log Out
          </button>
        </div>
      </nav>

      <main className="paper-wrap" ref={paperWrapRef}>
        <section className="paper">
          <h1>My Journal History</h1>
          <p className="subtitle">Your day, rewritten by AI.</p>

          <div className="top-tools">
            <input
              placeholder="Search apps, notes, categories..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />

            <select
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
            >
              <option value="all">All Categories</option>
              <option value="study">Study</option>
              <option value="work">Work</option>
              <option value="entertainment">Entertainment</option>
              <option value="communication">Communication</option>
              <option value="other">Other</option>
            </select>

            <input
              type="date"
              value={date}
              onChange={(event) => setDate(event.target.value)}
            />

            <button
              className="ai-btn"
              onClick={() => setShowAi(!showAi)}
            >
              ✨ Ask AI to summarize this day
            </button>
          </div>

          {showAi && (
            <motion.div
              className="ai-card"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
            >
              <strong>Today's AI Reflection</strong>
              <p>{aiReflection}</p>
            </motion.div>
          )}

          {loading && <p className="subtitle">Loading journal history...</p>}
          {error && <p className="subtitle">{error}</p>}
          {!loading && !error && filtered.length === 0 && (
            <p className="subtitle">No journal entries found for this date.</p>
          )}

          {filtered.map((hour, index) => (
            <motion.div
              key={hour.time_range}
              ref={(element) => {
                entryRefs.current[hour.time_range] = element;
              }}
              className="entry"
              whileHover={{ y: -4 }}
              initial={{ opacity: 0, y: 14 }}
              animate={{ opacity: 1, y: 0 }}
            >
              <div
                className="entry-head"
                onClick={() =>
                  setOpenEntry(openEntry === index ? null : index)
                }
              >
                <h2>{hour.time_range}</h2>
                <span>⌄</span>
              </div>

              <p>{buildSummary(hour)}</p>

              <div className="labels">
                {hour.categories.map((cat) => (
                  <span
                    key={cat.category}
                    className="tag"
                    style={{
                      background: colors[cat.category] || colors.other,
                    }}
                  >
                    {cat.category_display}
                  </span>
                ))}
              </div>

              <AnimatePresence>
                {openEntry === index && (
                  <motion.div
                    className="details"
                    initial={{ height: 0, opacity: 0 }}
                    animate={{
                      height: "auto",
                      opacity: 1,
                    }}
                    exit={{ height: 0, opacity: 0 }}
                  >
                    {hour.categories.map((cat) => (
                      <div key={cat.category}>
                        <strong>
                          {cat.category_display}
                        </strong>
                        <p>
                          {cat.total_minutes} mins •{" "}
                          {cat.activity_count} actions
                        </p>
                        <p>
                          Apps: {cat.titles.join(", ")}
                        </p>
                      </div>
                    ))}
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          ))}
        </section>

        <aside className="timeline">
          {filtered.map((item, index) => (
            <button
              key={item.time_range}
              type="button"
              style={{ top: `${timelinePositions[item.time_range] || 0}px` }}
              onClick={() => handleTimelineJump(item, index)}
            >
              {item.time_range.slice(0, 5)}
            </button>
          ))}
        </aside>

      </main>
    </motion.div>
  );
}
