import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import "../../styles/dashboard/AccountPage.css";
import { useUserPet } from "../../hooks/useUserPet";
import { getPetImage } from "../../utils/petDisplay";

type AccountPet = {
  pet_type?: string;
  pet_type_display?: string;
  level?: number;
  mood?: string;
  name?: string;
};

type AccountUser = {
  username?: string;
  email?: string;
  name?: string;
  profile?: {
    display_name?: string;
    pet_name?: string;
    pet_level?: number;
    pet_mood?: string;
    current_pet?: AccountPet | null;
  };
};

type SavedHomeState = {
  username?: string;
  email?: string;
};

const API_BASE_URL = "";
const HOME_STATE_KEY = "journaliseHomeState";

function getToken() {
  return (
    localStorage.getItem("accessToken") || localStorage.getItem("token") || ""
  );
}

function loadSavedHomeState(): SavedHomeState {
  try {
    const raw = localStorage.getItem(HOME_STATE_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

export default function AccountPage() {
  const navigate = useNavigate();
  const userPet = useUserPet();
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

  const displayName =
    user?.profile?.display_name ||
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
            <h2>{userPet.petName}</h2>
            <p>{userPet.petLabel}</p>
            <strong>Level {userPet.displayLevel}</strong>
          </div>

          <img
            src={getPetImage(userPet.petTypeIndex, userPet.assetLevel, 0)}
            alt={`${userPet.petName}, ${userPet.petLabel}`}
            className="account-pet"
          />
        </div>
      </section>
    </main>
  );
}
