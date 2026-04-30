export type CurrentPet = {
  pet_type?: string;
  pet_type_display?: string;
  level?: number;
  mood?: string;
  name?: string;
};

export type UserProfilePet = {
  display_name?: string;
  pet_name?: string;
  pet_level?: number;
  pet_mood?: string;
  current_pet?: CurrentPet | null;
};

const PET_FOLDERS = ["Dogs", "Cats", "Bunny"];
const PET_LABELS = ["Dog", "Cat", "Bunny"];
const PET_TYPE_TO_INDEX: Record<string, number> = {
  dog: 0,
  cat: 1,
  bunny: 2,
  frog: 2,
};
const MOOD_TO_STATE: Record<string, number> = {
  neutral: 0,
  focused: 1,
  happy: 5,
  tired: 4,
};

const petAssets = import.meta.glob("../assets/{Dogs,Cats,Bunny}/*.png", {
  eager: true,
  import: "default",
}) as Record<string, string>;

export function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}

export function petTypeToIndex(value?: string) {
  return PET_TYPE_TO_INDEX[value || ""] ?? 0;
}

export function getPetTypeLabel(value?: string) {
  const index = petTypeToIndex(value);
  return PET_LABELS[index] || "Pet";
}

export function profilePetLevel(profile?: UserProfilePet | null) {
  const level = Number(profile?.pet_level ?? profile?.current_pet?.level ?? 1);
  return clamp(Number.isFinite(level) ? level : 1, 1, 3);
}

export function petMoodToState(value?: string, fallback = 0) {
  return MOOD_TO_STATE[value || ""] ?? fallback;
}

export function getPetImage(
  petType: number,
  displayLevel: number,
  petState: number = 0,
) {
  const safePetType = clamp(petType, 0, 2);
  const assetLevel = clamp(displayLevel - 1, 0, 2);
  const safePetState = clamp(petState, 0, 5);
  const folder = PET_FOLDERS[safePetType] || PET_FOLDERS[0];
  const requestedName = `${safePetType}${assetLevel}${safePetState}.png`;
  const fallbackMoodName = `${safePetType}${assetLevel}0.png`;
  const fallbackLevelName = `${safePetType}00.png`;

  return (
    petAssets[`../assets/${folder}/${requestedName}`] ||
    petAssets[`../assets/${folder}/${fallbackMoodName}`] ||
    petAssets[`../assets/${folder}/${fallbackLevelName}`] ||
    petAssets["../assets/Dogs/000.png"]
  );
}

export function getProfilePetImage(
  profile?: UserProfilePet | null,
  petState?: number,
) {
  const petType = petTypeToIndex(profile?.current_pet?.pet_type);
  const level = profilePetLevel(profile);
  const state = petState ?? petMoodToState(profile?.pet_mood);
  return getPetImage(petType, level, state);
}

export function getProfilePetName(profile?: UserProfilePet | null) {
  return profile?.pet_name?.trim() || profile?.current_pet?.name || "Your pet";
}

export function getProfilePetLabel(profile?: UserProfilePet | null) {
  return getPetTypeLabel(profile?.current_pet?.pet_type);
}
