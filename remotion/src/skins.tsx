/* LỚP DA của các khối có sẵn (thẻ giá, nhãn, thẻ số, chữ lớn, checklist, nút kêu gọi, nhãn ngày) + KHUNG TRANG TRÍ cả video.
   Mỗi lớp da có hình khối riêng (nền thẻ, viền, bo góc, hoa văn, kiểu chữ nhãn), không chỉ đổi màu. */
import {InkScape} from './Ink';
import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {S, skinOf} from './style';

type Theme = {light: string; mid: string; dark: string; gold1: string; gold2: string};
export type SkinDef = {
  light: boolean; // thẻ sáng (chữ tối)
  card: (t: Theme, ac: string) => React.CSSProperties;
  ink: (t: Theme) => string;
  accent: (t: Theme) => string;
  big?: (t: Theme, ac: string) => React.CSSProperties; // chữ lớn (giá, số, chữ to)
  radius: (n: number) => number | string;
  arch?: boolean; // thẻ lớn có đỉnh vòm (Địa Trung Hải)
  orn: 'bar' | 'diamond' | 'wave' | 'line' | 'dots';
  label: React.CSSProperties; // nhãn nhỏ (DIỆN TÍCH…)
  cta: 'solid' | 'outline';
  badge: (t: Theme, ac: string) => {bg: string; fg: string};
};
const SERIF = '"Playfair Display", "Merriweather", serif';
const gold = (a = '#F7E7B4', b = '#D4AF37', c = '#9C7A1F'): React.CSSProperties =>
  ({background: `linear-gradient(180deg, ${a} 0%, ${b} 55%, ${c} 100%)`, WebkitBackgroundClip: 'text', backgroundClip: 'text', color: 'transparent'}) as any;

export const SKINS: Record<string, SkinDef> = {
  flat: {
    light: false,
    card: () => ({background: 'rgba(12,16,24,0.62)', backdropFilter: 'blur(22px) saturate(160%)', border: '1.5px solid rgba(255,255,255,0.16)', boxShadow: '0 18px 40px rgba(0,0,0,0.32)'}),
    ink: () => 'white', accent: (t) => t.light, radius: (n) => n, orn: 'bar',
    label: {letterSpacing: 2, textTransform: 'uppercase'}, cta: 'solid', badge: (t, ac) => ({bg: ac, fg: '#0B1220'}),
  },
  light: {
    light: true,
    card: () => ({background: 'rgba(255,255,255,0.94)', border: '1px solid rgba(0,0,0,0.06)', boxShadow: '0 16px 36px rgba(0,0,0,0.22)'}),
    ink: (t) => t.dark, accent: (t) => t.mid, radius: (n) => n, orn: 'bar',
    label: {letterSpacing: 2, textTransform: 'uppercase'}, cta: 'solid', badge: (t, ac) => ({bg: ac, fg: 'white'}),
  },
  // TÂN CỔ ĐIỂN: thẻ ngà, viền chỉ kép màu nhấn (vàng đồng), góc gần vuông, chữ có chân, hoa văn ◆
  classic: {
    light: true,
    card: (t, ac) => ({background: '#FBF7EE', border: `1.5px solid ${ac}`, boxShadow: `0 0 0 7px #FBF7EE, 0 0 0 8.5px ${ac}, 0 22px 44px rgba(40,25,5,0.32)`}),
    ink: () => '#3A2E1F', accent: () => '#B8975A', radius: () => 3, orn: 'diamond',
    big: () => ({fontFamily: SERIF, color: '#3A2E1F', letterSpacing: 1}),
    label: {fontFamily: SERIF, letterSpacing: 5, textTransform: 'uppercase', fontWeight: 700}, cta: 'solid', badge: (t, ac) => ({bg: ac, fg: '#FBF7EE'}),
  },
  // ĐỊA TRUNG HẢI: tường trắng vôi, thẻ đỉnh vòm, xanh Aegean + gạch nung, đường sóng
  med: {
    light: true,
    card: () => ({background: '#FFFFFF', border: '3px solid #F4EDE1', boxShadow: '0 16px 34px rgba(20,50,90,0.22)'}),
    ink: () => '#1D4E89', accent: () => '#C8623E', radius: (n) => n, arch: true, orn: 'wave',
    big: () => ({color: '#1D4E89', letterSpacing: -1}),
    label: {letterSpacing: 3, textTransform: 'uppercase', fontWeight: 800}, cta: 'solid', badge: () => ({bg: '#1D4E89', fg: 'white'}),
  },
  // THƯỢNG LƯU: đen nhám, chữ ánh vàng kim, góc vuông, viền chỉ vàng mảnh, giãn chữ rộng
  luxe: {
    light: false,
    card: () => ({background: 'linear-gradient(160deg, rgba(22,20,16,0.92), rgba(8,8,8,0.92))', border: '1px solid rgba(212,175,55,0.65)', boxShadow: '0 24px 50px rgba(0,0,0,0.55)'}),
    ink: () => '#F3E7C6', accent: () => '#D4AF37', radius: () => 0, orn: 'line',
    big: () => ({...gold(), fontFamily: SERIF, letterSpacing: 2}),
    label: {fontFamily: SERIF, letterSpacing: 8, textTransform: 'uppercase', fontWeight: 400}, cta: 'outline', badge: () => ({bg: 'transparent', fg: '#D4AF37'}),
  },
  // ĐÔNG DƯƠNG: xanh rêu đậm, viền vàng đồng, chữ ngà, góc gần vuông, hoa văn ◆
  indochine: {
    light: false,
    card: () => ({background: 'rgba(15,61,46,0.94)', border: '2px solid #C9A227', boxShadow: 'inset 0 0 0 6px rgba(15,61,46,0.94), inset 0 0 0 7px rgba(201,162,39,0.6), 0 20px 40px rgba(0,0,0,0.4)'}),
    ink: () => '#F3E9D2', accent: () => '#C9A227', radius: () => 4, orn: 'diamond',
    big: () => ({fontFamily: SERIF, color: '#F3E9D2'}),
    label: {fontFamily: SERIF, letterSpacing: 4, textTransform: 'uppercase', fontWeight: 700}, cta: 'solid', badge: () => ({bg: '#C9A227', fg: '#0F3D2E'}),
  },
  // JAPANDI: be gỗ mộc, phẳng không bóng, bo mềm, chữ mảnh nâu, chấm nhỏ
  japandi: {
    light: true,
    card: () => ({background: 'rgba(239,230,216,0.96)', border: 'none', boxShadow: 'none'}),
    ink: () => '#3B3127', accent: () => '#8C6A4A', radius: (n) => Math.min(Number(n) || 0, 22), orn: 'dots',
    big: () => ({color: '#3B3127', fontWeight: 400, letterSpacing: 1}),
    label: {letterSpacing: 4, textTransform: 'uppercase', fontWeight: 400}, cta: 'solid', badge: () => ({bg: '#8C6A4A', fg: '#EFE6D8'}),
  },
};
const HAND = '"Patrick Hand", "Nunito", cursive';
// VLOG / NHẬT KÝ: mẩu giấy dán băng keo vàng, chữ viết tay, hơi nghiêng
SKINS.scrap = {
  light: true,
  card: () => ({
    background: 'linear-gradient(rgba(247,220,107,0.82), rgba(247,220,107,0.82)) top center / 130px 30px no-repeat, #FFFDF7',
    border: 'none', boxShadow: '0 12px 26px rgba(0,0,0,0.28)', rotate: '-1.5deg', paddingTop: 30,
  } as any),
  ink: () => '#2B2B2B', accent: () => '#E76F51', radius: () => 4, orn: 'dots',
  big: () => ({fontFamily: HAND, color: '#2B2B2B', fontWeight: 400}),
  label: {fontFamily: HAND, fontWeight: 400, letterSpacing: 1}, cta: 'solid', badge: () => ({bg: '#E76F51', fg: 'white'}),
};
// DU LỊCH: vé tàu / boarding pass — giấy kem, khuyết lỗ bấm 2 bên, chữ hẹp in hoa
SKINS.ticket = {
  light: true,
  card: () => ({
    background: 'radial-gradient(circle at 0 50%, transparent 20px, #FFF6E6 21px) left / 51% 100% no-repeat, radial-gradient(circle at 100% 50%, transparent 20px, #FFF6E6 21px) right / 51% 100% no-repeat',
    border: 'none', boxShadow: 'none', filter: 'drop-shadow(0 12px 22px rgba(0,0,0,0.3))',
  } as any),
  ink: () => '#1F3B4D', accent: () => '#E07A5F', radius: () => 16, orn: 'line',
  big: () => ({fontFamily: '"Barlow Condensed", sans-serif', color: '#1F3B4D', letterSpacing: 2}),
  label: {fontFamily: '"Barlow Condensed", sans-serif', letterSpacing: 5, textTransform: 'uppercase', fontWeight: 700}, cta: 'solid', badge: () => ({bg: '#1F3B4D', fg: '#FFF6E6'}),
};
// PODCAST: tối mềm, bo lớn, chuyển sắc tím than, nhấn hồng dịu
SKINS.podcast = {
  light: false,
  card: () => ({background: 'linear-gradient(135deg, rgba(36,31,56,0.88), rgba(18,16,30,0.9))', border: '1px solid rgba(255,255,255,0.08)', boxShadow: '0 18px 40px rgba(0,0,0,0.4)'}),
  ink: () => '#F5F3FF', accent: () => '#F9A8D4', radius: (n) => Math.max(26, Number(n) || 0), orn: 'dots',
  label: {letterSpacing: 2, textTransform: 'uppercase', fontWeight: 700}, cta: 'solid', badge: () => ({bg: 'rgba(249,168,212,0.18)', fg: '#F9A8D4'}),
};

// INFOGRAPHIC PHẲNG: thẻ trắng viền đậm + bóng đổ cứng lệch (kiểu đồ họa thông tin), chữ đậm, không bo nhiều
SKINS.info = {
  light: true,
  card: (t) => ({background: '#FFFFFF', border: `4px solid ${t.dark}`, boxShadow: `8px 8px 0 ${t.dark}`}),
  ink: (t) => t.dark, accent: (t) => t.mid, radius: (n) => Math.min(Number(n) || 0, 16), orn: 'bar',
  big: (t) => ({color: t.dark, letterSpacing: -1}),
  label: {letterSpacing: 2, textTransform: 'uppercase', fontWeight: 900}, cta: 'solid', badge: (t, ac) => ({bg: ac, fg: 'white'}),
};
// BẢN TIN TRUYỀN HÌNH: thẻ trắng góc vuông, sọc đỏ dày bên trái, chữ đen đậm, nhãn đỏ in hoa
SKINS.news = {
  light: true,
  card: (t, ac) => ({background: '#FFFFFF', borderLeft: `16px solid ${ac}`, boxShadow: '0 10px 24px rgba(0,0,0,0.3)'}),
  ink: () => '#111111', accent: () => '#D7141A', radius: () => 0, orn: 'line',
  big: () => ({color: '#111111', letterSpacing: -1}),
  label: {letterSpacing: 2, textTransform: 'uppercase', fontWeight: 900}, cta: 'solid', badge: (t, ac) => ({bg: ac, fg: 'white'}),
};

export const skinDef = (): SkinDef | null => {
  const s = skinOf();
  return s === '3d' ? null : SKINS[s] || SKINS.flat;
};

/** hoa văn phân cách dưới chữ lớn: vạch / ◆ giữa 2 đường / sóng / đường mảnh / 3 chấm */
export const Orn: React.FC<{kind: SkinDef['orn']; color: string; k?: number; w?: number}> = ({kind, color, k = 1, w = 260}) => {
  const ww = w * k;
  if (kind === 'diamond')
    return (
      <div style={{display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 12, margin: '10px auto 0', width: ww}}>
        <div style={{flex: 1, height: 1.5, background: color}} />
        <div style={{width: 12, height: 12, background: color, transform: 'rotate(45deg)'}} />
        <div style={{flex: 1, height: 1.5, background: color}} />
      </div>
    );
  if (kind === 'wave')
    return (
      <svg width={ww} height={18} viewBox="0 0 260 18" style={{display: 'block', margin: '8px auto 0'}}>
        <path d="M0 9 Q 16 0 32 9 T 65 9 T 97 9 T 130 9 T 162 9 T 195 9 T 227 9 T 260 9" fill="none" stroke={color} strokeWidth={3.5} strokeLinecap="round" />
      </svg>
    );
  if (kind === 'line') return <div style={{height: 1, width: ww * 1.2, background: color, margin: '12px auto 0'}} />;
  if (kind === 'dots')
    return (
      <div style={{display: 'flex', gap: 10, justifyContent: 'center', marginTop: 10}}>
        {[0, 1, 2].map((i) => <span key={i} style={{width: 8, height: 8, borderRadius: 4, background: color, opacity: i === 1 ? 1 : 0.5}} />)}
      </div>
    );
  return <div style={{height: 8, borderRadius: 4, background: color, width: ww * 0.7, margin: '6px auto 0'}} />;
};

/* ================= KHUNG TRANG TRÍ CẢ VIDEO (style.frame) ================= */
export type FrameKind = 'ink' | 'classic' | 'arch' | 'corners' | 'letterbox' | 'grain' | 'leak' | 'datestamp' | 'rec' | 'wave' | 'ticker' | 'live' | 'grid' | 'coords' | 'none';
const Corner: React.FC<{c: string; s: number; style: React.CSSProperties}> = ({c, s, style}) => (
  <svg width={s} height={s} viewBox="0 0 100 100" style={{position: 'absolute', ...style}}>
    <path d="M4 96 V24 Q4 4 24 4 H96" fill="none" stroke={c} strokeWidth={3} />
    <path d="M16 96 V32 Q16 16 32 16 H96" fill="none" stroke={c} strokeWidth={1.5} />
    <path d="M24 24 l8 -8 l8 8 l-8 8 z" fill={c} />
  </svg>
);
export const FrameOverlay: React.FC = () => {
  const f = useCurrentFrame();
  const fr = S.style.frame;
  if (!fr) return null;
  const list: FrameKind[] = (Array.isArray(fr) ? fr : [fr.type || fr]).map((x: any) => (typeof x === 'string' ? x : x.type)) as any;
  const c = (typeof fr === 'object' && !Array.isArray(fr) && fr.color) || S.style.accent || '#D4AF37';
  const out: React.ReactNode[] = [];
  const optOf = (i: number): any => (Array.isArray(fr) ? (typeof fr[i] === 'object' ? fr[i] : {}) : typeof fr === 'object' ? fr : {});
  list.forEach((k, i) => {
    if (k === 'ink') {
      const o = optOf(i);
      out.push(<InkScape key={'ink' + i} pos="top" palette={o.palette || 'mono'} items={o.items} />);
    }
    if (k === 'letterbox')
      out.push(
        <React.Fragment key={'lb' + i}>
          <div style={{position: 'absolute', left: 0, right: 0, top: 0, height: 96, background: '#000'}} />
          <div style={{position: 'absolute', left: 0, right: 0, bottom: 0, height: 96, background: '#000'}} />
        </React.Fragment>,
      );
    if (k === 'classic')
      out.push(
        <React.Fragment key={'cl' + i}>
          <div style={{position: 'absolute', inset: 28, border: `2px solid ${c}`, opacity: 0.9}} />
          <div style={{position: 'absolute', inset: 40, border: `1px solid ${c}`, opacity: 0.7}} />
          {[{left: 18, top: 18}, {right: 18, top: 18, transform: 'scaleX(-1)'}, {left: 18, bottom: 18, transform: 'scaleY(-1)'}, {right: 18, bottom: 18, transform: 'scale(-1,-1)'}].map((p, j) => (
            <Corner key={j} c={c} s={120} style={p} />
          ))}
        </React.Fragment>,
      );
    if (k === 'corners')
      [{left: 40, top: 40}, {right: 40, top: 40, transform: 'scaleX(-1)'}, {left: 40, bottom: 40, transform: 'scaleY(-1)'}, {right: 40, bottom: 40, transform: 'scale(-1,-1)'}].forEach((p, j) =>
        out.push(
          <svg key={'co' + i + j} width={110} height={110} viewBox="0 0 100 100" style={{position: 'absolute', ...p}}>
            <path d="M2 70 V2 H70" fill="none" stroke={c} strokeWidth={3} />
          </svg>,
        ),
      );
    if (k === 'arch')
      out.push(
        <svg key={'ar' + i} width={1080} height={1920} viewBox="0 0 1080 1920" style={{position: 'absolute', left: 0, top: 0}}>
          <path d="M60 1880 V560 A480 480 0 0 1 1020 560 V1880 Z" fill="none" stroke={c} strokeWidth={5} opacity={0.95} />
          <path d="M84 1856 V566 A456 456 0 0 1 996 566 V1856 Z" fill="none" stroke={c} strokeWidth={2} opacity={0.6} />
        </svg>,
      );
    if (k === 'grain')
      out.push(
        <svg key={'gr' + i} width={1080} height={1920} style={{position: 'absolute', left: 0, top: 0, mixBlendMode: 'overlay', opacity: 0.32}}>
          <filter id="fgrain">
            <feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves={2} seed={f % 7} />
            <feColorMatrix type="saturate" values="0" />
          </filter>
          <rect width="1080" height="1920" filter="url(#fgrain)" />
        </svg>,
      );
  });
  const opt = (typeof fr === 'object' && !Array.isArray(fr) ? fr : (Array.isArray(fr) ? fr.find((x: any) => typeof x === 'object') : null)) || {};
  list.forEach((k, i) => {
    if (k === 'leak') {
      // vệt sáng hắt: 2 đốm cam – hồng trôi chậm ở mép khung, nhấp nháy nhẹ như phim
      const a = Math.sin(f / 45) * 0.5 + 0.5, b = Math.sin(f / 31 + 2) * 0.5 + 0.5;
      out.push(
        <React.Fragment key={'lk' + i}>
          <div style={{position: 'absolute', inset: 0, mixBlendMode: 'screen', opacity: 0.22 + 0.2 * a, background: `radial-gradient(45% 35% at ${-5 + 18 * a}% ${12 + 20 * b}%, rgba(255,140,60,0.95), transparent 70%)`}} />
          <div style={{position: 'absolute', inset: 0, mixBlendMode: 'screen', opacity: 0.16 + 0.18 * b, background: `radial-gradient(40% 30% at ${104 - 14 * b}% ${78 - 18 * a}%, rgba(255,90,140,0.9), transparent 70%)`}} />
        </React.Fragment>,
      );
    }
    if (k === 'datestamp')
      out.push(
        <div key={'ds' + i} style={{position: 'absolute', right: 70, top: 250, fontFamily: '"Courier New", monospace', fontWeight: 700, fontSize: 46, letterSpacing: 4, color: '#FF8A2B', textShadow: '0 0 6px rgba(255,120,30,0.9), 0 0 16px rgba(255,90,0,0.6)', opacity: 0.92}}>
          {opt.date || "'26  11  06"}
        </div>,
      );
    if (k === 'rec') {
      const sec = Math.floor(f / 30), tc = [Math.floor(sec / 3600), Math.floor(sec / 60) % 60, sec % 60, f % 30].map((x) => String(x).padStart(2, '0')).join(':');
      out.push(
        <React.Fragment key={'rc' + i}>
          <div style={{position: 'absolute', left: 70, top: 250, display: 'flex', alignItems: 'center', gap: 14, fontFamily: '"Courier New", monospace', fontWeight: 700, fontSize: 40, color: 'white', textShadow: '0 2px 6px rgba(0,0,0,0.6)'}}>
            <span style={{width: 26, height: 26, borderRadius: 13, background: '#FF2D2D', opacity: Math.floor(f / 15) % 2 ? 1 : 0.25}} /> REC
          </div>
          <div style={{position: 'absolute', right: 70, top: 254, fontFamily: '"Courier New", monospace', fontWeight: 700, fontSize: 36, color: 'white', textShadow: '0 2px 6px rgba(0,0,0,0.6)'}}>{tc}</div>
          {[{left: 50, top: 90}, {right: 50, top: 90, transform: 'scaleX(-1)'}, {left: 50, bottom: 260, transform: 'scaleY(-1)'}, {right: 50, bottom: 260, transform: 'scale(-1,-1)'}].map((p, j) => (
            <svg key={j} width={80} height={80} viewBox="0 0 100 100" style={{position: 'absolute', ...p}}>
              <path d="M4 60 V4 H60" fill="none" stroke="white" strokeWidth={5} opacity={0.85} />
            </svg>
          ))}
        </React.Fragment>,
      );
    }
    if (k === 'wave') {
      // sóng âm trang trí kiểu podcast (nhịp giả lập, không theo tiếng thật)
      const n = 48;
      out.push(
        <div key={'wv' + i} style={{position: 'absolute', left: 160, right: 160, bottom: 230, height: 80, display: 'flex', alignItems: 'center', gap: 6, opacity: 0.85}}>
          {Array.from({length: n}, (_, j) => {
            const h = 14 + 70 * Math.abs(Math.sin(f / 5 + j * 0.7) * Math.sin(f / 11 + j * 0.31));
            return <span key={j} style={{flex: 1, height: h, borderRadius: 4, background: (opt.color as string) || S.style.accent || '#F9A8D4'}} />;
          })}
        </div>,
      );
    }
  });
  const fopt = (k: string) => (Array.isArray(fr) ? fr.find((x: any) => typeof x === 'object' && x.type === k) : typeof fr === 'object' && fr.type === k ? fr : null) || {};
  list.forEach((k, i) => {
    if (k === 'ticker') {
      // dải chữ chạy kiểu thời sự: nhãn đỏ + chữ trắng chạy trên nền xanh đậm
      const o = fopt('ticker');
      const txt = (o.text as string) || 'CẬP NHẬT THỊ TRƯỜNG BẤT ĐỘNG SẢN  •  THEO DÕI ĐỂ XEM TIN MỚI MỖI NGÀY  •  ';
      const x = -((f * 4) % 2400);
      out.push(
        <div key={'tk' + i} style={{position: 'absolute', left: 0, right: 0, bottom: 230, height: 64, display: 'flex', background: (o.bg as string) || '#0B2545', overflow: 'hidden', boxShadow: '0 -4px 14px rgba(0,0,0,0.3)'}}>
          <div style={{flexShrink: 0, background: (o.color as string) || '#D7141A', color: 'white', fontFamily: '"Oswald", sans-serif', fontWeight: 700, fontSize: 34, padding: '0 24px', display: 'flex', alignItems: 'center', zIndex: 1}}>{(o.label as string) || 'TIN MỚI'}</div>
          <div style={{whiteSpace: 'nowrap', color: 'white', fontFamily: '"Roboto", sans-serif', fontWeight: 700, fontSize: 32, display: 'flex', alignItems: 'center', transform: `translateX(${x}px)`}}>{txt.repeat(6)}</div>
        </div>,
      );
    }
    if (k === 'live') {
      const o = fopt('live');
      const sec = Math.floor(f / 30);
      const hh = (o.time as string) || `${String(20 + Math.floor(sec / 3600)).padStart(2, '0')}:${String(30 + (Math.floor(sec / 60) % 30)).padStart(2, '0')}`;
      out.push(
        <div key={'lv' + i} style={{position: 'absolute', right: 50, top: 250, display: 'flex', gap: 0, fontFamily: '"Oswald", sans-serif', fontWeight: 700, fontSize: 34, boxShadow: '0 6px 16px rgba(0,0,0,0.3)'}}>
          <span style={{background: '#D7141A', color: 'white', padding: '6px 18px', display: 'flex', alignItems: 'center', gap: 10}}>
            <span style={{width: 14, height: 14, borderRadius: 7, background: 'white', opacity: Math.floor(f / 15) % 2 ? 1 : 0.35}} />{(o.label as string) || 'LIVE'}
          </span>
          <span style={{background: 'rgba(0,0,0,0.75)', color: 'white', padding: '6px 16px'}}>{hh}</span>
        </div>,
      );
    }
    if (k === 'grid')
      out.push(
        <div key={'gd' + i} style={{position: 'absolute', inset: 0, opacity: 0.16, backgroundImage: 'linear-gradient(rgba(255,255,255,0.9) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.9) 1px, transparent 1px)', backgroundSize: '90px 90px'}} />,
      );
    if (k === 'coords') {
      const o = fopt('coords');
      const lat = Number(o.lat ?? 10.7769), lng = Number(o.lng ?? 106.7009);
      const d = (v: number, p: string, q: string) => `${Math.abs(v).toFixed(4)}° ${v >= 0 ? p : q}`;
      out.push(
        <React.Fragment key={'cd' + i}>
          <div style={{position: 'absolute', left: 60, bottom: 240, fontFamily: '"Courier New", monospace', fontWeight: 700, fontSize: 30, color: 'white', textShadow: '0 2px 6px rgba(0,0,0,0.7)', lineHeight: 1.4, opacity: 0.9}}>
            {d(lat + Math.sin(f / 60) * 0.0004, 'N', 'S')}<br />{d(lng + Math.cos(f / 60) * 0.0004, 'E', 'W')}
          </div>
          <svg width={120} height={120} viewBox="-60 -60 120 120" style={{position: 'absolute', right: 50, top: 240, opacity: 0.9, filter: 'drop-shadow(0 2px 6px rgba(0,0,0,0.6))'}}>
            <circle r={52} fill="none" stroke="white" strokeWidth={2.5} />
            <g transform={`rotate(${Math.sin(f / 50) * 6})`}>
              <path d="M0 -44 L10 0 L0 8 L-10 0 Z" fill={c} />
              <path d="M0 44 L10 0 L0 -8 L-10 0 Z" fill="white" opacity={0.85} />
            </g>
            <text y={-30} textAnchor="middle" fontFamily="sans-serif" fontWeight={700} fontSize={14} fill="white" dy={-24}>N</text>
          </svg>
        </React.Fragment>,
      );
    }
  });
  return <AbsoluteFill style={{pointerEvents: 'none'}}>{out}</AbsoluteFill>;
};
