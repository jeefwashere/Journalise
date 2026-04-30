import { useEffect, useMemo, useState } from "react";
import {
  flowerCountFromStats,
  getProfilePetLabel,
  getProfilePetName,
  petAssetLevelFromFlowerCount,
  petTypeToIndex,
  type PetStat,
  type UserProfilePet,
} from "../utils/petDisplay";

type UserPetUser = {
  username?: string;
  email?: string;
  name?: string;
  profile?: UserProfilePet | null;
};

type SavedHomeState = {
  petName?: string;
  petType?: number;
  flowerTypes?: number[];
};

const HOME_STATE_KEY = "journaliseHomeState";

function getToken() {
  const token = localStorage.getItem("accessToken") || localStorage.getItem("token");

  if (!token || token === "undefined" || token === "null") {
    return "";
  }

  return token;
}

function loadSavedHomeState(): SavedHomeState {
  try {
    const raw = localStorage.getItem(HOME_STATE_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

export function useUserPet() {
  const savedHomeState = useMemo(loadSavedHomeState, []);
  const [user, setUser] = useState<UserPetUser | null>(null);
  const [flowerCount, setFlowerCount] = useState(() => {
    return Array.isArray(savedHomeState.flowerTypes)
      ? savedHomeState.flowerTypes.length
      : 0;
  });

  useEffect(() => {
    let isMounted = true;

    async function loadUserAndFlowers() {
      const token = getToken();
      const headers = {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      };

      try {
        const response = await fetch("/api/auth/me/", {
          credentials: "include",
          headers,
        });

        if (response.ok) {
          const nextUser: UserPetUser = await response.json();
          if (isMounted) {
            setUser(nextUser);
          }
        }
      } catch {
        if (isMounted) {
          setUser(null);
        }
      }

      try {
        const response = await fetch("/api/stats/", {
          credentials: "include",
          headers,
        });

        if (response.ok) {
          const stats: PetStat[] = await response.json();
          if (isMounted) {
            setFlowerCount(flowerCountFromStats(stats));
          }
        }
      } catch {
        // The saved local flower count is enough until stats are reachable.
      }
    }

    loadUserAndFlowers();

    return () => {
      isMounted = false;
    };
  }, []);

  const profile = user?.profile || null;
  const savedPetType = Number(savedHomeState.petType ?? 0);
  const petTypeIndex = profile?.current_pet
    ? petTypeToIndex(profile.current_pet.pet_type)
    : Math.min(2, Math.max(0, Number.isFinite(savedPetType) ? savedPetType : 0));
  const assetLevel = petAssetLevelFromFlowerCount(flowerCount);
  const petName = profile
    ? getProfilePetName(profile)
    : savedHomeState.petName || "Your pet";
  const petLabel = profile ? getProfilePetLabel(profile) : ["Dog", "Cat", "Bunny"][petTypeIndex] || "Pet";

  return {
    user,
    profile,
    petTypeIndex,
    assetLevel,
    displayLevel: assetLevel + 1,
    flowerCount,
    petName,
    petLabel,
  };
}
