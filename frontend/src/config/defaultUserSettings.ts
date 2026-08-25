import type { UserSettings } from "@/api/types";

import defaultUserSettings from "./defaultUserSettings.json";

// Renderer fallback copy of backend services.settings_service.DEFAULT_SETTINGS.
// Keep this file in sync through tests; backend defaults remain the canonical source.
export const DEFAULT_USER_SETTINGS = defaultUserSettings as UserSettings;
