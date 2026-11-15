/* Khối kiểu After Effects (vẽ bằng CSS/SVG, không cần thư viện ngoài, chữ tiếng Việt đầy đủ):
   - overlay: lớp hiệu ứng phủ khung có chế độ hoà trộn (light leak, lens flare, bokeh, hạt bay, bụi phim, film burn, tuyết,
     pháo giấy, hạt nhiễu, tia sáng)
   - shape: hình / mũi tên tự vẽ ra (arrow, line, circle, underline, box, callout, check, cross)
   - text3d: chữ khối 3D xoay trong không gian
   - card3d: ảnh/video trên mặt phẳng 3D, camera bay quanh
   - scene: cảnh dựng sẵn theo tham số (intro, pricetable, compare, amenities, stats, outro) */
import React from 'react';
import {FR} from './frame';
import {AbsoluteFill, Easing, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import * as Icons from 'lucide-react';
import {MediaFill} from './Media';
import {EASES, S, fontCss, fontWeight} from './style';

type Theme = {light: string; mid: string; dark: string; gold1: string; gold2: string};
const cl = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
const rnd = (n: number) => {
  const x = Math.sin(n * 127.1 + 311.7) * 43758.5453;
  return x - Math.floor(x);
};
/** x/y ≤ 1 = tỉ lệ khung, lớn hơn = px */
const px = (v: number | undefined, full: number, def: number) => (v == null ? def : Math.abs(v) <= 1 && v !== 0 ? v * full : v);
const env = (f: number, dur: number, a = 8, b = 8) => Math.min(interpolate(f, [0, a], [0, 1], cl), interpolate(f, [dur - b, dur], [1, 0], cl));
const headF = () => fontCss(S.style.heading || S.style.font);
const bodyF = () => fontCss(S.style.font);

/* =================== OVERLAY =================== */
/** chế độ hoà trộn mặc định của từng loại overlay (ElSeq áp lên lớp ngoài cùng để hoà với video bên dưới) */
export const OVERLAY_BLEND: Record<string, string> = {
  lightleak: 'screen', flare: 'screen', bokeh: 'screen', particles: 'screen', filmburn: 'screen', rays: 'screen',
  dust: 'normal', snow: 'normal', confetti: 'normal', grain: 'overlay', sparkle: 'screen',
};
export const OVERLAY_KINDS = Object.keys(OVERLAY_BLEND);

export const Overlay: React.FC<{e: any; dur: number; theme: Theme}> = ({e, dur, theme}) => {
  const f = useCurrentFrame();
  const k = Math.max(0, Math.min(1.5, (e.amount ?? 70) / 100));
  const kind = e.kind || 'lightleak';
  const seed = e.seed ?? 1;
  const sp = e.speed ?? 1;
  const t = f * sp;
  const fade = kind === 'filmburn' ? 1 : env(f, dur, e.inDur ? e.inDur * 30 : 10, e.outDur ? e.outDur * 30 : 12);
  const col = e.color;
  let node: React.ReactNode = null;
  switch (kind) {
    case 'lightleak': {
      const cs = col ? [col, col, col] : ['#ff7a18', '#ff3d77', '#ffd36e'];
      node = (
        <AbsoluteFill>
          {[0, 1, 2].map((i) => {
            const cx = 50 + Math.sin(t / (40 + i * 13) + seed * 3 + i * 2) * 55;
            const cy = 30 + Math.cos(t / (55 + i * 17) + seed + i) * 45 + i * 20;
            const r = 55 + 20 * Math.sin(t / 30 + i);
            const a = (0.55 + 0.35 * Math.sin(t / 22 + i * 1.7)) * k;
            return <AbsoluteFill key={i} style={{background: `radial-gradient(circle at ${cx}% ${cy}%, ${cs[i]} 0%, transparent ${r}%)`, opacity: Math.max(0, a)}} />;
          })}
        </AbsoluteFill>
      );
      break;
    }
    case 'flare': {
      const fx = px(e.x, FR.w, FR.w * 0.78) + Math.sin(t / 45) * 120 * (e.move ?? 1), fy = px(e.y, FR.h, FR.h * 0.2) + Math.cos(t / 60) * 40;
      const c = col || '#ffe7b0';
      const vx = FR.w / 2 - fx, vy = FR.h / 2 - fy;
      const ghosts = [0.35, 0.6, 0.9, 1.25, 1.6];
      node = (
        <AbsoluteFill style={{opacity: k * (0.85 + 0.15 * Math.sin(t / 7))}}>
          <AbsoluteFill style={{background: `radial-gradient(circle at ${fx}px ${fy}px, white 0, ${c} 3%, rgba(255,200,120,0.35) 12%, transparent 34%)`}} />
          <div style={{position: 'absolute', left: fx - 900, top: fy - 6, width: 1800, height: 12, background: `linear-gradient(90deg, transparent, ${c}, white, ${c}, transparent)`, filter: 'blur(4px)', opacity: 0.8}} />
          {ghosts.map((g, i) => {
            const r = [70, 40, 120, 26, 90][i];
            return (
              <div key={i} style={{position: 'absolute', left: fx + vx * g * 2 - r, top: fy + vy * g * 2 - r, width: r * 2, height: r * 2, borderRadius: '50%',
                background: i % 2 ? `radial-gradient(circle, transparent 55%, rgba(120,200,255,0.35) 70%, transparent 75%)` : `radial-gradient(circle, rgba(255,170,90,0.28), transparent 70%)`}} />
            );
          })}
        </AbsoluteFill>
      );
      break;
    }
    case 'rays': {
      const ox = px(e.x, FR.w, FR.w * 0.15), oy = px(e.y, FR.h, -100);
      const c = col || 'rgba(255,240,200,0.55)';
      node = (
        <AbsoluteFill style={{opacity: k * 0.9, background: `repeating-conic-gradient(from ${t * 0.15 + seed * 20}deg at ${ox}px ${oy}px, ${c} 0deg 3deg, transparent 3deg 11deg)`,
          WebkitMaskImage: `radial-gradient(circle at ${ox}px ${oy}px, black 0, transparent 75%)`, filter: 'blur(6px)'} as any} />
      );
      break;
    }
    case 'bokeh':
    case 'particles':
    case 'sparkle': {
      const n = Math.round((kind === 'bokeh' ? 18 : kind === 'sparkle' ? 26 : 60) * (e.density ?? 1));
      const pal = col ? [col] : kind === 'bokeh' ? ['#ffd59e', '#ffb3c7', '#bfe3ff', '#fff3c4'] : ['#fff6d8', '#ffe3a1', '#ffffff'];
      node = (
        <AbsoluteFill style={{opacity: k}}>
          {Array.from({length: n}, (_, i) => {
            const r0 = rnd(i + seed * 100), r1 = rnd(i * 3.1 + seed), r2 = rnd(i * 7.7 + seed * 5);
            const size = kind === 'bokeh' ? 40 + r2 * 120 : kind === 'sparkle' ? 18 + r2 * 26 : 3 + r2 * 7;
            const vy = kind === 'bokeh' ? 0.6 + r1 : 1.2 + r1 * 2.4;
            const x = r0 * FR.w + Math.sin(t / (25 + r1 * 30) + i) * (kind === 'bokeh' ? 40 : 25);
            const y = ((r1 * FR.h - t * vy) % (FR.h + 200) + FR.h + 200) % (FR.h + 200) - 100;
            const tw = 0.5 + 0.5 * Math.sin(t / (6 + r2 * 8) + i * 2);
            const c = pal[i % pal.length];
            if (kind === 'sparkle')
              return (
                <svg key={i} width={size} height={size} viewBox="-10 -10 20 20" style={{position: 'absolute', left: x, top: y, opacity: tw, transform: `rotate(${t * 2 + i * 40}deg) scale(${0.5 + tw * 0.7})`, filter: `drop-shadow(0 0 6px ${c})`}}>
                  <path d="M0 -10 L2 -2 L10 0 L2 2 L0 10 L-2 2 L-10 0 L-2 -2 Z" fill={c} />
                </svg>
              );
            return (
              <div key={i} style={{position: 'absolute', left: x - size / 2, top: y - size / 2, width: size, height: size, borderRadius: '50%',
                background: kind === 'bokeh' ? `radial-gradient(circle, ${c}cc 0%, ${c}66 55%, ${c}00 72%)` : c,
                boxShadow: kind === 'bokeh' ? undefined : `0 0 ${size * 2}px ${c}`, opacity: kind === 'bokeh' ? 0.35 + 0.4 * tw : 0.4 + 0.6 * tw}} />
            );
          })}
        </AbsoluteFill>
      );
      break;
    }
    case 'snow':
    case 'confetti': {
      const n = Math.round((kind === 'snow' ? 110 : 90) * (e.density ?? 1));
      const pal = col ? [col] : ['#ff4d6d', '#ffd60a', '#3a86ff', '#06d6a0', '#ff9f1c', '#c77dff'];
      node = (
        <AbsoluteFill style={{opacity: Math.min(1, k)}}>
          {Array.from({length: n}, (_, i) => {
            const r0 = rnd(i + seed * 50), r1 = rnd(i * 2.3 + seed), r2 = rnd(i * 5.9 + seed * 3);
            const vy = kind === 'snow' ? 1.5 + r1 * 3 : 6 + r1 * 8;
            const start = kind === 'confetti' ? -r2 * 900 - 40 : r1 * FR.h;
            const y = kind === 'confetti' ? start + t * vy : ((start + t * vy) % (FR.h + 60)) - 30;
            const x = r0 * FR.w + Math.sin(t / (14 + r2 * 20) + i) * (kind === 'snow' ? 30 : 60);
            if (kind === 'snow') {
              const s = 4 + r2 * 10;
              return <div key={i} style={{position: 'absolute', left: x, top: y, width: s, height: s, borderRadius: '50%', background: 'white', opacity: 0.55 + r2 * 0.45, filter: s > 10 ? 'blur(1.5px)' : undefined}} />;
            }
            if (y > FR.h + 40) return null;
            return (
              <div key={i} style={{position: 'absolute', left: x, top: y, width: 14 + r2 * 10, height: 8 + r1 * 8, background: pal[i % pal.length],
                transform: `rotate(${t * (4 + r1 * 8) + i * 30}deg) rotateX(${t * (10 + r2 * 10)}deg)`, borderRadius: 2}} />
            );
          })}
        </AbsoluteFill>
      );
      break;
    }
    case 'dust': {
      const fr = Math.floor(f / 2);
      node = (
        <AbsoluteFill style={{opacity: Math.min(1, k)}}>
          {Array.from({length: 26}, (_, i) => {
            const r0 = rnd(i + fr * 31 + seed), r1 = rnd(i * 4.3 + fr * 17), r2 = rnd(i * 9.1 + fr * 7);
            if (r2 < 0.45) return null;
            const s = 2 + r1 * 7;
            return <div key={i} style={{position: 'absolute', left: r0 * FR.w, top: r1 * FR.h, width: s * (r2 > 0.9 ? 4 : 1), height: s, borderRadius: r2 > 0.9 ? 4 : '50%', background: r2 > 0.75 ? 'rgba(255,255,255,0.75)' : 'rgba(20,14,8,0.7)', transform: `rotate(${r0 * 180}deg)`}} />;
          })}
          {[0, 1].map((i) => {
            const r = rnd(fr * 3 + i * 11 + seed);
            return r > 0.55 ? <div key={'s' + i} style={{position: 'absolute', left: rnd(fr + i * 5) * FR.w, top: 0, width: 2, height: FR.h, background: 'rgba(255,255,255,0.35)', opacity: r}} /> : null;
          })}
          <AbsoluteFill style={{background: `rgba(255,236,200,${0.04 + 0.04 * rnd(fr)})`}} />
        </AbsoluteFill>
      );
      break;
    }
    case 'filmburn': {
      // cháy phim: bùng lên giữa khối rồi tắt — hợp đặt ở điểm chuyển cảnh (khối 0,8–1,5s)
      const p = f / Math.max(1, dur);
      const a = Math.sin(Math.PI * Math.min(1, p)) * k;
      const side = e.side || (seed % 2 ? 'right' : 'left');
      const cx = side === 'left' ? 10 + p * 60 : side === 'right' ? 90 - p * 60 : 50;
      node = (
        <AbsoluteFill style={{opacity: Math.min(1, a * 1.3)}}>
          <AbsoluteFill style={{background: `radial-gradient(ellipse at ${cx}% ${40 + 20 * Math.sin(p * 4)}%, #fff7d6 0%, #ffb347 18%, #ff5e3a 38%, rgba(160,20,10,0.6) 58%, transparent 78%)`}} />
          <AbsoluteFill style={{background: `radial-gradient(circle at ${100 - cx}% ${70}%, rgba(255,140,40,0.7), transparent 45%)`, opacity: 0.7}} />
        </AbsoluteFill>
      );
      break;
    }
    case 'grain': {
      node = (
        <AbsoluteFill style={{opacity: 0.35 * k}}>
          <svg width={FR.w} height={FR.h}>
            <filter id={`gr${e._i ?? 0}`}>
              <feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves={2} seed={f % 50} />
              <feColorMatrix type="saturate" values="0" />
            </filter>
            <rect width={FR.w} height={FR.h} filter={`url(#gr${e._i ?? 0})`} />
          </svg>
        </AbsoluteFill>
      );
      break;
    }
  }
  return <AbsoluteFill style={{opacity: fade, pointerEvents: 'none'}}>{node}</AbsoluteFill>;
};

/* =================== SHAPE (vẽ ra) =================== */
export const SHAPE_KINDS = ['arrow', 'line', 'circle', 'underline', 'box', 'callout', 'check', 'cross', 'bracket'];
const ease3 = Easing.inOut(Easing.cubic);

export const Shape: React.FC<{e: any; dur: number; theme: Theme}> = ({e, dur, theme}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const kind = e.kind || 'arrow';
  const color = e.color || theme.gold1 || '#FFD400';
  const sw = e.width ?? (kind === 'underline' && e.marker ? 34 : 11);
  const drawF = Math.max(4, (e.draw ?? 0.6) * fps);
  const p = ease3(Math.min(1, f / drawF));
  const outF = Math.max(1, Math.min(dur - 1, (e.outDur ?? 0.25) * fps));
  const op = interpolate(f, [dur - outF, dur], [1, 0], cl);
  const x = px(e.x, FR.w, FR.w / 2), y = px(e.y, FR.h, 900);
  const w = e.w ?? 360, h = e.h ?? (kind === 'circle' ? 220 : 160);
  const x2 = px(e.x2, FR.w, x + 260), y2 = px(e.y2, FR.h, y - 200);
  const glow = e.glow === false ? undefined : `drop-shadow(0 0 ${e.glow ? 14 : 3}px ${e.glow ? color : 'rgba(0,0,0,0.5)'})`;
  const dash = (pp: number, key: string, d: string, extra?: React.SVGProps<SVGPathElement>) => (
    <path key={key} d={d} pathLength={1} strokeDasharray="1 1" strokeDashoffset={1 - Math.max(0, Math.min(1, pp))} fill="none" stroke={color} strokeWidth={sw} strokeLinecap="round" strokeLinejoin="round" {...extra} />
  );
  const paths: React.ReactNode[] = [];
  let label: React.ReactNode = null;
  const bend = e.bend ?? 0.25;
  const curve = (ax: number, ay: number, bx: number, by: number) => {
    const mx = (ax + bx) / 2, my = (ay + by) / 2;
    const nx = -(by - ay), ny = bx - ax;
    return {d: `M${ax},${ay} Q${mx + nx * bend},${my + ny * bend} ${bx},${by}`, cx: mx + nx * bend, cy: my + ny * bend};
  };
  switch (kind) {
    case 'arrow':
    case 'line': {
      const c = curve(x, y, x2, y2);
      paths.push(dash(kind === 'arrow' ? p / 0.8 : p, 'l', c.d));
      if (kind === 'arrow') {
        const ang = Math.atan2(y2 - c.cy, x2 - c.cx), L = Math.max(34, sw * 3.6);
        const a1 = ang + Math.PI * 0.82, a2 = ang - Math.PI * 0.82;
        const hp = Math.max(0, (p - 0.75) / 0.25);
        paths.push(dash(hp, 'h1', `M${x2},${y2} L${x2 + Math.cos(a1) * L},${y2 + Math.sin(a1) * L}`));
        paths.push(dash(hp, 'h2', `M${x2},${y2} L${x2 + Math.cos(a2) * L},${y2 + Math.sin(a2) * L}`));
      }
      break;
    }
    case 'circle': {
      // vòng khoanh tay: hơi méo, chạy quá 1 vòng một chút
      const rx = w / 2, ry = h / 2, n = 40, turns = e.rough === false ? 1 : 1.12;
      let d = '';
      for (let i = 0; i <= n; i++) {
        const a = -Math.PI * 0.6 + (i / n) * Math.PI * 2 * turns;
        const wob = e.rough === false ? 1 : 1 + 0.05 * Math.sin(i * 0.9 + 1) - 0.04 * (i / n);
        d += `${i ? 'L' : 'M'}${(x + Math.cos(a) * rx * wob).toFixed(1)},${(y + Math.sin(a) * ry * wob).toFixed(1)} `;
      }
      paths.push(dash(p, 'c', d));
      break;
    }
    case 'underline': {
      const wav = e.wave ? 14 : 0;
      let d = `M${x},${y}`;
      if (wav) for (let i = 1; i <= 8; i++) d += ` Q${x + (w * (i - 0.5)) / 8},${y + (i % 2 ? -wav : wav)} ${x + (w * i) / 8},${y}`;
      else d += ` Q${x + w / 2},${y + 10} ${x + w},${y - 4}`;
      paths.push(dash(p, 'u', d, e.marker ? {strokeOpacity: 0.55, strokeLinecap: 'butt'} : undefined));
      break;
    }
    case 'box': {
      const r = e.radius ?? 22;
      const l = x - w / 2, t = y - h / 2;
      paths.push(dash(p, 'b', `M${l + r},${t} H${l + w - r} Q${l + w},${t} ${l + w},${t + r} V${t + h - r} Q${l + w},${t + h} ${l + w - r},${t + h} H${l + r} Q${l},${t + h} ${l},${t + h - r} V${t + r} Q${l},${t} ${l + r},${t} Z`));
      break;
    }
    case 'bracket': {
      const l = x - w / 2, t = y - h / 2, c = Math.min(60, w / 4);
      paths.push(dash(p, 'b1', `M${l + c},${t} H${l} V${t + h} H${l + c}`));
      paths.push(dash(p, 'b2', `M${l + w - c},${t} H${l + w} V${t + h} H${l + w - c}`));
      break;
    }
    case 'check':
      paths.push(dash(p, 'k', `M${x - w * 0.3},${y} L${x - w * 0.08},${y + w * 0.22} L${x + w * 0.34},${y - w * 0.26}`));
      break;
    case 'cross':
      paths.push(dash(p / 0.55, 'x1', `M${x - w * 0.28},${y - w * 0.28} L${x + w * 0.28},${y + w * 0.28}`));
      paths.push(dash((p - 0.45) / 0.55, 'x2', `M${x + w * 0.28},${y - w * 0.28} L${x - w * 0.28},${y + w * 0.28}`));
      break;
    case 'callout': {
      // chấm nhấp nháy tại điểm + đường dẫn gấp khúc + nhãn chữ
      const midX = x2, midY = y;
      const d = Math.abs(y2 - y) > 4 ? `M${x},${y} L${x + (x2 - x) * 0.35},${y2} L${x2},${y2}` : `M${x},${y} L${midX},${midY}`;
      paths.push(dash(Math.min(1, p / 0.7), 'cl', d, {strokeWidth: Math.max(4, sw * 0.5)}));
      const pulse = (f % 30) / 30;
      paths.push(<circle key="dot" cx={x} cy={y} r={sw * 1.2} fill={color} />);
      paths.push(<circle key="ring" cx={x} cy={y} r={sw * (1.2 + pulse * 2.6)} fill="none" stroke={color} strokeWidth={3} opacity={1 - pulse} />);
      if (e.text) {
        const lp = spring({frame: f - drawF * 0.7, fps, config: {damping: 14, stiffness: 180}});
        const estW = String(e.text).length * (e.size ?? 46) * 0.56 + 60;
        const right = e.side ? e.side === 'right' : x2 >= x ? x2 + 12 + estW < FR.w - 20 : x2 - 12 - estW < 20;
        label = (
          <div style={{position: 'absolute', top: y2 - (e.size ?? 46) * 0.85, left: right ? x2 + 12 : undefined, right: right ? undefined : FR.w - x2 + 12,
            fontFamily: headF(), fontWeight: fontWeight(S.style.heading || S.style.font, 800), fontSize: e.size ?? 46, color: e.textColor || '#111',
            background: e.bg || color, padding: '6px 20px 4px', borderRadius: 12, whiteSpace: 'pre', opacity: lp, transform: `scale(${0.7 + 0.3 * lp})`,
            transformOrigin: right ? 'left center' : 'right center', boxShadow: '0 8px 22px rgba(0,0,0,0.35)'}}>
            {e.text}
          </div>
        );
      }
      break;
    }
  }
  // khung bao của hình (để trình edit chọn / kéo đúng chỗ, không phủ cả khung)
  const pad = sw * 2 + 30;
  const xs = kind === 'arrow' || kind === 'line' || kind === 'callout' ? [x, x2] : kind === 'underline' ? [x, x + w] : [x - w / 2, x + w / 2];
  const ys = kind === 'arrow' || kind === 'line' || kind === 'callout' ? [y, y2] : kind === 'underline' ? [y - 20, y + 20] : kind === 'check' || kind === 'cross' ? [y - w * 0.3, y + w * 0.3] : [y - h / 2, y + h / 2];
  const ex = kind === 'arrow' || kind === 'line' ? Math.abs(bend) * Math.hypot(x2 - x, y2 - y) * 0.6 : 0;
  const bb = [Math.min(...xs) - pad - ex, Math.min(...ys) - pad - ex, Math.max(...xs) + pad + ex, Math.max(...ys) + pad + ex];
  return (
    <AbsoluteFill style={{opacity: op}}>
      <svg width={bb[2] - bb[0]} height={bb[3] - bb[1]} viewBox={`${bb[0]} ${bb[1]} ${bb[2] - bb[0]} ${bb[3] - bb[1]}`} style={{position: 'absolute', left: bb[0], top: bb[1], overflow: 'visible', filter: glow}}>{paths}</svg>
      {label}
    </AbsoluteFill>
  );
};

/* =================== TEXT 3D =================== */
export const Text3D: React.FC<{e: any; dur: number; theme: Theme}> = ({e, dur, theme}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const size = e.size ?? 140;
  const font = e.font || S.style.heading || S.style.font;
  const text = (e.upper ?? true) ? String(e.text || '').toUpperCase() : String(e.text || '');
  const depth = Math.max(4, Math.min(60, e.depth ?? 26));
  const n = Math.max(6, Math.min(26, Math.round(depth / 2)));
  const step = depth / n;
  const face = e.face || 'solid';
  const color = e.color || 'white';
  const side = e.side || theme.dark || '#0b2a55';
  const sp = spring({frame: f, fps, config: EASES[e.ease || ''] || {damping: 13, stiffness: 120}});
  const tt = f / fps;
  const mo = e.motion || 'swing';
  let rx = 0, ry = 0, rz = 0, tz = 0, sc = 1;
  switch (mo) {
    case 'swing': ry = Math.sin(tt * 1.4) * 24 + (1 - sp) * -70; rx = 8 + Math.sin(tt * 0.9) * 5; break;
    case 'spin': ry = (1 - sp) * -360 + Math.sin(tt * 1.2) * 10; rx = 10; break;
    case 'rise': rx = (1 - sp) * 85 + 12; ry = Math.sin(tt) * 8; break;
    case 'tilt': rx = 14; ry = -22 + tt * 6; break;
    case 'float': rx = 10 + Math.sin(tt * 1.3) * 6; ry = Math.cos(tt * 1.1) * 14; tz = Math.sin(tt * 1.7) * 30; break;
    case 'zoom': tz = (1 - sp) * -1800; rx = 10; ry = Math.sin(tt) * 10; break;
    default: rx = 10;
  }
  if (mo !== 'zoom') sc = 0.4 + 0.6 * sp;
  const op = Math.min(interpolate(f, [0, 5], [0, 1], cl), interpolate(f, [dur - 7, dur], [1, 0], cl));
  const base: React.CSSProperties = {
    position: 'absolute', left: 0, top: 0, width: '100%', textAlign: 'center', whiteSpace: 'pre', fontFamily: fontCss(font), fontWeight: fontWeight(font, e.weight ?? 900),
    fontSize: size, lineHeight: 1.25, letterSpacing: e.spacing ?? 2, paddingTop: size * 0.12,
  };
  const faceCss: React.CSSProperties =
    face === 'gold'
      ? ({background: `linear-gradient(180deg, #fff6c8 0%, ${theme.gold1 || '#f5c542'} 45%, ${theme.gold2 || '#b8860b'} 100%)`, WebkitBackgroundClip: 'text', color: 'transparent'} as any)
      : face === 'chrome'
        ? ({background: 'linear-gradient(180deg, #ffffff 0%, #c9d3dd 46%, #6b7785 50%, #e9eef3 100%)', WebkitBackgroundClip: 'text', color: 'transparent'} as any)
        : {color};
  const y = px(e.y, FR.h, 700);
  return (
    <AbsoluteFill style={{perspective: 1500, perspectiveOrigin: `50% ${y}px`, opacity: op}}>
      <div style={{position: 'absolute', left: 40, right: 40, top: y, height: size * 1.6 * Math.max(1, text.split('\n').length), transformStyle: 'preserve-3d',
        transform: `translateX(${(px(e.x, FR.w, FR.w / 2) - FR.w / 2)}px) translateZ(${tz}px) rotateX(${rx}deg) rotateY(${ry}deg) rotateZ(${rz + (e.rotate || 0)}deg) scale(${sc})`}}>
        {Array.from({length: n}, (_, i) => {
          const z = -(n - i) * step;
          const shade = 0.55 + 0.45 * (i / n);
          return (
            <div key={i} style={{...base, color: side, filter: `brightness(${shade})`, transform: `translateZ(${z}px)`}}>
              {text}
            </div>
          );
        })}
        <div style={{...base, ...faceCss, transform: 'translateZ(0.5px)', textShadow: face === 'solid' ? `0 0 1px ${color}` : undefined, filter: e.glow ? `drop-shadow(0 0 18px ${e.glow === true ? color : e.glow})` : undefined}}>{text}</div>
      </div>
      {e.shadow !== false && <div style={{position: 'absolute', left: 140, right: 140, top: y + size * 1.55, height: 50, borderRadius: '50%', background: 'radial-gradient(ellipse, rgba(0,0,0,0.45), transparent 70%)', filter: 'blur(10px)', opacity: sp * 0.8}} />}
    </AbsoluteFill>
  );
};

/* =================== CARD 3D (ảnh/video trên mặt phẳng 3D) =================== */
export const Card3D: React.FC<{e: any; dur: number; theme: Theme; filter?: string}> = ({e, dur, theme, filter}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const w = e.w ?? 760, h = e.h ?? Math.round(w * (e.ratio ?? 1.25));
  const cy = px(e.y, FR.h, 760), cx = px(e.x, FR.w, FR.w / 2);
  const sp = spring({frame: f, fps, config: EASES[e.ease || ''] || {damping: 16, stiffness: 90}});
  const k = Math.min(1, f / Math.max(1, dur));
  const kk = Easing.inOut(Easing.sin)(k);
  const mo = e.move || 'orbit';
  let rx = 0, ry = 0, rz = 0, tz = 0, ty = 0;
  switch (mo) {
    case 'orbit': ry = -28 + 56 * kk; rx = 8; tz = (1 - sp) * -900; break;
    case 'flyIn': tz = (1 - sp) * -2200; rx = (1 - sp) * 50 + 6; rz = (1 - sp) * -12; ry = -10 + 20 * kk; break;
    case 'tiltIn': rx = (1 - sp) * 75 + 4 * Math.sin(f / 30); ty = (1 - sp) * 300; break;
    case 'float': rx = 10 + Math.sin(f / 25) * 5; ry = Math.sin(f / 35) * 16; ty = Math.sin(f / 20) * 14; tz = (1 - sp) * -600; break;
    case 'flip': ry = (1 - sp) * 180; rx = 6; break;
    case 'dolly': tz = -350 + 520 * kk; rx = 6 - 6 * kk; ry = 8 - 16 * kk; break;
    case 'swing': rz = Math.sin(f / 18) * 4 * (1 - k * 0.5); rx = 6; ry = Math.sin(f / 26) * 14; tz = (1 - sp) * -700; break;
  }
  const op = Math.min(interpolate(f, [0, 6], [0, 1], cl), interpolate(f, [dur - 8, dur], [1, 0], cl));
  const r = e.radius ?? 28;
  return (
    <AbsoluteFill style={{perspective: 1600, perspectiveOrigin: `${cx}px ${cy}px`, opacity: op}}>
      <div style={{position: 'absolute', left: cx - w / 2, top: cy - h / 2, width: w, height: h, transformStyle: 'preserve-3d',
        transform: `translateY(${ty}px) translateZ(${tz}px) rotateX(${rx}deg) rotateY(${ry}deg) rotateZ(${rz}deg)`}}>
        <div style={{position: 'absolute', inset: 0, borderRadius: r, overflow: 'hidden', backfaceVisibility: 'hidden', border: e.border === false ? undefined : `${e.borderW ?? 8}px solid ${e.borderColor || 'white'}`,
          boxShadow: '0 50px 90px rgba(0,0,0,0.55), 0 12px 30px rgba(0,0,0,0.35)', background: '#111'}}>
          {e.src ? <MediaFill src={e.src} from={e.from} zoom={1.04} panX={0} volume={e.volume} filter={filter} /> : null}
          <div style={{position: 'absolute', inset: 0, background: `linear-gradient(${115 + ry}deg, rgba(255,255,255,${0.22 * (e.gloss ?? 1)}) 0%, transparent 38%)`}} />
        </div>
        {mo === 'flip' && <div style={{position: 'absolute', inset: 0, borderRadius: r, background: `linear-gradient(135deg, ${theme.mid}, ${theme.dark})`, transform: 'rotateY(180deg)', backfaceVisibility: 'hidden'}} />}
        {e.label && (
          <div style={{position: 'absolute', left: '50%', bottom: -34, transform: 'translateX(-50%) translateZ(40px)', fontFamily: headF(), fontWeight: 800, fontSize: 48, color: '#111',
            background: theme.gold1 || '#FFD400', padding: '8px 28px 6px', borderRadius: 14, whiteSpace: 'nowrap', boxShadow: '0 10px 24px rgba(0,0,0,0.35)'}}>{e.label}</div>
        )}
        {e.reflect && (
          <div style={{position: 'absolute', left: 0, top: h + 14, width: w, height: h * 0.45, overflow: 'hidden', borderRadius: r, opacity: 0.25, transform: 'scaleY(-1)',
            WebkitMaskImage: 'linear-gradient(0deg, black, transparent 80%)'} as any}>
            {e.src ? <div style={{width: w, height: h, transform: `translateY(${-h * 0.55}px)`}}><MediaFill src={e.src} from={e.from} zoom={1.04} panX={0} filter={filter} /></div> : null}
          </div>
        )}
      </div>
    </AbsoluteFill>
  );
};

/* =================== SCENE (cảnh dựng sẵn theo tham số) =================== */
export const SCENE_KINDS = ['intro', 'pricetable', 'compare', 'amenities', 'stats', 'outro'];
/** "A: 1 | B: 2" hoặc ["A: 1", ...] hoặc [{label, value}] -> [{label, value, ...}] */
const rowsOf = (r: any): any[] => {
  if (!r) return [];
  const arr = Array.isArray(r) ? r : String(r).split(/\s*[|\n;]\s*/);
  return arr.filter(Boolean).map((x: any) => {
    if (typeof x !== 'string') return x;
    const i = x.indexOf(':');
    return i > 0 ? {label: x.slice(0, i).trim(), value: x.slice(i + 1).trim()} : {label: x.trim(), text: x.trim()};
  });
};
const Ico: React.FC<{name?: string; size: number; color: string}> = ({name, size, color}) => {
  if (!name) return null;
  const C = (Icons as any)[name];
  return C ? <C size={size} color={color} strokeWidth={2.4} /> : <span style={{fontSize: size * 0.9, lineHeight: 1}}>{name}</span>;
};
const countTo = (s: string, p: number) => {
  // "2,55 tỷ" -> đếm số đầu tiên từ 0 tới giá trị, giữ phần chữ
  const m = String(s).match(/(\d+(?:[.,]\d+)?)/);
  if (!m) return s;
  const raw = m[1], dec = (raw.split(/[.,]/)[1] || '').length, sep = raw.includes(',') ? ',' : '.';
  const v = parseFloat(raw.replace(',', '.')) * p;
  return s.replace(raw, v.toFixed(dec).replace('.', sep));
};

export const Scene: React.FC<{e: any; dur: number; theme: Theme}> = ({e, dur, theme}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const kind = e.kind || 'intro';
  const acc = e.accent || S.style.accent || theme.gold1 || '#FFD400';
  const dark = e.light ? false : e.dark ?? true;
  const fg = dark ? 'white' : '#111';
  const card = dark ? 'rgba(10,18,36,0.82)' : 'rgba(255,255,255,0.94)';
  const sub = dark ? 'rgba(255,255,255,0.75)' : 'rgba(0,0,0,0.6)';
  const op = Math.min(interpolate(f, [0, 6], [0, 1], cl), interpolate(f, [dur - 8, dur], [1, 0], cl));
  const hw = fontWeight(S.style.heading || S.style.font, 900);
  const rows = rowsOf(e.rows || e.items);
  const n = Math.max(1, rows.length);
  const t0 = (e.first ?? 0.45) * fps;
  const stepF = (e.step ?? Math.min(0.7, Math.max(0.25, (dur / fps - 1.4) / n))) * fps;
  const atOf = (i: number) => (Array.isArray(e.at) && e.at[i] != null ? e.at[i] * fps : t0 + i * stepF);
  const pin = (at: number, cfg = {damping: 14, stiffness: 170}) => spring({frame: f - at, fps, config: cfg});
  const y = px(e.y, FR.h, kind === 'intro' || kind === 'outro' ? 640 : 300);
  const bg = e.bg ?? (kind === 'intro' || kind === 'outro' ? 'dim' : 'none');
  const tIn = pin(0);
  const title = e.title ? (
    <div style={{fontFamily: headF(), fontWeight: hw, fontSize: e.titleSize ?? 72, color: fg, lineHeight: 1.2, paddingTop: 10, textAlign: 'center', whiteSpace: 'pre-line',
      opacity: tIn, transform: `translateY(${(1 - tIn) * 40}px)`, textShadow: dark ? '0 4px 18px rgba(0,0,0,0.5)' : 'none'}}>
      {e.upper === false ? e.title : String(e.title).toUpperCase()}
      <div style={{height: 8, width: 160 * pin(4), background: acc, borderRadius: 4, margin: '14px auto 0'}} />
    </div>
  ) : null;
  let body: React.ReactNode = null;
  switch (kind) {
    case 'intro':
    case 'outro': {
      const words = String(e.title || '').split(/\s+/).filter(Boolean);
      const bar = pin(0, {damping: 20, stiffness: 120});
      body = (
        <div style={{position: 'absolute', top: y, left: 70, right: 70, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 22}}>
          {e.kicker && (
            <div style={{fontFamily: bodyF(), fontWeight: 800, fontSize: 40, letterSpacing: 6, color: '#111', background: acc, padding: '8px 26px 6px', borderRadius: 999, opacity: bar, transform: `scale(${0.6 + 0.4 * bar})`}}>
              {String(e.kicker).toUpperCase()}
            </div>
          )}
          <div style={{fontFamily: headF(), fontWeight: hw, fontSize: e.titleSize ?? 112, color: fg, lineHeight: 1.18, textAlign: 'center', paddingTop: 14, textShadow: '0 6px 26px rgba(0,0,0,0.55)'}}>
            {words.map((w, i) => {
              const s = pin(5 + i * 3, {damping: 12, stiffness: 160});
              return (
                <span key={i} style={{display: 'inline-block', overflow: 'hidden', verticalAlign: 'bottom', margin: '0 0.14em', paddingTop: 20, marginTop: -20}}>
                  <span style={{display: 'inline-block', transform: `translateY(${(1 - s) * 110}%)`, color: (e.hl || []).includes(w) ? acc : undefined}}>{e.upper === false ? w : w.toUpperCase()}</span>
                </span>
              );
            })}
          </div>
          <div style={{height: 6, width: 520 * bar, background: `linear-gradient(90deg, transparent, ${acc}, transparent)`}} />
          {e.sub && <div style={{fontFamily: bodyF(), fontWeight: 600, fontSize: 46, color: sub, textAlign: 'center', opacity: pin(14), transform: `translateY(${(1 - pin(14)) * 24}px)`}}>{e.sub}</div>}
          {kind === 'outro' && (
            <div style={{display: 'flex', gap: 20, marginTop: 20, alignItems: 'flex-start'}}>
              {(rows.length ? rows : [{icon: 'UserPlus', text: 'Follow'}, {icon: 'Heart', text: 'Thả tim'}, {icon: 'MessageCircle', text: 'Inbox'}]).map((r: any, i: number) => {
                const s = pin(18 + i * 5, {damping: 9, stiffness: 190});
                return (
                  <div key={i} style={{display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'flex-start', gap: 10, width: 190, transform: `scale(${s})`}}>
                    <div style={{width: 130, height: 130, borderRadius: 999, background: i === 0 ? acc : card, display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 12px 28px rgba(0,0,0,0.4)'}}>
                      <Ico name={r.icon} size={64} color={i === 0 ? '#111' : fg} />
                    </div>
                    <div style={{fontFamily: bodyF(), fontWeight: 800, fontSize: 36, color: fg, textAlign: 'center', lineHeight: 1.25, whiteSpace: 'nowrap'}}>{r.text || r.label}</div>
                  </div>
                );
              })}
            </div>
          )}
          {e.handle && <div style={{fontFamily: bodyF(), fontWeight: 700, fontSize: 40, color: acc, opacity: pin(22)}}>{e.handle}</div>}
        </div>
      );
      break;
    }
    case 'pricetable': {
      body = (
        <div style={{position: 'absolute', top: y, left: 60, right: 60, display: 'flex', flexDirection: 'column', gap: 26}}>
          {title}
          <div style={{background: card, borderRadius: 30, padding: '14px 34px', boxShadow: '0 30px 70px rgba(0,0,0,0.45)', border: `2px solid ${acc}55`, transform: `scale(${0.9 + 0.1 * tIn})`, opacity: tIn}}>
            {rows.map((r: any, i: number) => {
              const s = pin(atOf(i));
              const hl = r.hl || r.best;
              return (
                <div key={i} style={{display: 'flex', alignItems: 'center', gap: 20, padding: '24px 6px', borderTop: i ? `2px solid ${dark ? 'rgba(255,255,255,0.12)' : 'rgba(0,0,0,0.08)'}` : 'none',
                  opacity: s, transform: `translateX(${(1 - s) * -80}px)`}}>
                  {r.icon && <Ico name={r.icon} size={52} color={acc} />}
                  <div style={{flex: 1, fontFamily: bodyF(), fontWeight: 700, fontSize: 46, color: fg, lineHeight: 1.3}}>
                    {r.label}
                    {r.note && <div style={{fontSize: 32, fontWeight: 500, color: sub}}>{r.note}</div>}
                  </div>
                  <div style={{fontFamily: headF(), fontWeight: hw, fontSize: hl ? 64 : 54, color: hl ? '#111' : acc, background: hl ? acc : 'transparent', padding: hl ? '4px 18px 0' : 0, borderRadius: 12, whiteSpace: 'nowrap', paddingTop: 8}}>
                    {e.count === false ? r.value : countTo(String(r.value ?? ''), Math.min(1, Math.max(0, (f - atOf(i)) / 14)))}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      );
      break;
    }
    case 'compare': {
      const A = e.a || {}, B = e.b || {};
      const ra = rowsOf(A.items), rb = rowsOf(B.items);
      const cr = rowsOf(e.rows); // [{label, a, b}]
      const m = Math.max(ra.length, rb.length, cr.length);
      const col = (side: any, items: any[], i0: number, c: string, win: boolean, dir: number) => {
        const s = pin(i0, {damping: 15, stiffness: 140});
        return (
          <div style={{flex: 1, background: card, borderRadius: 28, padding: '26px 24px', border: win ? `4px solid ${acc}` : `2px solid ${dark ? 'rgba(255,255,255,0.15)' : 'rgba(0,0,0,0.1)'}`,
            transform: `translateX(${(1 - s) * dir * 300}px) scale(${win ? 1.03 : 1})`, opacity: s, boxShadow: '0 24px 60px rgba(0,0,0,0.4)'}}>
            <div style={{fontFamily: headF(), fontWeight: hw, fontSize: 54, color: c, textAlign: 'center', paddingTop: 8}}>{side.name || ''}</div>
            {side.value && <div style={{fontFamily: headF(), fontWeight: hw, fontSize: 64, color: fg, textAlign: 'center', paddingTop: 8}}>{side.value}</div>}
            {items.map((it: any, i: number) => {
              const si = pin(atOf(i) + 4);
              const good = it.good ?? !/^[-✗x]/i.test(String(it.text || it.label));
              return (
                <div key={i} style={{display: 'flex', gap: 12, alignItems: 'flex-start', marginTop: 20, opacity: si, transform: `translateY(${(1 - si) * 20}px)`}}>
                  <Ico name={good ? 'CircleCheck' : 'CircleX'} size={40} color={good ? '#34d399' : '#f87171'} />
                  <div style={{fontFamily: bodyF(), fontWeight: 600, fontSize: 38, color: fg, lineHeight: 1.3}}>{String(it.text || it.label).replace(/^[-+✓✗]\s*/, '')}</div>
                </div>
              );
            })}
          </div>
        );
      };
      const vs = pin(8, {damping: 8, stiffness: 200});
      body = (
        <div style={{position: 'absolute', top: y, left: 40, right: 40, display: 'flex', flexDirection: 'column', gap: 28}}>
          {title}
          {cr.length ? (
            <div style={{background: card, borderRadius: 28, padding: '10px 26px', boxShadow: '0 24px 60px rgba(0,0,0,0.4)', opacity: tIn}}>
              <div style={{display: 'flex', fontFamily: headF(), fontWeight: hw, fontSize: 46, padding: '18px 0 8px', paddingTop: 22}}>
                <div style={{flex: 1.1}} />
                <div style={{flex: 1, textAlign: 'center', color: acc}}>{A.name || 'A'}</div>
                <div style={{flex: 1, textAlign: 'center', color: e.colorB || '#7dd3fc'}}>{B.name || 'B'}</div>
              </div>
              {cr.map((r: any, i: number) => {
                const s = pin(atOf(i));
                return (
                  <div key={i} style={{display: 'flex', alignItems: 'center', padding: '20px 0', borderTop: `2px solid ${dark ? 'rgba(255,255,255,0.12)' : 'rgba(0,0,0,0.08)'}`, opacity: s, transform: `translateY(${(1 - s) * 24}px)`}}>
                    <div style={{flex: 1.1, fontFamily: bodyF(), fontWeight: 600, fontSize: 38, color: sub}}>{r.label}</div>
                    <div style={{flex: 1, textAlign: 'center', fontFamily: headF(), fontWeight: 800, fontSize: 44, color: fg, paddingTop: 6}}>{r.a ?? ''}</div>
                    <div style={{flex: 1, textAlign: 'center', fontFamily: headF(), fontWeight: 800, fontSize: 44, color: fg, paddingTop: 6}}>{r.b ?? ''}</div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div style={{display: 'flex', gap: 22, position: 'relative'}}>
              {col(A, ra, 2, acc, e.win === 'a', -1)}
              {col(B, rb, 5, e.colorB || '#7dd3fc', e.win === 'b', 1)}
              <div style={{position: 'absolute', left: '50%', top: 20, transform: `translateX(-50%) scale(${vs}) rotate(${(1 - vs) * 90}deg)`, width: 110, height: 110, borderRadius: 999, background: acc,
                display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: headF(), fontWeight: hw, fontSize: 48, color: '#111', boxShadow: '0 10px 30px rgba(0,0,0,0.45)', paddingTop: 6}}>VS</div>
            </div>
          )}
          {m === 0 && null}
        </div>
      );
      break;
    }
    case 'amenities': {
      const lineP = interpolate(f, [t0 - 4, atOf(n - 1) + 10], [0, 1], cl);
      body = (
        <div style={{position: 'absolute', top: y, left: 60, right: 60, display: 'flex', flexDirection: 'column', gap: 30}}>
          {title}
          <div style={{position: 'relative', paddingLeft: 30}}>
            <div style={{position: 'absolute', left: 77, top: 40, width: 6, height: `calc(${lineP * 100}% - 80px)`, background: acc, borderRadius: 3, opacity: 0.8}} />
            {rows.map((r: any, i: number) => {
              const s = pin(atOf(i), {damping: 11, stiffness: 190});
              return (
                <div key={i} style={{display: 'flex', alignItems: 'center', gap: 26, marginBottom: 26, opacity: Math.min(1, s * 1.5), transform: `translateX(${(1 - s) * 60}px)`}}>
                  <div style={{width: 100, height: 100, borderRadius: 999, background: acc, flex: 'none', display: 'flex', alignItems: 'center', justifyContent: 'center', transform: `scale(${s})`, boxShadow: '0 10px 24px rgba(0,0,0,0.4)'}}>
                    <Ico name={r.icon || 'MapPin'} size={52} color="#111" />
                  </div>
                  <div style={{flex: 1, background: card, borderRadius: 22, padding: '18px 26px', display: 'flex', alignItems: 'center', gap: 16, boxShadow: '0 14px 34px rgba(0,0,0,0.35)'}}>
                    <div style={{flex: 1, fontFamily: bodyF(), fontWeight: 700, fontSize: 42, color: fg, lineHeight: 1.3}}>{r.text || r.label}</div>
                    {(r.dist || r.value) && <div style={{fontFamily: headF(), fontWeight: 800, fontSize: 40, color: '#111', background: acc, borderRadius: 999, padding: '6px 20px 2px', whiteSpace: 'nowrap', paddingTop: 8}}>{r.dist || r.value}</div>}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      );
      break;
    }
    case 'stats': {
      const cols = rows.length <= 2 ? 1 : 2;
      body = (
        <div style={{position: 'absolute', top: y, left: 50, right: 50, display: 'flex', flexDirection: 'column', gap: 30}}>
          {title}
          <div style={{display: 'grid', gridTemplateColumns: `repeat(${cols}, 1fr)`, gap: 24}}>
            {rows.map((r: any, i: number) => {
              const s = pin(atOf(i), {damping: 12, stiffness: 160});
              const cp = Math.min(1, Math.max(0, (f - atOf(i)) / 22));
              return (
                <div key={i} style={{background: card, borderRadius: 28, padding: '30px 20px', textAlign: 'center', transform: `scale(${0.6 + 0.4 * s})`, opacity: Math.min(1, s * 1.4), boxShadow: '0 20px 50px rgba(0,0,0,0.4)', borderTop: `8px solid ${acc}`}}>
                  {r.icon && <Ico name={r.icon} size={56} color={acc} />}
                  <div style={{fontFamily: headF(), fontWeight: hw, fontSize: cols === 1 ? 120 : 92, color: acc, lineHeight: 1.15, paddingTop: 10}}>{countTo(String(r.value ?? ''), Easing.out(Easing.cubic)(cp))}</div>
                  <div style={{fontFamily: bodyF(), fontWeight: 700, fontSize: 38, color: fg, lineHeight: 1.3}}>{r.label}</div>
                </div>
              );
            })}
          </div>
        </div>
      );
      break;
    }
  }
  return (
    <AbsoluteFill style={{opacity: op}}>
      {bg === 'dim' && <AbsoluteFill style={{background: 'radial-gradient(ellipse at 50% 45%, rgba(0,0,0,0.35), rgba(0,0,0,0.75))'}} />}
      {bg === 'dark' && <AbsoluteFill style={{background: `linear-gradient(160deg, ${theme.dark}, #050a14)`}} />}
      {bg === 'brand' && <AbsoluteFill style={{background: `linear-gradient(160deg, ${theme.mid}, ${theme.dark})`}} />}
      {body}
    </AbsoluteFill>
  );
};

/* =================== bám vật thể (motion tracking) =================== */
/** pts: [[giây video gốc, x, y], ...] (scripts/track.py) -> vị trí nội suy ở giây t */
export const trackAt = (pts: number[][] | undefined, t: number): [number, number] | null => {
  if (!pts || !pts.length) return null;
  if (t <= pts[0][0]) return [pts[0][1], pts[0][2]];
  const L = pts[pts.length - 1];
  if (t >= L[0]) return [L[1], L[2]];
  let lo = 0, hi = pts.length - 1;
  while (hi - lo > 1) {
    const m = (lo + hi) >> 1;
    if (pts[m][0] <= t) lo = m;
    else hi = m;
  }
  const a = pts[lo], b = pts[hi];
  const u = (t - a[0]) / Math.max(1e-6, b[0] - a[0]);
  return [a[1] + (b[1] - a[1]) * u, a[2] + (b[2] - a[2]) * u];
};
