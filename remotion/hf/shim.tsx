/* BỘ DỰNG HYPERFRAMES — lớp thay thế gói 'remotion' (tự viết, Apache-2.0 như phần còn lại của tool).
   Các khối trong remotion/src vẫn `import {...} from 'remotion'`; khi đóng gói cho HyperFrames (scripts/hf_engine.py),
   esbuild trỏ 'remotion' về file này. Nhờ vậy giữ nguyên toàn bộ khối đồ hoạ / 3D / bản đồ / cảnh AI mà không cần giấy phép Remotion.

   Cách chạy: HyperFrames mở trang, mỗi khung gửi sự kiện `hf-seek` (giây) -> dựng lại cây React cho khung đó (flushSync),
   chờ mọi delayRender (ảnh, video, font, bản đồ, 3D...) xong rồi mới chụp.
   Video: <OffthreadVideo> = <img> lấy khung từ máy chủ khung (hf_engine.py, ffmpeg giải mã tuần tự) — như cách Remotion làm.
   Tiếng: chế độ 'audio' chạy cả dòng thời gian, ghi lại mỗi khung đang phát gì / to bao nhiêu -> Python trộn bằng ffmpeg. */
import React, {createContext, forwardRef, useContext, useId, useLayoutEffect, useMemo, useRef} from 'react';
import {flushSync} from 'react-dom';
import {createRoot} from 'react-dom/client';

type HFConf = {comp: string; props?: any; fps?: number; base?: string; fs?: string; mode?: 'video' | 'audio' | 'still'; scale?: number; w?: number; h?: number};
const W_: any = typeof window !== 'undefined' ? window : {};
const HF: HFConf = W_.__HF || {comp: ''};

/* ---------------- thời gian ---------------- */
export type VideoConfig = {id: string; width: number; height: number; fps: number; durationInFrames: number; defaultProps: any; props: any};
const CfgCtx = createContext<VideoConfig | null>(null);
/** khung hiện tại (tính theo Sequence gần nhất) + độ dài của Sequence đó */
const TlCtx = createContext<{frame: number; dur: number}>({frame: 0, dur: 1});
let ABS = 0; // khung tuyệt đối đang dựng

export const useCurrentFrame = () => useContext(TlCtx).frame;
export const useVideoConfig = (): VideoConfig => {
  const c = useContext(CfgCtx);
  const t = useContext(TlCtx);
  if (!c) throw new Error('useVideoConfig() ngoài khung dựng');
  return useMemo(() => ({...c, durationInFrames: t.dur}), [c, t.dur]);
};

export const AbsoluteFill = forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(({style, ...rest}, ref) => (
  <div ref={ref} {...rest}
    style={{position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, width: '100%', height: '100%', display: 'flex', flexDirection: 'column', ...style}} />
));

type SeqProps = {from?: number; durationInFrames?: number; children?: React.ReactNode; name?: string; layout?: 'absolute-fill' | 'none';
  style?: React.CSSProperties; className?: string; premountFor?: number; postmountFor?: number; showInTimeline?: boolean; height?: number; width?: number};
export const Sequence = forwardRef<HTMLDivElement, SeqProps>(({from = 0, durationInFrames, children, layout = 'absolute-fill', style, className}, ref) => {
  const p = useContext(TlCtx);
  const dur = Math.max(0, Math.min(durationInFrames ?? Infinity, p.dur - from));
  const f = p.frame - from;
  const tl = useMemo(() => ({frame: f, dur}), [f, dur]);
  if (f < 0 || f >= dur) return null;
  const inner = <TlCtx.Provider value={tl}>{children}</TlCtx.Provider>;
  return layout === 'none' ? inner : <AbsoluteFill ref={ref} style={style} className={className}>{inner}</AbsoluteFill>;
});

export const Freeze: React.FC<{frame: number; active?: boolean | ((f: number) => boolean); children?: React.ReactNode}> = ({frame, active = true, children}) => {
  const p = useContext(TlCtx);
  const on = typeof active === 'function' ? active(p.frame) : active;
  const tl = useMemo(() => ({frame, dur: p.dur}), [frame, p.dur]);
  return on ? <TlCtx.Provider value={tl}>{children}</TlCtx.Provider> : <>{children}</>;
};

/* ---------------- interpolate / Easing / spring ---------------- */
type Extra = 'extend' | 'clamp' | 'identity' | 'wrap';
type InterpOpts = {easing?: (t: number) => number; extrapolateLeft?: Extra; extrapolateRight?: Extra};
const seg = (x: number, a: number, b: number, c: number, d: number, o: InterpOpts) => {
  let v = x;
  const L = o.extrapolateLeft || 'extend', R = o.extrapolateRight || 'extend';
  if (v < a) {
    if (L === 'identity') return v;
    if (L === 'clamp') v = a;
    if (L === 'wrap') v = a + ((((v - a) % (b - a)) + (b - a)) % (b - a));
  }
  if (v > b) {
    if (R === 'identity') return v;
    if (R === 'clamp') v = b;
    if (R === 'wrap') v = a + ((v - a) % (b - a));
  }
  if (c === d) return c;
  let u = a === b ? (v <= a ? 0 : 1) : (v - a) / (b - a);
  u = (o.easing || ((z: number) => z))(u);
  return c + u * (d - c);
};
export function interpolate(input: number, inR: readonly number[], outR: readonly number[], o: InterpOpts = {}): number {
  if (inR.length !== outR.length) throw new Error('interpolate(): inputRange và outputRange phải dài bằng nhau');
  if (inR.length < 2) throw new Error('interpolate(): cần ít nhất 2 mốc');
  if (typeof input !== 'number' || Number.isNaN(input)) throw new Error('interpolate(): đầu vào không phải số: ' + input);
  let i = 1;
  while (i < inR.length - 1 && inR[i] < input) i++;
  return seg(input, inR[i - 1], inR[i], outR[i - 1], outR[i], o);
}

const bez = (x1: number, y1: number, x2: number, y2: number) => {
  const A = (a: number, b: number) => 1 - 3 * b + 3 * a, B = (a: number, b: number) => 3 * b - 6 * a, C = (a: number) => 3 * a;
  const calc = (t: number, a: number, b: number) => ((A(a, b) * t + B(a, b)) * t + C(a)) * t;
  const slope = (t: number, a: number, b: number) => 3 * A(a, b) * t * t + 2 * B(a, b) * t + C(a);
  const tOf = (x: number) => {
    let t = x;
    for (let k = 0; k < 8; k++) {
      const s = slope(t, x1, x2);
      if (Math.abs(s) < 1e-7) break;
      t -= (calc(t, x1, x2) - x) / s;
    }
    if (t < 0 || t > 1 || Math.abs(calc(t, x1, x2) - x) > 1e-6) { // chia đôi cho chắc
      let lo = 0, hi = 1;
      t = x;
      for (let k = 0; k < 40; k++) {
        const v = calc(t, x1, x2);
        if (Math.abs(v - x) < 1e-7) break;
        if (v < x) lo = t; else hi = t;
        t = (lo + hi) / 2;
      }
    }
    return t;
  };
  return (x: number) => (x1 === y1 && x2 === y2 ? x : x <= 0 ? 0 : x >= 1 ? 1 : calc(tOf(x), y1, y2));
};
type EF = (t: number) => number;
export const Easing = {
  step0: (n: number) => (n > 0 ? 1 : 0),
  step1: (n: number) => (n >= 1 ? 1 : 0),
  linear: (t: number) => t,
  ease: bez(0.42, 0, 1, 1),
  quad: (t: number) => t * t,
  cubic: (t: number) => t * t * t,
  poly: (n: number) => (t: number) => Math.pow(t, n),
  sin: (t: number) => 1 - Math.cos((t * Math.PI) / 2),
  circle: (t: number) => 1 - Math.sqrt(1 - t * t),
  exp: (t: number) => Math.pow(2, 10 * (t - 1)),
  elastic: (b = 1) => {
    const p = b * Math.PI;
    return (t: number) => 1 - Math.pow(Math.cos((t * Math.PI) / 2), 3) * Math.cos(t * p);
  },
  back: (s = 1.70158) => (t: number) => t * t * ((s + 1) * t - s),
  bounce: (t: number) => {
    if (t < 1 / 2.75) return 7.5625 * t * t;
    if (t < 2 / 2.75) { const u = t - 1.5 / 2.75; return 7.5625 * u * u + 0.75; }
    if (t < 2.5 / 2.75) { const u = t - 2.25 / 2.75; return 7.5625 * u * u + 0.9375; }
    const u = t - 2.625 / 2.75;
    return 7.5625 * u * u + 0.984375;
  },
  bezier: (x1: number, y1: number, x2: number, y2: number) => bez(x1, y1, x2, y2),
  in: (e: EF) => e,
  out: (e: EF) => (t: number) => 1 - e(1 - t),
  inOut: (e: EF) => (t: number) => (t < 0.5 ? e(t * 2) / 2 : 1 - e((1 - t) * 2) / 2),
};

type SpringCfg = {damping?: number; mass?: number; stiffness?: number; overshootClamping?: boolean};
type SpState = {t: number; x: number; v: number};
/** lò xo tắt dần (nghiệm giải tích), bước theo từng khung như cách tính quen thuộc của các thư viện chuyển động */
const step = (s: SpState, now: number, c: number, m: number, k: number): SpState => {
  const dt = Math.min(now - s.t, 64) / 1000;
  const x0 = 1 - s.x, v0 = -s.v;
  const z = c / (2 * Math.sqrt(k * m)), w0 = Math.sqrt(k / m);
  if (z < 1) {
    const w1 = w0 * Math.sqrt(1 - z * z), e = Math.exp(-z * w0 * dt), sn = Math.sin(w1 * dt), cs = Math.cos(w1 * dt);
    const fr = e * (sn * ((v0 + z * w0 * x0) / w1) + x0 * cs);
    return {t: now, x: 1 - fr, v: z * w0 * fr - e * (cs * (v0 + z * w0 * x0) - w1 * x0 * sn)};
  }
  const e = Math.exp(-w0 * dt);
  return {t: now, x: 1 - e * (x0 + (v0 + w0 * x0) * dt), v: e * (v0 * (dt * w0 - 1) + dt * x0 * w0 * w0)};
};
const SP_CACHE = new Map<string, SpState[]>();
const springAt = (frame: number, fps: number, cfg: SpringCfg) => {
  const c = cfg.damping ?? 10, m = cfg.mass ?? 1, k = cfg.stiffness ?? 100;
  if (c <= 0) throw new Error('spring: damping phải > 0');
  const key = `${fps}|${c}|${m}|${k}`;
  let arr = SP_CACHE.get(key);
  if (!arr) { arr = []; SP_CACHE.set(key, arr); }
  const f = Math.max(0, frame), whole = Math.floor(f);
  let s: SpState = arr.length ? arr[arr.length - 1] : {t: 0, x: 0, v: 0};
  for (let i = arr.length; i <= whole; i++) {
    s = step(i ? arr[i - 1] : {t: 0, x: 0, v: 0}, (i / fps) * 1000, c, m, k);
    arr.push(s);
  }
  s = arr[whole];
  if (f % 1 > 0) s = step(s, (f / fps) * 1000, c, m, k);
  return s.x;
};
export const measureSpring = ({fps, config = {}, threshold = 0.005}: {fps: number; config?: SpringCfg; threshold?: number}) => {
  if (threshold === 0) return Infinity;
  if (threshold >= 1) return 0;
  let f = 0;
  while (Math.abs(springAt(f, fps, config) - 1) >= threshold) f++;
  let done = f;
  for (let i = 0; i < 20; i++) {
    f++;
    if (Math.abs(springAt(f, fps, config) - 1) >= threshold) { i = 0; done = f + 1; }
  }
  return done;
};
export function spring({frame, fps, config = {}, from = 0, to = 1, durationInFrames, durationRestThreshold, delay = 0, reverse = false}:
  {frame: number; fps: number; config?: SpringCfg; from?: number; to?: number; durationInFrames?: number; durationRestThreshold?: number; delay?: number; reverse?: boolean}) {
  const nat = reverse || durationInFrames !== undefined ? measureSpring({fps, config, threshold: durationRestThreshold}) : 0;
  const r = reverse ? (durationInFrames ?? nat) - frame : frame;
  const d = r + (reverse ? delay : -delay);
  const t = durationInFrames === undefined ? d : d / (durationInFrames / nat);
  if (durationInFrames && d > durationInFrames) return to;
  let v = springAt(t, fps, config);
  if (config.overshootClamping) v = Math.min(v, 1);
  return from === 0 && to === 1 ? v : interpolate(v, [0, 1], [from, to]);
}

/* ---------------- chờ tải (delayRender) ---------------- */
const PENDING = new Map<number, {label: string; t: number; ms: number}>();
let HID = 0;
let wake: (() => void)[] = [];
export const delayRender = (label = '', opt?: {timeoutInMilliseconds?: number; retries?: number}) => {
  const h = ++HID;
  PENDING.set(h, {label, t: Date.now(), ms: opt?.timeoutInMilliseconds ?? 30000});
  return h;
};
export const continueRender = (h: number) => {
  if (!PENDING.delete(h)) return;
  if (!PENDING.size) { const w = wake; wake = []; w.forEach((f) => f()); }
};
export const cancelRender = (e: unknown) => { console.error('[hf] cancelRender', e); };
const idle = () => new Promise<void>((res) => {
  if (!PENDING.size) return res();
  wake.push(res);
  const tick = () => { // quá hạn -> bỏ qua (báo lỗi) để không treo cả lượt dựng
    if (!PENDING.size) return;
    const now = Date.now();
    for (const [h, p] of PENDING) if (now - p.t > p.ms) { console.error(`[hf] quá hạn chờ: ${p.label || h}`); continueRender(h); }
    if (PENDING.size) setTimeout(tick, 250);
  };
  setTimeout(tick, 250);
});

/* ---------------- tệp tĩnh / ảnh / video ---------------- */
const BASE = (HF.base || '/public').replace(/\/$/, '');
export const staticFile = (p: string) => {
  if (/^(https?:|blob:|data:)/.test(p)) return p;
  return BASE + '/' + p.replace(/^\/+/, '').split('/').map((s) => encodeURIComponent(decodeURIComponentSafe(s))).join('/');
};
function decodeURIComponentSafe(s: string) { try { return decodeURIComponent(s); } catch { return s; } }
export const getStaticFiles = () => [];
export const getInputProps = () => HF.props || {};

/** gắn delayRender cho 1 thẻ <img> mỗi lần src đổi (chờ tải + giải mã xong) */
const useImgWait = (ref: React.RefObject<HTMLImageElement>, src: string | undefined, label: string) => {
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el || !src) return;
    const h = delayRender(label + ' ' + src.slice(-80));
    let done = false;
    const fin = () => { if (!done) { done = true; continueRender(h); } };
    const go = () => (el.decode ? el.decode().then(fin, () => (el.complete ? fin() : (el.onload = el.onerror = fin))) : (el.onload = el.onerror = fin));
    go();
    return fin;
  }, [src]);
};

export const Img = forwardRef<HTMLImageElement, React.ImgHTMLAttributes<HTMLImageElement> & {maxRetries?: number; pauseWhenLoading?: boolean; delayRenderTimeoutInMilliseconds?: number}>(
  ({src, maxRetries, pauseWhenLoading, delayRenderTimeoutInMilliseconds, ...rest}, fref) => {
    const ref = useRef<HTMLImageElement>(null);
    React.useImperativeHandle(fref, () => ref.current as HTMLImageElement);
    useImgWait(ref, src, 'ảnh');
    if (HF.mode === 'audio') return null;
    return <img ref={ref} src={src} {...rest} />;
  });

const absUrl = (s: string) => {
  try { return new URL(s, location.href).href; } catch { return s; }
};
/** đường dẫn file cho máy chủ khung: /public/... -> đường dẫn tương đối, http(s) giữ nguyên */
const fsKey = (s: string) => {
  const u = absUrl(s);
  return u.startsWith(location.origin + '/') ? decodeURIComponentSafe(u.slice(location.origin.length)) : u;
};

/* ---------------- tiếng: ghi lại mỗi khung (chế độ audio) ---------------- */
type Rec = {k: string; src: string; f: number; m: number; v: number; r: number; loop: boolean; s0: number};
let RECS: Rec[] = [];
const evalVol = (vol: number | ((f: number) => number) | undefined, f: number) => {
  const v = typeof vol === 'function' ? vol(f) : vol ?? 1;
  return Number.isFinite(v) ? Math.max(0, v) : 0;
};
type MediaProps = {src: string; startFrom?: number; trimBefore?: number; endAt?: number; trimAfter?: number; playbackRate?: number; muted?: boolean;
  volume?: number | ((f: number) => number); loop?: boolean; style?: React.CSSProperties; className?: string; transparent?: boolean; [k: string]: any};
const useMediaTime = (p: MediaProps) => {
  const f = useCurrentFrame();
  const s0 = p.trimBefore ?? p.startFrom ?? 0, rate = p.playbackRate || 1;
  return {f, s0, rate, m: s0 + f * rate};
};
const useRecord = (p: MediaProps, kind: string) => {
  const id = useId();
  const {f, s0, rate, m} = useMediaTime(p);
  const end = p.trimAfter ?? p.endAt;
  if (HF.mode !== 'audio' || p.muted || !p.src) return;
  if (end !== undefined && m >= end) return;
  const v = evalVol(p.volume, f);
  if (v <= 0) return;
  RECS.push({k: kind + id, src: fsKey(p.src), f: ABS, m, v, r: rate, loop: !!p.loop, s0});
};

export const Audio: React.FC<MediaProps> = (p) => {
  useRecord(p, 'a');
  return null;
};
export const Html5Audio = Audio;

export const OffthreadVideo: React.FC<MediaProps> = (p) => {
  useRecord(p, 'v');
  const {m} = useMediaTime(p);
  const ref = useRef<HTMLImageElement>(null);
  const end = p.trimAfter ?? p.endAt;
  const fps = HF.fps || 30;
  const url = HF.mode === 'audio' ? undefined
    : `${HF.fs}/f?s=${encodeURIComponent(fsKey(p.src))}&t=${(Math.max(0, m) / fps).toFixed(5)}${p.transparent ? '&a=1' : ''}`;
  useImgWait(ref, url, 'video');
  if (HF.mode === 'audio' || (end !== undefined && m >= end)) return null;
  const {src, startFrom, trimBefore, endAt, trimAfter, playbackRate, muted, volume, loop, transparent, toneMapped, onError, pauseWhenBuffering,
    acceptableTimeShiftInSeconds, delayRenderTimeoutInMilliseconds, delayRenderRetries, imageFormat, toneFrequency, allowAmplificationDuringRender,
    onVideoFrame, showInTimeline, name, crossOrigin, audioStreamIndex, ...rest} = p;
  return <img ref={ref} src={url} {...rest} />;
};
export const Video = OffthreadVideo;
export const Html5Video = OffthreadVideo;

/* ---------------- đăng ký khung dựng ---------------- */
type CompDef = {id: string; component: React.ComponentType<any>; width: number; height: number; fps: number; durationInFrames: number;
  defaultProps?: any; calculateMetadata?: (a: any) => any};
const REG: CompDef[] = [];
export const Composition: React.FC<CompDef> = (p) => { if (!REG.find((x) => x.id === p.id)) REG.push(p); return null; };
export const Still: React.FC<any> = (p) => <Composition fps={30} durationInFrames={1} {...p} />;
export const Folder: React.FC<{children?: React.ReactNode}> = ({children}) => <>{children}</>;

let BOOT: Promise<any> | null = null;
let RENDER: ((f: number) => void) | null = null;
let N = 1;
const settle = async () => {
  // chờ ảnh / video / font / bản đồ / 3D; font chỉ tải khi có chữ dùng tới -> đọc bố cục rồi chờ document.fonts
  for (let k = 0; k < 3; k++) {
    await Promise.resolve();
    await idle();
    void document.body.offsetHeight;
    if (document.fonts && document.fonts.status !== 'loaded') await document.fonts.ready;
    await new Promise((r) => setTimeout(r, 0));
    if (!PENDING.size) break;
  }
};
const seekTo = async (frame: number) => {
  await BOOT;
  ABS = Math.max(0, Math.min(N - 1, frame));
  flushSync(() => RENDER!(ABS));
  await settle();
};

export const registerRoot = (RootC: React.ComponentType) => {
  BOOT = (async () => {
    const tmp = document.createElement('div');
    const r0 = createRoot(tmp);
    flushSync(() => r0.render(<RootC />));
    r0.unmount();
    const c = REG.find((x) => x.id === HF.comp);
    if (!c) throw new Error('Không có khung dựng: ' + HF.comp + ' (có: ' + REG.map((x) => x.id).join(', ') + ')');
    let props = {...(c.defaultProps || {}), ...(HF.props || {})};
    const meta = {width: c.width, height: c.height, fps: c.fps, durationInFrames: c.durationInFrames};
    if (c.calculateMetadata) {
      const m = await c.calculateMetadata({props, defaultProps: c.defaultProps, compositionId: c.id, abortSignal: new AbortController().signal});
      if (m) {
        for (const k of ['width', 'height', 'fps', 'durationInFrames'] as const) if (m[k]) (meta as any)[k] = m[k];
        if (m.props) props = m.props;
      }
    }
    N = meta.durationInFrames;
    const cfg: VideoConfig = {id: c.id, ...meta, defaultProps: c.defaultProps, props};
    const stage = document.getElementById('stage')!;
    stage.style.width = meta.width + 'px';
    stage.style.height = meta.height + 'px';
    const root = createRoot(stage);
    const Comp = c.component;
    RENDER = (f: number) => root.render(
      <CfgCtx.Provider value={cfg}>
        <TlCtx.Provider value={{frame: f, dur: meta.durationInFrames}}>
          <Comp {...props} />
        </TlCtx.Provider>
      </CfgCtx.Provider>,
    );
    W_.__hfMeta = meta;
    if (HF.mode === 'audio') { // chạy cả dòng thời gian, ghi tiếng từng khung
      const out: Rec[] = [];
      for (let f = 0; f < N; f++) {
        RECS = [];
        ABS = f;
        flushSync(() => RENDER!(f));
        for (const x of RECS) out.push(x);
      }
      W_.__AUDIO = {fps: meta.fps, n: N, recs: out};
      document.title = 'AUDIO_DONE';
      return meta;
    }
    ABS = 0;
    flushSync(() => RENDER!(0));
    await settle();
    return meta;
  })();
  BOOT.catch((e) => { console.error('[hf] lỗi khởi động', e); W_.__hfError = String(e && e.stack || e); document.title = 'HF_ERROR'; });
  W_.__hf = W_.__hf || {};
  W_.__hf.buildReady = W_.__hf.buildReady || {};
  W_.__hf.buildReady.remotion = BOOT;
  W_.__hfSeek = seekTo;
  W_.__hfPending = () => [...PENDING.values()].map((p) => p.label);
  window.addEventListener('hf-seek', (e: any) => {
    const fps = HF.fps || 30;
    e.detail.waitUntil(seekTo(Math.floor(e.detail.time * fps + 1e-4))); // HyperFrames có thể tua tới giữa khung (+0,5)
  });
};
