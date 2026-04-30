import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import "../../styles/dashboard/MainPage.css";
import TrackingToggle from "../../components/TrackingToggle";

type CloudConfig = {
  top: number;
  duration: number;
  delay: number;
  scale: number;
};

type ApiStat = {
  category: string;
  category_display: string;
  total_minutes: number;
};

type HomePet = {
  petType: number;
  petLevel: number;
};

type Flower = {
  id: string;
  x: number;
  y: number;
  size: number;
  type: number;
  rotation: number;
};

const API_BASE_URL = "";
const HOME_STATE_KEY = "journaliseHomeState";

const PET_FOLDERS = ["Dogs", "Cats", "Bunny", "Frogs"];
const FLOWER_BY_CATEGORY: Record<string, number> = {
  communication: 4,
  other: 5,
  study: 6,
  work: 7,
  break: 8,
};

const petAssets = import.meta.glob("../../assets/{Dogs,Cats,Bunny,Frogs}/*.png", {
  eager: true,
  import: "default",
}) as Record<string, string>;

const flowerAssets = import.meta.glob("../../assets/Flowers/*.png", {
  eager: true,
  import: "default",
}) as Record<string, string>;

function todayISO() {
  return new Date().toISOString().slice(0, 10);
}

function getToken() {
  const token = localStorage.getItem("accessToken") || localStorage.getItem("token");

  if (!token || token === "undefined" || token === "null") {
    return "";
  }

  return token;
}

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}

function seededUnit(seed: number) {
  const value = Math.sin(seed * 12.9898) * 43758.5453;
  return value - Math.floor(value);
}

function loadSavedPet(): HomePet {
  try {
    const raw = localStorage.getItem(HOME_STATE_KEY);
    const saved = raw ? JSON.parse(raw) : null;

    return {
      petType: clamp(Number(saved?.petType ?? 0), 0, 3),
      petLevel: clamp(Number(saved?.petLevel ?? 0), 0, 3),
    };
  } catch {
    return { petType: 0, petLevel: 0 };
  }
}

function makeFlowerPatch(types: number[]) {
  return types.map((type, index) => {
    const row = index % 4;
    const baseY = 57 + row * 8;

    return {
      id: `${type}-${index}`,
      type,
      x: 9 + seededUnit(index + type * 31) * 82,
      y: baseY + seededUnit(index + type * 47) * 7,
      size: 22 + seededUnit(index + type * 59) * 16,
      rotation: -14 + seededUnit(index + type * 71) * 28,
    };
  });
}

function flowerTypesFromStats(stats: ApiStat[]) {
  return stats.flatMap((item) => {
    const count = Math.max(1, Math.round(item.total_minutes / 15));
    const flowerType = FLOWER_BY_CATEGORY[item.category] || FLOWER_BY_CATEGORY.other;

    return Array.from({ length: count }, () => flowerType);
  });
}

function getPetImage(petType: number, petLevel: number, petState: number) {
  const folder = PET_FOLDERS[petType] || PET_FOLDERS[0];
  const requestedName = `${petType}${petLevel}${petState}.png`;
  const fallbackName = `${petType}0${petState}.png`;
  const restingName = `${petType}${petLevel}0.png`;
  const defaultName = "000.png";

  return (
    petAssets[`../../assets/${folder}/${requestedName}`] ||
    petAssets[`../../assets/${folder}/${fallbackName}`] ||
    petAssets[`../../assets/${folder}/${restingName}`] ||
    petAssets[`../../assets/Dogs/${defaultName}`]
  );
}

function getFlowerImage(type: number) {
  return (
    flowerAssets[`../../assets/Flowers/${type}.png`] ||
    flowerAssets["../../assets/Flowers/5.png"]
  );
}

export default function MainPage() {
  const navigate = useNavigate();
  const savedPet = useMemo(loadSavedPet, []);
  const [petType, setPetType] = useState(savedPet.petType);
  const [petLevel, setPetLevel] = useState(savedPet.petLevel);
  const [isTracking, setIsTracking] = useState(false);
  const [isTrackingPending, setIsTrackingPending] = useState(false);
  const [activePetState, setActivePetState] = useState<number | null>(null);
  const [earnedFlowerTypes, setEarnedFlowerTypes] = useState<number[]>([]);

  const defaultPetState = isTracking ? 1 : 0;
  const petState = activePetState ?? defaultPetState;

  useEffect(() => {
    let isMounted = true;

    async function loadUser() {
      try {
        const token = getToken();
        const response = await fetch(`${API_BASE_URL}/api/auth/me/`, {
          credentials: "include",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
        });

        if (!response.ok) return;

        const user = await response.json();
        const currentPetType = user?.profile?.current_pet?.pet_type;
        const nextPetType = ["dog", "cat", "bunny", "frog"].indexOf(
          currentPetType,
        );
        const nextPetLevel = Number(user?.profile?.pet_level ?? 1) - 1;

        if (isMounted && nextPetType >= 0) {
          setPetType(clamp(nextPetType, 0, 3));
          setPetLevel(clamp(nextPetLevel, 0, 3));
        }
      } catch {
        // Local signup state is enough until the account endpoint is available.
      }
    }

    loadUser();

    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    let isMounted = true;

    async function loadFlowers() {
      try {
        const token = getToken();
        const response = await fetch(`${API_BASE_URL}/api/stats/?date=${todayISO()}`, {
          credentials: "include",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
        });

        if (!response.ok) return;

        const stats: ApiStat[] = await response.json();
        const nextFlowerTypes = flowerTypesFromStats(stats);

        if (isMounted) {
          setEarnedFlowerTypes(nextFlowerTypes);
        }
      } catch {
        try {
          const raw = localStorage.getItem(HOME_STATE_KEY);
          const saved = raw ? JSON.parse(raw) : null;
          const savedFlowers = Array.isArray(saved?.flowerTypes)
            ? saved.flowerTypes
            : [];

          if (isMounted) {
            setEarnedFlowerTypes(savedFlowers.filter(Number.isFinite));
          }
        } catch {
          if (isMounted) setEarnedFlowerTypes([]);
        }
      }
    }

    loadFlowers();

    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    setActivePetState(null);
  }, [isTracking]);

  const flowers = useMemo<Flower[]>(
    () => makeFlowerPatch(earnedFlowerTypes),
    [earnedFlowerTypes],
  );

  const handlePetClick = () => {
    setActivePetState(isTracking ? 3 : 2);

    window.setTimeout(() => {
      setActivePetState(null);
    }, 2000);
  };

  const handleTrackingToggle = async (enabled: boolean) => {
    const previousTracking = isTracking;
    setIsTracking(enabled);
    setIsTrackingPending(true);

    try {
      const token = getToken();
      const response = await fetch(`${API_BASE_URL}/api/journal/tracking/`, {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ enabled }),
      });

      if (!response.ok) {
        throw new Error("Tracking request failed");
      }

      const result = await response.json();
      setIsTracking(Boolean(result.tracking));
    } catch {
      setIsTracking(previousTracking);
    } finally {
      setIsTrackingPending(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("accessToken");
    localStorage.removeItem("token");
    localStorage.removeItem("journaliseIsAuthenticated");
    localStorage.removeItem(HOME_STATE_KEY);
    navigate("/login");
  };

  const clouds: CloudConfig[] = [
    { top: 10, duration: 70, delay: 10, scale: 1.1 },
    { top: 28, duration: 90, delay: 35, scale: 0.85 },
    { top: 50, duration: 60, delay: 55, scale: 1.3 },
    { top: 16, duration: 80, delay: 20, scale: 0.95 },
    { top: 65, duration: 100, delay: 45, scale: 1.0 },
  ];

  return (
    <main className="home-page" aria-label="Journalise home garden">
      <nav className="home-nav" aria-label="Main navigation">
        <Link to="/home" className="home-logo">
          Journalise
        </Link>

        <div className="home-nav-links">
          <Link to="/stats">Stats</Link>
          <Link to="/journal">Journal</Link>
          <Link to="/account">My Account</Link>
          <button type="button" onClick={handleLogout}>
            Log Out
          </button>
        </div>
      </nav>

      <div className="home-sky" aria-hidden="true">
        {clouds.map((cloud, index) => (
          <div
            key={index}
            className="home-cloud"
            style={{
              top: `${cloud.top}%`,
              animationDuration: `${cloud.duration}s`,
              animationDelay: `-${cloud.delay}s`,
              transform: `scale(${cloud.scale})`,
            }}
          >
            <div className="home-cloud-body" />
            <div className="home-cloud-bump home-cloud-bump--sm" />
            <div className="home-cloud-bump home-cloud-bump--lg" />
            <div className="home-cloud-bump home-cloud-bump--md" />
          </div>
        ))}
      </div>

      <div className="home-hills" aria-hidden="true">
        <div className="home-hill home-hill--back" />
        <div className="home-hill home-hill--front" />
      </div>

      <div className="home-flowers" aria-label="Earned flowers">
        {flowers.map((flower) => (
          <img
            key={flower.id}
            src={getFlowerImage(flower.type)}
            alt=""
            className="home-flower"
            style={{
              left: `${flower.x}%`,
              top: `${flower.y}%`,
              width: `${flower.size}px`,
              transform: `translate(-50%, -50%) rotate(${flower.rotation}deg)`,
            }}
          />
        ))}
      </div>

      <button className="home-pet-button" onClick={handlePetClick}>
        <img
          src={getPetImage(petType, petLevel, petState)}
          alt="Your pet"
          className="home-pet"
        />
      </button>

      <div className="home-tracking">
        <TrackingToggle
          isTracking={isTracking}
          onToggle={handleTrackingToggle}
          disabled={isTrackingPending}
        />
      </div>
    </main>
  );
}
