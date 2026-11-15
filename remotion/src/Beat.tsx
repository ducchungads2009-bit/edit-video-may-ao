/* DỰNG THEO NHỊP NHẠC — các khối chạy theo nhịp (plan.beats, giây trên video xuất):
 *  beatFrames ("Khung nhịp"): các khung bo góc bật ra từng cái theo nhịp, kín khung hình -> thu lại thành ô -> bung ra.
 *  beatStrips ("Dải chéo"): các dải xiên lần lượt trượt vào theo nhịp, lộ dần cảnh mới (chuyển cảnh).
 * Bố cục tự đổi theo khung hình: ngang -> khung đứng xếp hàng ngang; dọc -> dải ngang xếp chồng; vuông -> lưới 2×2. */
import React, {createContext, useContext} from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame} from 'remotion';
import {FR} from './frame';
import {MediaFill} from './Media';

const FPS = 30;
/** nhịp nhạc (giây, tuyệt đối trên video xuất) — EditPlan cung cấp */
export const BeatCtx = createContext<number[]>([]);

/** các mốc (giây, tính từ lúc khối hiện) để bật từng phần: theo nhịp nằm trong khối, thiếu thì chia đều */
export const beatTimes = (beats: number[], start: number, dur: number, n: number, every = 1, spread = 0.6): number[] => {
  const pick = beats.filter((b) => b >= start - 0.02 && b < start + dur - 0.05).map((b) => Math.max(0, b - start))
    .filter((_, k) => k % Math.max(1, every) === 0).slice(0, n);
  if (!pick.length) { const st = (dur * spread) / n; return Array.from({length: n}, (_, k) => k * st); }
  const gaps = pick.slice(1).map((x, k) => x - pick[k]).sort((x, y) => x - y);
  const step = Math.max(0.15, gaps.length ? gaps[gaps.length >> 1] : 0.35);
  while (pick.length < n) pick.push(pick[pick.length - 1] + step);
  return pick;
};

type Rect = {x: number; y: number; w: number; h: number};
const lerp = (a: number, b: number, k: number) => a + (b - a) * k;
const mix = (r: Rect, s: Rect, k: number): Rect => ({x: lerp(r.x, s.x, k), y: lerp(r.y, s.y, k), w: lerp(r.w, s.w, k), h: lerp(r.h, s.h, k)});

/** bố cục theo tỉ lệ khung: cols (khung đứng) | rows (dải ngang) | grid */
export const autoLayout = (lay?: string) => {
  if (lay && lay !== 'auto') return lay;
  const a = FR.w / FR.h;
  return a > 1.2 ? 'cols' : a < 0.8 ? 'rows' : 'grid';
};
const defCount = (lay: string) => (lay === 'cols' ? (FR.w / FR.h > 1.6 ? 5 : 4) : lay === 'rows' ? 3 : 4);

/** vị trí từng khung: đầy đủ (full) và dạng ô thu nhỏ (tile) */
const layoutRects = (lay: string, n: number, gap: number): {full: Rect[]; tile: Rect[]} => {
  const W = FR.w, H = FR.h, full: Rect[] = [], tile: Rect[] = [];
  if (lay === 'grid') {
    const c = Math.ceil(Math.sqrt(n)), r = Math.ceil(n / c);
    const cw = (W - gap * (c + 1)) / c, ch = (H - gap * (r + 1)) / r;
    for (let k = 0; k < n; k++) {
      const i = k % c, j = Math.floor(k / c);
      const R = {x: gap + i * (cw + gap), y: gap + j * (ch + gap), w: cw, h: ch};
      full.push(R);
      const s = Math.min(cw, ch) * 0.72;
      tile.push({x: R.x + (cw - s) / 2, y: R.y + (ch - s) / 2, w: s, h: s});
    }
  } else if (lay === 'rows') {
    const bh = (H - gap * (n + 1)) / n;
    for (let k = 0; k < n; k++) {
      const R = {x: gap, y: gap + k * (bh + gap), w: W - 2 * gap, h: bh};
      full.push(R);
      const s = Math.min(bh, W * 0.42);
      tile.push({x: (W - s) / 2, y: R.y + (bh - s) / 2, w: s, h: s});
    }
  } else {
    const cw = (W - gap * (n + 1)) / n;
    for (let k = 0; k < n; k++) {
      const R = {x: gap + k * (cw + gap), y: gap, w: cw, h: H - 2 * gap};
      full.push(R);
      tile.push({x: R.x, y: (H - cw) / 2, w: cw, h: cw});
    }
  }
  return {full, tile};
};

/** KHUNG NHỊP */
export const BeatFrames: React.FC<{e: any; dur: number; filter?: string}> = ({e, dur, filter}) => {
  const f = useCurrentFrame();
  const beats = useContext(BeatCtx);
  const lay = autoLayout(e.layout);
  const n = Math.max(2, Math.min(8, Math.round(e.count || defCount(lay))));
  const gap = e.gap ?? Math.round(Math.min(FR.w, FR.h) * 0.012);
  const rad = e.radius ?? Math.round(Math.min(FR.w, FR.h) * 0.035);
  const D = dur / FPS;
  const srcs: string[] = (Array.isArray(e.srcs) && e.srcs.length ? e.srcs : [e.src]).filter(Boolean);
  const T = beatTimes(beats, e.start, D, n, e.every || 1, 0.55);
  const {full, tile} = layoutRects(lay, n, gap);
  // pha thu ô: sau khung cuối 1 nhịp (hoặc 0,5s); pha bung: 0,45s cuối
  const tAll = T[n - 1];
  const inb = beats.filter((b) => b > e.start + tAll + 0.1 && b < e.start + D - 0.3).map((b) => b - e.start);
  const tCol = e.collapse === false ? Infinity : inb[0] ?? Math.min(D - 0.6, tAll + 0.5);
  const soft = !!e.soft; // nhạc êm / vừa: khung hiện dần, thu / bung chậm (không nảy)
  const sm = (x: number) => (x <= 0 ? 0 : x >= 1 ? 1 : x * x * (3 - 2 * x));
  const tExp = e.exit === 'cut' ? Infinity : D - (soft ? 0.9 : 0.45);
  const t = f / FPS;
  const kCol = t < tCol ? 0 : soft ? sm((t - tCol) / 0.8) : spring({frame: f - Math.round(tCol * FPS), fps: FPS, config: {damping: 16, stiffness: 140}});
  const kExp = t < tExp ? 0 : interpolate(t, [tExp, D], [0, 1], {extrapolateRight: 'clamp', easing: (x) => x * x * (3 - 2 * x)});
  const one = srcs.length <= 1; // 1 nguồn: các khung là "cửa sổ" nhìn vào cùng 1 cảnh
  const frameR: Rect = {x: 0, y: 0, w: FR.w, h: FR.h};
  return (
    <AbsoluteFill style={{background: e.bg || '#000', overflow: 'hidden'}}>
      {full.map((R, k) => {
        const tk = T[k];
        if (t < tk) return null;
        const ki = soft ? sm((t - tk) / Math.max(0.35, Math.min(0.9, (T[1] ?? tk + 0.6) - (T[0] ?? 0)))) : spring({frame: f - Math.round(tk * FPS), fps: FPS, config: {damping: 15, stiffness: 170, mass: 0.7}});
        let r = mix(R, tile[k], kCol);
        if (kExp > 0) r = mix(r, frameR, kExp);
        // bật vào: khung đứng trượt từ dưới lên, dải ngang trượt từ cạnh, lưới phóng ra
        const mv = soft ? 0.12 : 1; // hiện dần: chỉ trượt nhẹ + rõ dần
        const off = lay === 'cols' ? {dx: 0, dy: (1 - ki) * FR.h * 0.6 * mv} : lay === 'rows' ? {dx: (k % 2 ? 1 : -1) * (1 - ki) * FR.w * 0.7 * mv, dy: 0} : {dx: 0, dy: 0};
        const sc = lay === 'grid' ? (soft ? 0.94 + 0.06 * ki : 0.6 + 0.4 * ki) : soft ? 1.03 - 0.03 * ki : 1;
        const rr = lerp(rad, kCol > 0 ? Math.min(r.w, r.h) * 0.18 : rad, kCol) * (1 - kExp);
        const src = srcs[k % Math.max(1, srcs.length)];
        const from = Array.isArray(e.froms) && e.froms[k] != null ? e.froms[k] : e.from || 0;
        return (
          <div key={k} style={{position: 'absolute', left: r.x + off.dx, top: r.y + off.dy, width: r.w, height: r.h, borderRadius: rr, overflow: 'hidden',
            transform: sc !== 1 ? `scale(${sc})` : undefined, opacity: soft ? ki : Math.min(1, ki * 1.4), boxShadow: kExp < 1 ? '0 6px 24px rgba(0,0,0,.35)' : undefined}}>
            {one ? (
              // cửa sổ: lớp cảnh toàn khung đặt lệch ngược lại -> các khung ghép thành 1 cảnh liền
              <div style={{position: 'absolute', left: -(r.x + off.dx), top: -(r.y + off.dy), width: FR.w, height: FR.h}}>
                {src ? <MediaFill src={src} from={from} zoom={1.04 + 0.04 * (t / D)} panX={0} filter={filter} /> : null}
              </div>
            ) : (
              src ? <MediaFill src={src} from={from} zoom={1.06} panX={0} filter={filter} /> : null
            )}
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

/** DẢI CHÉO: lộ dần cảnh mới qua các dải xiên (che video chính) */
export const BeatStrips: React.FC<{e: any; dur: number; filter?: string}> = ({e, dur, filter}) => {
  const f = useCurrentFrame();
  const beats = useContext(BeatCtx);
  const n = Math.max(2, Math.min(7, Math.round(e.count || 3)));
  const D = dur / FPS;
  const T = beatTimes(beats, e.start, D, n, e.every || 1, 0.6);
  const a = FR.w / FR.h;
  const ang = e.angle || (a > 1.2 ? 28 : a < 0.8 ? 18 : 24); // độ nghiêng (so với trục đứng)
  const Dg = Math.ceil(Math.hypot(FR.w, FR.h) * 1.08);
  const bw = Dg / n;
  const line = e.line ?? '#000';
  const lw = e.lineW ?? Math.round(Math.min(FR.w, FR.h) * 0.006);
  const t = f / FPS;
  return (
    <AbsoluteFill style={{overflow: 'hidden', pointerEvents: 'none'}}>
      <div style={{position: 'absolute', left: (FR.w - Dg) / 2, top: (FR.h - Dg) / 2, width: Dg, height: Dg, transform: `rotate(${ang}deg)`}}>
        {Array.from({length: n}, (_, k) => {
          const tk = T[k];
          if (t < tk) return null;
          const sm = (x: number) => (x <= 0 ? 0 : x >= 1 ? 1 : x * x * (3 - 2 * x));
          const ki = e.soft ? sm((t - tk) / 0.7) : spring({frame: f - Math.round(tk * FPS), fps: FPS, config: {damping: 18, stiffness: 160}});
          const dir = k % 2 ? -1 : 1; // dải chẵn trượt từ dưới, lẻ từ trên
          const ty = (1 - ki) * Dg * dir * (e.soft ? 0.25 : 1);
          return (
            <div key={k} style={{position: 'absolute', left: k * bw - 1, top: ty, width: bw + 2, height: Dg, overflow: 'hidden', opacity: e.soft ? ki : 1,
              borderLeft: k && line !== 'none' ? `${lw}px solid ${line}` : undefined}}>
              <div style={{position: 'absolute', left: Dg / 2 - FR.w / 2 - k * bw + 1, top: Dg / 2 - FR.h / 2 - ty, width: FR.w, height: FR.h,
                transform: `rotate(${-ang}deg)`, transformOrigin: '50% 50%'}}>
                {e.src ? <MediaFill src={e.src} from={e.from || 0} zoom={1.05} panX={0} filter={filter} /> : null}
              </div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

/** MÀN MÀU (đen / trắng) phủ kín khung — màn đen chen giữa cảnh kiểu trailer, kết bằng màn đen; fadeIn / fadeOut (giây) */
export const Solid: React.FC<{e: any; dur: number}> = ({e, dur}) => {
  const f = useCurrentFrame();
  const fi = Math.round((e.fadeIn || 0) * FPS), fo = Math.round((e.fadeOut || 0) * FPS);
  let op = 1;
  if (fi > 0) op = Math.min(op, interpolate(f, [0, fi], [0, 1], {extrapolateRight: 'clamp'}));
  if (fo > 0) op = Math.min(op, interpolate(f, [dur - fo, dur], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}));
  return <AbsoluteFill style={{background: e.color || '#000', opacity: op * (e.opacity ?? 1)}} />;
};

/** VIỀN PHIM (letterbox) — tự theo khung: ngang = tỉ lệ 2.39 điện ảnh, dọc / vuông = dải mỏng trên dưới; trượt vào / ra */
export const Bars: React.FC<{e: any; dur: number}> = ({e, dur}) => {
  const f = useCurrentFrame();
  const a = FR.w / FR.h;
  const full = e.size ?? (a > 1.2 ? Math.max(0, (FR.h - FR.w / 2.39) / 2) : FR.h * (a < 0.8 ? 0.06 : 0.08));
  const kin = interpolate(f, [0, 12], [0, 1], {extrapolateRight: 'clamp', easing: (x) => 1 - (1 - x) * (1 - x)});
  const kout = interpolate(f, [dur - 9, dur], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const h = full * Math.min(kin, kout);
  const c = e.color || '#000';
  return (
    <AbsoluteFill style={{pointerEvents: 'none'}}>
      <div style={{position: 'absolute', left: 0, right: 0, top: 0, height: h, background: c}} />
      <div style={{position: 'absolute', left: 0, right: 0, bottom: 0, height: h, background: c}} />
    </AbsoluteFill>
  );
};
