import React, {useEffect, useState} from 'react';
import {
  AbsoluteFill,
  Audio,
  Freeze,
  OffthreadVideo,
  Sequence,
  continueRender,
  delayRender,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import * as Icons from 'lucide-react';
import {BRoll, brollArea, Pip, DayBadge, Captions, mediaSrc, RateCtx, MaskCtx, maskCss, ViewCtx, viewOf} from './Media';
import {FONTS} from './fonts';
import {S, Style, TextStyle, animStyle, headFont} from './style';
import {NEW_LOOKS, Sticker, StyledText, StyleIcon} from './Styled';
import {skinOf} from './style';
import {FrameOverlay, Orn, skinDef} from './skins';
import {InkScape} from './Ink';
import {Bubble, Chart, Counter, Note, Phrase, PresenterBg, Spark, Stamp, Tabs, Tiles, presenterAt, presenterWrap} from './Graphics2';
import {MapBlock} from './MapBlock';
import {Orbit} from './Orbit';
import {Object3D, Photo3D, Screen3D, Text3DPro, handAt} from './Three3D';
import {MapTour} from './MapTour';
import {BrandLayer, BrandMark} from './Brand';
import {FR, fy, DEFAULT_Y} from './frame';
import {Bars, BeatCtx, BeatFrames, BeatStrips, Solid} from './Beat';
import {Card3D, OVERLAY_BLEND, Overlay, Scene, Shape, Text3D, trackAt} from './AE';

/* ===== Kiểu dữ liệu của "kịch bản dựng" (plan.json) ===== */
// sfx: tên hiệu ứng trong public/sfx (pop, tick, ding, whoosh) hoặc đường dẫn file âm thanh; sfxVolume: âm lượng riêng
// behind: true = nằm SAU người (cần tách người khỏi nền, render.py tự làm)
// --- chung cho mọi khối hình (trình edit kéo/thả/căn chỉnh trên khung hình) ---
// dx, dy: dời (px trên khung 1080x1920) · sc: phóng to/thu nhỏ (1 = giữ) · rot: xoay (độ) · org: tâm phóng/xoay [x, y] (px)
// fxIn / fxOut: hiệu ứng vào / ra chung (pop, fade, up, down, left, right, blur, zoomOut, wipe, spin, drop, flip / fade, pop, up,
//   down, left, right, blur, zoom, spin, wipe) — chữ kiểu thường & nhãn dán dùng anim/out riêng; inDur / outDur: thời gian vào / ra (giây)
// group: mã nhóm (các khối cùng mã di chuyển cùng nhau) · rate: tốc độ phát video trám / khung hình (0.25–4)
// kf: KHUNG HÌNH CHÍNH [{t: giây tính từ lúc khối hiện, dx?, dy?, sc?, rot?, op?(0–1)}] — giữa 2 điểm chạy mượt (ease)
export type Kf = {t: number; dx?: number; dy?: number; sc?: number; rot?: number; op?: number};
// follow: 'face' = khối chạy theo mặt người (dữ liệu _work/mat.json -> props.faces)
type Xf = {follow?: string; kf?: Kf[]; op?: number; dx?: number; dy?: number; sc?: number; rot?: number; org?: [number, number]; fxIn?: string; fxOut?: string; inDur?: number; outDur?: number; group?: string; rate?: number; _i?: number};
// sfxOff: dời tiếng hiệu ứng so với lúc khối hiện (giây, âm = kêu trước)
// z: LỚP (số lớn = nằm trên). z < 0 = sau người (cần tách nền). Không ghi: sau người -10, ảnh trám 10, phụ đề 20 (capZ), còn lại 30
// hidden: ẩn (con mắt ở đầu lớp trên timeline) — không hiện, không kêu
type Base = Xf & {hidden?: boolean; start: number; end: number; sfx?: string; sfxVolume?: number; sfxOff?: number; y?: number; behind?: boolean; z?: number};
export type El =
  | (Base & {type: 'priceHook'; price: string; sub: string})
  | (Base & {type: 'chip'; icon: string; text: string})
  | (Base & {type: 'bigQuestion'; text: string})
  | (Base & {type: 'checklist'; title: string; items: {text: string; at: number}[]})
  | (Base & {type: 'rangeCard'; label: string; value: string; note?: string})
  | (Base & {type: 'cta'; icon: string; text: string})
  // transition (kiểu vào): zoom | slide | up | fade | cut | whip | circle; exit: fade | cut | slide | zoom (mặc định theo style.broll)
  | (Base & {type: 'broll'; src: string; from?: number; label?: string; transition?: string; exit?: string; volume?: number})
  // look: card3d (thẻ 3D xanh) | clean (bo góc, viền trắng) | round (tròn) | polaroid
  | (Base & {type: 'pip'; src: string; from?: number; label?: string; volume?: number; look?: string})
  | (Base & {type: 'dayBadge'; day: number; total: number})
  // dựng theo nhịp: Khung nhịp (khung bo góc bật theo nhịp -> thu thành ô -> bung) / Dải chéo (dải xiên lộ cảnh mới theo nhịp) — Beat.tsx
  | (Base & {type: 'beatFrames'; src?: string; srcs?: string[]; from?: number; froms?: number[]; count?: number; layout?: string; gap?: number; radius?: number; collapse?: boolean; exit?: string; bg?: string; every?: number})
  | (Base & {type: 'solid'; color?: string; fadeIn?: number; fadeOut?: number; opacity?: number})
  | (Base & {type: 'bars'; size?: number; color?: string})
  | (Base & {type: 'beatStrips'; src: string; from?: number; count?: number; angle?: number; line?: string; lineW?: number; every?: number})
  // khối editorial (Graphics2.tsx) + chế độ người nói
  | (Base & {type: 'phrase' | 'counter' | 'stamp' | 'tabs' | 'tiles' | 'note' | 'bubble' | 'spark' | 'presenter' | 'chart'; [k: string]: any})
  // chữ tự do: look cũ (plain/box/gold/tag) + look mới (outline/clean/shadow/solid/highlight/neon); mọi thông số
  // không ghi thì lấy theo plan.style.text (phong cách). hl: từ khóa tô màu; anim/out: kiểu hiện/ẩn
  | (Base & TextStyle & {type: 'text'; text: string; x?: number; width?: number; align?: 'center' | 'left' | 'right'; font?: string; italic?: boolean; rotate?: number; hl?: string[] | string})
  // nhãn dán: icon lucide (ArrowDown, Flame, Heart, Star...) hoặc emoji; loop: bob | pulse | spin | shake | none
  | (Base & {type: 'sticker'; icon: string; size?: number; color?: string; x?: number; anim?: string; out?: string; loop?: string; rotate?: number})
  | (Base & {type: 'audio'; src: string; from?: number; volume?: number})
  // tiếng hiệu ứng đứng riêng (không gắn khối hình nào): kêu lúc start
  | (Base & {type: 'sfx'})
  // HIỆU ỨNG HÌNH áp lên cả khung (như track Hiệu ứng CapCut): shake | glitch | rgb | flash | vhs | blur | beat | bw ; amount 0–100
  | (Base & {type: 'fx'; style: string; amount?: number})
  // BẢN ĐỒ: đường đi từ dự án tới tiện ích (xem MapBlock.tsx)
  // VÒNG QUAY ảnh/video quanh người (Orbit.tsx) · BẢN ĐỒ KỂ CHUYỆN vệ tinh: vùng tô màu, viền phát sáng, nhãn, ảnh tròn (MapTour.tsx)
  | (Base & {type: 'orbit'; items?: any[]; [k: string]: any})
  | (Base & {type: 'mapTour'; regions?: any[]; [k: string]: any})
  | (Base & {type: 'map'; places?: any[]; paths?: any[]; lineMode?: string; style?: string; theme?: string; hideLabels?: boolean; camera?: string; frame?: string; color?: string})
  // zoom video chính để nhấn mạnh: punch (giật vào) | in (từ từ vào) | out (từ từ ra) | pulse (vào rồi ra) | shake (rung)
  // | smooth (vào êm – giữ – ra êm, cho video chill/thơ/podcast); style.effects.zoomEase = 'smooth' ép mọi zoom thành êm
  // scale: độ phóng (1.2 = 120%); x, y: điểm zoom tính theo tỉ lệ khung (0–1), mặc định giữa-trên (0.5, 0.4)
  // KHỐI KIỂU AE (AE.tsx): overlay (lớp hiệu ứng hoà trộn: kind lightleak|flare|rays|bokeh|particles|sparkle|dust|filmburn|snow|confetti|grain,
  // amount 0–100, color, blend) · shape (vẽ ra: kind arrow|line|circle|underline|box|bracket|check|cross|callout; x,y,x2,y2,w,h, color, width, draw giây)
  // · text3d (chữ khối 3D: text, size, depth, face solid|gold|chrome, motion swing|spin|rise|tilt|float|zoom) · card3d (ảnh/video mặt phẳng 3D:
  // src, w, ratio, move orbit|flyIn|tiltIn|float|flip|dolly|swing) · scene (cảnh dựng sẵn: kind intro|pricetable|compare|amenities|stats|outro)
  | (Base & {type: 'overlay' | 'shape' | 'text3d' | 'card3d' | 'scene'; [k: string]: any})
  // 3D THẬT (Three3D.tsx, Three.js): text3dPro (chữ khối kim loại, bóng đổ, vệt sáng) · photo3d (ảnh bay vòng quanh người, phóng ảnh ra
  // trước mặt: hero) · object3d (ghim / nhà / bảng giá / mô hình .glb đặt trên mặt đất của cảnh)
  | (Base & {type: 'text3dPro' | 'photo3d' | 'object3d' | 'screen3d'; [k: string]: any})
  | (Base & {type: 'zoom'; style?: 'punch' | 'in' | 'out' | 'pulse' | 'shake' | 'smooth'; scale?: number; x?: number; y?: number});

/** Chỉnh màu & ánh sáng (100 = giữ nguyên). all: áp cả cho ảnh/video trám */
// hue: xoay tông màu (độ, -30..30) · sepia: ngả cổ điển 0-100 · fade: nâng vùng tối kiểu phim (matte) 0-100 · tint: phủ màu (hex) + tintAmount 0-100
export type Color = {brightness?: number; contrast?: number; saturation?: number; warmth?: number; vignette?: number; hue?: number; sepia?: number; fade?: number; tint?: string; tintAmount?: number; all?: boolean};
// làm đẹp người (render.py xử lý trước bằng scripts/beauty.py)
export type Beauty = {smooth?: number; bright?: number; lip?: number; lipColor?: string; blush?: number; blushColor?: string; sharpen?: number};

export type Theme = {
  light: string; // xanh sáng
  mid: string; // xanh chính (màu logo)
  dark: string; // xanh đậm
  gold1: string;
  gold2: string;
};

export type PlanProps = {
  videoSrc: string;
  durationSec: number;
  /** video xuất dài hơn video chính (voice / khối kéo quá cuối): từ giây tailFrom đứng hình ở khung cuối (giây tailSrc của
   *  video gốc, khung của đoạn bắt đầu ở tailA) */
  tailFrom?: number; tailSrc?: number; tailA?: number; tailAt?: number; // tailAt: bắt đầu đứng hình sớm hơn (cuối video có khung đen)
  theme: Theme;
  cuts: number[]; // mốc chuyển cảnh: chớp sáng + zoom (không âm thanh)
  elements: El[];
  sfxVolume: number;
  captions?: {w: string; start: number; end: number}[][]; // phụ đề tự động (render.py tạo)
  captionTop?: number;
  captionsFrom?: number;
  captionSize?: number;
  captionUpper?: boolean;
  segments?: [number, number][]; // các đoạn GIỮ LẠI của video chính (giây trong video), nối liền nhau
  transition?: JoinFx; // kiểu chuyển mặc định ở điểm nối (auto: cùng lần quay -> zoom cut, khác -> mờ chồng)
  joinFx?: Record<string, string>; // kiểu chuyển riêng từng điểm nối, khoá "b>a" (giây nguồn)
  clipBounds?: Clip[]; // vị trí từng clip/lần quay trong video chính (để biết điểm nối có cùng lần quay không)
  cutFx?: 'none' | 'flash' | 'bump' | 'flash+bump'; // hiệu ứng ở điểm đổi cảnh tự nhiên (mặc định không)
  videoVolume?: number; // âm lượng tiếng gốc (1 = giữ nguyên, 0 = tắt)
  music?: {src: string; volume?: number; from?: number}; // nhạc nền, tự lặp, nhỏ dần ở đầu/cuối
  color?: Color;
  style?: Style; // phong cách: font, kiểu chữ, phụ đề, kiểu chèn minh họa (xem style.ts)
  // lớp NGƯỜI đã tách nền (render.py tạo): đè lên các element "behind": true. i = đoạn số, from/len = khung trên video xuất
  person?: {i: number; from: number; len: number; ext?: number; off?: number; src: string}[];
  capZ?: number; // lớp của phụ đề (mặc định 20)
  brandMark?: BrandMark | false; // logo + SĐT của người dùng (scripts/thuong_hieu.py), nằm trên cùng
  joinSfx?: boolean | string; // âm thanh ở điểm nối (xem JOIN_SFX)
  joinSfxMap?: Record<string, string>; // âm riêng từng điểm nối, khoá "b>a" như joinFx; '' = tắt ở điểm đó
  // tốc độ: speed = cả video (1 = giữ), segSpeed = riêng từng đoạn, khoá = giây bắt đầu đoạn trong video gốc ("12.34").
  // Trình phát xem trước đổi tốc độ phát; render.py áp lên bản xuất cuối (chữ/hiệu ứng trong đoạn cũng nhanh/chậm theo)
  speed?: number;
  segSpeed?: Record<string, number>;
  segCurve?: Record<string, string>;
  // che mờ biển số / mã QR / vùng tự chọn (scripts/che_mo.py): vệt [giây video gốc, x, y, w, h] (px khung video chính)
  blurs?: Blur[];
  // tiếng gốc từng đoạn: keep | mute (không ghi = tự động: tắt khi chậm < 0,75× hoặc nhanh > 2,5×); segSmooth: mci | blend | off (lúc xuất)
  segAudio?: Record<string, string>;
  // tiếng gốc từng đoạn (khoá = giây bắt đầu đoạn): âm lượng (1 = giữ), vuốt to dần / nhỏ dần (giây)
  segVol?: Record<string, number>;
  segFadeIn?: Record<string, number>;
  segFadeOut?: Record<string, number>;
  segSmooth?: Record<string, string>;
  // lật / cắt khung video chính từng đoạn, khoá = giây bắt đầu đoạn (như segSpeed): {flip: h|v|hv, s: phóng ≥1, x, y: tâm 0–1}
  segXf?: Record<string, MXf>;
  // khung hình video chính cho CẢ video (segXf của từng đoạn ghi đè từng thông số): kích thước, dời, xoay, cắt mép, bo góc, lật;
  // bg = nền lộ ra khi thu nhỏ / dời: black | blur (mờ từ chính video) | mã màu
  mainXf?: MXf & {bg?: string};
  // cỡ cảnh tự động (toàn / trung / cận): đổi đột ngột ở mốc t (giây video GỐC), phóng s quanh tâm (x, y) — scripts/canh_co.py
  shots?: {t: number; s: number; x?: number; y?: number; k?: string}[];
  shotFade?: number; // giây hoà trộn khi đổi cỡ cảnh (mặc định 0.5; 0 = cắt thẳng)
  faces?: {step: number; faces: number[][]}; // vùng mặt theo thời gian video gốc (scripts/mat.py) — cho khối bám mặt
  beats?: number[]; // nhịp nhạc nền (giây, scripts/nhip.py) — hiệu ứng 'beat' nảy theo nhịp
  // DỰNG THEO NHỊP: các đoạn [from, to] (giây video xuất) dựng theo nhạc — trong đoạn này không phát tiếng hiệu ứng (nhạc đã đủ nhịp)
  beatEdit?: {on?: boolean; from?: number; to?: number; keepSfx?: boolean};
};

/** lớp của khối (xem Base.z) */
export const zOf = (e: any): number => (typeof e?.z === 'number' ? e.z : e?.behind ? -10 : e?.type === 'broll' || e?.type === 'beatFrames' || e?.type === 'beatStrips' || ((e?.type === 'map' || e?.type === 'mapTour') && e.frame !== 'card') ? 10 : e?.type === 'overlay' ? 18 : 30);
export const isBehind = (e: any) => zOf(e) < 0;
export const CAP_Z = 20;

/** khối này dùng hiệu ứng hiện/ẩn riêng (anim/out) hay hiệu ứng chung (fxIn/fxOut) */
export const nativeAnim = (e: any, style?: Style) => {
  if (e.type === 'sticker') return true;
  if (e.type !== 'text') return false;
  const look = e.look || style?.text?.look || 'plain';
  return look === 'plain' || NEW_LOOKS.includes(look);
};

export const colorFilter = (c?: Color) => {
  if (!c) return undefined;
  const b = (c.brightness ?? 100) / 100, k = (c.contrast ?? 100) / 100, s = (c.saturation ?? 100) / 100;
  const h = c.hue ?? 0, sp = (c.sepia ?? 0) / 100;
  if (b === 1 && k === 1 && s === 1 && !h && !sp) return undefined;
  return `brightness(${b}) contrast(${k}) saturate(${s})${sp ? ` sepia(${sp})` : ''}${h ? ` hue-rotate(${h}deg)` : ''}`;
};

const ColorOverlay: React.FC<{c?: Color}> = ({c}) => {
  if (!c) return null;
  const w = c.warmth ?? 0, v = c.vignette ?? 0, fd = c.fade ?? 0, ta = c.tintAmount ?? 0;
  return (
    <>
      {fd > 0 && <AbsoluteFill style={{background: 'rgb(70,70,78)', mixBlendMode: 'lighten', opacity: Math.min(1, fd / 100) * 0.9}} />}
      {c.tint && ta > 0 && <AbsoluteFill style={{background: c.tint, mixBlendMode: 'color', opacity: Math.min(1, ta / 100) * 0.6}} />}
      {w !== 0 && (
        <AbsoluteFill style={{background: w > 0 ? 'rgb(255,150,40)' : 'rgb(40,130,255)', mixBlendMode: 'soft-light', opacity: Math.min(1, Math.abs(w) / 100) * 0.7}} />
      )}
      {v > 0 && (
        <AbsoluteFill style={{background: `radial-gradient(ellipse at center, rgba(0,0,0,0) 45%, rgba(0,0,0,${Math.min(1, v / 100) * 0.85}) 100%)`}} />
      )}
    </>
  );
};

/* ===== Điểm nối giữa các đoạn: chọn kiểu chuyển ===== */
// cut: cắt thẳng | zoom: zoom cut (đổi cỡ khung, che cú nhảy khi cùng 1 lần quay) | fade: mờ chồng hình + tiếng | flash: chớp sáng
// whip (lia nhanh) | slide (đẩy ngang) | up (đẩy lên) | zoomin (zoom xuyên) | blur (nhòe chồng): 2 cảnh chồng nhau 0,2s như fade
export type JoinFx = 'auto' | 'cut' | 'zoom' | 'fade' | 'flash' | 'whip' | 'slide' | 'up' | 'zoomin' | 'blur';
export const OVERLAP = new Set(['fade', 'whip', 'slide', 'up', 'zoomin', 'blur']);
const easeIO = (x: number) => (x <= 0 ? 0 : x >= 1 ? 1 : x < 0.5 ? 2 * x * x : 1 - Math.pow(-2 * x + 2, 2) / 2);
/** style của cảnh lúc RA (mode out, k: 0->1) hoặc VÀO (mode in, k: 0->1) ở điểm nối kiểu chồng */
export const joinStyle = (type: string | null | undefined, mode: 'in' | 'out', k0: number): React.CSSProperties => {
  if (!type || !OVERLAP.has(type)) return {};
  const k = easeIO(Math.max(0, Math.min(1, k0)));
  const r = 1 - k;
  if (mode === 'out') {
    switch (type) {
      case 'fade': return {opacity: 1 - k0};
      case 'blur': return {opacity: 1 - k0, filter: `blur(${k * 22}px)`};
      case 'whip': return {transform: `translateX(${-k * FR.w}px)`, filter: `blur(${Math.sin(Math.PI * k) * 30}px)`};
      case 'slide': return {transform: `translateX(${-k * FR.w}px)`};
      case 'up': return {transform: `translateY(${-k * FR.h}px)`};
      case 'zoomin': return {transform: `scale(${1 + k * 0.7})`, opacity: 1 - k0, filter: `blur(${k * 14}px)`};
    }
  } else {
    switch (type) {
      case 'blur': return {filter: r > 0.01 ? `blur(${r * 22}px)` : undefined};
      case 'whip': return {transform: `translateX(${r * FR.w}px)`, filter: r > 0.01 ? `blur(${Math.sin(Math.PI * r) * 30}px)` : undefined};
      case 'slide': return {transform: `translateX(${r * FR.w}px)`};
      case 'up': return {transform: `translateY(${r * FR.h}px)`};
      case 'zoomin': return {transform: `scale(${1.3 - 0.3 * k})`, filter: r > 0.01 ? `blur(${r * 12}px)` : undefined};
    }
  }
  return {};
};
export type Clip = {file?: string; start: number; end: number};
export const joinKey = (b: number, a: number) => `${Math.round(b * 100) / 100}>${Math.round(a * 100) / 100}`;
const clipOf = (t: number, clips?: Clip[]) => (clips || []).findIndex((c) => t >= c.start - 0.05 && t < c.end + 0.05);
/** kiểu chuyển thực tế của điểm nối giữa đoạn i và i+1 */
export const joinType = (segs: [number, number][], i: number, def: JoinFx = 'auto', over?: Record<string, string>, clips?: Clip[]): Exclude<JoinFx, 'auto'> => {
  const [, b] = segs[i], [a2] = segs[i + 1];
  let o = over?.[joinKey(b, a2)] as JoinFx | undefined;
  if (!o && over) {
    // khoá viết kiểu khác ("4.0>6.0", "4.00>6") -> so theo số
    for (const [k, v] of Object.entries(over)) {
      const [kb, ka] = k.split('>').map(Number);
      if (Math.abs(kb - b) < 0.011 && Math.abs(ka - a2) < 0.011) {
        o = v as JoinFx;
        break;
      }
    }
  }
  const want = o && o !== 'auto' ? o : def;
  if (Math.abs(a2 - b) < 0.05) return 'cut'; // liền mạch: không cần hiệu ứng
  if (want !== 'auto') return want;
  const c1 = clipOf(b, clips), c2 = clipOf(a2, clips);
  // phong cách êm (zoomEase smooth): không dùng zoom cut giật khung, luôn mờ chồng
  if ((S.style as any).effects?.zoomEase === 'smooth') return 'fade';
  return c1 >= 0 && c1 === c2 && Math.abs(a2 - b) < 25 ? 'zoom' : 'fade';
};
const TR = 6; // khung hình mờ chồng (0,2s)
const AF = 2; // khung hình vuốt tiếng ở điểm cắt (≈0,07s) — hết tiếng "bụp"

/* ---------- CHE MỜ (biển số, mã QR, mã vạch, vùng tự chọn) — bám theo vệt, nằm cùng lớp với video nên đi theo zoom / cắt đoạn ---------- */
export type Blur = {id?: string; kind?: string; mode?: 'blur' | 'den' | 'mosaic' | 'icon'; off?: boolean; track: number[][]; strength?: number;
  grow?: number; round?: number; color?: string; icon?: string};  // grow: phóng hộp che quanh tâm · round: bo góc (0–0.5 cạnh ngắn) · icon: emoji / tên icon
export const BLURS: {v: Blur[]} = {v: []};
/** hộp che lúc giây t (video gốc): nội suy giữa 2 lần thấy; khoảng trống > 1,2 giây = vật đã khuất (vùng tự dò; vùng tự vẽ "tay" nối liền giữa các mốc) */
export const blurBoxAt = (b: Blur, t: number): number[] | null => {
  const tr = b.track || [];
  if (!tr.length || b.off) return null;
  const tol = 0.2;
  if (t < tr[0][0] - tol || t > tr[tr.length - 1][0] + tol) return null;
  if (t <= tr[0][0]) return tr[0].slice(1);
  for (let i = 1; i < tr.length; i++) {
    if (t <= tr[i][0]) {
      const a = tr[i - 1], c = tr[i];
      if (b.kind !== 'tay' && c[0] - a[0] > 1.2) return t - a[0] < tol ? a.slice(1) : c[0] - t < tol ? c.slice(1) : null;
      const k = (t - a[0]) / Math.max(1e-6, c[0] - a[0]);
      return [1, 2, 3, 4].map((j) => a[j] + (c[j] - a[j]) * k);
    }
  }
  return tr[tr.length - 1].slice(1);
};
const BlurBoxes: React.FC<{url: string; a: number; style: React.CSSProperties; scale: number}> = ({url, a, style, scale}) => {
  const f = useCurrentFrame();
  const t = a + f / FPS;
  const act = BLURS.v.map((b) => ({b, r: blurBoxAt(b, t)})).filter((x) => x.r);
  if (!act.length) return null;
  const vs: React.CSSProperties = {...style, transform: undefined, filter: undefined};
  return (
    <AbsoluteFill style={{transform: scale !== 1 ? `scale(${scale})` : undefined, transformOrigin: '50% 38%', pointerEvents: 'none'}}>
      {act.map(({b, r}, k) => {
        const [x0, y0, w0, h0] = r as number[];
        const g = b.grow && b.grow > 0 ? b.grow : 1;
        const w = w0 * g, h = h0 * g, x = x0 - (w - w0) / 2, y = y0 - (h - h0) / 2;
        const rad = Math.min(w, h) * (b.round != null ? Math.max(0, Math.min(0.5, b.round)) : 0.22);
        if (b.mode === 'den')
          return <div key={k} style={{position: 'absolute', left: x, top: y, width: w, height: h, borderRadius: rad, background: b.color || '#111'}} />;
        if (b.mode === 'icon') {
          // biểu tượng che: nền mờ + icon / emoji ở giữa (vd 🔒, 😎, lucide "Lock")
          const ic = b.icon || '🔒';
          const sz = Math.min(w, h) * 0.78;
          const Comp = /^[A-Z][A-Za-z0-9]+$/.test(ic) ? (Icons as any)[ic] : null;
          const amt = Math.max(14, Math.min(60, (b.strength ?? 1) * Math.min(w, h) * 0.4));
          const clip = `inset(${y}px ${FR.w - x - w}px ${FR.h - y - h}px ${x}px round ${rad}px)`;
          return (
            <React.Fragment key={k}>
              <AbsoluteFill style={{clipPath: clip}}>
                <OffthreadVideo src={url} startFrom={Math.round(a * FPS)} muted style={{...vs, filter: `${style.filter || ''} blur(${amt}px)`, transform: 'scale(1.06)'}} />
                {b.color && <AbsoluteFill style={{background: b.color}} />}
              </AbsoluteFill>
              <div style={{position: 'absolute', left: x, top: y, width: w, height: h, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: sz, lineHeight: 1, filter: 'drop-shadow(0 3px 6px rgba(0,0,0,.45))'}}>
                {Comp ? <Comp size={sz} color="#fff" strokeWidth={2.4} /> : ic}
              </div>
            </React.Fragment>
          );
        }
        const amt = Math.max(14, Math.min(60, (b.strength ?? 1) * Math.min(w, h) * 0.4));
        const clip = `inset(${y}px ${FR.w - x - w}px ${FR.h - y - h}px ${x}px round ${rad}px)`;
        if (b.mode === 'mosaic') {
          // ô vuông (mosaic): vẽ video nhỏ đi `cell` lần rồi phóng lại, giữ điểm ảnh vuông
          const cell = Math.max(10, Math.round(Math.min(w, h) / 6));
          return (
            <AbsoluteFill key={k} style={{clipPath: clip}}>
              <div style={{position: 'absolute', left: 0, top: 0, width: FR.w / cell, height: FR.h / cell, transform: `scale(${cell})`, transformOrigin: '0 0', imageRendering: 'pixelated'}}>
                <OffthreadVideo src={url} startFrom={Math.round(a * FPS)} muted style={{...vs, width: '100%', height: '100%', imageRendering: 'pixelated'}} />
              </div>
            </AbsoluteFill>
          );
        }
        return (
          <AbsoluteFill key={k} style={{clipPath: clip}}>
            <OffthreadVideo src={url} startFrom={Math.round(a * FPS)} muted style={{...vs, filter: `${style.filter || ''} blur(${amt}px)`, transform: 'scale(1.06)'}} />
            <AbsoluteFill style={{background: 'rgba(120,120,120,.18)'}} />
          </AbsoluteFill>
        );
      })}
    </AbsoluteFill>
  );
};

const SegClip: React.FC<{url: string; a: number; len: number; ext: number; fadeInA: number; fadeOutA: number; volume: number; scale: number; style: React.CSSProperties; outFx?: string | null; inFx?: string | null; blurBg?: boolean; aud?: SegAud}> = ({
  url, a, len, ext, fadeInA, fadeOutA, volume, scale, style, outFx, inFx, blurBg, aud,
}) => {
  const f = useCurrentFrame();
  const total = len + ext;
  const tr = ext > 0 && f >= len ? joinStyle(outFx, 'out', (f - len) / ext) : inFx && f < TR ? joinStyle(inFx, 'in', f / TR) : {};
  const vol = (fr: number) => {
    let k = 1;
    if (fadeInA > 0) k *= Math.min(1, (fr + 1) / fadeInA);
    if (fadeOutA > 0) k *= Math.min(1, Math.max(0, (total - fr) / fadeOutA));
    if (aud) k *= aud.v * fadeK(fr, len, aud.fi, aud.fo);
    return volume * k;
  };
  return (
    <AbsoluteFill style={{overflow: 'hidden', ...tr}}>
      {blurBg && <AbsoluteFill><OffthreadVideo src={url} startFrom={Math.round(a * FPS)} muted style={{...style, objectFit: 'cover', filter: `${style.filter || ''} blur(38px) brightness(0.75)`, transform: 'scale(1.15)'}} /></AbsoluteFill>}
      <OffthreadVideo
        src={url}
        startFrom={Math.round(a * FPS)}
        volume={vol}
        muted={volume <= 0}
        style={{...style, transform: scale !== 1 ? `scale(${scale})` : undefined, transformOrigin: '50% 38%'}}
      />
      {BLURS.v.length > 0 && <BlurBoxes url={url} a={a} style={style} scale={scale} />}
    </AbsoluteFill>
  );
};

/** cỡ khung từng đoạn (zoom cut: đổi 100% <-> 108% ở điểm nối cùng lần quay) */
export const segScales = (segments: [number, number][] | undefined, fx: JoinFx = 'auto', joinFx?: Record<string, string>, clips?: Clip[]) => {
  const scales: number[] = [];
  if (!segments) return scales;
  const types = segments.slice(0, -1).map((_, i) => joinType(segments, i, fx, joinFx, clips));
  segments.forEach((_, i) => scales.push(i && types[i - 1] === 'zoom' ? (scales[i - 1] === 1 ? 1.08 : 1) : 1));
  return scales;
};

/** Lớp người (nền trong suốt) đè lên trên các element đặt sau người — khớp từng khung với video chính */
const PersonLayer: React.FC<{p: PlanProps; filter?: string}> = ({p, filter}) => {
  const segs = p.segments;
  const scales = segScales(segs, p.transition, p.joinFx, p.clipBounds);
  const jt = (i: number) => (segs && i >= 0 && i < segs.length - 1 ? joinType(segs, i, p.transition || 'auto', p.joinFx, p.clipBounds) : null);
  const segStart = (i: number) => (segs ? Math.round(segs.slice(0, i).reduce((s, [a, b]) => s + b - a, 0) * FPS) : 0);
  // vẽ đoạn sau trước -> phần đuôi mờ dần của đoạn trước nằm trên (giống video chính)
  return (
    <>
      {[...(p.person || [])].reverse().map((x, k) => {
        const out = jt(x.i);
        const ext = x.ext && out && OVERLAP.has(out) ? Math.min(x.ext, TR) : 0;
        const inn = x.from === segStart(x.i) ? jt(x.i - 1) : null;
        return (
          <Sequence key={k} from={x.from} durationInFrames={Math.max(1, x.len + ext)} premountFor={FPS}>
            <AbsoluteFill style={segTf(p.segXf, segs ? segs[x.i][0] : 0)}>
            <PersonPiece src={x.src} off={x.off || 0} len={x.len} ext={ext} scale={scales[x.i] ?? 1} filter={filter} outFx={out} inFx={inn} />
            </AbsoluteFill>
          </Sequence>
        );
      })}
    </>
  );
};
const PersonPiece: React.FC<{src: string; off: number; len: number; ext: number; scale: number; filter?: string; outFx?: string | null; inFx?: string | null}> = ({src, off, len, ext, scale, filter, outFx, inFx}) => {
  const f = useCurrentFrame();
  const tr = ext > 0 && f >= len ? joinStyle(outFx, 'out', (f - len) / ext) : inFx && f < TR ? joinStyle(inFx, 'in', f / TR) : {};
  return (
    <AbsoluteFill style={{overflow: 'hidden', ...tr}}>
      <OffthreadVideo
        src={mediaSrc(src)}
        startFrom={off}
        transparent
        muted
        style={{width: '100%', height: '100%', objectFit: 'cover', filter, transform: scale !== 1 ? `scale(${scale})` : undefined, transformOrigin: '50% 38%'}}
      />
    </AbsoluteFill>
  );
};

/** Video chính: cả file, hoặc ghép các đoạn giữ lại (segments) — cắt không cần xuất lại file.
    Ở mỗi điểm nối: tự chọn zoom cut / mờ chồng / cắt thẳng, và luôn vuốt tiếng cho khỏi giật. */
const segOpt = (m: Record<string, any> | undefined, a: number) => (m ? Object.entries(m).find(([k]) => Math.abs(+k - a) < 0.006)?.[1] : undefined);
/** âm lượng + vuốt tiếng riêng của đoạn bắt đầu ở giây a: {v, fi, fo} (fi/fo tính bằng khung) */
export type SegAud = {v: number; fi: number; fo: number};
export const segAudOf = (p: {segVol?: Record<string, number>; segFadeIn?: Record<string, number>; segFadeOut?: Record<string, number>}, a: number): SegAud => ({
  v: +(segOpt(p.segVol, a) ?? 1),
  fi: Math.round(+(segOpt(p.segFadeIn, a) ?? 0) * FPS),
  fo: Math.round(+(segOpt(p.segFadeOut, a) ?? 0) * FPS),
});
/** hệ số vuốt to/nhỏ dần tại khung fr của 1 đoạn dài total khung */
export const fadeK = (fr: number, total: number, fi: number, fo: number) =>
  (fi > 0 ? Math.min(1, Math.max(0, (fr + 1) / fi)) : 1) * (fo > 0 ? Math.min(1, Math.max(0, (total - fr) / fo)) : 1);
/** tiếng gốc của đoạn bắt đầu ở giây a có bị tắt không (slow-motion / timelapse) — giống auto_mute() trong scripts/render.py */
export const segMuted = (p: {speed?: number; segSpeed?: Record<string, number>; segCurve?: Record<string, string>; segAudio?: Record<string, string>}, a: number) => {
  const au = segOpt(p.segAudio, a);
  if (au === 'mute') return true;
  if (au === 'keep') return false;
  if (segOpt(p.segCurve, a)) return false;
  const r = (+(p.speed || 1)) * (+(segOpt(p.segSpeed, a) || 1));
  return r < 0.75 || r > 2.5;
};
type Tail = {from: number; src: number; a: number};
/** đứng hình ở khung cuối của video chính trong phần kéo dài thêm */
const TailFreeze: React.FC<{url: string; tail: Tail; style: React.CSSProperties; tf?: React.CSSProperties}> = ({url, tail, style, tf}) => (
  <Sequence from={Math.round(tail.from * FPS)} premountFor={FPS}>
    <AbsoluteFill style={tf}>
      <Freeze frame={0}>
        {style.objectFit === 'contain' && <AbsoluteFill><OffthreadVideo src={url} startFrom={Math.max(0, Math.round(tail.src * FPS) - 5)} muted style={{...style, objectFit: 'cover', filter: `${style.filter || ''} blur(38px) brightness(0.75)`, transform: 'scale(1.15)'}} /></AbsoluteFill>}
        <OffthreadVideo src={url} startFrom={Math.max(0, Math.round(tail.src * FPS) - 5)} muted style={style} />
      </Freeze>
    </AbsoluteFill>
  </Sequence>
);
const tailOf = (p: PlanProps): Tail | undefined => (p.tailFrom != null && p.tailFrom < p.durationSec - 0.02 ? {from: p.tailAt ?? p.tailFrom, src: p.tailSrc ?? p.tailFrom, a: p.tailA ?? 0} : undefined);

const MainVideo: React.FC<{src: string; segments?: [number, number][]; volume: number; filter?: string; fx?: JoinFx; joinFx?: Record<string, string>; clips?: Clip[]; segXf?: PlanProps['segXf']; noXf?: boolean; keepBand?: number[]; tail?: Tail; muteAt?: (a: number) => boolean; fit?: string; audAt?: (a: number) => SegAud}> = ({
  src, segments, volume: vol0, filter, fx = 'auto', joinFx, clips, segXf, noXf, keepBand, tail, muteAt, fit, audAt,
}) => {
  const volume = !segments?.length && muteAt?.(0) ? 0 : vol0;
  // keepBand [y0, y1, feather] (px): giữ nguyên dải này của video gốc (vd phụ đề cháy sẵn) khi đoạn được phóng to (segXf)
  const kb = keepBand && keepBand.length >= 2 ? keepBand : null;
  const kbMask = kb ? (() => { const f = kb[2] ?? 80; const g = `linear-gradient(to bottom, transparent ${kb[0] - f}px, black ${kb[0]}px, black ${kb[1]}px, transparent ${kb[1] + f}px)`; return {WebkitMaskImage: g, maskImage: g} as React.CSSProperties; })() : null;
  const tf = (a: number) => (noXf ? undefined : segTf(segXf, a));
  // fit: cover (cắt cho đầy khung — mặc định) | blur (giữ trọn hình, nền mờ phía sau — khung khác tỉ lệ video) | contain (viền đen)
  const blurBg = fit === 'blur';
  const style: React.CSSProperties = {width: '100%', height: '100%', objectFit: fit === 'blur' || fit === 'contain' ? 'contain' : 'cover', filter, ...(blurBg ? {position: 'absolute', inset: 0} : {})};
  const url = mediaSrc(src);
  const {durationInFrames: compLen} = useVideoConfig();
  const wa = audAt ? audAt(0) : null;
  const wholeVol = (fr: number) => (wa ? volume * wa.v * fadeK(fr, compLen, wa.fi, wa.fo) : volume);
  if (!segments || !segments.length)
    return tail ? (
      <>
        <Sequence durationInFrames={Math.max(1, Math.round(tail.from * FPS))}>
          <AbsoluteFill style={tf(0)}>
            <OffthreadVideo src={url} volume={wholeVol} muted={volume <= 0} style={style} />
            {BLURS.v.length > 0 && <BlurBoxes url={url} a={0} style={style} scale={1} />}
          </AbsoluteFill>
        </Sequence>
        <TailFreeze url={url} tail={tail} style={style} tf={tf(0)} />
      </>
    ) : (
      <AbsoluteFill style={tf(0)}>
        {blurBg && <AbsoluteFill><OffthreadVideo src={url} muted style={{...style, objectFit: 'cover', filter: `${filter || ''} blur(38px) brightness(0.75)`, transform: 'scale(1.15)'}} /></AbsoluteFill>}
        <OffthreadVideo src={url} volume={wholeVol} muted={volume <= 0} style={style} />
        {BLURS.v.length > 0 && <BlurBoxes url={url} a={0} style={style} scale={1} />}
      </AbsoluteFill>
    );
  const n = segments.length;
  const types = segments.slice(0, -1).map((_, i) => joinType(segments, i, fx, joinFx, clips));
  const scales = segScales(segments, fx, joinFx, clips);
  let acc = 0;
  const items = segments.map(([a, b], i) => {
    const from = Math.round(acc * FPS);
    acc += b - a;
    const to = Math.round(acc * FPS);
    const len = Math.max(1, to - from);
    const next = i < n - 1 ? types[i] : null, prev = i ? types[i - 1] : null;
    const ext = next && OVERLAP.has(next) ? TR : 0; // đoạn trước chạy dài thêm, chồng lên đầu đoạn sau
    return {i, a, from, len, ext, next, prev, fadeInA: prev && OVERLAP.has(prev) ? TR : prev ? AF : 0, fadeOutA: next && OVERLAP.has(next) ? TR : next ? AF : 0};
  });
  return (
    <>
      {/* vẽ đoạn sau trước, đoạn trước sau -> phần đuôi mờ dần của đoạn trước nằm trên */}
      {[...items].reverse().map((it) => (
        <Sequence key={it.i} from={it.from} durationInFrames={it.len + it.ext} premountFor={FPS}>
          <AbsoluteFill style={tf(it.a)}>
            <SegClip url={url} a={it.a} len={it.len} ext={it.ext} fadeInA={it.fadeInA} fadeOutA={it.fadeOutA} volume={muteAt?.(it.a) ? 0 : volume} scale={scales[it.i]} style={style} outFx={it.next} inFx={it.prev} blurBg={blurBg} aud={audAt?.(it.a)} />
          </AbsoluteFill>
          {kbMask && tf(it.a) && (
            <AbsoluteFill style={kbMask}>
              <SegClip url={url} a={it.a} len={it.len} ext={it.ext} fadeInA={it.fadeInA} fadeOutA={it.fadeOutA} volume={0} scale={1} style={style} outFx={it.next} inFx={it.prev} />
            </AbsoluteFill>
          )}
        </Sequence>
      ))}
      {tail && <TailFreeze url={url} tail={tail} style={style} tf={tf(tail.a)} />}
    </>
  );
};

/** khung hình video chính: s (phóng, <1 = thu nhỏ), dx/dy (px dời), rot (độ), crop [trên, phải, dưới, trái] (% khung),
    round (px bo góc), flip h|v|hv; x/y = tâm phóng kiểu cũ (0–1) */
export type MXf = {flip?: string; s?: number; x?: number; y?: number; dx?: number; dy?: number; rot?: number; crop?: number[]; round?: number};
export const MXF: {v?: MXf & {bg?: string}} = {};
const xfAt = (m: PlanProps['segXf'], a: number): MXf | undefined => {
  const k = m ? Object.keys(m).find((x) => Math.abs(+x - a) < 0.006) : undefined;
  const v = k !== undefined ? m![k] : undefined;
  return MXF.v || v ? {...(MXF.v || {}), ...(v || {})} : undefined;
};
/** khung hình có làm lộ nền phía sau không (thu nhỏ / dời / xoay / cắt mép) */
export const xfReveals = (v?: MXf) => !!v && ((v.s ?? 1) < 1 || !!v.dx || !!v.dy || !!v.rot || !!(v.crop && v.crop.some((c) => c > 0)));
export const anyReveal = (p: {mainXf?: MXf; segXf?: Record<string, MXf>}) => xfReveals(p.mainXf) || Object.values(p.segXf || {}).some((v) => xfReveals({...(p.mainXf || {}), ...v}));
/** style lật / cắt khung cho đoạn bắt đầu ở giây a của video gốc (dùng cho cả video chính và lớp người đã tách) */
export const segTf = (m: PlanProps['segXf'], a: number): React.CSSProperties | undefined => {
  const v = xfAt(m, a);
  if (!v) return undefined;
  const s = Math.max(0.1, Math.min(5, v.s ?? 1)), fx = v.flip?.includes('h') ? -1 : 1, fy = v.flip?.includes('v') ? -1 : 1;
  const dx = v.dx || 0, dy = v.dy || 0, rot = v.rot || 0;
  const c = (v.crop || []).map((x) => Math.max(0, Math.min(49, +x || 0)));
  const hasCrop = c.some((x) => x > 0) || (v.round || 0) > 0;
  if (s === 1 && fx === 1 && fy === 1 && !dx && !dy && !rot && !hasCrop) return undefined;
  const st: React.CSSProperties = {
    transform: `translate(${dx}px, ${dy}px) rotate(${rot}deg) scale(${s * fx}, ${s * fy})`,
    transformOrigin: `${(v.x ?? 0.5) * 100}% ${(v.y ?? 0.5) * 100}%`,
  };
  if (hasCrop) st.clipPath = `inset(${c[0] || 0}% ${c[1] || 0}% ${c[2] || 0}% ${c[3] || 0}%${v.round ? ` round ${v.round / Math.max(0.1, s)}px` : ''})`;
  return st;
};

/** mốc (giây, trên video xuất) của các điểm nối có kiểu chớp sáng */
const flashJoins = (segs: [number, number][] | undefined, fx: JoinFx, over?: Record<string, string>, clips?: Clip[]) => {
  if (!segs || segs.length < 2) return [];
  const out: number[] = [];
  let acc = 0;
  segs.forEach(([a, b], i) => {
    acc += b - a;
    if (i < segs.length - 1 && joinType(segs, i, fx, over, clips) === 'flash') out.push(acc);
  });
  return out;
};

// tên trong thư viện (public/sfx/<tên>.wav) | "cua-ban/<file>" (âm thanh riêng trong public/sfx/cua-ban) | đường dẫn file trong dự án
const sfxSrc = (s: string) => (/^cua-ban\//.test(s) ? staticFile(`sfx/${s}`) : /[./]/.test(s) ? mediaSrc(s) : staticFile(`sfx/${s}.wav`));
// âm thanh dài: phát đủ (tối đa 2s) thay vì cắt sau 0,6s
const LONG_SFX = new Set(['typing', 'riser', 'boom', 'tada', 'sparkle', 'bell', 'cash', 'ding', 'success', 'impact']);
/** âm thanh ở điểm nối theo kiểu chuyển (joinSfx: true = tự chọn, chuỗi = dùng 1 âm cho mọi điểm nối) */
const JOIN_SFX: Record<string, string> = {whip: 'whoosh-manh', zoomin: 'whoosh-manh', slide: 'swoosh', up: 'swoosh', fade: 'whoosh-nhe', blur: 'whoosh-nhe', flash: 'whoosh'};
const keyIn = (m: Record<string, string> | undefined, b: number, a: number) => {
  if (!m) return undefined;
  const k = Object.keys(m).find((x) => {
    const [u, v] = x.split('>').map(Number);
    return Math.abs(u - b) < 0.02 && Math.abs(v - a) < 0.02;
  });
  return k === undefined ? undefined : m[k];
};
/** âm ở điểm nối: q = số điểm nối, key = "b>a", d = âm mặc định (theo kiểu chuyển), s = âm thực dùng ('' = không) */
export const joinSounds = (p: PlanProps): {f: number; t: number; s: string; d: string; q: number; key: string}[] => {
  const segs = p.segments;
  if (!segs || segs.length < 2) return [];
  const out: {f: number; t: number; s: string; d: string; q: number; key: string}[] = [];
  let acc = 0;
  segs.forEach(([a, b], i) => {
    acc += b - a;
    if (i >= segs.length - 1) return;
    const ty = joinType(segs, i, p.transition || 'auto', p.joinFx, p.clipBounds);
    const d = !p.joinSfx ? '' : typeof p.joinSfx === 'string' ? (ty === 'cut' || ty === 'zoom' ? '' : p.joinSfx) : JOIN_SFX[ty] || '';
    const ov = keyIn(p.joinSfxMap, b, segs[i + 1][0]);
    const s = ov !== undefined ? ov : d;
    const t = Math.max(0, acc - 4 / FPS);
    out.push({f: Math.round(t * FPS), t, s, d, q: i, key: `${Math.round(b * 100) / 100}>${Math.round(segs[i + 1][0] * 100) / 100}`});
  });
  return out;
};

/** mọi tiếng hiệu ứng trên video (giây): của khối (lúc hiện + sfxOff), từng dòng checklist, điểm nối */
export type SfxEv = {t: number; s: string; vol: number; kind: 'el' | 'item' | 'join'; i?: number; j?: number; q?: number; key?: string; frames: number};
export const sfxEvents = (p: PlanProps): SfxEv[] => {
  const out: SfxEv[] = [];
  (p.elements || []).forEach((e0, n) => {
    const e = e0 as any;
    if (!e || e.end <= e.start) return;
    const i = e._i ?? n;
    const v = e.sfxVolume ?? p.sfxVolume;
    const d = Math.round((e.end - e.start) * FPS);
    if (e.sfx) out.push({t: Math.max(0, e.start + (e.sfxOff || 0)), s: e.sfx, vol: v, kind: 'el', i, frames: LONG_SFX.has(e.sfx) || e.type === 'sfx' ? Math.min(90, Math.max(18, e.type === 'sfx' ? 60 : d)) : 18});
    if (e.type === 'checklist') (e.items || []).forEach((it: any, j: number) => out.push({t: Math.max(e.start, it.at), s: 'ding', vol: v * 0.7, kind: 'item', i, j, frames: 18}));
  });
  joinSounds(p).forEach((j) => j.s && out.push({t: j.t, s: j.s, vol: p.sfxVolume * 0.8, kind: 'join', q: j.q, key: j.key, frames: 24}));
  // đoạn dựng theo nhịp: bỏ tiếng hiệu ứng tự gắn (giữ khối "Tiếng" người dùng đặt riêng)
  const be = p.beatEdit;
  const inBeat = (t: number) => !!be && !!be.on && !be.keepSfx && t >= (be.from ?? 0) - 0.05 && t <= (be.to ?? 1e9) + 0.05;
  return out.filter((ev) => !(inBeat(ev.t) && !(ev.kind === 'el' && (p.elements[ev.i ?? -1] as any)?.type === 'sfx'))).sort((a, b) => a.t - b.t);
};


const FPS = 30;
const ThemeCtx = React.createContext<Theme>({light: '#4FB3FF', mid: '#1F6FC0', dark: '#0A2F6B', gold1: '#FFE9A0', gold2: '#F2B526'});
const useT = () => React.useContext(ThemeCtx);

/** chờ tải xong các font được dùng (phong cách + từng chữ) trước khi dựng khung */
const useFonts = (p: PlanProps) => {
  const [h] = useState(() => delayRender('fonts'));
  useEffect(() => {
    const st = p.style || {};
    const names = new Set<string>(['Be Vietnam Pro']);
    [st.font, st.heading, st.captions?.font].forEach((n) => n && names.add(n));
    (p.elements || []).forEach((e: any) => e && e.font && names.add(e.font));
    const jobs: Promise<any>[] = [];
    names.forEach((n) => {
      const f = FONTS.find((x) => x.family.toLowerCase() === n.toLowerCase() || x.id === n.toLowerCase());
      if (!f) return;
      f.weights.forEach((w) => jobs.push(document.fonts.load(`${w} 40px "${f.family}"`, 'Ngày ữ Ặ')));
    });
    const to = setTimeout(() => continueRender(h), 8000);
    Promise.all(jobs).catch(() => null).then(() => {
      clearTimeout(to);
      continueRender(h);
    });
  }, [h]);
};

/* ===== Vật liệu dùng chung: kính mờ + khối 3D ===== */
const glass = (t: Theme): React.CSSProperties => {
  const d = skinDef();
  if (d) return d.card(t, accentOf(t));
  return {
    background: `linear-gradient(145deg, rgba(255,255,255,0.28) 0%, ${t.dark}B3 55%, ${t.dark}D9 100%)`,
    backdropFilter: 'blur(18px) saturate(140%)',
    border: '2px solid rgba(255,255,255,0.45)',
    boxShadow: `inset 0 3px 0 rgba(255,255,255,0.45), inset 0 -6px 18px rgba(0,0,0,0.25), 0 24px 50px rgba(3,20,50,0.55)`,
  };
};
const accentOf = (t: Theme) => S.style.accent || (skinDef()?.accent(t) ?? t.light);
const inkOf = (t: Theme) => skinDef()?.ink(t) ?? 'white';
const isFlat = () => skinOf() !== '3d';
const isLight = () => !!skinDef()?.light;
const rad = (n: number) => skinDef()?.radius(n) ?? n;
const labelCss = (): React.CSSProperties => skinDef()?.label || {};

// Huy hiệu tròn 3D chứa icon: gradient tỏa, viền sáng, vệt bóng phía trên
const Badge3D: React.FC<{size: number; from: string; to: string; children: React.ReactNode}> = ({size, from, to, children}) =>
  isFlat() ? (
    <div style={{width: size, height: size, borderRadius: '50%', flexShrink: 0, background: to, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>{children}</div>
  ) : (
  <div
    style={{
      position: 'relative',
      width: size,
      height: size,
      borderRadius: '50%',
      flexShrink: 0,
      background: `radial-gradient(circle at 30% 25%, ${from} 0%, ${to} 75%)`,
      boxShadow: `inset 0 -${size * 0.08}px ${size * 0.15}px rgba(0,0,0,0.35), inset 0 ${size * 0.05}px ${size * 0.08}px rgba(255,255,255,0.6), 0 ${size * 0.12}px ${size * 0.25}px rgba(0,0,0,0.4)`,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
    }}
  >
    <div
      style={{
        position: 'absolute',
        top: size * 0.07,
        left: size * 0.18,
        width: size * 0.64,
        height: size * 0.36,
        borderRadius: '50%',
        background: 'linear-gradient(180deg, rgba(255,255,255,0.75), rgba(255,255,255,0))',
      }}
    />
    <div style={{position: 'relative', filter: 'drop-shadow(0 4px 4px rgba(0,0,0,0.35))', display: 'flex'}}>{children}</div>
  </div>
);

const Icon: React.FC<{name: string; size: number; color?: string}> = ({name, size, color}) => <StyleIcon name={name} size={size} color={color} />;

/** chỗ đặt icon theo phong cách (style.icons.bg): huy hiệu 3D (mặc định) | tròn phẳng | vuông bo | không nền */
const IconHolder: React.FC<{icon: string; size: number; from: string; to: string; color?: string}> = ({icon, size, from, to, color}) => {
  const ic = S.style.icons || {};
  const bg = ic.bg || 'badge';
  if (bg === 'none')
    return (
      <div style={{width: size * 0.8, height: size, flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', filter: 'drop-shadow(0 4px 6px rgba(0,0,0,0.4))'}}>
        <Icon name={icon} size={size * 0.72} color={color} />
      </div>
    );
  if (bg === 'circle' || bg === 'square')
    return (
      <div style={{width: size, height: size, flexShrink: 0, borderRadius: bg === 'circle' ? '50%' : size * 0.26, background: ic.bgColor || to, display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 8px 18px rgba(0,0,0,0.3)'}}>
        <Icon name={icon} size={size * 0.55} color={color} />
      </div>
    );
  return (
    <Badge3D size={size} from={from} to={to}>
      <Icon name={icon} size={size * 0.55} color={color} />
    </Badge3D>
  );
};

// Chữ 3D: gradient vàng + lớp đùn khối xanh đậm
const text3D = (t: Theme, depth: number): React.CSSProperties =>
  isFlat()
    ? {color: inkOf(t), textShadow: isLight() || skinDef()?.big ? 'none' : '0 6px 26px rgba(0,0,0,0.35)', letterSpacing: -1, ...(skinDef()?.big?.(t, accentOf(t)) || {})}
    : ({
  background: `linear-gradient(180deg, #FFFFFF 0%, ${t.gold1} 35%, ${t.gold2} 100%)`,
  WebkitBackgroundClip: 'text',
  backgroundClip: 'text',
  color: 'transparent',
  filter: [...Array(depth)].map((_, i) => `drop-shadow(0 ${i < depth - 1 ? 2 : 10}px ${i < depth - 1 ? 0 : 14}px ${i < depth - 1 ? t.dark : 'rgba(0,0,0,0.5)'})`).join(' '),
}) as React.CSSProperties;

// Vệt sáng quét ngang (shine)
const Shine: React.FC<{period?: number}> = ({period = 70}) => {
  const f = useCurrentFrame();
  if (isFlat()) return null;
  const x = interpolate(f % period, [0, 25], [-60, 160], {extrapolateRight: 'clamp'});
  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        borderRadius: 'inherit',
        overflow: 'hidden',
        pointerEvents: 'none',
      }}
    >
      <div
        style={{
          position: 'absolute',
          top: '-20%',
          bottom: '-20%',
          left: `${x}%`,
          width: '22%',
          transform: 'skewX(-20deg)',
          background: 'linear-gradient(90deg, rgba(255,255,255,0), rgba(255,255,255,0.55), rgba(255,255,255,0))',
        }}
      />
    </div>
  );
};

const useInOut = (durFrames: number) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const inn = spring({frame: f, fps, config: {damping: 13, stiffness: 160}});
  const out = interpolate(f, [durFrames - 8, durFrames], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return {inn, out, f, fps};
};

/* ===== Các khối đồ họa ===== */
const PriceHook: React.FC<{price: string; sub: string; dur: number; y?: number}> = ({price, sub, dur, y = 520}) => {
  const t = useT();
  const {inn, out, f, fps} = useInOut(dur);
  const sub2 = spring({frame: f - 8, fps, config: {damping: 14}});
  const tilt = Math.sin(f / 9) * 4;
  if (isFlat()) {
    const ac = accentOf(t);
    const bar = interpolate(f, [4, 16], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
    return (
      <AbsoluteFill style={{alignItems: 'center', top: y, opacity: out}}>
        <div style={{position: 'relative', transform: `translateY(${(1 - inn) * 40}px)`, opacity: Math.min(1, inn * 1.4), borderRadius: skinDef()?.arch ? '400px 400px 24px 24px' : rad(28), padding: skinDef()?.arch ? '90px 70px 34px' : '26px 60px 30px', textAlign: 'center', ...glass(t)}}>
          <div style={{fontFamily: headFont(), fontWeight: 900, fontSize: 150, lineHeight: 1.15, ...text3D(t, 1)}}>{price}</div>
          <Orn kind={skinDef()?.orn || 'bar'} color={ac} k={bar} w={360} />
        </div>
        {sub && (
          <div style={{marginTop: 22, transform: `translateY(${(1 - sub2) * 30}px)`, opacity: sub2, fontFamily: headFont(), fontWeight: 700, letterSpacing: 1, color: inkOf(t), padding: '10px 30px', borderRadius: rad(999), ...glass(t), ...labelCss(), fontSize: isFlat() && skinOf() !== 'flat' && skinOf() !== 'light' ? 38 : 46} as React.CSSProperties}>
            {sub}
          </div>
        )}
      </AbsoluteFill>
    );
  }
  return (
    <AbsoluteFill style={{alignItems: 'center', top: y, opacity: out, perspective: 1200}}>
      <div
        style={{
          position: 'relative',
          transform: `scale(${inn}) rotateX(${8}deg) rotateY(${tilt}deg) rotate(-3deg)`,
          background: `linear-gradient(135deg, ${t.light} 0%, ${t.mid} 45%, ${t.dark} 100%)`,
          borderRadius: 40,
          padding: '18px 56px 26px',
          border: '3px solid rgba(255,255,255,0.6)',
          boxShadow: `inset 0 4px 0 rgba(255,255,255,0.5), inset 0 -10px 24px rgba(0,0,0,0.3), 0 14px 0 ${t.dark}, 0 40px 70px rgba(0,0,0,0.5)`,
        }}
      >
        <div style={{fontFamily: headFont(), fontWeight: 900, fontSize: 150, letterSpacing: -3, lineHeight: 1.05, paddingTop: 34, ...text3D(t, 6)}}>{price}</div>
        <Shine />
      </div>
      <div
        style={{
          marginTop: 40,
          transform: `translateY(${(1 - sub2) * 60}px)`,
          opacity: sub2,
          ...glass(t),
          color: 'white',
          fontFamily: headFont(),
          fontWeight: 800,
          fontSize: 58,
          padding: '14px 38px',
          borderRadius: 999,
        }}
      >
        {sub}
      </div>
    </AbsoluteFill>
  );
};

const Chip: React.FC<{icon: string; text: string; y: number; dur: number}> = ({icon, text, y, dur}) => {
  const t = useT();
  const {inn, out, f} = useInOut(dur);
  const float = Math.sin(f / 12) * 4;
  const lay = S.style.layout || {};
  const al = lay.align || 'left';
  const mx = lay.marginX != null ? Math.max(24, Math.min(240, lay.marginX)) : 46;
  const iconRight = lay.iconPos === 'right';
  const side: React.CSSProperties = al === 'right' ? {right: mx} : al === 'center' ? {left: '50%'} : {left: mx};
  const slide = al === 'right' ? 700 : al === 'center' ? 0 : -700;
  return (
    <div
      style={{
        position: 'absolute',
        top: y + float,
        ...side,
        transform: `${al === 'center' ? 'translateX(-50%) ' : ''}translateX(${(1 - inn) * slide}px)${al === 'center' ? ` scale(${0.6 + 0.4 * inn})` : ''}`,
        opacity: al === 'center' ? out * inn : out,
        display: 'flex',
        flexDirection: iconRight ? 'row-reverse' : 'row',
        alignItems: 'center',
        gap: 20,
        borderRadius: rad(999),
        padding: iconRight ? '12px 12px 12px 40px' : '12px 40px 12px 12px',
        whiteSpace: 'nowrap',
        ...glass(t),
      }}
    >
      <IconHolder icon={icon} size={isFlat() ? 76 : 84} from={t.light} to={skinDef() ? skinDef()!.badge(t, accentOf(t)).bg : t.dark} color={skinDef() && !S.style.icons?.color ? skinDef()!.badge(t, accentOf(t)).fg : undefined} />
      <span style={{fontFamily: headFont(), fontWeight: isFlat() ? 700 : 800, fontSize: isFlat() ? 46 : 50, color: inkOf(t), textShadow: isFlat() ? 'none' : '0 3px 8px rgba(0,0,0,0.4)'}}>{text}</span>
    </div>
  );
};

const BigQuestion: React.FC<{text: string; dur: number; y?: number}> = ({text, dur, y = 620}) => {
  const t = useT();
  const {inn, out, f} = useInOut(dur);
  const shake = f < 14 ? Math.sin(f * 2.2) * 10 : 0;
  if (isFlat())
    return (
      <AbsoluteFill style={{alignItems: 'center', top: y, opacity: out}}>
        <div style={{transform: `scale(${0.85 + 0.15 * inn})`, opacity: Math.min(1, inn * 1.5), fontFamily: headFont(), fontWeight: 900, fontSize: 130, lineHeight: 1.2, textAlign: 'center', padding: '0 60px', color: isLight() ? 'white' : inkOf(t), textShadow: '0 8px 30px rgba(0,0,0,0.45)', ...(skinDef()?.big && !isLight() ? skinDef()!.big!(t, accentOf(t)) : {}), ...(skinDef()?.big && isLight() ? {fontFamily: (skinDef()!.big!(t, accentOf(t)) as any).fontFamily} : {})}}>
          {text}
          <Orn kind={skinDef()?.orn || 'bar'} color={accentOf(t)} k={Math.min(1, inn)} w={240} />
        </div>
      </AbsoluteFill>
    );
  return (
    <AbsoluteFill style={{alignItems: 'center', top: y, opacity: out}}>
      <div
        style={{
          transform: `scale(${inn}) translateX(${shake}px) rotate(-3deg)`,
          fontFamily: headFont(),
          fontWeight: 900,
          fontSize: 140,
          textAlign: 'center',
          ...text3D(t, 9),
        }}
      >
        {text}
      </div>
    </AbsoluteFill>
  );
};

const Checklist: React.FC<{title: string; items: {text: string; at: number}[]; start: number; dur: number; y?: number}> = ({title, items, start, dur, y = 240}) => {
  const t = useT();
  const {inn, out, f, fps} = useInOut(dur);
  return (
    <div
      style={{
        position: 'absolute',
        top: y,
        left: 46,
        right: 130,
        opacity: out,
        transform: `translateY(${(1 - inn) * -80}px)`,
        borderRadius: rad(36),
        padding: '28px 34px',
        ...glass(t),
      }}
    >
      <div
        style={{
          display: 'inline-block',
          fontFamily: headFont(),
          fontWeight: 900,
          fontSize: 50,
          color: t.dark,
          background: `linear-gradient(180deg, ${t.gold1}, ${t.gold2})`,
          padding: '6px 26px',
          borderRadius: 14,
          marginBottom: 12,
          boxShadow: `0 6px 0 #B07D0E, 0 12px 20px rgba(0,0,0,0.3)`,
          ...(isFlat() ? {background: 'transparent', boxShadow: 'none', padding: '0 0 6px', color: accentOf(t), fontSize: 44, letterSpacing: 2, textTransform: 'uppercase', borderBottom: `3px solid ${accentOf(t)}`, borderRadius: 0, ...labelCss()} : {}),
        } as React.CSSProperties}
      >
        {title}
      </div>
      {items.map((it, i) => {
        const s = spring({frame: f - (it.at - start) * fps, fps, config: {damping: 12}});
        if (s <= 0.001) return null;
        return (
          <div key={i} style={{display: 'flex', alignItems: 'center', gap: 18, margin: '16px 0', opacity: s, transform: `translateX(${(1 - s) * 80}px)`}}>
            <div style={{transform: `scale(${s})`}}>
              <Badge3D size={isFlat() ? 52 : 62} from="#7CF0A0" to={isFlat() ? accentOf(t) : '#0F8A3C'}>
                <Icons.Check size={isFlat() ? 32 : 38} color={isFlat() && !isLight() ? '#0B1220' : 'white'} strokeWidth={4} />
              </Badge3D>
            </div>
            <span style={{fontFamily: headFont(), fontWeight: isFlat() ? 700 : 800, fontSize: isFlat() ? 46 : 48, color: inkOf(t), textShadow: isFlat() ? 'none' : '0 3px 8px rgba(0,0,0,0.4)'}}>{it.text}</span>
          </div>
        );
      })}
    </div>
  );
};

const RangeCard: React.FC<{label: string; value: string; note?: string; dur: number; y?: number}> = ({label, value, note, dur, y = 280}) => {
  const t = useT();
  const {inn, out, f} = useInOut(dur);
  const tilt = Math.sin(f / 10) * 3;
  return (
    <AbsoluteFill style={{alignItems: 'center', top: y, opacity: out, perspective: 1200}}>
      <div
        style={{
          position: 'relative',
          transform: isFlat() ? `translateY(${(1 - inn) * 40}px)` : `scale(${0.7 + 0.3 * inn}) rotateX(6deg) rotateY(${tilt}deg)`,
          opacity: inn,
          borderRadius: skinDef()?.arch ? '300px 300px 24px 24px' : rad(40),
          padding: skinDef()?.arch ? '70px 64px 30px' : '26px 54px 30px',
          textAlign: 'center',
          ...glass(t),
        }}
      >
        <div style={{fontFamily: headFont(), fontWeight: 700, fontSize: 42, color: isFlat() ? accentOf(t) : 'rgba(255,255,255,0.9)', ...(isFlat() ? {letterSpacing: 2, textTransform: 'uppercase', fontSize: 36, ...labelCss()} : {})} as React.CSSProperties}>{label}</div>
        <div style={{fontFamily: headFont(), fontWeight: 900, fontSize: 116, lineHeight: 1.15, paddingTop: isFlat() ? 8 : 24, ...text3D(t, 5)}}>{value}</div>
        {note && <div style={{fontFamily: headFont(), fontWeight: 700, fontSize: 40, color: inkOf(t), opacity: isFlat() ? 0.8 : 1, marginTop: 6}}>{note}</div>}
        <Shine />
      </div>
    </AbsoluteFill>
  );
};

const CTA: React.FC<{icon: string; text: string; dur: number; y?: number}> = ({icon, text, dur, y = 1120}) => {
  const t = useT();
  const {inn, f} = useInOut(dur + 100); // không mờ ra ở cuối
  const pulse = 1 + Math.sin(f / 5) * 0.035;
  if (isFlat()) {
    const ac = S.style.accent || t.mid;
    return (
      <AbsoluteFill style={{alignItems: 'center', top: y}}>
        <div style={{transform: `translateY(${(1 - inn) * 200}px) scale(${1 + Math.sin(f / 7) * 0.02})`, display: 'flex', alignItems: 'center', gap: 16, borderRadius: rad(999), padding: '12px 40px 12px 12px', boxShadow: '0 16px 36px rgba(0,0,0,0.3)',
          ...(skinDef()?.cta === 'outline' ? {background: 'rgba(8,8,8,0.82)', border: `1.5px solid ${accentOf(t)}`} : skinDef() && skinDef() !== null && !['flat', 'light'].includes(skinOf()) ? glass(t) : {background: isLight() ? 'white' : ac})}}>
          <div style={{width: 76, height: 76, borderRadius: rad(38), background: skinDef()?.cta === 'outline' ? 'transparent' : isLight() ? accentOf(t) : 'rgba(255,255,255,0.22)', border: skinDef()?.cta === 'outline' ? `1.5px solid ${accentOf(t)}` : 'none', display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
            <Icon name={icon} size={42} color={skinDef()?.cta === 'outline' ? accentOf(t) : 'white'} />
          </div>
          <span style={{fontFamily: headFont(), fontWeight: 800, fontSize: 46, color: skinDef()?.cta === 'outline' ? inkOf(t) : isLight() ? inkOf(t) : 'white', whiteSpace: 'nowrap', ...(skinDef()?.cta === 'outline' ? {letterSpacing: 3, textTransform: 'uppercase', fontSize: 40, fontWeight: 600} : {})} as React.CSSProperties}>{text}</span>
        </div>
      </AbsoluteFill>
    );
  }
  return (
    <AbsoluteFill style={{alignItems: 'center', top: y}}>
      <div
        style={{
          position: 'relative',
          transform: `translateY(${(1 - inn) * 300}px) scale(${pulse})`,
          display: 'flex',
          alignItems: 'center',
          gap: 18,
          background: `linear-gradient(135deg, ${t.light} 0%, ${t.mid} 50%, ${t.dark} 100%)`,
          borderRadius: 999,
          padding: '14px 46px 14px 14px',
          border: '3px solid rgba(255,255,255,0.6)',
          boxShadow: `inset 0 4px 0 rgba(255,255,255,0.45), 0 10px 0 ${t.dark}, 0 30px 50px rgba(0,0,0,0.5)`,
        }}
      >
        <IconHolder icon={icon} size={86} from={t.gold1} to={t.gold2} color={S.style.icons?.color ? undefined : t.dark} />
        <span style={{fontFamily: headFont(), fontWeight: 900, fontSize: 50, color: 'white', whiteSpace: 'nowrap', textShadow: '0 3px 6px rgba(0,0,0,0.35)'}}>{text}</span>
        <Shine period={50} />
      </div>
    </AbsoluteFill>
  );
};

/** Chữ tự do: plain (chữ viền), box (khung kính), gold (chữ 3D vàng), tag (nhãn vàng) */
const FreeText: React.FC<{text: string; y: number; size: number; look: string; color?: string; dur: number}> = ({text, y, size, look, color, dur}) => {
  const t = useT();
  const {inn, out} = useInOut(dur);
  const base: React.CSSProperties = {fontFamily: headFont(), fontWeight: 900, fontSize: size, lineHeight: text.includes('\n') ? 1.35 : 1.2, textAlign: 'center', whiteSpace: 'pre-wrap'};
  const looks: Record<string, React.CSSProperties> = {
    plain: {color: color || 'white', WebkitTextStroke: `${Math.round(size / 7)}px ${t.dark}`, paintOrder: 'stroke fill', textShadow: '0 8px 24px rgba(0,0,0,0.6)'} as any,
    box: {color: color || 'white', padding: '18px 40px', borderRadius: 32, ...glass(t), textShadow: '0 3px 8px rgba(0,0,0,0.4)'},
    // chừa chỗ phía trên cho dấu tiếng Việt (vùng tô vàng chỉ phủ trong khung chữ)
    gold: {...text3D(t, 6), lineHeight: 1.35, padding: `${Math.round(size * 0.22)}px 12px ${Math.round(size * 0.06)}px`},
    tag: {color: color || t.dark, background: `linear-gradient(180deg, ${t.gold1}, ${t.gold2})`, padding: '10px 34px', borderRadius: 18, boxShadow: `0 6px 0 #B07D0E, 0 14px 24px rgba(0,0,0,0.35)`},
  };
  if (isFlat()) {
    looks.gold = {...text3D(t, 1), lineHeight: 1.3};
    looks.tag = {color: isLight() ? 'white' : '#0B1220', background: accentOf(t), padding: '10px 32px', borderRadius: 14};
    looks.plain = {color: color || 'white', textShadow: '0 4px 18px rgba(0,0,0,0.55)', WebkitTextStroke: `${Math.round(size / 18)}px rgba(0,0,0,0.65)`, paintOrder: 'stroke fill'} as any;
  }
  return (
    <AbsoluteFill style={{alignItems: 'center', top: y, opacity: out, padding: '0 60px'}}>
      <div style={{...base, ...(looks[look] || looks.plain), transform: `scale(${0.6 + 0.4 * inn})`, opacity: inn}}>{text}</div>
    </AbsoluteFill>
  );
};

/* ===== Zoom nhấn mạnh trên video chính ===== */
const ease = (x: number) => (x <= 0 ? 0 : x >= 1 ? 1 : x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2);
const useZoomFx = (zooms: El[]) => {
  const f = useCurrentFrame();
  let k = 1, ox = 50, oy = 40, tx = 0, ty = 0;
  for (const z of zooms as any[]) {
    const a = z.start * FPS, b = z.end * FPS;
    if (f < a - 1 || f > b + 1) continue;
    const s = Math.max(1.01, z.scale ?? (z.style === 'shake' ? 1.08 : 1.2));
    const d = Math.max(1, b - a), t = f - a;
    const outR = Math.min(6, d / 3);
    let m = 0; // 0 = không zoom, 1 = zoom đủ
    const soft = (S.style as any).effects?.zoomEase === 'smooth';
    switch (soft ? 'smooth' : z.style || 'punch') {
      case 'smooth': {
        // vào êm ~1s, giữ, ra êm ~1,2s (không giật khung)
        const ai = Math.min(FPS * 1.0, d * 0.4), ao = Math.min(FPS * 1.2, d * 0.45);
        m = t < ai ? ease(t / ai) : t > d - ao ? 1 - ease((t - (d - ao)) / ao) : 1;
        break;
      }
      case 'punch':
        m = interpolate(t, [0, 3, d - outR, d], [0, 1, 1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
        break;
      case 'in':
        m = t < d - outR ? ease(t / Math.max(1, d - outR)) : interpolate(t, [d - outR, d], [1, 0], {extrapolateRight: 'clamp'});
        break;
      case 'out':
        m = t < 3 ? interpolate(t, [0, 3], [0, 1]) : 1 - ease((t - 3) / Math.max(1, d - 3));
        break;
      case 'pulse':
        m = Math.sin(Math.PI * Math.min(1, Math.max(0, t / d)));
        break;
      case 'shake': {
        m = interpolate(t, [0, 2, d - 3, d], [0, 1, 1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
        const amp = 14 * m * Math.max(0.2, 1 - t / d);
        tx += Math.sin(t * 2.9) * amp;
        ty += Math.cos(t * 3.7) * amp * 0.7;
        break;
      }
    }
    if (m > 0) {
      k *= 1 + (s - 1) * m;
      ox = (z.x ?? 0.5) * 100;
      oy = (z.y ?? 0.4) * 100;
    }
  }
  return {k, origin: `${ox}% ${oy}%`, tx, ty};
};

/* ===== Chuyển cảnh: zoom đẩy + chớp sáng (không âm thanh) ===== */
const useCutZoom = (cuts: number[]) => {
  const f = useCurrentFrame();
  let z = 1;
  for (const c of cuts) {
    const d = f - c * FPS;
    if (d >= -3 && d < 12) z = Math.max(z, interpolate(d, [-3, 0, 12], [1, 1.1, 1], {extrapolateRight: 'clamp'}));
  }
  return z;
};
const Flash: React.FC = () => {
  const f = useCurrentFrame();
  return <AbsoluteFill style={{background: 'white', opacity: interpolate(f, [0, 2, 7], [0, 0.45, 0], {extrapolateRight: 'clamp'})}} />;
};

/** khối âm thanh / nhạc: âm lượng, tốc độ (rate), vuốt to dần (fadeIn) / nhỏ dần (fadeOut) — giây */
const AudioEl: React.FC<{e: any; dur: number}> = ({e, dur}) => {
  const v = e.volume ?? 1, fi = Math.round((e.fadeIn || 0) * FPS), fo = Math.round((e.fadeOut || 0) * FPS);
  const rate = e.rate && e.rate > 0 ? e.rate : 1;
  return <Audio src={mediaSrc(e.src)} startFrom={Math.round((e.from ?? 0) * FPS)} playbackRate={rate} loop={!!e.loop} volume={(f) => v * fadeK(f, dur, fi, fo)} />;
};

const renderEl = (e: El, dur: number, theme: Theme, filter?: string) => {
  switch (e.type) {
    case 'priceHook': return <PriceHook price={e.price} sub={e.sub} dur={dur} y={e.y} />;
    case 'chip': return <Chip icon={e.icon} text={e.text} y={e.y ?? 240} dur={dur} />;
    case 'bigQuestion': return <BigQuestion text={e.text} dur={dur} y={e.y} />;
    case 'checklist': return <Checklist title={e.title} items={e.items || []} start={e.start} dur={dur} y={e.y} />;
    case 'rangeCard': return <RangeCard label={e.label} value={e.value} note={e.note} dur={dur} y={e.y} />;
    case 'cta': return <CTA icon={e.icon} text={e.text} dur={dur} y={e.y} />;
    case 'pip': return <Pip src={e.src} from={e.from} label={e.label} y={e.y} look={(e as any).look} dur={dur} theme={theme} volume={e.volume} filter={filter} w={(e as any).w} h={(e as any).h} x={(e as any).x} />;
    case 'broll': return <BRoll src={e.src} from={e.from} label={e.label} transition={e.transition} exit={(e as any).exit} tdur={(e as any).inDur} dur={dur} theme={theme} volume={e.volume} filter={filter} area={(e as any).area} split={(e as any).split} feather={(e as any).feather} seam={(e as any).seam} />;
    case 'dayBadge': return <DayBadge day={e.day} total={e.total} theme={theme} />;
    case 'text': {
      const look = e.look || S.style.text?.look || 'plain';
      return look === 'plain' || NEW_LOOKS.includes(look) ? (
        <StyledText {...(e as any)} look={look} y={e.y ?? 700} dur={dur} theme={theme} />
      ) : (
        <FreeText text={e.text} y={e.y ?? 700} size={e.size ?? S.style.text?.size ?? 80} look={look} color={e.color} dur={dur} />
      );
    }
    case 'sticker': return <Sticker icon={e.icon} size={e.size} color={e.color} x={e.x} y={e.y ?? 600} anim={e.anim as any} out={e.out as any} loop={e.loop} rotate={e.rotate} dur={dur} inDur={e.inDur} outDur={e.outDur} />;
    case 'map': return <MapBlock e={e as any} dur={dur} theme={theme} />;
    case 'orbit': return <Orbit e={e as any} dur={dur} />;
    case 'text3dPro': return <Text3DPro e={e} dur={dur} />;
    case 'photo3d': return <Photo3D e={e as any} dur={dur} />;
    case 'object3d': return <Object3D e={e} dur={dur} />;
    case 'screen3d': return <Screen3DEl e={e} dur={dur} />;
    case 'mapTour': return <MapTour e={e as any} dur={dur} />;
    case 'phrase': return <Phrase e={e} dur={dur} theme={theme} />;
    case 'counter': return <Counter e={e} dur={dur} theme={theme} />;
    case 'stamp': return <Stamp e={e} dur={dur} />;
    case 'tabs': return <Tabs e={e} dur={dur} theme={theme} />;
    case 'tiles': return <Tiles e={e} dur={dur} theme={theme} />;
    case 'note': return <Note e={e} dur={dur} theme={theme} />;
    case 'bubble': return <Bubble e={e} dur={dur} theme={theme} />;
    case 'spark': return <Spark e={e} dur={dur} theme={theme} />;
    case 'chart': return <Chart e={e} dur={dur} theme={theme} />;
    case 'overlay': return <Overlay e={e} dur={dur} theme={theme} />;
    case 'shape': return <Shape e={e} dur={dur} theme={theme} />;
    case 'text3d': return <Text3D e={e} dur={dur} theme={theme} />;
    case 'card3d': return <Card3D e={e} dur={dur} theme={theme} filter={filter} />;
    case 'scene': return <Scene e={e} dur={dur} theme={theme} />;
    case 'audio': return e.src ? <AudioEl e={e} dur={dur} /> : null;
    case 'beatFrames': return <BeatFrames e={e} dur={dur} filter={filter} />;
    case 'beatStrips': return <BeatStrips e={e} dur={dur} filter={filter} />;
    case 'solid': return <Solid e={e} dur={dur} />;
    case 'bars': return <Bars e={e} dur={dur} />;
  }
  return null;
};

const KF_PROPS = ['dx', 'dy', 'sc', 'rot', 'op'] as const;
const kfEase = (x: number) => (x < 0.5 ? 2 * x * x : 1 - Math.pow(-2 * x + 2, 2) / 2);
/** giá trị dời / phóng / xoay / độ mờ của khối ở giây rel (tính từ lúc khối hiện) — có keyframe thì nội suy */
export const kfAt = (e: any, rel: number) => {
  const base: Record<string, number> = {dx: e.dx || 0, dy: e.dy || 0, sc: e.sc && e.sc > 0 ? e.sc : 1, rot: e.rot || 0, op: e.op ?? 1};
  const kf: Kf[] = Array.isArray(e.kf) ? [...e.kf].sort((a, b) => a.t - b.t) : [];
  if (!kf.length) return base;
  const out = {...base};
  for (const k of KF_PROPS) {
    const pts = kf.filter((p) => typeof (p as any)[k] === 'number');
    if (!pts.length) continue;
    if (rel <= pts[0].t) out[k] = (pts[0] as any)[k];
    else if (rel >= pts[pts.length - 1].t) out[k] = (pts[pts.length - 1] as any)[k];
    else {
      const j = pts.findIndex((p) => p.t > rel);
      const a = pts[j - 1], b = pts[j];
      const x = kfEase((rel - a.t) / Math.max(1e-6, b.t - a.t));
      out[k] = (a as any)[k] + ((b as any)[k] - (a as any)[k]) * x;
    }
  }
  return out;
};

/* ===== ảnh trám nửa khung: dời người nói sang phần còn lại cho khỏi bị che ===== */
const splitShift = (els: El[], t: number, faceY: (t: number) => number | null): number => {
  let sh = 0;
  for (const e of els as any[]) {
    if (e.type !== 'broll' || t < e.start - 0.05 || t > e.end + 0.05) continue;
    const A = brollArea(e);
    // mặc định KHÔNG dời video chính — chỉ dời khi bật rõ follow: true (ở khối hoặc style.broll)
    if (A.area === 'full' || !(e.follow ?? (S.style.broll as any)?.follow)) continue;
    const sm = (x: number) => (x <= 0 ? 0 : x >= 1 ? 1 : x * x * (3 - 2 * x));
    const env = Math.min(sm((t - e.start) / 0.45), sm((e.end - t) / 0.45));
    const fy = faceY(t) ?? 760;
    const room = Math.max(0, A.h - A.feather * 0.5); // dời tối đa mà chỗ hở vẫn nằm dưới phần trám đặc
    let want: number;
    if (A.area === 'bottom') want = Math.max(-room, Math.min(0, (FR.h - A.h) * 0.48 - fy));
    else want = Math.min(room, Math.max(0, A.h + (FR.h - A.h) * 0.42 - fy));
    sh += want * env;
  }
  return sh;
};

/* ===== khối BÁM MẶT ===== */
const FaceCtx = React.createContext<{faces?: PlanProps['faces']; segs?: [number, number][]; p?: PlanProps}>({});
/** giây video gốc -> giây video xuất (null = đoạn đã cắt) */
const srcToOutT = (segs: [number, number][] | undefined, t: number): number | null => {
  if (!segs || !segs.length) return t;
  let acc = 0;
  for (const [a, b] of segs) {
    if (t >= a && t < b) return acc + (t - a);
    acc += b - a;
  }
  return null;
};
/** MÀN HÌNH 3D: đổi cử chỉ tay (giây gốc, scripts/tay.py) sang giây trong khối; tay đè lên kính = lớp người cắt quanh bàn tay */
const Screen3DEl: React.FC<{e: any; dur: number}> = ({e, dur}) => {
  const fc = React.useContext(FaceCtx);
  const f = useCurrentFrame();
  const conv = (pts: any[] | undefined) =>
    (pts || []).map((q: any) => {
      const o = srcToOutT(fc.segs, q[0]);
      return o == null ? null : [o - e.start, ...q.slice(1)];
    }).filter((q: any) => q && q[0] > -1 && q[0] < e.end - e.start + 1) as number[][];
  const hand = conv(e.handPts);
  const ev = conv(e.swipes).map((q) => ({t: q[0], dir: q[1] ?? 1}));
  const hp = handAt(hand, f / FPS);
  const p = fc.p;
  const over = e.handOver !== false && hp && p && p.person && p.person.length;
  const from = Math.round(e.start * FPS);
  const r = e.handR ?? (hp && hp.length >= 5 ? Math.max(70, hp[4] * 0.62) : 150);
  const mx = hp && hp.length >= 5 ? hp[2] : hp ? hp[0] : 0, my = hp && hp.length >= 5 ? hp[3] : hp ? hp[1] + r * 0.4 : 0;
  return (
    <>
      <Screen3D e={e} dur={dur} hand={hand} ev={ev} />
      {over ? (
        <AbsoluteFill style={{WebkitMaskImage: `radial-gradient(ellipse ${r}px ${r * 1.2}px at ${mx}px ${my}px, #000 62%, transparent 100%)`,
          maskImage: `radial-gradient(ellipse ${r}px ${r * 1.2}px at ${mx}px ${my}px, #000 62%, transparent 100%)`}}>
          <Sequence from={-from}>
            <PersonLayer p={p} />
          </Sequence>
        </AbsoluteFill>
      ) : null}
    </>
  );
};
const outToSrcT = (segs: [number, number][] | undefined, t: number) => {
  if (!segs || !segs.length) return t;
  let acc = 0;
  for (const [a, b] of segs) {
    if (t < acc + (b - a)) return a + (t - acc);
    acc += b - a;
  }
  return segs[segs.length - 1][1];
};
/** tâm mặt ở giây t (video gốc), nội suy giữa 2 mẫu; mất mặt thì lấy mẫu gần nhất trong 1,5 giây */
const faceCenter = (m: PlanProps['faces'], t: number): [number, number] | null => {
  if (!m?.faces?.length) return null;
  const st = m.step || 0.5, F = m.faces;
  const c = (f: number[]) => (f && f.length >= 5 ? [f[1] + f[3] / 2, f[2] + f[4] / 2] as [number, number] : null);
  const i0 = Math.max(0, Math.min(F.length - 1, Math.floor(t / st))), i1 = Math.min(F.length - 1, i0 + 1);
  const a = c(F[i0]), b = c(F[i1]);
  if (a && b) {
    const u = Math.max(0, Math.min(1, t / st - i0));
    return [a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u];
  }
  for (let d = 1; d <= Math.ceil(1.5 / st); d++) {
    const x = c(F[i0 - d]) || c(F[i0 + d]);
    if (x) return x;
  }
  return a || b;
};

/** lớp bọc mỗi khối: dời / phóng / xoay + hiệu ứng vào/ra chung. data-el = số thứ tự khối (để trình edit bấm chọn, kéo thả) */
const FxWrap: React.FC<{e: El; dur: number; children: React.ReactNode}> = ({e, dur, children}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const org = e.org ? `${e.org[0]}px ${e.org[1]}px` : '540px 960px';
  const v = kfAt(e, f / fps);
  const fc = React.useContext(FaceCtx);
  if (e.follow === 'face' && fc.faces) {
    const p0 = faceCenter(fc.faces, outToSrcT(fc.segs, e.start)), p1 = faceCenter(fc.faces, outToSrcT(fc.segs, e.start + f / fps));
    if (p0 && p1) {
      v.dx += p1[0] - p0[0];
      v.dy += p1[1] - p0[1];
    }
  }
  // bám vật thể: trackPts = [[giây gốc, x, y]] (scripts/track.py) — khối dời theo chuyển động của điểm được bám
  const tp = (e as any).trackPts;
  if (Array.isArray(tp) && tp.length) {
    const q0 = trackAt(tp, outToSrcT(fc.segs, e.start)), q1 = trackAt(tp, outToSrcT(fc.segs, e.start + f / fps));
    if (q0 && q1) {
      v.dx += q1[0] - q0[0];
      v.dy += q1[1] - q0[1];
    }
  }
  const sc = v.sc > 0 ? v.sc : 1;
  const tf = v.dx || v.dy || v.rot || sc !== 1 ? `translate(${v.dx}px, ${v.dy}px) rotate(${v.rot}deg) scale(${sc})` : undefined;
  const fin = e.fxIn && e.fxIn !== 'none' ? e.fxIn : '', fout = e.fxOut && e.fxOut !== 'none' ? e.fxOut : '';
  const fx = !nativeAnim(e, S.style) && (fin || fout)
    ? animStyle((fin || 'none') as any, (fout || 'none') as any, f, dur, fps, e.inDur ? e.inDur * fps : undefined, e.outDur ? e.outDur * fps : undefined, {ease: (e as any).ease, mblur: (e as any).mblur})
    : null;
  return (
    <AbsoluteFill data-el={e._i} style={{transform: tf, transformOrigin: org, pointerEvents: 'none', opacity: v.op < 1 ? Math.max(0, v.op) : undefined}}>
      {fx ? <AbsoluteFill style={{...fx, transformOrigin: org}}>{children}</AbsoluteFill> : children}
    </AbsoluteFill>
  );
};

const ElSeq: React.FC<{e: El; p: PlanProps; filter?: string}> = ({e, p, filter}) => {
  const from = Math.round(e.start * FPS);
  const dur = Math.max(1, Math.round((e.end - e.start) * FPS));
  const vol = e.sfxVolume ?? p.sfxVolume;
  // chế độ hoà trộn (screen / add / multiply / overlay / soft-light…) đặt ở lớp ngoài cùng để hoà với video bên dưới
  const bl = (e as any).blend || (e.type === 'overlay' ? OVERLAY_BLEND[(e as any).kind || 'lightleak'] : undefined);
  const blend = bl && bl !== 'normal' ? (bl === 'add' ? 'plus-lighter' : bl) : undefined;
  return (
    <Sequence from={from} durationInFrames={dur} premountFor={'src' in e || e.type === 'orbit' || e.type === 'photo3d' || e.type === 'object3d' || e.type === 'text3dPro' || e.type === 'screen3d' ? FPS : e.type === 'map' || e.type === 'mapTour' ? FPS * 2 : 0} style={blend ? {mixBlendMode: blend as any} : undefined}>
      {e.type === 'audio' || e.type === 'zoom' || e.type === 'sfx' || e.type === 'fx' ? (
        renderEl(e, dur, p.theme, filter)
      ) : (
        <RateCtx.Provider value={e.rate && e.rate > 0 ? e.rate : 1}>
          <MaskCtx.Provider value={maskCss(e)}>
            <ViewCtx.Provider value={viewOf(e)}>
              <FxWrap e={e} dur={dur}>{renderEl(e, dur, p.theme, filter)}</FxWrap>
            </ViewCtx.Provider>
          </MaskCtx.Provider>
        </RateCtx.Provider>
      )}
      {typeof (e as any).credit === 'string' && (e as any).credit && <Credit e={e} dur={dur} />}
    </Sequence>
  );
};
/** ghi nguồn ảnh giấy phép mở (Openverse / Creative Commons): chữ nhỏ ở góc ảnh trám, dưới khung nổi */
const Credit: React.FC<{e: El; dur: number}> = ({e, dur}) => {
  const f = useCurrentFrame();
  const op = interpolate(f, [4, 12, dur - 8, dur], [0, 1, 1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const ee = e as any;
  const top = e.type === 'broll' ? FR.h - (FR.h === 1920 ? 420 : 56) : (ee.y ?? fy(260)) + (ee.h ?? 560) + 70;
  return (
    <div style={{position: 'absolute', left: e.type === 'broll' ? 28 : 0, right: e.type === 'broll' ? undefined : 0, top: Math.min(FR.h - 40, top), textAlign: e.type === 'broll' ? 'left' : 'center',
      fontFamily: 'Inter, sans-serif', fontSize: 20, color: 'rgba(255,255,255,0.82)', textShadow: '0 1px 3px rgba(0,0,0,0.8)', opacity: op, pointerEvents: 'none'}}>
      {ee.credit}
    </div>
  );
};

/* ===== hiệu ứng hình áp lên cả khung ===== */
const rnd = (n: number) => {
  const x = Math.sin(n * 12.9898 + 78.233) * 43758.5453;
  return x - Math.floor(x);
};
const useFrameFx = (fxs: any[], beats?: number[]) => {
  const f = useCurrentFrame();
  const tr: string[] = [], fl: string[] = [];
  const over: React.ReactNode[] = [];
  let glitch = 0, rgb = 0, vhs = 0, glow = 0;
  for (const e of fxs) {
    const a = Math.round(e.start * FPS), b = Math.round(e.end * FPS);
    if (f < a || f >= b) continue;
    const k = Math.max(0, Math.min(1, (e.amount ?? 60) / 100));
    const lf = f - a;
    switch (e.style) {
      case 'shake':
        tr.push(`translate(${Math.sin(f * 2.7) * 22 * k}px, ${Math.cos(f * 3.3) * 15 * k}px) rotate(${Math.sin(f * 1.9) * 0.8 * k}deg)`);
        break;
      case 'glitch':
        if (rnd(Math.floor(f / 2)) > 0.55) {
          glitch = Math.max(glitch, k);
          tr.push(`translateX(${(rnd(f) - 0.5) * 40 * k}px)`);
        }
        rgb = Math.max(rgb, k * 0.5);
        break;
      case 'rgb':
        rgb = Math.max(rgb, k);
        break;
      case 'flash': {
        const per = 15, x = lf % per;
        over.push(<AbsoluteFill key={'fl' + e._i} style={{background: 'white', opacity: Math.max(0, 0.8 * k * (1 - x / 6))}} />);
        break;
      }
      case 'vhs':
        vhs = Math.max(vhs, k);
        rgb = Math.max(rgb, k * 0.35);
        fl.push(`saturate(${1 + 0.35 * k}) contrast(${1 + 0.1 * k})`);
        tr.push(`translateY(${rnd(Math.floor(f / 3)) > 0.9 ? 6 * k : 0}px)`);
        break;
      case 'blur':
        fl.push(`blur(${14 * k}px)`);
        break;
      case 'bw':
        fl.push(`grayscale(1) contrast(${1 + 0.25 * k})`);
        break;
      case 'glow': // bloom: vùng sáng toả hào quang (giống Glow của AE)
        glow = Math.max(glow, k);
        break;
      case 'dreamy': // mơ màng: bloom + mềm + ấm nhẹ
        glow = Math.max(glow, k * 0.8);
        fl.push(`saturate(${1 + 0.1 * k}) sepia(${0.12 * k})`);
        break;
      case 'beat': {
        const bt = (beats && beats.length ? beats : Array.from({length: Math.ceil((e.end - e.start) * 2) + 1}, (_, n) => e.start + n * 0.5)).map((x) => Math.round(x * FPS));
        const last = bt.filter((x) => x <= f && x >= a).pop();
        if (last !== undefined) tr.push(`scale(${1 + 0.07 * k * Math.exp(-(f - last) / 4)})`);
        break;
      }
    }
  }
  if (glitch > 0) fl.push('url(#fxglitch)');
  if (glow > 0) fl.push('url(#fxglow)');
  if (rgb > 0) fl.push('url(#fxrgb)');
  const defs =
    glitch > 0 || rgb > 0 || glow > 0 ? (
      <svg width="0" height="0" style={{position: 'absolute'}}>
        <defs>
          <filter id="fxglitch" x="0" y="0" width="100%" height="100%">
            <feTurbulence type="fractalNoise" baseFrequency="0.0002 0.06" numOctaves={1} seed={Math.floor(f / 2)} result="n" />
            <feDisplacementMap in="SourceGraphic" in2="n" scale={70 * glitch} xChannelSelector="R" yChannelSelector="A" />
          </filter>
 <filter id="fxglow" x="0" y="0" width="100%" height="100%" colorInterpolationFilters="sRGB">
            <feColorMatrix in="SourceGraphic" type="matrix" values={`1.6 0 0 0 -0.62  0 1.6 0 0 -0.62  0 0 1.6 0 -0.62  0 0 0 1 0`} result="hi" />
            <feGaussianBlur in="hi" stdDeviation={10 + 26 * glow} result="b" />
            <feComponentTransfer in="b" result="b2"><feFuncA type="linear" slope={1} /><feFuncR type="linear" slope={0.5 + glow} /><feFuncG type="linear" slope={0.5 + glow} /><feFuncB type="linear" slope={0.5 + glow} /></feComponentTransfer>
            <feBlend in="SourceGraphic" in2="b2" mode="screen" />
          </filter>
          <filter id="fxrgb" x="0" y="0" width="100%" height="100%" colorInterpolationFilters="sRGB">
            <feColorMatrix in="SourceGraphic" type="matrix" values="1 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 1 0" result="r" />
            <feOffset in="r" dx={-10 * rgb} dy="0" result="r2" />
            <feColorMatrix in="SourceGraphic" type="matrix" values="0 0 0 0 0  0 1 0 0 0  0 0 0 0 0  0 0 0 1 0" result="g" />
            <feColorMatrix in="SourceGraphic" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 1 0 0  0 0 0 1 0" result="b" />
            <feOffset in="b" dx={10 * rgb} dy="0" result="b2" />
            <feBlend in="r2" in2="g" mode="screen" result="rg" />
            <feBlend in="rg" in2="b2" mode="screen" />
          </filter>
        </defs>
      </svg>
    ) : null;
  if (vhs > 0)
    over.push(
      <AbsoluteFill key="vhs" style={{background: `repeating-linear-gradient(0deg, rgba(0,0,0,${0.18 * vhs}) 0 2px, transparent 2px 5px)`, mixBlendMode: 'multiply'}} />,
      <AbsoluteFill key="vhs2" style={{background: `linear-gradient(180deg, transparent ${(f * 7) % 100}%, rgba(255,255,255,${0.08 * vhs}) ${(f * 7) % 100 + 2}%, transparent ${(f * 7) % 100 + 6}%)`}} />,
    );
  return {style: {transform: tr.join(' ') || undefined, filter: fl.join(' ') || undefined} as React.CSSProperties, over, defs};
};

/** xem trước MẪU (thư viện mẫu của trình chỉnh sửa): vẽ các khối trên nền minh hoạ, không cần video */
export const ElPreview: React.FC<{els: any[]; theme: Theme; style?: Style}> = ({els, theme, style}) => {
  S.style = style || {};
  const list = els.map((e, i) => ({...e, _i: i})) as El[];
  const ffx = useFrameFx(list.filter((e) => e.type === 'fx'));
  const zfx = useZoomFx(list.filter((e) => e.type === 'zoom'));
  const vis = list.filter((e) => !['fx', 'zoom', 'audio', 'sfx'].includes(e.type)).sort((a, b) => zOf(a) - zOf(b));
  return (
    <ThemeCtx.Provider value={theme}>
      <AbsoluteFill style={{background: '#0b0f17'}}>
        {ffx.defs}
        <AbsoluteFill style={ffx.style}>
          <AbsoluteFill style={{transform: `translate(${zfx.tx}px, ${zfx.ty}px) scale(${zfx.k})`, transformOrigin: zfx.origin}}>
            {/* nền minh hoạ: trời chiều + toà nhà + người (để thấy chữ / hiệu ứng nằm trên video thế nào) */}
            <AbsoluteFill style={{background: 'linear-gradient(180deg, #2a3f66 0%, #6b6f9c 38%, #e7a07a 62%, #3a3550 63%, #1b1f2e 100%)'}} />
            <div style={{position: 'absolute', left: 640, top: 520, width: 220, height: 220, borderRadius: 110, background: '#ffe6b0', boxShadow: '0 0 120px 40px rgba(255,200,140,0.6)'}} />
            {[[60, 700, 200, 560], [300, 560, 160, 700], [820, 640, 200, 620]].map(([x, y, w, h], i) => <div key={i} style={{position: 'absolute', left: x, top: y, width: w, height: h, background: '#232a3d', boxShadow: 'inset 0 0 0 6px #2c3550'}} />)}
            <div style={{position: 'absolute', left: 340, top: 1080, width: 400, height: 460, borderRadius: 200, background: 'linear-gradient(180deg, #c99c7c, #8a634c)'}} />
            <div style={{position: 'absolute', left: 200, top: 1460, width: 680, height: 600, borderRadius: '340px 340px 0 0', background: 'linear-gradient(180deg, #34507e, #1c2a44)'}} />
          </AbsoluteFill>
          {vis.map((e) => <ElSeq key={e._i} e={e} p={{theme, sfxVolume: 0} as any} />)}
          {ffx.over}
        </AbsoluteFill>
      </AbsoluteFill>
    </ThemeCtx.Provider>
  );
};

/** khối mẫu cho ảnh minh họa phong cách (StylePreview): nhãn ngày + chip + thẻ số theo lớp da của phong cách */
export const DemoBlocks: React.FC<{theme: Theme}> = ({theme}) => {
  const chart = /chart/.test(String((S.style as any).graphics?.ghiChu || ''));
  return (
    <ThemeCtx.Provider value={theme}>
      <DayBadge day={3} total={30} theme={theme} />
      <Chip icon="MapPin" text="Gần trung tâm" y={chart ? 760 : 820} dur={1000} />
      {chart ? (
        <Chart e={{kind: 'bar', title: 'Giá TB (tr/m²)', data: 'Q1: 120, Q2: 95, Thủ Đức: 60', y: 900, height: 470, start: 0}} dur={1000} theme={theme} />
      ) : (
        <RangeCard label="Diện tích" value="72 m²" dur={1000} y={1010} />
      )}
    </ThemeCtx.Provider>
  );
};

export const EditPlan: React.FC<PlanProps> = (p) => {
  S.style = p.style || {};
  MXF.v = p.mainXf;
  useFonts(p);
  const cutFx = p.cutFx || 'none';
  const zoom = useCutZoom(cutFx.includes('bump') ? p.cuts || [] : []);
  const flashes = [...(cutFx.includes('flash') ? p.cuts || [] : []), ...flashJoins(p.segments, p.transition || 'auto', p.joinFx, p.clipBounds)];
  const zfx = useZoomFx((p.elements || []).filter((e) => e && e.type === 'zoom'));
  const {durationInFrames, height: frameH, width: frameW} = useVideoConfig();
  FR.h = frameH;
  FR.w = frameW; // khung hình (9:16 / 4:5 / 1:1 / 16:9): các khối đọc FR.h thay cho 1920
  BLURS.v = (p.blurs || []).filter((b) => b && !b.off && Array.isArray(b.track) && b.track.length);
  const filter = colorFilter(p.color);
  const all = !!p.color?.all;
  // khung thấp hơn 1920 -> khối chưa ghi y thì đặt theo tỉ lệ (y mặc định thiết kế cho khung dọc)
  const els0 = (p.elements || []).map((e, i) => (e ? {...e, _i: e._i ?? i, ...(frameH !== 1920 && (e as any).y == null && DEFAULT_Y[e.type] != null ? {y: fy(DEFAULT_Y[e.type])} : {})} : e)).filter((e: any) => e && e.end > e.start && !e.hidden) as El[];
  // khối hiện trong lúc người nói thu nhỏ trên nền SÁNG (giấy be / xanh nhạt) -> chữ tự đổi sang màu mực đậm
  const lightP = els0.filter((e: any) => e.type === 'presenter' && e.mode !== 'full' && !['dark', 'color'].includes(e.bg));
  const els = els0.map((e: any) => (e.type !== 'presenter' && lightP.some((q: any) => e.start >= q.start - 0.05 && e.start < q.end) ? {...e, _light: true} : e)) as El[];
  const hasPerson0 = !!(p.person && p.person.length);
  // vòng quay chưa ghi tâm -> lấy theo mặt người nói (_work/mat.json): tâm ngang = mặt, tâm dọc = ngang ngực
  const orbAt = (e: any) => {
    if ((e.type !== 'orbit' && e.type !== 'photo3d') || (e.cx != null && e.cy != null) || !p.faces?.faces?.length) return e;
    const st = p.faces.step || 0.5, F = p.faces.faces;
    const bx: number[][] = [];
    for (let k = 0; k <= 4; k++) {
      const tt = outToSrcT(p.segments, e.start + ((e.end - e.start) * k) / 4);
      const fr = F[Math.max(0, Math.min(F.length - 1, Math.round(tt / st)))];
      if (fr && fr.length >= 5) bx.push(fr);
    }
    if (!bx.length) return e;
    const av = (j: number) => bx.reduce((s2, b) => s2 + b[j], 0) / bx.length;
    const x = av(1) + av(3) / 2, y = av(2) + av(4) / 2, h = av(4);
    if (e.type === 'photo3d') return {...e, cx: e.cx ?? x / FR.w, cy: e.cy ?? Math.min(FR.h * 0.67, y + h * 1.1), rx: e.rx ?? Math.max(300, Math.min(440, h * 2.3))};
    return {...e, cx: e.cx ?? x / FR.w, cy: e.cy ?? Math.min(FR.h * 0.67, y + h * 0.85), rx: e.rx ?? Math.max(330, Math.min(470, h * 2.6))};
  };
  // vòng quay quanh người: có lớp người -> tách 2 lớp (nửa sau nằm SAU người, nửa trước đè lên người)
  const els1 = hasPerson0 ? els.map(orbAt).flatMap((e: any) => ((e.type === 'orbit' || e.type === 'photo3d') && e.behind !== false ? [{...e, _half: 'back', z: -10, behind: true}, {...e, _half: 'front', behind: false, z: typeof e.z === 'number' && e.z > 0 ? e.z : undefined}] : [e])) as El[] : (els.map(orbAt) as El[]);
  const hasPerson = hasPerson0;
  // xếp theo LỚP (z), cùng lớp thì theo thứ tự khối; lớp âm nằm sau người (khi đã tách người)
  const byZ = (a: El, b: El) => zOf(a) - zOf(b) || (a._i ?? 0) - (b._i ?? 0);
  const vis = els1.filter((e) => e.type !== 'audio' && e.type !== 'zoom' && e.type !== 'sfx' && e.type !== 'fx' && e.type !== 'presenter');
  const behind = hasPerson ? vis.filter(isBehind).sort(byZ) : [];
  const front = vis.filter((e) => !behind.includes(e)).sort(byZ);
  const capZ = p.capZ ?? CAP_Z;
  type Item = {k: 'el'; z: number; e: El} | {k: 'cap' | 'flash' | 'color'; z: number};
  const items: Item[] = [
    ...front.map((e): Item => ({k: 'el', z: zOf(e), e})),
    ...(p.captions ? [{k: 'cap', z: capZ} as Item] : []),
    {k: 'flash', z: Math.max(capZ, 20) + 0.001} as Item,
    ...(all ? [{k: 'color', z: 15} as Item] : []),
  ].sort((a, b) => a.z - b.z || (a.k === 'el' ? 1 : 0) - (b.k === 'el' ? 1 : 0) || (a.k === 'el' && b.k === 'el' ? ((a as any).e._i ?? 0) - ((b as any).e._i ?? 0) : 0));
  const rest = els.filter((e) => e.type === 'audio' || e.type === 'zoom' || e.type === 'sfx');
  const ffx = useFrameFx(els.filter((e) => e.type === 'fx'), p.beats);
  // chế độ người nói (thẻ / nửa màn / góc / cửa sổ)
  const gf = useCurrentFrame();
  const shY = splitShift(els, gf / FPS, (t) => {
    const c = faceCenter(p.faces, outToSrcT(p.segments, t));
    return c ? c[1] : null;
  });
  const mainT = {transform: `translate(${zfx.tx}px, ${zfx.ty + shY}px) scale(${zoom * zfx.k})`, transformOrigin: zfx.origin};
  // cỡ cảnh (toàn/trung/cận) — đổi ở chỗ ngắt câu, hoà trộn nhẹ giữa cỡ cũ và cỡ mới (shotFade giây, 0 = cắt thẳng)
  const shotTf = (x: null | {s: number; x?: number; y?: number}): React.CSSProperties | undefined =>
    x && x.s > 1.001 ? {transform: `scale(${x.s})`, transformOrigin: `${(x.x ?? 0.5) * 100}% ${(x.y ?? 0.45) * 100}%`} : undefined;
  const {shot, prevShot, shotK} = (() => {
    const L = p.shots;
    if (!L || !L.length) return {shot: null, prevShot: null, shotK: 1};
    const st = outToSrcT(p.segments, gf / FPS);
    let i = -1;
    for (let j = 0; j < L.length; j++) if (L[j].t <= st + 1e-3) i = j;
    const D = Math.max(0, p.shotFade ?? 0.5);
    const cur = i >= 0 ? L[i] : null, prev = i > 0 ? L[i - 1] : null;
    const el = cur ? st - cur.t : 99;
    return {shot: cur, prevShot: prev && D > 0 && el < D ? prev : null, shotK: D > 0 ? ease(Math.min(1, el / D)) : 1};
  })();
  const shotT = shotTf(shot);
  // phong cách có style.presenter (vd khung tranh thủy mặc) -> áp cả video nếu plan chưa có khối người nói nào
  const sp = (S.style as any).presenter;
  const presEls = sp && !els.some((e: any) => e.type === 'presenter') ? [...els, {type: 'presenter', start: 0, end: (p.durationSec || 9999) + 1, inDur: 0.01, outDur: 0.01, ...sp}] : els;
  const pres = presenterAt(presEls, gf / FPS, (t) => {
    const c = faceCenter(p.faces, outToSrcT(p.segments, t));
    return c ? c[1] : null;
  });
  const pw = pres ? presenterWrap(pres.st, pres.e.mode) : null;
  const wrapP = (node: React.ReactNode) => (pw ? <AbsoluteFill style={pw.outer}><AbsoluteFill style={pw.inner}>{node}</AbsoluteFill></AbsoluteFill> : node);
  const mv = p.music?.volume ?? 0.15;
  return (
    <ThemeCtx.Provider value={p.theme}>
      <FaceCtx.Provider value={{faces: p.faces, segs: p.segments, p}}>
      <BeatCtx.Provider value={p.beats || []}>
      <AbsoluteFill style={{background: 'black'}} data-comp="1">
        {ffx.defs}
        <AbsoluteFill style={ffx.style}>
        {pres && <PresenterBg bg={pres.bg} color={pres.bgColor} show={pres.show} />}
        {anyReveal(p) && (p.mainXf?.bg || 'black') !== 'black' && wrapP(
          p.mainXf?.bg === 'blur' ? (
            <AbsoluteFill style={{...mainT, filter: `${filter || ''} blur(42px) brightness(0.62)`, transform: `${mainT.transform} scale(1.15)`}}>
              <MainVideo tail={tailOf(p)} fit={(p as any).mainFit} muteAt={(a) => segMuted(p, a)} src={p.videoSrc} segments={p.segments} volume={0} fx={p.transition} joinFx={p.joinFx} clips={p.clipBounds} noXf />
            </AbsoluteFill>
          ) : (
            <AbsoluteFill style={{background: p.mainXf!.bg}} />
          ),
        )}
        {(S.style as any).backdrop?.type === 'ink' ? (
          // nền vẽ phủ cả khung (video chỉ có tiếng): tranh thủy mặc chuyển động nhẹ, nằm dưới chữ / ảnh minh họa
          <InkScape pos="full" palette={(S.style as any).backdrop.palette || 'color'} items={(S.style as any).backdrop.items} drift />
        ) : null}
        {wrapP(
          <AbsoluteFill style={(S.style as any).backdrop ? {...mainT, opacity: 0} : mainT /* có nền vẽ: video ẩn hình, vẫn giữ tiếng */}>
            <AbsoluteFill style={shotT}>
              <MainVideo tail={tailOf(p)} fit={(p as any).mainFit} muteAt={(a) => segMuted(p, a)} src={p.videoSrc} segments={p.segments} volume={p.videoVolume ?? 1} filter={filter} fx={p.transition} joinFx={p.joinFx} clips={p.clipBounds} segXf={p.segXf} keepBand={(p as any).keepBand} audAt={(a) => segAudOf(p, a)} />
            </AbsoluteFill>
            {prevShot && (
              <AbsoluteFill style={{...(shotTf(prevShot) || {}), opacity: 1 - shotK}}>
                <MainVideo tail={tailOf(p)} fit={(p as any).mainFit} muteAt={(a) => segMuted(p, a)} src={p.videoSrc} segments={p.segments} volume={0} filter={filter} fx={p.transition} joinFx={p.joinFx} clips={p.clipBounds} segXf={p.segXf} keepBand={(p as any).keepBand} />
              </AbsoluteFill>
            )}
          </AbsoluteFill>,
        )}
        {pw && pw.bar > 0 && <div style={{position: 'absolute', left: 0, right: 0, top: pw.bar - 5, height: 10, background: '#111'}} />}
        {pres && pres.e.mode === 'window' && pres.show > 0.5 && (
          <div style={{position: 'absolute', left: pres.st.cx - (FR.w * pres.st.s) / 2 - pres.st.frame, top: pres.st.cy - (FR.h * pres.st.s) / 2 - 54, width: FR.w * pres.st.s + pres.st.frame * 2, height: 54, background: 'white', borderRadius: '22px 22px 0 0', display: 'flex', alignItems: 'center', gap: 12, paddingLeft: 22, opacity: Math.min(1, (pres.show - 0.5) * 2)}}>
            {['#FF5F57', '#FEBC2E', '#28C840'].map((c) => <span key={c} style={{width: 18, height: 18, borderRadius: 9, background: c}} />)}
          </div>
        )}
        {!all && !hasPerson && <ColorOverlay c={p.color} />}
        {behind.map((e, i) => (
          <ElSeq key={'s' + i} e={e} p={p} filter={all ? filter : undefined} />
        ))}
        {hasPerson && (
          wrapP(
            <AbsoluteFill style={mainT}>
              <AbsoluteFill style={shotT}>
                <PersonLayer p={p} filter={filter} />
              </AbsoluteFill>
            </AbsoluteFill>,
          )
        )}
        {!all && hasPerson && <ColorOverlay c={p.color} />}
        <FrameOverlay />
        {items.map((it, n) =>
          it.k === 'el' ? (
            <ElSeq key={'e' + (it.e._i ?? n)} e={it.e} p={p} filter={all ? filter : undefined} />
          ) : it.k === 'cap' ? (
            <AbsoluteFill key="cap" style={{pointerEvents: 'none', transform: (p as any).captionX ? `translateX(${(p as any).captionX}px)` : undefined}} data-el="cap">
              <Captions pages={p.captions!} top={p.captionTop ?? Math.min(fy(1390), FR.h - 200)} from={p.captionsFrom ?? 0} theme={p.theme} size={p.captionSize} upper={p.captionUpper} />
            </AbsoluteFill>
          ) : it.k === 'color' ? (
            <ColorOverlay key="color" c={p.color} />
          ) : (
            <React.Fragment key="flash">
              {flashes.map((c, i) => (
                <Sequence key={'c' + i} from={Math.max(0, Math.round(c * FPS) - 2)} durationInFrames={10}>
                  <Flash />
                </Sequence>
              ))}
            </React.Fragment>
          ),
        )}
        {ffx.over}
        {p.brandMark ? <BrandLayer b={p.brandMark} dodge={els.some((e) => e.type === 'dayBadge')} /> : null}
        </AbsoluteFill>
        {rest.map((e, i) => (
          <ElSeq key={'r' + i} e={e} p={p} />
        ))}
        {/* tiếng hiệu ứng: của khối, checklist, điểm nối (xem sfxEvents) */}
        {sfxEvents({...p, elements: els}).map((ev, k) =>
          ev.vol > 0 ? (
            <Sequence key={'sx' + k} from={Math.round(ev.t * FPS)} durationInFrames={ev.frames}>
              <Audio src={sfxSrc(ev.s)} volume={ev.vol} />
            </Sequence>
          ) : null,
        )}
        {p.music?.src && mv > 0 && (
          <Audio
            src={mediaSrc(p.music.src)}
            loop
            playbackRate={(p.music as any).rate > 0 ? (p.music as any).rate : 1}
            startFrom={Math.round((p.music.from ?? 0) * FPS)}
            volume={(f) => mv * interpolate(f, [0, 15, durationInFrames - 45, durationInFrames], [0, 1, 1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})}
          />
        )}
      </AbsoluteFill>
      </BeatCtx.Provider>
      </FaceCtx.Provider>
    </ThemeCtx.Provider>
  );
};

/* ===== CHỈ TIẾNG (bộ dựng nhanh): cùng tiếng như EditPlan — tiếng gốc từng đoạn (vuốt / mờ chồng ở điểm nối), ảnh trám có tiếng,
   khối âm thanh, tiếng hiệu ứng, nhạc nền — nhưng không vẽ hình nên Remotion dựng tiếng rất nhanh ===== */
export const AudioPlan: React.FC<PlanProps> = (p) => {
  S.style = p.style || {};
  const {durationInFrames} = useVideoConfig();
  const url = mediaSrc(p.videoSrc);
  const vol0 = p.videoVolume ?? 1;
  const segs = p.segments;
  const els = (p.elements || []).map((e, i) => (e ? {...e, _i: e._i ?? i} : e)).filter((e: any) => e && e.end > e.start && !e.hidden) as El[];
  const mv = p.music?.volume ?? 0.15;
  let main: React.ReactNode = null;
  if (!segs || !segs.length) {
    const v = segMuted(p, 0) ? 0 : vol0;
    const wa = segAudOf(p, 0);
    main = v > 0 ? <Audio src={url} volume={(f) => v * wa.v * fadeK(f, durationInFrames, wa.fi, wa.fo)} /> : null;
  } else {
    const n = segs.length;
    const types = segs.slice(0, -1).map((_, i) => joinType(segs, i, p.transition || 'auto', p.joinFx, p.clipBounds));
    let acc = 0;
    main = segs.map(([a, b], i) => {
      const from = Math.round(acc * FPS);
      acc += b - a;
      const len = Math.max(1, Math.round(acc * FPS) - from);
      const next = i < n - 1 ? types[i] : null, prev = i ? types[i - 1] : null;
      const ext = next && OVERLAP.has(next) ? TR : 0;
      const fadeInA = prev && OVERLAP.has(prev) ? TR : prev ? AF : 0, fadeOutA = next && OVERLAP.has(next) ? TR : next ? AF : 0;
      const total = len + ext;
      const v = segMuted(p, a) ? 0 : vol0;
      if (v <= 0) return null;
      const sa = segAudOf(p, a);
      const vol = (fr: number) => {
        let k = 1;
        if (fadeInA > 0) k *= Math.min(1, (fr + 1) / fadeInA);
        if (fadeOutA > 0) k *= Math.min(1, Math.max(0, (total - fr) / fadeOutA));
        return v * k * sa.v * fadeK(fr, len, sa.fi, sa.fo);
      };
      return (
        <Sequence key={'m' + i} from={from} durationInFrames={total}>
          <Audio src={url} startFrom={Math.round(a * FPS)} volume={vol} />
        </Sequence>
      );
    });
  }
  return (
    <>
      {main}
      {els.map((e: any, i) => {
        const d = Math.max(1, Math.round((e.end - e.start) * FPS));
        const from = Math.round(e.start * FPS);
        if (e.type === 'audio' && e.src)
          return <Sequence key={'a' + i} from={from} durationInFrames={d}><AudioEl e={e} dur={d} /></Sequence>;
        if ((e.type === 'broll' || e.type === 'pip') && e.src && e.volume > 0 && !e.freeze && /\.(mp4|mov|webm|m4v|mkv)(\?|$)/i.test(e.src))
          return <Sequence key={'v' + i} from={from} durationInFrames={d}><Audio src={mediaSrc(e.src)} startFrom={Math.round((e.from ?? 0) * 30)} volume={e.volume} playbackRate={e.rate || 1} /></Sequence>;
        return null;
      })}
      {sfxEvents({...p, elements: els}).map((ev, k) =>
        ev.vol > 0 ? (
          <Sequence key={'sx' + k} from={Math.round(ev.t * FPS)} durationInFrames={ev.frames}>
            <Audio src={sfxSrc(ev.s)} volume={ev.vol} />
          </Sequence>
        ) : null,
      )}
      {p.music?.src && mv > 0 && (
        <Audio
          src={mediaSrc(p.music.src)}
          loop
          playbackRate={(p.music as any).rate > 0 ? (p.music as any).rate : 1}
          startFrom={Math.round((p.music.from ?? 0) * FPS)}
          volume={(f) => mv * interpolate(f, [0, 15, durationInFrames - 45, durationInFrames], [0, 1, 1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})}
        />
      )}
    </>
  );
};
