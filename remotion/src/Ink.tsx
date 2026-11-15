/* Tranh THỦY MẶC vẽ bằng SVG (nét mực, núi mờ sương, trăng, thuyền, lau sậy, chim) — cho phong cách thơ / tâm sự.
   pos: 'top' = dải giấy sương phủ phía trên khung (chữ mực đặt trên dải này) + lau sậy 2 góc dưới
        'full' = cả bức tranh làm nền (dùng sau người nói ở chế độ khung tranh — presenter bg 'ink')
   palette: 'mono' (mực tàu) | 'color' (nhạt màu: trời xanh, trăng vàng, núi xanh lục) | 'night' (đêm trăng) | 'dawn' (bình minh hồng đào) */
import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';

type Pal = {paper: string; sky: string; far: string; near: string; ink: string; sun: string; sunLine?: string; reed: string; head: string; boat: string; hat: string; mist: string};
export const INK_PAL: Record<string, Pal> = {
  mono: {paper: '#EFE9DC', sky: '#EFE9DC', far: '#9A9893', near: '#5E5C58', ink: '#2A2826', sun: 'none', sunLine: '#A8A39A', reed: '#2A2826', head: '#4A4744', boat: '#2A2826', hat: '#2A2826', mist: '#EFE9DC'},
  color: {paper: '#F3EEE3', sky: '#DCE4EA', far: '#9FB2C2', near: '#5F7D6E', ink: '#2E2A26', sun: '#F2D27E', reed: '#5E7A55', head: '#A08060', boat: '#7A4A2A', hat: '#C9A46A', mist: '#F3EEE3'},
  night: {paper: '#1D2533', sky: '#141B27', far: '#3A4658', near: '#262F3E', ink: '#E9E4D6', sun: '#EFEBDD', reed: '#0E131C', head: '#3B4556', boat: '#0E131C', hat: '#0E131C', mist: '#1D2533'},
  dawn: {paper: '#F6EEE4', sky: '#F4DCC6', far: '#A9B5B0', near: '#6F8579', ink: '#2E2A26', sun: '#F0B48C', reed: '#5E7A55', head: '#A08060', boat: '#4A3A30', hat: '#B8956A', mist: '#F6EEE4'},
};

/* núi răng cưa có độ nhám (giả ngẫu nhiên, ổn định theo seed) */
const rnd = (s: number) => {
  let x = s;
  return () => ((x = (x * 9301 + 49297) % 233280) / 233280);
};
const ridge = (seed: number, x0: number, x1: number, base: number, peaks: [number, number][]) => {
  // peaks: [x, đỉnh y] -> nối thành dãy núi, chèn răng cưa nhỏ
  const r = rnd(seed);
  const pts: [number, number][] = [[x0, base]];
  const all: [number, number][] = [[x0, base - 10], ...peaks, [x1, base - 10]];
  for (let k = 0; k < all.length - 1; k++) {
    const [ax, ay] = all[k], [bx, by] = all[k + 1];
    const mx = (ax + bx) / 2, my = Math.max(ay, by) + (base - Math.max(ay, by)) * 0.45;
    for (const [px, py, qx, qy] of [[ax, ay, mx, my], [mx, my, bx, by]] as number[][]) {
      const n = 7;
      for (let i = 1; i <= n; i++) {
        const t = i / n;
        pts.push([px + (qx - px) * t + (r() - 0.5) * 8, py + (qy - py) * t + (r() - 0.5) * 14]);
      }
    }
  }
  pts.push([x1, base]);
  return 'M' + pts.map(([x, y]) => `${x.toFixed(1)} ${y.toFixed(1)}`).join(' L') + ' Z';
};

const Defs: React.FC<{id: string; p: Pal}> = ({id, p}) => (
  <defs>
    <filter id={id + 'rough'} x="-5%" y="-5%" width="110%" height="110%">
      <feTurbulence type="fractalNoise" baseFrequency="0.035" numOctaves="2" seed="3" />
      <feDisplacementMap in="SourceGraphic" scale="9" />
      <feGaussianBlur stdDeviation="0.8" />
    </filter>
    <filter id={id + 'brush'} x="-5%" y="-20%" width="110%" height="140%">
      <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="1" seed="7" result="n" />
      <feDisplacementMap in="SourceGraphic" in2="n" scale="2.2" />
    </filter>
    <filter id={id + 'paper'}>
      <feTurbulence type="fractalNoise" baseFrequency="0.75" numOctaves="3" seed="11" />
      <feColorMatrix values="0 0 0 0 0.45  0 0 0 0 0.40  0 0 0 0 0.33  0 0 0 0.10 0" />
    </filter>
    <radialGradient id={id + 'glow'}>
      <stop offset="0.55" stopColor={p.sun === 'none' ? p.paper : p.sun} stopOpacity="0.55" />
      <stop offset="1" stopColor={p.sun === 'none' ? p.paper : p.sun} stopOpacity="0" />
    </radialGradient>
    {(['far', 'near'] as const).map((k) => (
      <linearGradient key={k} id={id + k} x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stopColor={p[k]} stopOpacity="0.95" />
        <stop offset="0.55" stopColor={p[k]} stopOpacity="0.45" />
        <stop offset="1" stopColor={p[k]} stopOpacity="0" />
      </linearGradient>
    ))}
  </defs>
);

const Birds: React.FC<{x: number; y: number; c: string; f: number; id: string}> = ({x, y, c, f, id}) => {
  const dx = (f * 0.35) % 1400;
  const flap = Math.sin(f / 9) * 6;
  const bird = (bx: number, by: number, s: number) => (
    <path
      d={`M${bx - 60 * s} ${by + flap * s} Q${bx - 28 * s} ${by - 34 * s} ${bx} ${by} Q${bx + 34 * s} ${by - 40 * s} ${bx + 74 * s} ${by - 6 * s + flap * s}`}
      fill="none" stroke={c} strokeWidth={6 * s} strokeLinecap="round" filter={`url(#${id}brush)`}
    />
  );
  return <g transform={`translate(${((x + dx) % 1500) - 200} 0)`}>{bird(0, y, 1)}{bird(110, y - 40, 0.85)}{bird(-30, y + 60, 0.7)}</g>;
};

const Reeds: React.FC<{x: number; base: number; c: string; head: string; flip?: boolean; f: number; id: string}> = ({x, base, c, head, flip, f, id}) => {
  const sw = (k: number) => Math.sin(f / 40 + k) * 6;
  const reeds = [[0, 520, 1], [40, 430, 0.9], [-50, 360, 0.8]];
  return (
    <g transform={flip ? `translate(${x} 0) scale(-1 1)` : `translate(${x} 0)`} filter={`url(#${id}brush)`}>
      {reeds.map(([dx, h, s], k) => {
        const top = base - h, bend = sw(k) + 30 * s;
        return (
          <g key={k}>
            <path d={`M${dx} ${base} Q${dx + bend * 0.4} ${base - h * 0.5} ${dx + bend} ${top}`} fill="none" stroke={c} strokeWidth={5 * s} strokeLinecap="round" />
            <ellipse cx={dx + bend} cy={top - 22 * s} rx={11 * s} ry={34 * s} fill={head} transform={`rotate(${bend / 3} ${dx + bend} ${top - 22 * s})`} />
          </g>
        );
      })}
    </g>
  );
};

const Boat: React.FC<{x: number; y: number; p: Pal; f: number; id: string}> = ({x, y, p, f, id}) => {
  const bob = Math.sin(f / 30) * 3;
  return (
    <g transform={`translate(${x} ${y + bob})`} filter={`url(#${id}brush)`}>
      <path d="M-160 0 Q0 52 160 -20 Q20 30 -160 0 Z" fill={p.boat} />
      <path d="M-70 -6 Q-10 -70 50 -2" fill={p.hat === p.boat ? 'none' : p.hat} stroke={p.ink} strokeWidth={7} />
      <path d="M105 -90 L105 -20" stroke={p.ink} strokeWidth={10} strokeLinecap="round" />
      <path d="M86 -96 L105 -126 L124 -96 Z" fill={p.hat} />
      <path d="M150 -110 L80 90" stroke={p.ink} strokeWidth={5} strokeLinecap="round" />
      {[0, 1, 2].map((k) => (
        <path key={k} d={`M${120 + k * 6} ${30 + k * 22} H${230 - k * 20}`} stroke={p.sun !== 'none' && p.sun !== p.ink ? p.sun : p.far} strokeWidth={5} strokeLinecap="round" opacity={0.8} />
      ))}
    </g>
  );
};

export const InkScape: React.FC<{pos?: 'top' | 'full'; palette?: string; items?: string[]; drift?: boolean}> = ({pos = 'top', palette = 'mono', items, drift}) => {
  const f = useCurrentFrame();
  const p = INK_PAL[palette] || INK_PAL.mono;
  const id = 'ink' + palette + pos;
  const has = (k: string) => !items || items.includes(k);
  // drift: tranh "thở" chậm (phóng nhẹ 1 → 1,05 rồi về, chu kỳ ~24s) cho video chỉ có tiếng khỏi đứng im
  const dz = drift ? 1.025 + 0.025 * Math.sin(f / (30 * 24 / (2 * Math.PI))) : 1;
  if (pos === 'full')
    return (
      <AbsoluteFill style={drift ? {transform: `scale(${dz})`, transformOrigin: '50% 45%'} : undefined}>
        <svg width={1080} height={1920} viewBox="0 0 1080 1920" style={{position: 'absolute', inset: 0}}>
          <Defs id={id} p={p} />
          <rect width={1080} height={1920} fill={p.paper} />
          <linearGradient id={id + 'sky'} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor={p.sky} />
            <stop offset="1" stopColor={p.paper} />
          </linearGradient>
          <rect width={1080} height={1000} fill={`url(#${id}sky)`} />
          {has('sun') && (
            <g>
              <circle cx={850} cy={560} r={150} fill={`url(#${id}glow)`} />
              <circle cx={850} cy={560} r={78} fill={p.sun} stroke={p.sunLine || 'none'} strokeWidth={5} />
            </g>
          )}
          {has('birds') && <Birds x={160} y={600} c={p.ink} f={f} id={id} />}
          <path d={ridge(5, -20, 1100, 860, [[160, 650], [380, 600], [600, 660], [860, 610], [1000, 640]])} fill={`url(#${id}far)`} filter={`url(#${id}rough)`} />
          <path d={ridge(9, -20, 1100, 940, [[90, 760], [330, 730], [720, 720], [960, 690]])} fill={`url(#${id}near)`} filter={`url(#${id}rough)`} />
          <linearGradient id={id + 'mist'} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor={p.mist} stopOpacity="0" />
            <stop offset="0.45" stopColor={p.mist} stopOpacity="0.95" />
            <stop offset="1" stopColor={p.mist} stopOpacity="0" />
          </linearGradient>
          <rect y={760} width={1080} height={300} fill={`url(#${id}mist)`} />
          {[[120, 1080, 380], [560, 1150, 300], [60, 1300, 420], [620, 1420, 340], [200, 1600, 320]].map(([x, y, w], k) => (
            <path key={k} d={`M${x} ${y} h${w}`} stroke={p.far} strokeWidth={6} strokeLinecap="round" opacity={0.6} filter={`url(#${id}brush)`} />
          ))}
          {has('boat') && <Boat x={480} y={1040} p={p} f={f} id={id} />}
          {has('reeds') && <Reeds x={110} base={1940} c={p.reed} head={p.head} f={f} id={id} />}
          {has('reeds') && <Reeds x={970} base={1940} c={p.reed} head={p.head} flip f={f} id={id} />}
          <rect width={1080} height={1920} filter={`url(#${id}paper)`} />
        </svg>
      </AbsoluteFill>
    );
  // TOP: dải giấy sương phía trên (0 → ~640px) + lau sậy 2 góc dưới
  return (
    <AbsoluteFill style={{pointerEvents: 'none'}}>
      <svg width={1080} height={1920} viewBox="0 0 1080 1920" style={{position: 'absolute', inset: 0}}>
        <Defs id={id} p={p} />
        <linearGradient id={id + 'band'} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor={p.sky} stopOpacity="1" />
          <stop offset="0.45" stopColor={p.paper} stopOpacity="0.97" />
          <stop offset="0.75" stopColor={p.paper} stopOpacity="0.75" />
          <stop offset="1" stopColor={p.paper} stopOpacity="0" />
        </linearGradient>
        <rect width={1080} height={700} fill={`url(#${id}band)`} />
        {has('sun') && (
          <g>
            <circle cx={880} cy={150} r={110} fill={`url(#${id}glow)`} />
            <circle cx={880} cy={150} r={62} fill={p.sun} stroke={p.sunLine || 'none'} strokeWidth={4} />
          </g>
        )}
        {has('birds') && <Birds x={60} y={150} c={p.ink} f={f} id={id} />}
        <g opacity={0.95}>
          <path d={ridge(5, -20, 1100, 640, [[120, 470], [330, 430], [560, 480], [800, 440], [1000, 470]])} fill={`url(#${id}far)`} filter={`url(#${id}rough)`} />
          <path d={ridge(9, -20, 1100, 700, [[60, 540], [250, 520], [700, 515], [940, 500]])} fill={`url(#${id}near)`} filter={`url(#${id}rough)`} />
        </g>
        {has('reeds') && <Reeds x={70} base={1960} c={p.reed} head={p.head} f={f} id={id} />}
        {has('reeds') && <Reeds x={1010} base={1960} c={p.reed} head={p.head} flip f={f} id={id} />}
        <rect width={1080} height={700} filter={`url(#${id}paper)`} />
      </svg>
    </AbsoluteFill>
  );
};
