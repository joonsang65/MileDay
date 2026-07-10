import { describe, expect, it } from "vitest";

import { ApiClientError } from "@/api/client";

import { getUserFacingErrorMessage } from "./errorMessages";

describe("getUserFacingErrorMessage", () => {
  it("API error code를 사용자용 한글 메시지로 매핑한다", () => {
    const error = new ApiClientError({
      code: "GOAL_CREATE_FAILED",
      message: "Failed to create goal.",
      status: 500,
      detail: { message: "null value violates not-null constraint" },
    });

    expect(getUserFacingErrorMessage(error)).toBe("목표를 추가하지 못했습니다.");
  });

  it("네트워크 오류는 서버 연결 실패 메시지로 표시한다", () => {
    expect(getUserFacingErrorMessage(new TypeError("Failed to fetch"))).toBe(
      "서버에 연결하지 못했습니다.",
    );
  });
});
