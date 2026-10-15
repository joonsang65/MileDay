import { readFile, mkdir } from "node:fs/promises";
import { createServer } from "node:http";
import { resolve, extname, sep } from "node:path";
import { chromium } from "playwright";

/* global window, document, URL */

const root = resolve("out/renderer");
const artifacts = resolve("../artifacts/today-panel");
await mkdir(artifacts, { recursive: true });
const server = createServer(async (request, response) => {
  const path = resolve(root, `.${new URL(request.url, "http://localhost").pathname === "/" ? "/index.html" : new URL(request.url, "http://localhost").pathname}`);
  if (!path.startsWith(root + sep)) { response.writeHead(403).end(); return; }
  try {
    const types = { ".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".ttf": "font/ttf" };
    response.writeHead(200, { "Content-Type": types[extname(path)] ?? "application/octet-stream" });
    response.end(await readFile(path));
  } catch { response.writeHead(404).end(); }
});
await new Promise((done) => server.listen(0, "127.0.0.1", done));
const origin = `http://127.0.0.1:${server.address().port}`;
const browser = await chromium.launch({ headless: true });
const today = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Seoul", year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date());
const goal = { id: "g", title: "Portfolio planning", deadline: today, color: "#7F9278", is_completed: false, is_recurring: false, recurrence_type: null, created_at: "", updated_at: "" };
const milestones = Array.from({ length: 18 }, (_, i) => ({ id: `m${i}`, goal_id: "g", goal_title: goal.title, title: `Milestone ${i + 1}: Review project notes and prepare the next release`, color: goal.color, scheduled_date: today, is_completed: false }));
const day = { date: today, is_today: true, goal_count: 1, milestone_count: milestones.length, completed_milestone_count: 0, goals: [goal], milestones };
try {
  for (const viewport of [{ width: 420, height: 300 }, { width: 640, height: 480 }, { width: 980, height: 760 }]) {
    const page = await browser.newPage({ viewport });
    const errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    await page.addInitScript(() => {
      window.mileday = {
        platform: "win32",
        authToken: { get: async () => "layout-test-token" },
        uiSettings: { get: async () => ({ baseFontSize: 12, goalFontSize: 13, resizeEnabled: false, todaySidePanelEnabled: true, settingsPanelSize: "small", opacity: 1, theme: "system", fontFamily: "system" }) },
      };
    });
    await page.route("**/*", async (route) => {
      const url = new URL(route.request().url());
      if (url.origin === origin) { await route.continue(); return; }
      let data;
      if (url.pathname === "/settings") data = { calendar_view: "month", holiday_display: "normal", week_starts_on: 1, language: "en", timezone: "Asia/Seoul", gemini_data_consent: false };
      else if (url.pathname === "/goals") data = [goal];
      else if (url.pathname === "/calendar/month") data = { year: Number(url.searchParams.get("year")), month: Number(url.searchParams.get("month")), days: [day], goals: [goal], milestones };
      else if (url.pathname.includes("/calendar/date/")) data = day;
      else if (url.pathname.endsWith("/complete")) { milestones[0].is_completed = true; data = milestones[0]; }
      else { await route.abort(); return; }
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ success: true, data }) });
    });
    await page.goto(origin);
    const panel = page.getByRole("complementary", { name: "Today's schedule" });
    await panel.getByRole("button").first().waitFor();
    const calendar = page.locator(".calendar-surface");
    const calendarBounds = await calendar.boundingBox();
    const panelBounds = await panel.boundingBox();
    if (calendarBounds.width < (viewport.width < 900 ? viewport.width - 50 : 570)) throw new Error(`Calendar shrank at ${viewport.width}`);
    if (panelBounds.x < 0 || panelBounds.y < 0 || panelBounds.x + panelBounds.width > viewport.width || panelBounds.y + panelBounds.height > viewport.height) throw new Error(`Panel overflows at ${viewport.width}`);
    const scroll = panel.locator(".today-side-panel-scroll");
    if (!await scroll.evaluate((element) => element.scrollHeight > element.clientHeight)) throw new Error("Panel does not scroll independently");
    const toggle = panel.getByRole("button", { name: milestones[0].title, exact: true });
    await toggle.click();
    await page.waitForFunction((name) => document.querySelector(`.today-side-panel button[aria-label="${name}"]`).getAttribute("aria-pressed") === "true", milestones[0].title);
    await page.screenshot({ path: resolve(artifacts, `${viewport.width}x${viewport.height}.png`) });
    if (viewport.width < 900) {
      await page.locator(".today-panel-toggle").click();
      if (await panel.isVisible()) throw new Error("Compact panel did not close");
      await page.locator(".today-panel-toggle").click();
      if (!await panel.isVisible()) throw new Error("Compact panel did not reopen");
    } else if (panelBounds.x < calendarBounds.x + calendarBounds.width) throw new Error("Wide panel overlaps calendar");
    if (errors.length) throw new Error(errors.join("\n"));
    await page.close();
  }
} finally {
  await browser.close();
  await new Promise((done) => server.close(done));
}
console.log("Today's panel layout and toggle checks passed at 420x300, 640x480, and 980x760.");
