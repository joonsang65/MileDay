import { AUTH_LANGUAGE_KEY } from "@/config/storageKeys";
import type { AuthLanguage } from "@/types/auth";

export function getInitialAuthLanguage(): AuthLanguage {
  return localStorage.getItem(AUTH_LANGUAGE_KEY) === "en" ? "en" : "ko";
}
