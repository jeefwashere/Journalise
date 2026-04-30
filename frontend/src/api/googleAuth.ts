import api from "./api";

type GoogleCodeResponse = {
  code?: string;
  error?: string;
};

type GoogleCodeClient = {
  requestCode: () => void;
};

type GoogleAccounts = {
  oauth2: {
    initCodeClient: (config: {
      client_id: string;
      scope: string;
      ux_mode: "popup";
      callback: (response: GoogleCodeResponse) => void;
      error_callback?: (error: unknown) => void;
    }) => GoogleCodeClient;
  };
};

declare global {
  interface Window {
    google?: {
      accounts: GoogleAccounts;
    };
  }
}

const GOOGLE_SCRIPT_SRC = "https://accounts.google.com/gsi/client";

let googleScriptPromise: Promise<void> | null = null;
let googleClientIdPromise: Promise<string> | null = null;

const loadGoogleScript = () => {
  if (window.google?.accounts) {
    return Promise.resolve();
  }

  if (googleScriptPromise) {
    return googleScriptPromise;
  }

  googleScriptPromise = new Promise((resolve, reject) => {
    const existingScript = document.querySelector<HTMLScriptElement>(
      `script[src="${GOOGLE_SCRIPT_SRC}"]`,
    );

    if (existingScript) {
      existingScript.addEventListener("load", () => resolve(), { once: true });
      existingScript.addEventListener(
        "error",
        () => reject(new Error("Could not load Google sign-in.")),
        { once: true },
      );
      return;
    }

    const script = document.createElement("script");
    script.src = GOOGLE_SCRIPT_SRC;
    script.async = true;
    script.defer = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("Could not load Google sign-in."));
    document.head.appendChild(script);
  });

  return googleScriptPromise;
};

const getGoogleClientId = async () => {
  if (!googleClientIdPromise) {
    googleClientIdPromise = api
      .get("auth/google/config/")
      .then((response) => response.data.client_id as string);
  }

  return googleClientIdPromise;
};

export const preloadGoogleAuth = async () => {
  await Promise.all([loadGoogleScript(), getGoogleClientId()]);
};

export const loginWithGoogle = async () => {
  await preloadGoogleAuth();
  const clientId = await getGoogleClientId();

  if (!window.google?.accounts) {
    throw new Error("Google sign-in is not available.");
  }

  const code = await new Promise<string>((resolve, reject) => {
    const client = window.google!.accounts.oauth2.initCodeClient({
      client_id: clientId,
      scope: "openid email profile",
      ux_mode: "popup",
      callback: (response) => {
        if (response.error) {
          reject(new Error(response.error));
          return;
        }

        if (!response.code) {
          reject(new Error("Google did not return an authorization code."));
          return;
        }

        resolve(response.code);
      },
      error_callback: () => reject(new Error("Google sign-in was cancelled.")),
    });

    client.requestCode();
  });

  const response = await api.post("auth/google/", { code });
  localStorage.setItem("accessToken", response.data.access_token);
  localStorage.setItem("currentUser", JSON.stringify(response.data.user));
  return response.data;
};
