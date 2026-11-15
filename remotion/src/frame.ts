/* KHUNG HÌNH (tỉ lệ) của video: dọc 1080×1920, 4:5 1080×1350, vuông 1080×1080, ngang 1920×1080.
   Cỡ chữ / khối giữ nguyên px (khung ngang -> chữ tương đối nhỏ hơn, hợp màn hình ngang).
   FR.h được EditPlan đặt mỗi khung (theo useVideoConfig().height) — các khối đọc FR.h thay cho số 1920. */
export const FORMATS: Record<string, {w: number; h: number; scale: number; label: string}> = {
  '9:16': {w: 1080, h: 1920, scale: 1, label: 'Dọc 9:16 (TikTok, Reels, Shorts)'},
  '4:5': {w: 1080, h: 1350, scale: 1, label: 'Dọc 4:5 (Facebook, Instagram)'},
  '1:1': {w: 1080, h: 1080, scale: 1, label: 'Vuông 1:1'},
  '16:9': {w: 1920, h: 1080, scale: 1, label: 'Ngang 16:9 (YouTube)'},
};
export const fmtOf = (f?: string) => FORMATS[f || '9:16'] || FORMATS['9:16'];
export const FR = {w: 1080, h: 1920};
/** x mặc định thiết kế cho khung rộng 1080 -> khung hiện tại */
export const fx = (x: number) => (FR.w === 1080 ? x : Math.round((x * FR.w) / 1080));
/** y mặc định thiết kế cho khung dọc 1920 -> khung hiện tại (giữ tỉ lệ) */
export const fy = (y: number) => (FR.h === 1920 ? y : Math.round((y * FR.h) / 1920));
/** y mặc định của từng loại khối (thiết kế cho khung 1920) — GIỐNG DEFAULT_Y trong editor/logic.ts */
export const DEFAULT_Y: Record<string, number> = {text3d: 600, scene: 300, card3d: 760, chart: 300, phrase: 300, counter: 420, stamp: 600, tabs: 260, tiles: 300, note: 260, bubble: 380, spark: 300, presenter: 1290, chip: 240, priceHook: 520, bigQuestion: 620, checklist: 240, rangeCard: 280, cta: 1120, pip: 260, text: 700, sticker: 600};
