import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { chromium } from "playwright";

/* global document, getComputedStyle, window */

const css = await readFile(resolve("src/styles.css"), "utf8");

const dayCells = Array.from({ length: 42 }, (_, index) => {
  const day = index + 1;
  return `
    <button type="button" class="day-cell ${day === 15 ? "today selected" : ""}">
      <span class="day-number">${day}</span>
      <span class="holiday-name">Holiday</span>
      <span class="event-list" aria-hidden="true">
        <span class="event-text goal-event">Goal ${day} 2/4</span>
        <span class="event-text goal-event">Long goal title ${day} 1/3</span>
      </span>
      <span class="dot-row" aria-hidden="true">
        <span class="dot goal-dot" style="background:#1478f2"></span>
        <span class="dot goal-dot" style="background:#7f9278"></span>
        <span class="dot goal-dot" style="background:#b75d57"></span>
      </span>
    </button>`;
}).join("");

function renderDocument(settingsPanelSize) {
  return `<!doctype html>
  <html data-settings-panel-size="${settingsPanelSize}">
    <head>
      <meta charset="utf-8" />
      <style>${css}</style>
    </head>
    <body>
      <main class="app-shell">
        <header class="app-header">
          <div class="header-title"><h1>2026. 8.</h1></div>
          <div class="header-actions">
            <div class="segmented"><button class="active">월</button><button>주</button></div>
            <button class="icon-button" type="button">S</button>
            <button class="add-button" type="button">+</button>
          </div>
        </header>
        <div class="workspace planner-workspace">
          <div class="primary-pane">
            <section class="calendar-surface">
              <div class="weekday-row">
                <span>일</span><span>월</span><span>화</span><span>수</span><span>목</span><span>금</span><span>토</span>
              </div>
              <div class="calendar-grid month">${dayCells}</div>
            </section>
          </div>
        </div>
        <footer class="app-credit"><strong>mileday</strong><span>made by test</span></footer>
        <div class="floating-layer side">
          <section class="floating-panel banded settings-floating-panel" role="dialog">
            <header class="floating-panel-header">
              <div class="floating-panel-title-row"><h2>설정</h2></div>
              <button class="icon-button compact-icon" type="button">x</button>
            </header>
            <div class="floating-panel-body">
              <section class="settings-panel">
                <form class="settings-form">
                  <div class="settings-section">
                    <div class="settings-section-title"><svg></svg><h3>기본 설정</h3></div>
                    <label class="settings-field"><span>기본 캘린더</span><select><option>월간</option></select></label>
                    <label class="settings-field"><span>휴일 표현</span><select><option>이름 표시</option></select></label>
                    <label class="settings-field"><span>주 시작 요일</span><select><option>일요일</option></select></label>
                  </div>
                  <div class="settings-section">
                    <div class="settings-section-title"><svg></svg><h3>글자 및 화면</h3></div>
                    <label class="settings-field settings-field-range"><span>기본 글자 크기(px)</span><div class="settings-range-row"><input class="settings-range-input" type="range" /><span class="settings-range-value">12px</span></div></label>
                    <label class="settings-field"><span>시스템 글자</span><select><option>크게</option></select></label>
                  </div>
                  <div class="settings-section settings-section-advanced">
                    <div class="settings-section-title"><svg></svg><h3>앱 고급 설정</h3></div>
                    <label class="toggle-row settings-toggle-row"><input type="checkbox" /><span><strong>창 크기 조정</strong><small>켜져 있을 때만 창 모서리를 마우스로 잡아 크기를 조정할 수 있습니다.</small></span></label>
                    <label class="toggle-row settings-toggle-row"><input type="checkbox" /><span><strong>컴퓨터 시작 시 자동 실행</strong><small>MileDay가 자동으로 시작됩니다.</small></span></label>
                  </div>
                  <button class="primary-button compact" type="button">저장</button>
                </form>
                <a class="survey-button">POC 설문 참여</a>
                <button class="danger-button settings-logout" type="button">로그아웃</button>
              </section>
            </div>
          </section>
        </div>
        <div class="floating-layer center">
          <section class="floating-panel plain schedule-create-panel" role="dialog">
            <header class="floating-panel-header">
              <div class="floating-panel-title-row"><h2>일정 추가</h2></div>
              <button class="icon-button compact-icon" type="button">x</button>
            </header>
            <div class="floating-panel-body">
              <form class="panel-form">
                <div class="creation-tabs"><button class="active">새 목표 추가</button><button>기존 목표에 추가</button></div>
                <div class="manual-goal-row">
                  <div class="manual-goal-fields">
                    <label>목표 제목<input value="포트폴리오 준비" /></label>
                    <label>마감일<input type="date" value="2026-09-30" /></label>
                  </div>
                  <fieldset class="color-field"><legend>색상</legend><div class="color-options"><button class="selected"></button><button></button><button></button></div></fieldset>
                </div>
                <fieldset class="manual-milestone-field">
                  <legend>세부 마일스톤</legend>
                  <ul class="manual-milestone-list">
                    <li><label>이름<input value="이력서 초안 작성" /></label><label>날짜<input type="date" value="2026-09-01" /></label><button class="icon-button compact-icon danger-icon" type="button">x</button></li>
                  </ul>
                </fieldset>
                <div class="panel-actions"><button class="ghost-button panel-button">취소</button><button class="primary-button panel-primary">일정 추가</button></div>
              </form>
            </div>
          </section>
        </div>
        <div class="floating-layer center">
          <section class="floating-panel plain schedule-create-panel ai-panel-sample" role="dialog">
            <header class="floating-panel-header">
              <div class="floating-panel-title-row"><h2>일정 추천</h2></div>
              <button class="icon-button compact-icon" type="button">x</button>
            </header>
            <div class="floating-panel-body">
              <form class="ai-input-panel">
                <p class="muted-text">목표를 바탕으로 일정 초안을 준비해 드립니다.</p>
                <div class="ai-consent-box">
                  <label class="toggle-row ai-consent-toggle"><input type="checkbox" /><span><strong>Gemini 전송 동의</strong><small>일정 추천을 만들 때 입력한 목표와 가능 날짜를 Gemini로 전송합니다.</small></span></label>
                  <button class="icon-button compact-icon ai-consent-help-button" type="button">?</button>
                </div>
                <div class="ai-consent-help">
                  <strong>왜 동의가 필요한가요?</strong>
                  <p>AI가 목표에 맞는 마일스톤과 날짜를 제안하려면 입력한 목표와 일정 가능 범위를 Gemini에 보내야 합니다.</p>
                  <ul>
                    <li>전송 내용: 목표 설명, 오늘 날짜, 시간대, 추천에 사용할 가능 날짜와 가능 시간</li>
                    <li>전송하지 않는 내용: 비밀번호를 포함한 모든 개인 정보, 사용자 앱 설정 값</li>
                  </ul>
                </div>
                <textarea>데이터 분석 과제를 끝내고 싶어.</textarea>
                <div class="panel-actions"><button class="primary-button panel-primary">제안 만들기</button></div>
              </form>
              <div class="ai-draft-panel">
                <div class="panel-form">
                  <label>목표 제목<input value="데이터 분석 과제" /></label>
                  <label>마감일<input type="date" value="2026-09-30" /></label>
                </div>
                <div class="draft-meta-row"><span>balanced</span><span>2개 선택</span></div>
                <ul class="draft-list">
                  <li><span class="drag-handle">=</span><input class="draft-checkbox" type="checkbox" checked /><input class="draft-title-input" value="자료 수집" /><input class="draft-date-input" type="date" value="2026-09-04" /><button class="icon-button compact-icon danger-icon">x</button></li>
                </ul>
                <button class="secondary-toggle draft-add-button">마일스톤 추가</button>
              </div>
            </div>
          </section>
        </div>
        <div class="floating-layer center">
          <section class="floating-panel banded goal-list-modal-panel" role="dialog">
            <header class="floating-panel-header"><div class="floating-panel-title-row"><h2>전체 목표</h2></div><button class="icon-button compact-icon">x</button></header>
            <div class="floating-panel-body">
              <div class="goal-list-tabs"><button class="goal-list-tab button-primary">진행중</button><button class="goal-list-tab button-secondary">완료</button><button class="goal-list-tab button-secondary">전체</button></div>
              <ul class="plain-list day-view-list goal-list-scroll">
                <li class="goal-list-item">
                  <div class="editable-row goal-list-row goal-list-row-with-toggle">
                    <button class="icon-button compact-icon goal-list-icon-button">□</button>
                    <div class="goal-list-color-cell"><span class="color-swatch goal-list-color-swatch"></span></div>
                    <div class="goal-list-content"><div class="goal-list-title-row"><strong class="goal-list-title">포트폴리오 준비</strong></div><div class="goal-list-meta"><span>2026-09-30까지</span><span>40%</span></div></div>
                    <button class="icon-button compact-icon goal-list-icon-button">⌄</button>
                  </div>
                </li>
              </ul>
            </div>
          </section>
        </div>
        <div class="floating-layer center">
          <section class="floating-panel banded goal-list-modal-panel date-detail-floating-panel" role="dialog">
            <header class="floating-panel-header"><div class="floating-panel-title-row"><h2>하루보기</h2><span class="floating-panel-subtitle">2026-09-01</span></div><button class="icon-button compact-icon">x</button></header>
            <div class="floating-panel-body">
              <section class="detail-panel day-view-panel">
                <div class="panel-heading day-view-heading"><h2 class="day-view-title">하루보기<span class="day-view-date">2026-09-01</span></h2><span class="day-view-summary"><span>목표 1</span><span>마일스톤 2</span></span></div>
                <div class="section-block"><h3 class="day-view-section-title">목표</h3><ul class="plain-list day-view-list"><li class="editable-item"><div class="editable-row goal-row split-goal-row single-goal-row"><button class="goal-check-button">□</button><button class="goal-edit-target"><span class="goal-color-bar"></span><span class="day-view-row-content"><strong>포트폴리오 준비</strong><small>2026-09-30</small></span></button><button class="row-icon-button">›</button></div></li></ul></div>
              </section>
            </div>
          </section>
        </div>
      </main>
    </body>
  </html>`;
}

const viewports = [
  { width: 420, height: 300 },
  { width: 460, height: 330 },
  { width: 520, height: 380 },
  { width: 1366, height: 768 },
];

const browser = await chromium.launch({ headless: true });
const failures = [];

try {
  for (const viewport of viewports) {
    for (const settingsPanelSize of ["small", "large"]) {
      const page = await browser.newPage({ viewport });
      await page.setContent(renderDocument(settingsPanelSize), { waitUntil: "load" });
      const result = await page.evaluate(() => {
        const calendar = document.querySelector(".calendar-surface").getBoundingClientRect();
        const dayCell = document.querySelector(".day-cell").getBoundingClientRect();
        const panel = document.querySelector(".settings-floating-panel").getBoundingClientRect();
        const schedulePanel = document.querySelector(".schedule-create-panel").getBoundingClientRect();
        const goalPanel = document.querySelector(".goal-list-modal-panel").getBoundingClientRect();
        const dayViewPanel = document.querySelector(".date-detail-floating-panel").getBoundingClientRect();
        const body = document.body;
        const app = document.querySelector(".app-shell");
        const eventListDisplay = getComputedStyle(document.querySelector(".event-list")).display;

        return {
          documentWidth: document.documentElement.scrollWidth,
          documentHeight: document.documentElement.scrollHeight,
          viewportWidth: window.innerWidth,
          viewportHeight: window.innerHeight,
          bodyWidth: body.scrollWidth,
          bodyHeight: body.scrollHeight,
          appWidth: app.scrollWidth,
          appHeight: app.scrollHeight,
          calendarWidth: calendar.width,
          calendarHeight: calendar.height,
          dayCellWidth: dayCell.width,
          dayCellHeight: dayCell.height,
          panelWidth: panel.width,
          panelHeight: panel.height,
          schedulePanelWidth: schedulePanel.width,
          goalPanelWidth: goalPanel.width,
          dayViewPanelWidth: dayViewPanel.width,
          eventListDisplay,
          settingsLabelFontSize: Number.parseFloat(getComputedStyle(document.querySelector(".settings-field")).fontSize),
          scheduleLabelFontSize: Number.parseFloat(getComputedStyle(document.querySelector(".panel-form > label")).fontSize),
          aiConsentFontSize: Number.parseFloat(getComputedStyle(document.querySelector(".ai-consent-toggle strong")).fontSize),
          draftInputFontSize: Number.parseFloat(getComputedStyle(document.querySelector(".draft-title-input")).fontSize),
          goalTitleFontSize: Number.parseFloat(getComputedStyle(document.querySelector(".goal-list-title")).fontSize),
          dayViewTitleFontSize: Number.parseFloat(getComputedStyle(document.querySelector(".day-view-row-content strong")).fontSize),
        };
      });
      await page.close();

      const label = `${viewport.width}x${viewport.height}/${settingsPanelSize}`;
      if (result.documentWidth > viewport.width || result.bodyWidth > viewport.width) {
        failures.push(
          `${label}: horizontal overflow ` +
            `(document ${result.documentWidth}, body ${result.bodyWidth}, app ${result.appWidth}, viewport ${viewport.width})`,
        );
      }
      if (result.documentHeight > viewport.height || result.bodyHeight > viewport.height || result.appHeight > viewport.height) {
        failures.push(`${label}: shell vertical overflow`);
      }
      if (result.calendarWidth < 300 || result.calendarHeight < 190) {
        failures.push(`${label}: calendar is too small (${result.calendarWidth}x${result.calendarHeight})`);
      }
      if (result.dayCellWidth < 50 || result.dayCellHeight < 28) {
        failures.push(`${label}: day cell is too small (${result.dayCellWidth}x${result.dayCellHeight})`);
      }
      if (result.panelWidth > viewport.width - 12 || result.panelHeight > viewport.height) {
        failures.push(`${label}: settings panel exceeds viewport (${result.panelWidth}x${result.panelHeight})`);
      }
      if (
        result.schedulePanelWidth > viewport.width - 12 ||
        result.goalPanelWidth > viewport.width - 12 ||
        result.dayViewPanelWidth > viewport.width - 12
      ) {
        failures.push(
          `${label}: system panels exceed viewport ` +
            `(schedule ${result.schedulePanelWidth}, goal ${result.goalPanelWidth}, day ${result.dayViewPanelWidth})`,
        );
      }
      if (
        settingsPanelSize === "large" &&
        (
          result.settingsLabelFontSize < 12 ||
          result.scheduleLabelFontSize < 13 ||
          result.aiConsentFontSize < 13 ||
          result.draftInputFontSize < 13 ||
          result.goalTitleFontSize < 14 ||
          result.dayViewTitleFontSize < 14
        )
      ) {
        failures.push(`${label}: large system text was not applied`);
      }
      if (viewport.width <= 460 && result.eventListDisplay !== "none") {
        failures.push(`${label}: compact calendar should hide event text`);
      }
    }
  }
} finally {
  await browser.close();
}

if (failures.length > 0) {
  console.error(failures.join("\n"));
  process.exit(1);
}

console.log("Compact layout checks passed.");
