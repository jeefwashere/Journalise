import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import "../../styles/dashboard/AccountPage.css";

type AccountPet = {
  pet_type?: string;
  pet_type_display?: string;
  level?: number;
  name?: string;
};

type AccountUser = {
  username?: string;
  email?: string;
  name?: string;
  profile?: {
    display_name?: string;
    pet_level?: number;
    current_pet?: AccountPet | null;
  };
};

type SavedHomeState = {
  username?: string;
  email?: string;
  petName?: string;
  petType?: number;
  petLevel?: number;
};

const API_BASE_URL = "";
const HOME_STATE_KEY = "journaliseHomeState";
const PET_FOLDERS = ["Dogs", "Cats", "Bunny", "Frogs"];
const PET_LABELS = ["Dog", "Cat", "Bunny", "Frog"];

const petAssets = import.meta.glob("../../assets/{Dogs,Cats,Bunny,Frogs}/*.png", {
  eager: true,
  import: "default",
}) as Record<string, string>;

function getToken() {
  return (
    localStorage.getItem("accessToken") || localStorage.getItem("token") || ""
  );
}

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}

function loadSavedHomeState(): SavedHomeState {
  try {
    const raw = localStorage.getItem(HOME_STATE_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

function petTypeToIndex(value?: string) {
  const index = ["dog", "cat", "bunny", "frog"].indexOf(value || "");
  return index >= 0 ? index : 0;
}

function getPetImage(petType: number, petLevel: number) {
  const folder = PET_FOLDERS[petType] || PET_FOLDERS[0];
  const requestedName = `${petType}${petLevel}0.png`;
  const fallbackName = `${petType}00.png`;

  return (
    petAssets[`../../assets/${folder}/${requestedName}`] ||
    petAssets[`../../assets/${folder}/${fallbackName}`] ||
    petAssets["../../assets/Dogs/000.png"]
  );
}

export default function AccountPage() {
  const navigate = useNavigate();
  const savedHomeState = useMemo(loadSavedHomeState, []);
  const [user, setUser] = useState<AccountUser | null>(null);
  const [loading, setLoading] = useState(true);

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

        const nextUser: AccountUser = await response.json();
        if (isMounted) setUser(nextUser);
      } catch {
        if (isMounted) setUser(null);
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    loadUser();

    return () => {
      isMounted = false;
    };
  }, []);

  const handleLogout = () => {
    localStorage.removeItem("accessToken");
    localStorage.removeItem("token");
    localStorage.removeItem("journaliseIsAuthenticated");
    localStorage.removeItem(HOME_STATE_KEY);
    navigate("/login");
  };

  const apiPet = user?.profile?.current_pet;
  const savedPetType = clamp(Number(savedHomeState.petType ?? 0), 0, 3);
  const petType = apiPet ? petTypeToIndex(apiPet.pet_type) : savedPetType;
  const apiLevel = Number(user?.profile?.pet_level ?? apiPet?.level);
  const savedLevel = Number(savedHomeState.petLevel ?? 0) + 1;
  const displayLevel = clamp(Number.isFinite(apiLevel) ? apiLevel : savedLevel, 1, 4);
  const assetLevel = clamp(displayLevel - 1, 0, 3);
  const petName = apiPet?.name || savedHomeState.petName || "Your pet";
  const petLabel = apiPet?.pet_type_display || PET_LABELS[petType] || "Pet";
  const displayName =
    user?.profile?.display_name ||
    user?.name ||
    user?.username ||
    savedHomeState.username ||
    "Journalise friend";
  const email = user?.email || savedHomeState.email || "No email saved yet";
  const username = user?.username || savedHomeState.username || "Not signed in";

  return (
    <main className="account-page">
      <nav className="account-nav" aria-label="Main navigation">
        <Link to="/home" className="account-logo">
          Journalise
        </Link>

        <div className="account-nav-links">
          <Link to="/stats">Stats</Link>
          <Link to="/journal">Journal</Link>
          <Link to="/account">My Account</Link>
          <button type="button" onClick={handleLogout}>
            Log Out
          </button>
        </div>
      </nav>

      <section className="account-content">
        <div className="account-panel">
          <div>
            <p className="account-kicker">My Account</p>
            <h1>{displayName}</h1>
          </div>

          <dl className="account-details">
            <div>
              <dt>Username</dt>
              <dd>{username}</dd>
            </div>
            <div>
              <dt>Email</dt>
              <dd>{email}</dd>
            </div>
            <div>
              <dt>Status</dt>
              <dd>{loading ? "Loading..." : "Ready to journal"}</dd>
            </div>
          </dl>
        </div>

        <div className="account-panel account-pet-panel">
          <div className="account-pet-copy">
            <p className="account-kicker">Current Pet</p>
            <h2>{petName}</h2>
            <p>{petLabel}</p>
            <strong>Level {displayLevel}</strong>
          </div>

          <img
            src={getPetImage(petType, assetLevel)}
            alt={`${petName}, ${petLabel}`}
            className="account-pet"
          />
        </div>
      </section>
    </main>
  );
}
