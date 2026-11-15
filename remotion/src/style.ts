/* Phong cách toàn cục của video (plan.json -> "style"), lấy từ video mẫu hoặc bộ phong cách đã lưu.
   Mọi khối đồ họa đọc S.style để biết font, kiểu chữ, kiểu phụ đề, kiểu chèn minh họa. */
import {interpolate, spring} from 'remotion';
import {fontCss, fontWeight} from './fonts';

export type TextAnim = 'pop' | 'bounce' | 'fade' | 'up' | 'down' | 'left' | 'right' | 'blur' | 'zoomOut' | 'wipe' | 'type' | 'words' | 'spin' | 'drop' | 'flip' | 'none'
  // chữ động từng ký tự / từng từ (kinetic typography)
  | 'stagger' | 'wave' | 'flip3d' | 'maskUp' | 'typeCursor' | 'glitch' | 'scramble' | 'rise' | 'spoken';
export type TextOut = 'fade' | 'pop' | 'up' | 'down' | 'left' | 'right' | 'blur' | 'zoom' | 'spin' | 'wipe' | 'none';
export type TextLook = 'plain' | 'outline' | 'clean' | 'shadow' | 'solid' | 'highlight' | 'neon' | 'box' | 'gold' | 'tag' | 'skew' | 'tape' | 'pill2' | 'dashed' | 'chat';
export type CapPreset = 'tiktok' | 'karaoke' | 'box' | 'wordbox' | 'pop' | 'single' | 'minimal' | 'outline';

export type TextStyle = {
  look?: TextLook;
  color?: string; // màu chữ
  bg?: string; // màu nền (solid / highlight)
  stroke?: number; // độ dày viền (px)
  strokeColor?: string;
  shadow?: 'none' | 'soft' | 'hard' | 'glow';
  anim?: TextAnim; // kiểu hiện
  out?: TextOut; // kiểu ẩn
  upper?: boolean;
  radius?: number;
  size?: number;
  weight?: number;
  hlColor?: string; // màu từ khóa được tô
  hlStyle?: 'color' | 'marker' | 'box'; // từ khóa: đổi màu | bôi vàng bút dạ quang (2 thanh + chấm tay cầm) | ô đen chữ trắng
  spacing?: number; // giãn chữ (px)
  ease?: string; // spring | smooth | snappy | bouncy | elastic | linear
  mblur?: boolean | number; // nhòe chuyển động
};

export type Style = {
  font?: string; // font chữ đồ họa
  heading?: string; // font chữ to / tiêu đề (mặc định = font)
  text?: TextStyle; // mặc định cho chữ tự do
  captions?: {
    preset?: CapPreset;
    font?: string;
    size?: number;
    weight?: number;
    color?: string;
    active?: string; // màu từ đang đọc
    activeBg?: string; // nền từ đang đọc (wordbox) / nền dòng (box)
    stroke?: number;
    strokeColor?: string;
    upper?: boolean;
    anim?: 'pop' | 'fade' | 'up' | 'none';
  };
  broll?: {
    enter?: 'zoom' | 'slide' | 'up' | 'fade' | 'cut' | 'whip' | 'circle';
    exit?: 'fade' | 'cut' | 'slide' | 'zoom';
    kenburns?: boolean;
    overlay?: boolean; // phủ tối trên/dưới cho chữ dễ đọc
    pip?: 'card3d' | 'clean' | 'round' | 'polaroid';
    // vùng ảnh trám: full (che cả khung) | top (nửa trên) | bottom (nửa dưới) — người nói vẫn thấy ở phần còn lại,
    // mép giao giữa 2 hình hoà trộn mờ dần (feather px, 0 = cắt thẳng); split = tỉ lệ chiều cao vùng trám (0.3–0.6)
    area?: 'full' | 'top' | 'bottom';
    split?: number;
    feather?: number;
    seam?: string; // đường kẻ mảnh ở mép giao (màu), bỏ = không
    follow?: boolean; // true = tự dời video chính cho mặt khỏi bị che (mặc định KHÔNG dời)
  };
  templates?: boolean; // false = phong cách này không dùng các khối 3D xanh có sẵn
  // lớp da của các khối có sẵn (thẻ giá, nhãn, checklist, nút kêu gọi, nhãn ngày…): 3d (cũ, bóng bẩy) | flat (kính tối, viền mảnh,
  // chữ sạch — hiện đại) | light (thẻ trắng, chữ đậm màu thương hiệu)
  skin?: '3d' | 'flat' | 'light' | 'classic' | 'med' | 'luxe' | 'indochine' | 'japandi' | 'scrap' | 'ticket' | 'podcast' | 'info' | 'news';
  // khung trang trí phủ cả video: classic (viền chỉ kép + hoa văn góc) | arch (viền vòm) | corners (góc chữ L) | letterbox (dải đen)
  // | grain (hạt phim); nhiều kiểu: mảng ['letterbox','grain']; màu: {type, color}
  frame?: any;
  // khung người nói cho cả video (vd {mode: 'window', bg: 'ink-color', s: 0.62, y: 1180}) khi plan không có khối presenter
  presenter?: any;
  // nền vẽ phủ cả khung thay cho hình video (video chỉ có tiếng): {type: 'ink', palette: mono|color|night|dawn, items?}
  backdrop?: any;
  // chuyển động chung: {ease: 'smooth'|'snappy'|'bouncy'|'elastic', mblur: true} — áp cho mọi chữ / khối có hiệu ứng vào-ra
  motion?: {ease?: string; mblur?: boolean | number};
  accent?: string; // màu nhấn cho da flat/light (mặc định theme.light / theme.mid)
  // bố cục học từ video mẫu: căn lề mặc định của chữ, lề ngang, vùng hay đặt chữ, icon đứng phía nào của chữ
  layout?: {
    align?: 'center' | 'left' | 'right';
    marginX?: number; // px tính trên khung 1080
    textZone?: 'top' | 'middle' | 'bottom';
    iconPos?: 'left' | 'right' | 'above' | 'below' | 'none';
    maxBlocks?: number; // số khối chữ/hình tối đa cùng lúc
    stackGap?: number; // khoảng cách giữa các dòng/khối xếp chồng (px)
  };
  // cách chọn icon: emoji hay icon nét (lucide) / icon đặc, nền phía sau, màu, bộ icon hay dùng
  icons?: {
    kind?: 'emoji' | 'lucide' | 'filled' | 'none';
    bg?: 'badge' | 'circle' | 'square' | 'none'; // badge = huy hiệu 3D (mặc định cũ)
    bgColor?: string;
    color?: string;
    stroke?: number;
    size?: number;
    set?: string[]; // icon/emoji hay dùng (Claude rút từ icon-mau.jpg)
    map?: Record<string, string>; // ý -> icon theo cách mẫu chọn (vd {"giá": "💰"}) — Claude dùng khi viết plan
  };
};

/** phong cách đang dùng (EditPlan gán lúc dựng) */
export const S: {style: Style} = {style: {}};

export const headFont = () => fontCss(S.style.heading || S.style.font);
export const bodyFont = () => fontCss(S.style.font);
export {fontCss, fontWeight};

const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;

/** kiểu hiện/ẩn chữ -> style cho khung chữ. f: khung hiện tại (từ lúc xuất hiện), dur: số khung */
// inF / outF: số khung của hiệu ứng vào / ra (mặc định 8 / 7 khung); đổi được để hiệu ứng nhanh/chậm hơn
// bộ đường cong chuyển động (giống easing của AE): mặc định | smooth (mượt, không nảy) | snappy (nhanh gọn) | bouncy (nảy)
// | elastic (nảy đàn hồi nhiều) | linear
export const EASES: Record<string, {damping: number; stiffness: number; mass?: number}> = {
  spring: {damping: 14, stiffness: 160},
  smooth: {damping: 200, stiffness: 90},
  snappy: {damping: 22, stiffness: 320},
  bouncy: {damping: 8, stiffness: 190},
  elastic: {damping: 5, stiffness: 140},
};
export type AnimOpts = {ease?: string; mblur?: boolean | number};
const animCore = (anim: TextAnim, out: TextOut, f0: number, dur: number, fps: number, inF?: number, outF?: number, ease?: string) => {
  const ki = inF && inF > 0 ? 8 / inF : 1;
  const f = f0 * ki; // thời gian "đã co giãn" cho hiệu ứng vào
  const oF = Math.max(1, Math.min(dur - 1, outF && outF > 0 ? outF : 7));
  const lin = interpolate(f, [0, 8], [0, 1], clamp);
  const cfg = EASES[ease || ''] || EASES.spring;
  const inn = ease === 'linear' ? lin : spring({frame: f, fps, config: cfg});
  const bnc = ease === 'linear' ? lin : spring({frame: f, fps, config: ease && EASES[ease] ? cfg : {damping: 7, stiffness: 180}});
  const o = interpolate(f0, [dur - oF, dur], [1, 0], clamp); // 1 -> 0 lúc ẩn
  let tx = 0, ty = 0, sc = 1, op = 1, blur = 0, rot = 0, ry = 0;
  let clip: string | undefined;
  switch (anim) {
    case 'pop': sc = 0.6 + 0.4 * inn; op = interpolate(f, [0, 4], [0, 1], clamp); break;
    case 'bounce': sc = bnc; break;
    case 'fade': op = lin; break;
    case 'up': ty = (1 - inn) * 90; op = lin; break;
    case 'down': ty = -(1 - inn) * 90; op = lin; break;
    case 'left': tx = (1 - inn) * 160; op = lin; break;
    case 'right': tx = -(1 - inn) * 160; op = lin; break;
    case 'blur': blur = (1 - lin) * 22; op = lin; sc = 1.08 - 0.08 * lin; break;
    case 'zoomOut': sc = 1.8 - 0.8 * inn; op = lin; break;
    case 'wipe': clip = `inset(-20% ${(1 - interpolate(f, [0, 12], [0, 1], clamp)) * 100}% -20% -5%)`; break;
    case 'spin': rot = -(1 - inn) * 180; sc = inn; op = lin; break;
    case 'drop': ty = -(1 - bnc) * 260; op = lin; break;
    case 'flip': ry = (1 - inn) * 90; op = lin; break;
    default: break; // type / words / kinetic: xử lý trong khối chữ
  }
  if (out !== 'none' && o < 1) {
    const k = 1 - o;
    op *= o;
    if (out === 'pop') sc *= 1 - 0.4 * k;
    if (out === 'up') ty -= 70 * k;
    if (out === 'down') ty += 70 * k;
    if (out === 'left') tx -= 160 * k;
    if (out === 'right') tx += 160 * k;
    if (out === 'blur') blur += 20 * k;
    if (out === 'zoom') sc *= 1 + 0.6 * k;
    if (out === 'spin') { rot += 180 * k; sc *= 1 - 0.7 * k; }
    if (out === 'wipe') { op = op / Math.max(0.001, o); clip = `inset(-20% -5% -20% ${k * 100}%)`; }
  }
  return {tx, ty, sc, op, blur, rot, ry, clip};
};
export const animStyle = (anim: TextAnim, out: TextOut, f0: number, dur: number, fps: number, inF?: number, outF?: number, opts?: AnimOpts): React.CSSProperties => {
  const g: any = (S.style as any).motion || {};
  const ease = opts?.ease || g.ease;
  const c = animCore(anim, out, f0, dur, fps, inF, outF, ease);
  let blur = c.blur;
  // nhòe chuyển động giả: đo vận tốc giữa 2 khung liền nhau, chạy nhanh thì nhòe (giống motion blur của AE)
  const mb = opts?.mblur ?? g.mblur;
  if (mb && f0 > 0) {
    const p = animCore(anim, out, f0 - 1, dur, fps, inF, outF, ease);
    const v = Math.hypot(c.tx - p.tx, c.ty - p.ty) + Math.abs(c.sc - p.sc) * 400 + Math.abs(c.rot - p.rot) * 3 + Math.abs(c.ry - p.ry) * 3;
    blur += Math.min(14, v * 0.22 * (typeof mb === 'number' ? mb : 1));
  }
  return {
    transform: `translate(${c.tx}px, ${c.ty}px) scale(${c.sc})${c.rot ? ` rotate(${c.rot}deg)` : ''}${c.ry ? ` perspective(900px) rotateY(${c.ry}deg)` : ''}`,
    opacity: c.op,
    filter: blur > 0.3 ? `blur(${blur.toFixed(2)}px)` : undefined,
    clipPath: c.clip,
  };
};

/** đổ bóng chữ */
export const shadowCss = (kind: string | undefined, color: string) =>
  kind === 'none'
    ? 'none'
    : kind === 'hard'
      ? `6px 7px 0 ${color}`
      : kind === 'glow'
        ? `0 0 18px ${color}, 0 0 42px ${color}`
        : '0 8px 24px rgba(0,0,0,0.55)';

/** tách chữ thành các đoạn có/không tô màu theo danh sách từ khóa */
export const splitHl = (text: string, hl?: string[] | string) => {
  const list = (Array.isArray(hl) ? hl : hl ? [hl] : []).filter(Boolean);
  if (!list.length) return [{t: text, hl: false}];
  const re = new RegExp('(' + list.map((s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|') + ')', 'gi');
  return text.split(re).filter((s) => s !== '').map((t) => ({t, hl: list.some((h) => h.toLowerCase() === t.toLowerCase())}));
};

export const skinOf = (): string => (S.style.skin as any) || '3d';
