import React, {createContext, useContext} from 'react';
import {FR, fy} from './frame';
import {AbsoluteFill, Freeze, Img, OffthreadVideo, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';

import {S, fontCss, fontWeight, headFont, skinOf} from './style';
import {skinDef} from './skins';
const isVideo = (src: string) => /\.(mp4|mov|webm|m4v)(\?|$)/i.test(src);
/** đường dẫn trong public/ (lúc render) hoặc URL đầy đủ (lúc xem trước trong trình chỉnh sửa) */
export const mediaSrc = (s: string) => (/^(https?:|\/|blob:|data:)/.test(s) ? s : staticFile(s));

/** tốc độ phát của video trám / khung hình (1 = bình thường) — EditPlan đặt theo element.rate */
export const RateCtx = createContext(1);
/** MẶT NẠ cho ảnh/video trám & khung nổi (clip-path theo % khung media): mask = circle | round | heart | diamond | star |
 *  split-l | split-r | split-t | split-b ; maskX, maskY (0–1, tâm), maskS (cỡ, 1 = vừa) */
export const MaskCtx = createContext<string | undefined>(undefined);
/** cách hiện ảnh/video trám: flip (h | v | hv) lật gương, cs/cx/cy cắt khung (phóng cs lần quanh tâm cx, cy 0–1),
 *  freeze = đứng hình ở khung đầu, kb = false: tắt zoom chậm (Ken Burns) */
// fit: cover (phủ kín, cắt bớt — mặc định) | contain (vừa khung, nền đen) | blur (vừa khung, nền là chính ảnh làm mờ)
export type View = {flip?: string; cs?: number; cx?: number; cy?: number; freeze?: boolean; kb?: boolean; fit?: string; rot?: number};
export const ViewCtx = createContext<View>({});
export const viewOf = (e: any): View => ({flip: e.flip, cs: e.cropS, cx: e.cropX, cy: e.cropY, freeze: !!e.freeze, kb: e.kb, fit: e.fit, rot: e.rotIn});
const poly = (pts: [number, number][], cx: number, cy: number, s: number) =>
  `polygon(${pts.map(([x, y]) => `${(cx + (x - 50) * s).toFixed(2)}% ${(cy + (y - 50) * s).toFixed(2)}%`).join(', ')})`;
const HEART: [number, number][] = Array.from({length: 40}, (_, i) => {
  const t = (i / 40) * Math.PI * 2;
  const x = 16 * Math.pow(Math.sin(t), 3), y = 13 * Math.cos(t) - 5 * Math.cos(2 * t) - 2 * Math.cos(3 * t) - Math.cos(4 * t);
  return [50 + x * 2.9, 47 - y * 2.9];
});
const STAR: [number, number][] = Array.from({length: 10}, (_, i) => {
  const a = -Math.PI / 2 + (i * Math.PI) / 5, r = i % 2 ? 20 : 48;
  return [50 + Math.cos(a) * r, 52 + Math.sin(a) * r];
});
export const maskCss = (e: any): string | undefined => {
  const m = e?.mask;
  if (!m || m === 'none') return undefined;
  const cx = (e.maskX ?? 0.5) * 100, cy = (e.maskY ?? 0.5) * 100, s = e.maskS ?? 1;
  switch (m) {
    case 'circle': return `circle(${(36 * s).toFixed(1)}% at ${cx}% ${cy}%)`;
    case 'round': { const ix = Math.max(0, 50 - 42 * s), iy = Math.max(0, 50 - 42 * s); return `inset(${iy + cy - 50}% ${ix - (cx - 50)}% ${iy - (cy - 50)}% ${ix + cx - 50}% round 6%)`; }
    case 'heart': return poly(HEART, cx, cy, s);
    case 'diamond': return poly([[50, 6], [94, 50], [50, 94], [6, 50]], cx, cy, s);
    case 'star': return poly(STAR, cx, cy, s);
    case 'split-l': return `inset(0 ${100 - cx}% 0 0)`;
    case 'split-r': return `inset(0 0 0 ${cx}%)`;
    case 'split-t': return `inset(0 0 ${100 - cy}% 0)`;
    case 'split-b': return `inset(${cy}% 0 0 0)`;
  }
  return undefined;
};

export type Theme = {light: string; mid: string; dark: string; gold1: string; gold2: string};

export const MediaFill: React.FC<{src: string; from?: number; zoom: number; panX: number; volume?: number; filter?: string}> = ({
  src,
  from = 0,
  zoom,
  panX,
  volume = 0,
  filter,
}) => {
  const rate = useContext(RateCtx);
  const mask = useContext(MaskCtx);
  const v = useContext(ViewCtx);
  const z = v.kb === false ? 1 : zoom, px = v.kb === false ? 0 : panX;
  const cs = v.cs && v.cs > 1 ? v.cs : 1;
  const fx = v.flip?.includes('h') ? -1 : 1, fy = v.flip?.includes('v') ? -1 : 1;
  const pos = `${(v.cx ?? 0.5) * 100}% ${(v.cy ?? 0.5) * 100}%`;
  const fit = v.fit === 'contain' || v.fit === 'blur' ? 'contain' : 'cover';
  const style: React.CSSProperties = {
    clipPath: mask,
    width: '100%',
    height: '100%',
    objectFit: fit,
    objectPosition: pos, // vùng giữ lại khi ảnh/video khác tỉ lệ khung (chọn ở hộp "Chọn vùng hiện")
    transform: `scale(${z * cs}) translateX(${px}px)`, // lật làm ở lớp ngoài quanh TÂM (lật quanh điểm cắt lệch tâm sẽ làm hở mép)
    transformOrigin: pos,
    filter,
  };
  const one = (st: React.CSSProperties, muted?: boolean) =>
    !isVideo(src) ? (
      <Img src={mediaSrc(src)} style={st} />
    ) : (
      <OffthreadVideo src={mediaSrc(src)} transparent={/\.webm(\?|$)/i.test(src)} muted={muted || !volume || v.freeze} volume={muted ? 0 : volume || 0} startFrom={Math.round(from * 30)} playbackRate={rate} style={st} />
    );
  let node = one(style);
  if (fx < 0 || fy < 0) node = <div style={{width: '100%', height: '100%', transform: `scale(${fx}, ${fy})`}}>{node}</div>;
  // xoay ẢNH BÊN TRONG khung (rotIn, độ): 90/270 đổi chiều khung ảnh theo khung chứa (đơn vị cq*), góc lẻ thì phóng thêm cho khỏi hở mép
  const rq = ((Math.round(v.rot || 0) % 360) + 360) % 360;
  if (rq) {
    const side = rq === 90 || rq === 270;
    const th = (rq * Math.PI) / 180;
    const extra = side || rq === 180 ? 1 : Math.abs(Math.cos(th)) + Math.abs(Math.sin(th)) * 1.78;
    node = (
      <div style={{position: 'relative', width: '100%', height: '100%', overflow: 'hidden', containerType: 'size'} as any}>
        <div style={{position: 'absolute', left: '50%', top: '50%', width: side ? '100cqh' : '100%', height: side ? '100cqw' : '100%', transform: `translate(-50%, -50%) rotate(${rq}deg) scale(${extra})`}}>{node}</div>
      </div>
    );
  }
  if (v.fit === 'blur')
    node = (
      <div style={{position: 'relative', width: '100%', height: '100%', overflow: 'hidden', clipPath: mask}}>
        <div style={{position: 'absolute', inset: 0}}>{one({...style, objectFit: 'cover', objectPosition: '50% 50%', transform: 'scale(1.15)', filter: `${filter || ''} blur(40px) brightness(0.7)`}, true)}</div>
        <div style={{position: 'absolute', inset: 0}}>{one(style)}</div>
      </div>
    );
  return v.freeze ? <Freeze frame={0}>{node}</Freeze> : node;
};

/** Ảnh/video minh họa toàn màn hình, che video gốc (tiếng gốc vẫn giữ) */
/** vùng trám nửa khung: [top px, cao px, feather px, area] */
export const brollArea = (e: any): {area: 'full' | 'top' | 'bottom'; top: number; h: number; feather: number; split: number} => {
  const st = S.style.broll || {};
  const area = (e?.area || st.area || 'full') as any;
  let split = e?.split ?? st.split ?? 0.45;
  if (split > 1) split /= 100; // trình edit ghi theo %
  split = Math.max(0.25, Math.min(0.7, split));
  const feather = Math.max(0, e?.feather ?? st.feather ?? 170);
  const h = Math.round(FR.h * split);
  return {area, split, feather, h, top: area === 'bottom' ? FR.h - h : 0};
};

export const BRoll: React.FC<{src: string; from?: number; label?: string; transition?: string; exit?: string; tdur?: number; dur: number; theme: Theme; volume?: number; filter?: string; area?: string; split?: number; feather?: number; seam?: string}> = ({
  area: area0,
  split: split0,
  feather: feather0,
  seam: seam0,
  src,
  from,
  label,
  transition,
  exit,
  tdur,
  dur,
  theme,
  volume,
  filter,
}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const mask = useContext(MaskCtx); // ảnh trám có mặt nạ: cắt cả khối, ngoài mặt nạ thấy video chính
  const st = S.style.broll || {};
  const A = brollArea({area: area0, split: split0, feather: feather0});
  const half = A.area !== 'full';
  const tr = transition || st.enter || (half ? 'fade' : 'zoom');
  const ex = exit || st.exit || 'fade';
  // tdur (giây): mờ chồng / nhòe chồng chậm, đều (dựng theo nhạc êm); không có thì bật nhanh như cũ
  const slowN = tdur && tdur > 0 ? Math.max(2, Math.round(tdur * fps)) : 0;
  const slow = slowN ? interpolate(f, [0, slowN], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: (x: number) => x * x * (3 - 2 * x)}) : 0;
  const inn = slowN ? slow : spring({frame: f, fps, config: {damping: 16, stiffness: 140}});
  const fast = interpolate(f, [0, 6], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const med = slowN ? slow : interpolate(f, [0, 12], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: (x: number) => 1 - Math.pow(1 - x, 3)});
  const bnc = spring({frame: f, fps, config: {damping: 11, stiffness: 120}});
  const k = interpolate(f, [dur - 6, dur], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}); // 0 -> 1 lúc ra
  const kbOn = st.kenburns !== false;
  const kb = kbOn ? interpolate(f, [0, dur], [1.04, 1.16]) : 1; // Ken Burns
  const pan = kbOn ? interpolate(f, [0, dur], [-20, 20]) : 0;
  const enter: React.CSSProperties =
    tr === 'slide'
      ? {transform: `translateX(${(1 - inn) * FR.w}px)`}
      : tr === 'up'
        ? {transform: `translateY(${(1 - inn) * FR.h}px)`}
        : tr === 'fade'
          ? {opacity: inn}
          : tr === 'cut'
            ? {}
            : tr === 'whip'
              ? {transform: `translateX(${(1 - fast) * FR.w}px)`, filter: fast < 1 ? `blur(${(1 - fast) * 30}px)` : undefined}
              : tr === 'circle'
                ? {clipPath: `circle(${fast * 120}% at 50% 50%)`}
                : tr === 'blur'
                  ? {opacity: med, filter: med < 1 ? `blur(${(1 - med) * 36}px)` : undefined, transform: `scale(${1.06 - 0.06 * med})`}
                  : tr === 'zoomout'
                    ? {transform: `scale(${1.35 - 0.35 * inn})`, opacity: Math.min(1, inn * 1.5)}
                    : tr === 'wipe'
                      ? {clipPath: `inset(0 ${(1 - med) * 100}% 0 0)`}
                      : tr === 'diag'
                        ? {clipPath: `polygon(0 0, ${med * 220}% 0, ${med * 220 - 120}% 100%, 0 100%)`}
                        : tr === 'split'
                          ? {clipPath: `inset(0 ${(1 - med) * 50}% 0 ${(1 - med) * 50}%)`}
                          : tr === 'spin'
                            ? {transform: `rotate(${(1 - inn) * -25}deg) scale(${0.6 + 0.4 * inn})`, opacity: Math.min(1, inn * 1.6)}
                            : tr === 'drop'
                              ? {transform: `translateY(${(1 - bnc) * -FR.h}px)`}
                              : tr === 'flash' || tr === 'glitch'
                                ? {transform: tr === 'glitch' && f < 8 ? `translateX(${(f % 2 ? 1 : -1) * (8 - f) * 6}px)` : undefined}
                                : {transform: `scale(${0.85 + 0.15 * inn})`, opacity: inn, borderRadius: (1 - inn) * 80};
  const leave: React.CSSProperties =
    ex === 'cut'
      ? {opacity: f >= dur - 1 ? 0 : 1}
      : ex === 'slide'
        ? {transform: `translateX(${-k * FR.w}px)`}
        : ex === 'zoom'
          ? {transform: `scale(${1 + k * 0.3})`, opacity: 1 - k}
          : ex === 'zoomout'
            ? {transform: `scale(${1 - k * 0.25})`, opacity: 1 - k}
            : ex === 'blur'
              ? {opacity: 1 - k, filter: k > 0.01 ? `blur(${k * 36}px)` : undefined}
              : ex === 'up'
                ? {transform: `translateY(${-k * k * FR.h}px)`}
                : ex === 'down'
                  ? {transform: `translateY(${k * k * FR.h}px)`}
                  : ex === 'whip'
                    ? {transform: `translateX(${-k * k * FR.w}px)`, filter: k > 0.01 ? `blur(${k * 30}px)` : undefined}
                    : ex === 'wipe'
                      ? {clipPath: `inset(0 0 0 ${k * 100}%)`}
                      : ex === 'circle'
                        ? {clipPath: `circle(${(1 - k) * 120}% at 50% 50%)`}
                        : ex === 'flash'
                          ? {opacity: f >= dur - 1 ? 0 : 1}
                          : {opacity: 1 - k};
  const lab = spring({frame: f - 8, fps, config: {damping: 14}});
  if (half) {
    // nửa khung: vào/ra mềm (mờ + trượt nhẹ từ mép), mép giao hoà trộn bằng mặt nạ dải mờ
    const sm = (x: number) => (x <= 0 ? 0 : x >= 1 ? 1 : x * x * (3 - 2 * x));
    const nIn = tr === 'cut' ? 1 : sm(f / 12), nOut = ex === 'cut' ? (f >= dur - 1 ? 0 : 1) : 1 - sm((f - (dur - 12)) / 12);
    const vis = Math.min(nIn, nOut);
    const dir = A.area === 'bottom' ? 1 : -1;
    const slide = tr === 'slide' || tr === 'up' || tr === 'whip' ? (1 - nIn) * 120 * dir : (1 - vis) * 40 * dir;
    const F = Math.min(A.feather, A.h * 0.6);
    const g = A.area === 'bottom' ? `linear-gradient(180deg, transparent 0px, black ${F}px)` : `linear-gradient(0deg, transparent 0px, black ${F}px)`;
    const seam = seam0 ?? (st as any).seam;
    const seamY = A.area === 'bottom' ? F * 0.5 : A.h - F * 0.5;
    return (
      <MaskCtx.Provider value={undefined}>
        <div style={{position: 'absolute', left: 0, width: FR.w, top: A.top, height: A.h, opacity: vis, transform: `translateY(${slide}px)`, overflow: 'hidden', WebkitMaskImage: F > 0 ? g : undefined, maskImage: F > 0 ? g : undefined, clipPath: mask}}>
          <MediaFill src={src} from={from} zoom={kbOn ? interpolate(f, [0, dur], [1.02, 1.1]) : 1} panX={pan * 0.6} volume={volume} filter={filter} />
          {st.overlay === true && <AbsoluteFill style={{background: A.area === 'bottom' ? 'linear-gradient(0deg, rgba(0,0,0,0.45), rgba(0,0,0,0) 40%)' : 'linear-gradient(180deg, rgba(0,0,0,0.45), rgba(0,0,0,0) 40%)'}} />}
        </div>
        {seam && <div style={{position: 'absolute', left: 140, right: 140, top: A.top + seamY - 1, height: 3, borderRadius: 2, background: `linear-gradient(90deg, transparent, ${seam}, transparent)`, opacity: vis * 0.9}} />}
        {label && (
          <div style={{position: 'absolute', left: 0, right: 0, top: A.area === 'bottom' ? FR.h - 380 : A.h - F - 90, display: 'flex', justifyContent: 'center', opacity: lab * vis}}>
            <div style={{transform: `translateY(${(1 - lab) * 30}px)`, background: 'rgba(0,0,0,0.55)', color: 'white', fontFamily: headFont(), fontWeight: 800, fontSize: 44, padding: '10px 30px', borderRadius: 999, border: `2px solid ${theme.light}`}}>{label}</div>
          </div>
        )}
      </MaskCtx.Provider>
    );
  }
  return (
    <MaskCtx.Provider value={undefined}>
    <AbsoluteFill style={{...leave, clipPath: mask}}>
      <AbsoluteFill style={{overflow: 'hidden', background: mask || /\.(webm|png)(\?|$)/i.test(src) ? 'transparent' : 'black', ...enter}}>
        <MediaFill src={src} from={from} zoom={kb} panX={pan} volume={volume} filter={filter} />
        {/* phủ tối nhẹ phía trên & dưới cho chữ dễ đọc */}
        {st.overlay !== false && (
          <AbsoluteFill style={{background: 'linear-gradient(180deg, rgba(0,0,0,0.35) 0%, rgba(0,0,0,0) 25%, rgba(0,0,0,0) 65%, rgba(0,0,0,0.45) 100%)'}} />
        )}
      </AbsoluteFill>
      {(tr === 'flash' || tr === 'glitch') && f < 8 && <AbsoluteFill style={{background: tr === 'flash' ? 'white' : 'transparent', opacity: tr === 'flash' ? (1 - f / 8) * 0.9 : 1, boxShadow: tr === 'glitch' ? `inset ${(f % 3) * 6}px 0 0 rgba(255,0,80,0.5), inset -${(f % 3) * 6}px 0 0 rgba(0,220,255,0.5)` : undefined}} />}
      {ex === 'flash' && f >= dur - 6 && <AbsoluteFill style={{background: 'white', opacity: ((f - (dur - 6)) / 6) * 0.9}} />}
      {label && (
        <div style={{position: 'absolute', top: fy(1180), left: 0, right: 0, display: 'flex', justifyContent: 'center'}}>
          <div
            style={{
              transform: `translateY(${(1 - lab) * 60}px)`,
              opacity: lab,
              background: `linear-gradient(135deg, ${theme.light}, ${theme.mid} 50%, ${theme.dark})`,
              color: 'white',
              fontFamily: headFont(),
              fontWeight: 900,
              fontSize: 56,
              padding: '16px 40px',
              borderRadius: 22,
              border: '3px solid rgba(255,255,255,0.6)',
              boxShadow: `inset 0 3px 0 rgba(255,255,255,0.45), 0 10px 0 ${theme.dark}, 0 24px 40px rgba(0,0,0,0.45)`,
              textShadow: '0 3px 6px rgba(0,0,0,0.35)',
            }}
          >
            {label}
          </div>
        </div>
      )}
    </AbsoluteFill>
    </MaskCtx.Provider>
  );
};

/** Khung ảnh/video nổi (picture-in-picture) kiểu thẻ 3D */
export const Pip: React.FC<{src: string; from?: number; label?: string; y?: number; look?: string; dur: number; theme: Theme; volume?: number; filter?: string; w?: number; h?: number; x?: number}> = ({
  w: w0,
  h: h0,
  x: x0,
  src,
  from,
  label,
  look,
  y = 260,
  dur,
  theme,
  volume,
  filter,
}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const inn = spring({frame: f, fps, config: {damping: 13, stiffness: 150}});
  const out = interpolate(f, [dur - 8, dur], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const tilt = Math.sin(f / 14) * 4;
  const kb = interpolate(f, [0, dur], [1.0, 1.1]);
  const lk = look || S.style.broll?.pip || 'card3d';
  // khung tự do: w = bề rộng khung (px), h = chiều cao phần ảnh (px), x = tâm ngang (0–1)
  const xOff = x0 != null ? (x0 <= 1 ? x0 * FR.w : x0) - FR.w / 2 : 0;
  if (lk !== 'card3d') {
    const round = lk === 'round';
    const pol = lk === 'polaroid';
    const w = w0 ?? (round ? 640 : 860);
    return (
      <AbsoluteFill style={{alignItems: 'center', top: y, opacity: out, transform: xOff ? `translateX(${xOff}px)` : undefined}}>
        <div
          style={{
            width: w,
            transform: `scale(${0.6 + 0.4 * inn}) rotate(${pol ? -4 + Math.sin(f / 20) : 0}deg)`,
            opacity: inn,
            background: pol ? '#fff' : 'white',
            padding: pol ? '22px 22px 90px' : round ? 10 : 8,
            borderRadius: round ? '50%' : pol ? 6 : 36,
            boxShadow: '0 24px 60px rgba(0,0,0,0.5)',
            position: 'relative',
          }}
        >
          <div style={{height: h0 ?? (round ? w - 20 : 560), borderRadius: round ? '50%' : pol ? 2 : 30, overflow: 'hidden', background: 'black'}}>
            <MediaFill src={src} from={from} zoom={kb} panX={0} volume={volume} filter={filter} />
          </div>
          {label && (
            <div style={{position: pol || round ? 'absolute' : 'static', left: 0, right: 0, ...(round ? {top: '100%', marginTop: 16} : {bottom: 18}), fontFamily: headFont(), fontWeight: 800, fontSize: 46, color: pol || lk === 'clean' ? '#1d2433' : 'white', textAlign: 'center', padding: pol || round ? 0 : '12px 10px 4px', textShadow: round ? '0 4px 12px rgba(0,0,0,0.7)' : 'none'}}>
              {label}
            </div>
          )}
        </div>
      </AbsoluteFill>
    );
  }
  return (
    <AbsoluteFill style={{alignItems: 'center', top: y, opacity: out, perspective: 1400, transform: xOff ? `translateX(${xOff}px)` : undefined}}>
      <div
        style={{
          width: w0 ?? 880,
          transform: `scale(${0.6 + 0.4 * inn}) rotateX(6deg) rotateY(${tilt}deg) rotate(-2deg)`,
          opacity: inn,
          borderRadius: 40,
          padding: 12,
          background: `linear-gradient(145deg, rgba(255,255,255,0.7), ${theme.mid}CC 60%, ${theme.dark})`,
          boxShadow: `0 16px 0 ${theme.dark}, 0 40px 70px rgba(0,0,0,0.55)`,
        }}
      >
        <div style={{height: h0 ?? 560, borderRadius: 30, overflow: 'hidden', background: 'black'}}>
          <MediaFill src={src} from={from} zoom={kb} panX={0} volume={volume} filter={filter} />
        </div>
        {label && (
          <div style={{fontFamily: headFont(), fontWeight: 900, fontSize: 50, color: 'white', textAlign: 'center', padding: '14px 10px 6px', textShadow: '0 3px 8px rgba(0,0,0,0.4)'}}>
            {label}
          </div>
        )}
      </div>
    </AbsoluteFill>
  );
};

/** Nhãn NGÀY X/Y + thanh tiến độ */
export const DayBadge: React.FC<{day: number; total: number; theme: Theme}> = ({day, total, theme}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const pop = spring({frame: f, fps, config: {damping: 12}});
  const fill = interpolate(f, [8, 30], [(day - 1) / total, day / total], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const sd = skinDef();
  if (sd) {
    const ac = S.style.accent || sd.accent(theme);
    const bd = sd.badge(theme, ac);
    return (
      <div style={{position: 'absolute', top: 150, left: 50, transform: `scale(${pop})`, transformOrigin: 'left top', display: 'flex', alignItems: 'center', gap: 16,
        ...sd.card(theme, ac), borderRadius: sd.radius(999) as any, padding: '10px 26px 10px 14px'}}>
        <span style={{background: bd.bg === 'transparent' ? 'transparent' : bd.bg, border: bd.bg === 'transparent' ? `1px solid ${ac}` : 'none', color: bd.fg, fontFamily: headFont(), fontWeight: 900, fontSize: 30, borderRadius: sd.radius(999) as any, padding: '6px 16px', letterSpacing: 1, ...sd.label} as React.CSSProperties}>NGÀY</span>
        <span style={{fontFamily: headFont(), fontWeight: 900, fontSize: 44, color: sd.ink(theme)}}>{day}<span style={{opacity: 0.5, fontWeight: 700}}>/{total}</span></span>
        <div style={{width: 120, height: 8, borderRadius: 4, background: sd.light ? 'rgba(0,0,0,0.1)' : 'rgba(255,255,255,0.18)', overflow: 'hidden'}}>
          <div style={{width: `${fill * 100}%`, height: '100%', background: ac}} />
        </div>
      </div>
    );
  }
  return (
    <div style={{position: 'absolute', top: 150, left: 50, right: 150, transform: `scale(${pop})`, transformOrigin: 'left top'}}>
      <div
        style={{
          display: 'inline-block',
          background: `linear-gradient(180deg, ${theme.gold1}, ${theme.gold2})`,
          color: theme.dark,
          fontFamily: headFont(),
          fontWeight: 900,
          fontSize: 52,
          padding: '8px 28px',
          borderRadius: 18,
          boxShadow: `0 6px 0 #B07D0E, 0 14px 24px rgba(0,0,0,0.35)`,
        }}
      >
        NGÀY {day}/{total}
      </div>
      <div style={{marginTop: 20, height: 14, borderRadius: 7, background: 'rgba(255,255,255,0.3)', overflow: 'hidden'}}>
        <div style={{width: `${fill * 100}%`, height: '100%', background: `linear-gradient(90deg, ${theme.light}, ${theme.gold2})`}} />
      </div>
    </div>
  );
};

/** Phụ đề tự động. Kiểu (style.captions.preset): tiktok (mặc định: chữ viền, từ đang đọc vàng) · karaoke (từ đã đọc đổi màu)
 *  box (cả dòng trên nền tối) · wordbox (từ đang đọc có nền màu) · pop (từng từ bật ra khi đọc) · single (1 từ to mỗi lần)
 *  minimal (chữ trắng nhỏ, bóng mờ) · outline (viền đen dày, từ đang đọc vàng) */
type Word = {w: string; start: number; end: number};
export const Captions: React.FC<{pages: Word[][]; top: number; from: number; theme: Theme; size?: number; upper?: boolean}> = ({pages, top, from, theme, size, upper}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = f / fps;
  if (t < from) return null;
  const c = S.style.captions || {};
  const preset = c.preset || 'tiktok';
  let page = pages.find((p) => p.length && t >= p[0].start && t < p[p.length - 1].end);
  if (!page) return null;
  const sz = size ?? c.size ?? (preset === 'single' ? 110 : preset === 'minimal' ? 58 : 70);
  const up = upper ?? c.upper ?? !['minimal', 'karaoke'].includes(preset);
  const font = c.font || S.style.font;
  const weight = fontWeight(font, c.weight ?? (preset === 'minimal' ? 700 : 900));
  const color = c.color || 'white';
  const active = c.active || (preset === 'karaoke' ? theme.light : preset === 'wordbox' ? 'white' : preset === 'outline' ? '#FFE500' : theme.gold1);
  const activeBg = c.activeBg || (preset === 'box' ? 'rgba(0,0,0,0.6)' : theme.mid);
  const strokeColor = c.strokeColor || (preset === 'outline' ? '#000' : theme.dark);
  const stroke = c.stroke ?? (preset === 'outline' ? Math.round(sz / 4.5) : preset === 'minimal' || preset === 'box' || preset === 'wordbox' ? 0 : Math.round(sz / 7));
  if (preset === 'single') {
    const w = page.find((x) => t >= x.start && t < x.end) || [...page].reverse().find((x) => t >= x.start);
    if (!w) return null;
    page = [w];
  }
  const start = page[0].start;
  const an = c.anim || (preset === 'minimal' ? 'fade' : 'pop');
  const pop = spring({frame: f - start * fps, fps, config: {damping: 14, stiffness: 200}});
  const lin = interpolate(f - start * fps, [0, 5], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const boxT = an === 'pop' ? `scale(${0.85 + 0.15 * pop})` : an === 'up' ? `translateY(${(1 - pop) * 40}px)` : 'none';
  const boxO = an === 'fade' || an === 'up' ? lin : 1;
  const line = (
    <div
      style={{
        position: 'absolute',
        top,
        left: 40,
        right: 130,
        textAlign: 'center',
        transform: boxT,
        opacity: boxO,
        textWrap: 'balance' as any,
      }}
    >
      <span
        style={
          preset === 'box'
            ? ({background: activeBg, borderRadius: 18, padding: '6px 14px', WebkitBoxDecorationBreak: 'clone', boxDecorationBreak: 'clone', lineHeight: 1.55} as any)
            : undefined
        }
      >
        {page.map((w, i) => {
          const isOn = t >= w.start && t < w.end;
          const said = t >= w.start;
          if (preset === 'pop' && !said) return null;
          const wp = spring({frame: f - w.start * fps, fps, config: {damping: 11, stiffness: 220}});
          const col = preset === 'karaoke' ? (said ? active : color) : isOn && preset !== 'box' && preset !== 'minimal' ? active : isOn && preset === 'box' ? active : color;
          return (
            <span
              key={i}
              style={{
                display: 'inline-block',
                margin: preset === 'single' ? 0 : `0 ${Math.round(sz / 5)}px`,
                fontFamily: fontCss(font),
                fontWeight: weight,
                fontSize: sz,
                lineHeight: 1.2,
                textTransform: up ? 'uppercase' : 'none',
                color: col,
                transform:
                  preset === 'pop' || preset === 'single'
                    ? `scale(${0.4 + 0.6 * wp})`
                    : isOn && (preset === 'tiktok' || preset === 'outline')
                      ? 'scale(1.12)'
                      : 'scale(1)',
                ...(preset === 'wordbox' && isOn ? {background: activeBg, borderRadius: 14, padding: '0 12px', boxShadow: '0 6px 16px rgba(0,0,0,0.35)'} : {}),
                ...(stroke ? ({WebkitTextStroke: `${stroke}px ${strokeColor}`, paintOrder: 'stroke fill'} as any) : {}),
                textShadow: preset === 'box' ? 'none' : preset === 'minimal' ? '0 3px 12px rgba(0,0,0,0.75)' : preset === 'outline' ? '0 6px 0 rgba(0,0,0,0.6)' : '0 8px 24px rgba(0,0,0,0.6)',
                paddingTop: Math.round(sz * 0.08),
              }}
            >
              {up || (w as any).keep || /\d/.test(w.w) ? w.w : w.w.toLocaleLowerCase('vi')}
            </span>
          );
        })}
      </span>
    </div>
  );
  return line;
};
