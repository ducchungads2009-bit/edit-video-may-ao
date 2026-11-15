/* LOGO + SỐ ĐIỆN THOẠI của người dùng, chèn tự động lên mọi video (⚙ Cài đặt → Logo & SĐT; scripts/thuong_hieu.py).
   plan.brandMark = {logo?, logoPos: tl|tr|tc|bl|custom (+ logoX tâm ngang 0–1, logoY mép trên px), logoSize (px ngang), logoOpacity (0–1), logoWhen: all|startend|end,
                     phone?, phoneLabel?, phonePos: under|bottom|top, phoneWhen: all|startend|end, phoneBg, phoneColor,
                     endCard (màn kết logo to + SĐT), endSec (giây cuối, mặc định 4), font}
   Nằm trên cùng (trên chữ, phụ đề). */
import React from 'react';
import {AbsoluteFill, Img, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {mediaSrc} from './Media';
import {fy, FR} from './frame';

export type BrandMark = {
  logo?: string; logoPos?: string; logoX?: number; logoY?: number; logoSize?: number; logoOpacity?: number; logoWhen?: string;
  phone?: string; phoneLabel?: string; phonePos?: string; phoneWhen?: string; phoneBg?: string; phoneColor?: string;
  phoneX?: number; phoneY?: number; phoneSize?: number;
  endCard?: boolean; endSec?: number; font?: string;
};

const START = 4; // "đầu + cuối": hiện 4 giây đầu
const fadeWin = (t: number, a: number, b: number, d = 0.35) => {
  if (t < a || t > b) return 0;
  let k = 1;
  if (a > 0) k = Math.min(k, (t - a) / d);
  if (b < 1e8) k = Math.min(k, (b - t) / d);
  return Math.max(0, k);
};

/** độ hiện 0–1 theo chế độ hiện (cả video / đầu + cuối / chỉ cuối) */
const visOf = (when: string | undefined, t: number, dur: number, endSec: number, endCard: boolean) => {
  const endA = dur - endSec;
  const hideEnd = endCard ? endA : 1e9; // có màn kết -> khối góc ẩn đi trong màn kết
  if (when === 'end') return endCard ? 0 : fadeWin(t, endA, 1e9);
  if (when === 'startend') return Math.max(fadeWin(t, 0, Math.min(START, endA - 0.5)), endCard ? 0 : fadeWin(t, endA, 1e9));
  return fadeWin(t, 0, hideEnd);
};

const Phone: React.FC<{b: BrandMark; size: number; label?: boolean}> = ({b, size, label}) => (
  <div style={{display: 'inline-flex', alignItems: 'center', gap: size * 0.35, background: b.phoneBg || '#E63946', color: b.phoneColor || '#FFFFFF',
    borderRadius: 999, padding: `${size * 0.32}px ${size * 0.75}px`, fontFamily: b.font || 'Montserrat', fontWeight: 800, fontSize: size,
    boxShadow: '0 8px 24px rgba(0,0,0,.35)', whiteSpace: 'nowrap', letterSpacing: 0.5}}>
    <span style={{fontSize: size * 0.95}}>📞</span>
    {label && b.phoneLabel ? <span style={{fontWeight: 500, opacity: 0.9}}>{b.phoneLabel}</span> : null}
    <span>{b.phone}</span>
  </div>
);

export const BrandLayer: React.FC<{b: BrandMark; dodge?: boolean}> = ({b, dodge}) => {
  const f = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();
  const t = f / fps, dur = durationInFrames / fps;
  const endSec = Math.max(2, Math.min(b.endSec ?? 4, dur / 2));
  const endCard = !!b.endCard && (!!b.logo || !!b.phone) && dur > 6;
  const W = b.logoSize ?? 170;
  // video có nhãn NGÀY X/Y (góc trên trái) -> logo góc trên trái / giữa tự dời sang góc trên phải
  // vị trí tự do (kéo trong ⚙ Cài đặt → Logo & SĐT) thì giữ nguyên, không tự dời
  const pos = b.logoPos === 'custom' ? 'custom' : dodge && (b.logoPos || 'tl') !== 'bl' ? 'tr' : b.logoPos || 'tl';
  const cx = (b.logoX ?? 0.5) * FR.w;
  const top = pos === 'custom' ? fy(b.logoY ?? 150) : pos === 'bl' ? fy(1180) : 150;
  const logoBox: React.CSSProperties = {position: 'absolute', top, width: W,
    ...(pos === 'custom' ? {left: cx - W / 2} : pos === 'tr' ? {right: 44} : pos === 'tc' ? {left: FR.w / 2 - W / 2} : {left: 44})};
  const lv = b.logo ? visOf(b.logoWhen, t, dur, endSec, endCard) : 0;
  const pv = b.phone ? visOf(b.phoneWhen, t, dur, endSec, endCard) : 0;
  const pp = b.phonePos || 'under';
  // SĐT dưới logo: cùng góc với logo
  const PS = b.phoneSize ?? 42;
  const phoneBox: React.CSSProperties = pp === 'custom'
    ? {position: 'absolute', top: fy(b.phoneY ?? 1250), left: (b.phoneX ?? 0.5) * FR.w, transform: 'translateX(-50%)'}
    : pp === 'under' && b.logo
    ? {position: 'absolute', top: top + W * 0.62 + 18, ...(pos === 'custom' ? {left: cx, transform: 'translateX(-50%)'} : pos === 'tr' ? {right: 44} : pos === 'tc' ? {left: 0, right: 0, textAlign: 'center'} : {left: 44})}
    : pp === 'top' || (pp === 'under' && !b.logo) ? {position: 'absolute', top: dodge ? 250 : 160, left: 0, right: 0, textAlign: 'center'}
    : {position: 'absolute', top: fy(1250), left: 0, right: 0, textAlign: 'center'};
  // màn kết
  const ea = dur - endSec;
  const ek = endCard ? interpolate(t, [ea, ea + 0.45], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}) : 0;
  const pop = (d: number) => interpolate(t, [ea + d, ea + d + 0.35], [0.6, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return (
    <AbsoluteFill style={{pointerEvents: 'none'}} data-el="brand">
      {lv > 0 && (
        <div style={{...logoBox, opacity: lv * (b.logoOpacity ?? 0.92)}}>
          <Img src={mediaSrc(b.logo!)} style={{width: '100%', height: 'auto', display: 'block', filter: 'drop-shadow(0 3px 8px rgba(0,0,0,.35))'}} />
        </div>
      )}
      {pv > 0 && (
        <div style={{...phoneBox, opacity: pv}}>
          <Phone b={b} size={pp === 'under' && b.logo ? PS * 0.81 : PS} label={pp !== 'under'} />
        </div>
      )}
      {ek > 0 && (
        <AbsoluteFill style={{background: `rgba(0,0,0,${0.55 * ek})`, opacity: ek, alignItems: 'center', justifyContent: 'flex-start', paddingTop: fy(480), flexDirection: 'column', gap: 46}}>
          {b.logo && <Img src={mediaSrc(b.logo)} style={{width: 420, height: 'auto', transform: `scale(${pop(0.05)})`, filter: 'drop-shadow(0 6px 18px rgba(0,0,0,.45))'}} />}
          {b.phone && (
            <div style={{transform: `scale(${pop(0.25)})`, textAlign: 'center'}}>
              {b.phoneLabel ? <div style={{fontFamily: b.font || 'Montserrat', fontWeight: 700, fontSize: 44, color: '#fff', marginBottom: 18, textShadow: '0 3px 10px rgba(0,0,0,.5)'}}>{b.phoneLabel}</div> : null}
              <Phone b={b} size={64} />
            </div>
          )}
        </AbsoluteFill>
      )}
    </AbsoluteFill>
  );
};
