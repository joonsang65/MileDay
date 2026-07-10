import { ApiClientError } from "@/api/client";

const errorMessages: Record<string, string> = {
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
};

export function getUserFacingErrorMessage(error: unknown): string {
  if (error instanceof ApiClientError) {
    return errorMessages[error.code] ?? error.message ?? "요청을 처리하지 못했습니다.";
  }
  if (error instanceof TypeError) {
    return "서버에 연결하지 못했습니다.";
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "요청을 처리하지 못했습니다.";
}
