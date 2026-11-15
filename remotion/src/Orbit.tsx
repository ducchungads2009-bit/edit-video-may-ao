/* Khối VÒNG QUAY: ảnh / video minh họa xếp thành vòng elip quay quanh người nói (kiểu băng chuyền 3D).
   Nửa vòng PHÍA SAU nằm sau người (khi đã tách người — render.py tự làm cho khối orbit), nửa PHÍA TRƯỚC đè lên người.
   element: {type: 'orbit', items: [{src, from?} | "assets/..."], cx (0–1, tâm ngang, mặc định 0.5), cy (px, tâm dọc — ngang
   ngực, mặc định 1150), rx (px bán kính ngang, 430), ry (px bán kính dọc, 80 — độ nghiêng của vòng), tilt (độ, nghiêng vòng),
   period (giây / vòng, 9), dir (1 | -1), cardW (230), cardH (330), radius (bo góc, 22), look: glass | clean | white,
   backDim (0–1, độ tối nửa sau, 0.45), turn (true: thẻ xoay theo vòng như trụ 3D), spread (giây bung ra lúc đầu, 0.6)}
   _half: 'back' | 'front' (EditPlan tự tách khối thành 2 lớp khi có lớp người) */
import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {MediaFill} from './Media';
import {FR, fy} from './frame';

export type OrbitEl = {
  items?: (string | {src: string; from?: number})[];
  cx?: number;
  cy?: number;
  rx?: number;
  ry?: number;
  tilt?: number;
  period?: number;
  dir?: number;
  cardW?: number;
  cardH?: number;
  radius?: number;
  look?: string;
  backDim?: number;
  turn?: boolean;
  spread?: number;
  phase?: number;
  _half?: 'back' | 'front';
};

const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;

/** vị trí thẻ i ở khung f — dùng chung cho 2 lớp để khớp nhau tuyệt đối */
export const orbitPose = (e: OrbitEl, i: number, n: number, f: number, fps: number, dur: number) => {
  const T = Math.max(1.5, e.period ?? 9);
  const dir = e.dir === -1 ? -1 : 1;
  const th = (2 * Math.PI * i) / Math.max(1, n) + ((e.phase ?? 0) * Math.PI) / 180 + (dir * 2 * Math.PI * f) / (fps * T);
  const sp = Math.max(0.05, e.spread ?? 0.6);
  const open = spring({frame: f, fps, config: {damping: 15, stiffness: 90}, durationInFrames: Math.round(sp * fps * 1.6)});
  const close = interpolate(f, [dur - Math.round(fps * 0.4), dur], [1, 0], clamp);
  const k = Math.min(open, close);
  const rx = (e.rx ?? 430) * k, ry = (e.ry ?? 80) * k;
  const tl = ((e.tilt ?? 0) * Math.PI) / 180;
  const sx = Math.sin(th) * rx, sy = Math.cos(th) * ry; // cos > 0 = phía trước (thấp hơn, to hơn)
  const x = (e.cx ?? 0.5) * FR.w + sx * Math.cos(tl) - sy * Math.sin(tl);
  const y = (e.cy ?? fy(1150)) + sx * Math.sin(tl) + sy * Math.cos(tl);
  const d = Math.cos(th); // độ sâu -1 (sau) .. 1 (trước)
  const s = (0.6 + 0.4 * (d + 1) / 2) * (0.25 + 0.75 * k);
  return {x, y, d, s, rotY: e.turn === false ? 0 : -Math.sin(th) * 48, k};
};

export const Orbit: React.FC<{e: OrbitEl; dur: number}> = ({e, dur}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const items = (e.items || []).map((x) => (typeof x === 'string' ? {src: x} : x)).filter((x) => x && x.src);
  if (!items.length) return null;
  const W = e.cardW ?? 230, H = e.cardH ?? 330, R = e.radius ?? 22;
  const dim = Math.max(0, Math.min(1, e.backDim ?? 0.45));
  const look = e.look || 'glass';
  const poses = items.map((it, i) => ({it, i, ...orbitPose(e, i, items.length, f, fps, dur)}));
  const show = poses.filter((p) => (e._half === 'back' ? p.d < 0 : e._half === 'front' ? p.d >= 0 : true)).sort((a, b) => a.d - b.d);
  return (
    <AbsoluteFill style={{pointerEvents: 'none', perspective: 1400}}>
      {show.map((p) => {
        const light = 1 - dim * (1 - (p.d + 1) / 2);
        const border = look === 'white' ? '6px solid #fff' : look === 'clean' ? 'none' : '2px solid rgba(255,255,255,.55)';
        return (
          <div
            key={p.i}
            style={{
              position: 'absolute', left: p.x - W / 2, top: p.y - H / 2, width: W, height: H, borderRadius: R, overflow: 'hidden', border,
              transform: `scale(${p.s}) rotateY(${p.rotY}deg)`, transformOrigin: '50% 50%',
              boxShadow: `0 ${18 * p.s}px ${44 * p.s}px rgba(0,0,0,${0.25 + 0.3 * (p.d + 1) / 2})`,
              filter: `brightness(${light.toFixed(3)})${p.d < -0.2 ? ` blur(${(-p.d - 0.2) * 2.2}px)` : ''}`,
              opacity: Math.min(1, p.k * 2), background: '#111',
            }}
          >
            <MediaFill src={p.it.src} from={p.it.from} zoom={1} panX={0} />
            {look === 'glass' && (
              <div style={{position: 'absolute', inset: 0, borderRadius: R, background: 'linear-gradient(135deg, rgba(255,255,255,.28) 0%, rgba(255,255,255,0) 38%, rgba(255,255,255,0) 70%, rgba(255,255,255,.12) 100%)'}} />
            )}
          </div>
        );
      })}
    </AbsoluteFill>
  );
};
