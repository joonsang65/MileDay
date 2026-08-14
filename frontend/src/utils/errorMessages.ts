import { ApiClientError } from "@/api/client";

export type MessageLanguage = "ko" | "en";

const errorMessages: Record<MessageLanguage, Record<string, string>> = {
  ko: {
    UNAUTHORIZED: "다시 로그인해 주세요.",
    AUTH_INVALID_TOKEN: "다시 로그인해 주세요.",
    AUTH_TOKEN_EXPIRED: "다시 로그인해 주세요.",
    AUTH_INVALID_CREDENTIALS: "이메일 또는 비밀번호를 확인해 주세요.",
    GOAL_CREATE_FAILED: "목표를 추가하지 못했습니다.",
    GOAL_UPDATE_FAILED: "목표를 수정하지 못했습니다.",
    GOAL_DELETE_FAILED: "목표를 삭제하지 못했습니다.",
    GOAL_NOT_FOUND: "목표를 찾지 못했습니다.",
    MILESTONE_CREATE_FAILED: "작업을 추가하지 못했습니다.",
    MILESTONE_UPDATE_FAILED: "작업을 수정하지 못했습니다.",
    MILESTONE_DELETE_FAILED: "작업을 삭제하지 못했습니다.",
    MILESTONE_NOT_FOUND: "작업을 찾지 못했습니다.",
    SETTINGS_UPDATE_FAILED: "설정을 저장하지 못했습니다.",
    CALENDAR_INVALID_DATE: "날짜 형식이 올바르지 않습니다.",
    BAD_REQUEST: "입력값을 확인해 주세요.",
    INTERNAL_SERVER_ERROR: "서버 오류가 발생했습니다.",
  },
  en: {
    UNAUTHORIZED: "Please log in again.",
    AUTH_INVALID_TOKEN: "Please log in again.",
    AUTH_TOKEN_EXPIRED: "Please log in again.",
    AUTH_INVALID_CREDENTIALS: "Please check your email or password.",
    GOAL_CREATE_FAILED: "Could not add the goal.",
    GOAL_UPDATE_FAILED: "Could not update the goal.",
    GOAL_DELETE_FAILED: "Could not delete the goal.",
    GOAL_NOT_FOUND: "Could not find the goal.",
    MILESTONE_CREATE_FAILED: "Could not add the task.",
    MILESTONE_UPDATE_FAILED: "Could not update the task.",
    MILESTONE_DELETE_FAILED: "Could not delete the task.",
    MILESTONE_NOT_FOUND: "Could not find the task.",
    SETTINGS_UPDATE_FAILED: "Could not save settings.",
    CALENDAR_INVALID_DATE: "The date format is invalid.",
    BAD_REQUEST: "Please check your input.",
    INTERNAL_SERVER_ERROR: "A server error occurred.",
  },
};

const fallbackMessages: Record<MessageLanguage, { requestFailed: string; connectionFailed: string }> = {
  ko: {
    requestFailed: "요청을 처리하지 못했습니다.",
    connectionFailed: "서버에 연결하지 못했습니다.",
  },
  en: {
    requestFailed: "Could not process the request.",
    connectionFailed: "Could not connect to the server.",
  },
};

export function getUserFacingErrorMessage(error: unknown, language: MessageLanguage = "ko"): string {
  const messages = errorMessages[language];
  const fallback = fallbackMessages[language];
  if (error instanceof ApiClientError) {
    return messages[error.code] ?? fallback.requestFailed;
  }
  if (error instanceof TypeError) {
    return fallback.connectionFailed;
  }
  if (error instanceof Error) {
    return fallback.requestFailed;
  }
  return fallback.requestFailed;
}
