/* Ảnh minh họa cho bộ phong cách DỰNG THEO NHỊP NHẠC (style.beat.preset):
 * khung hình đặc trưng của kiểu dựng (chia khung, dải chéo, viền phim, glitch, mờ chồng…) + chữ theo phong cách
 * + dải timeline nhịp ở dưới: vạch nhịp và độ dài từng cảnh (thưa/dày dần) theo kiểu. */
import React, {useEffect, useState} from 'react';
import {AbsoluteFill, Img, continueRender, delayRender, staticFile} from 'remotion';
import {FONTS} from './fonts';
import {S, Style} from './style';
import {StyledText} from './Styled';
import {Overlay} from './AE';

export type BeatPreviewProps = {style: Style; theme: any; preset: string; imgs?: string[]; title?: string; sub?: string};

/** độ dài cảnh (số nhịp) cho 3 phần đầu–giữa–cuối, như dung_nhip.KIEU[...].ramp */
const RAMP: Record<string, number[]> = {
  trailer: [4, 2, 1], 'nang-dong': [1, 1, 1], 'sang-trong': [4, 2, 2], 'chia-khung': [2, 2, 1], glitch: [2, 1, 1], chill: [4, 4, 4],
};
const NAME: Record<string, string> = {
  trailer: 'TRAILER', 'nang-dong': 'NĂNG ĐỘNG', 'sang-trong': 'SANG TRỌNG', 'chia-khung': 'CHIA KHUNG', glitch: 'GLITCH', chill: 'CHILL',
};
const SH = 1580; // chiều cao vùng cảnh (phần dưới dành cho timeline)

const Pic: React.FC<{src?: string; style?: React.CSSProperties; fallback?: string}> = ({src, style, fallback}) =>
  src ? <Img src={staticFile(src)} style={{position: 'absolute', objectFit: 'cover', width: '100%', height: '100%', ...style}} />
    : <div style={{position: 'absolute', width: '100%', height: '100%', background: fallback || 'linear-gradient(160deg,#5b6b84,#1b2333)', ...style}} />;

export const BeatPreview: React.FC<BeatPreviewProps> = (p) => {
  S.style = p.style || {};
  const [h] = useState(() => delayRender('fonts'));
  useEffect(() => {
    const names = [p.style?.font, p.style?.heading, 'Be Vietnam Pro'].filter(Boolean) as string[];
    const jobs: Promise<any>[] = [];
    names.forEach((n) => {
      const f = FONTS.find((x) => x.family.toLowerCase() === n.toLowerCase());
      f?.weights.forEach((w) => jobs.push(document.fonts.load(`${w} 40px "${f.family}"`, 'Ngày ữ Ặ')));
    });
    Promise.all(jobs).catch(() => null).then(() => continueRender(h));
  }, [h]);
  const th = p.theme || {light: '#4FB3FF', mid: '#1F6FC0', dark: '#0A2F6B', gold1: '#FFE9A0', gold2: '#F2B526'};
  const k = RAMP[p.preset] ? p.preset : 'chia-khung';
  const im = (i: number) => (p.imgs && p.imgs.length ? p.imgs[i % p.imgs.length] : undefined);
  const acc = (p.style?.text as any)?.hlColor || th.gold2 || '#FFD166';
  const title = p.title || 'Giá chỉ 2,5 tỷ';
  const sub = p.sub || 'Căn hộ view sông';
  const T = (y: number, size?: number, extra: any = {}, scrim = 0.55) => (
    <>
      {scrim > 0 && <div style={{position: 'absolute', left: 0, right: 0, top: y - 230, height: 560,
        background: `radial-gradient(75% 50% at 50% 50%, rgba(0,0,0,${scrim}) 0%, rgba(0,0,0,${scrim * 0.6}) 45%, transparent 75%)`}} />}
      <StyledText text={title} hl={['2,5 tỷ']} y={y} dur={1000} theme={th} anim="none" out="none" size={size ?? (p.style?.text as any)?.size ?? 104} {...extra} />
      <StyledText text={sub} y={y + 200} dur={1000} theme={th} anim="none" out="none" size={56} look={'clean' as any} upper={false} color="#FFFFFF" />
    </>
  );

  let scene: React.ReactNode = null;
  if (k === 'chia-khung') {
    // KHUNG NHỊP: 3 dải bo góc bật ra theo nhịp; dải thứ 3 đang trượt vào
    const gap = 18, bh = (SH - gap * 4) / 3;
    scene = (
      <AbsoluteFill style={{background: '#0d0f14'}}>
        {[0, 1, 2].map((i) => (
          <div key={i} style={{position: 'absolute', left: gap + (i === 2 ? 140 : 0), top: gap + i * (bh + gap), width: 1080 - gap * 2, height: bh,
            borderRadius: 38, overflow: 'hidden', boxShadow: '0 18px 50px #0009', opacity: i === 2 ? 0.92 : 1}}>
            <Pic src={im(i)} style={{transform: `scale(${1.08 + i * 0.03})`}} />
          </div>
        ))}
        {/* dải chéo đang lướt vào theo nhịp, lộ dần cảnh kế tiếp (chuyển đoạn) */}
        {[0, 1, 2].map((i) => {
          const x = 700 + i * 150, w = 120, sk = 420;
          const poly = `polygon(${x + sk}px 0, ${x + sk + w}px 0, ${x + w}px ${SH}px, ${x}px ${SH}px)`;
          return (
            <div key={'s' + i} style={{position: 'absolute', inset: 0, clipPath: poly}}>
              <Pic src={im(6)} style={{filter: 'brightness(1.1) saturate(1.2)'}} />
              <div style={{position: 'absolute', inset: 0, background: `linear-gradient(90deg, #fff 0 6px, transparent 6px)`, opacity: 0.9}} />
            </div>
          );
        })}
        <AbsoluteFill style={{background: 'linear-gradient(90deg, #000a 0%, #0006 45%, transparent 75%)'}} />
        {T(640)}
      </AbsoluteFill>
    );
  } else if (k === 'trailer') {
    // viền phim đen, cảnh tối tương phản, chớp trắng loé ở mép, chữ to giữa
    scene = (
      <AbsoluteFill style={{background: '#000'}}>
        <Pic src={im(0)} style={{filter: 'contrast(1.25) saturate(0.75) brightness(0.62)', transform: 'scale(1.12)'}} />
        <AbsoluteFill style={{background: 'radial-gradient(70% 55% at 50% 45%, transparent 30%, #000c 100%)'}} />
        <AbsoluteFill style={{background: 'linear-gradient(90deg, transparent 72%, #fff8 88%, #fff 100%)', mixBlendMode: 'screen'}} />
        <div style={{position: 'absolute', left: 0, right: 0, top: 0, height: 250, background: '#000'}} />
        <div style={{position: 'absolute', left: 0, right: 0, top: SH - 250, height: 250, background: '#000'}} />
        <div style={{position: 'absolute', left: 0, right: 0, top: 168, textAlign: 'center', color: '#fff9', fontFamily: 'Be Vietnam Pro', fontSize: 34, letterSpacing: 14, fontWeight: 700}}>SẮP RA MẮT</div>
        {T(640, 116, {}, 0)}
      </AbsoluteFill>
    );
  } else if (k === 'nang-dong') {
    // zoom giật + lia nhanh: cảnh A phóng nghiêng, cảnh B lia vào theo đường chéo, vệt tốc độ
    scene = (
      <AbsoluteFill style={{background: '#111', overflow: 'hidden'}}>
        <div style={{position: 'absolute', inset: 0, transform: 'scale(1.22) rotate(-3deg)'}}><Pic src={im(0)} /></div>
        <div style={{position: 'absolute', inset: 0, clipPath: 'polygon(58% 0, 100% 0, 100% 100%, 30% 100%)', overflow: 'hidden'}}>
          {[-60, -30, 0].map((dx, i) => (
            <div key={i} style={{position: 'absolute', inset: 0, transform: `translateX(${dx}px) scale(1.06)`, opacity: i === 2 ? 1 : 0.35, filter: i === 2 ? 'blur(3px)' : 'blur(8px)'}}><Pic src={im(1)} /></div>
          ))}
        </div>
        <div style={{position: 'absolute', left: 0, right: 0, top: 0, bottom: 0, clipPath: 'polygon(57% 0, 59% 0, 31% 100%, 29% 100%)', background: '#fff'}} />
        {Array.from({length: 9}, (_, i) => (
          <div key={i} style={{position: 'absolute', left: 560 + ((i * 97) % 420), top: 160 + i * 150, width: 240 + ((i * 53) % 160), height: 6, borderRadius: 3, background: '#ffffffaa'}} />
        ))}
        {T(640, undefined, {}, 0.8)}
      </AbsoluteFill>
    );
  } else if (k === 'sang-trong') {
    // đẩy chậm + mờ chồng 2 cảnh, ánh sáng loé ấm, viền vàng mảnh
    scene = (
      <AbsoluteFill style={{background: '#120d08'}}>
        <Pic src={im(0)} style={{filter: 'sepia(0.22) saturate(1.05) brightness(0.62)', transform: 'scale(1.06)'}} />
        <Pic src={im(1)} style={{opacity: 0.45, mixBlendMode: 'screen', filter: 'sepia(0.3) brightness(0.9)', transform: 'scale(1.15)',
          WebkitMaskImage: 'linear-gradient(180deg, transparent 10%, #000 55%)', maskImage: 'linear-gradient(180deg, transparent 10%, #000 55%)'}} />
        <AbsoluteFill style={{mixBlendMode: 'screen'}}><Overlay e={{kind: 'lightleak', amount: 90, _i: 2}} dur={1000} theme={th} /></AbsoluteFill>
        <AbsoluteFill style={{background: 'linear-gradient(180deg, #0008, transparent 30%, transparent 60%, #000a)'}} />
        <div style={{position: 'absolute', left: 60, right: 60, top: 60, bottom: 60, border: `2px solid ${acc}99`}} />
        {T(560)}
      </AbsoluteFill>
    );
  } else if (k === 'glitch') {
    // tách màu RGB + các dải ngang bị xô lệch + vạch quét
    const src = im(0);
    const url = src ? staticFile(src) : '';
    scene = (
      <AbsoluteFill style={{background: '#05060a', overflow: 'hidden'}}>
        <svg width={1080} height={SH} style={{position: 'absolute', left: 0, top: 0}}>
          <defs>
            {['r', 'g', 'b'].map((c, i) => (
              <filter key={c} id={'ch' + c} colorInterpolationFilters="sRGB">
                <feColorMatrix type="matrix" values={[c === 'r' ? '1 0 0 0 0' : '0 0 0 0 0', c === 'g' ? '0 1 0 0 0' : '0 0 0 0 0', c === 'b' ? '0 0 1 0 0' : '0 0 0 0 0', '0 0 0 1 0'].join(' ')} />
              </filter>
            ))}
          </defs>
          <g style={{mixBlendMode: 'screen' as any}}>
            {url && <image href={url} x={-22} y={0} width={1124} height={SH} preserveAspectRatio="xMidYMid slice" filter="url(#chr)" />}
            {url && <image href={url} x={0} y={0} width={1124} height={SH} preserveAspectRatio="xMidYMid slice" filter="url(#chg)" style={{mixBlendMode: 'screen' as any}} />}
            {url && <image href={url} x={22} y={0} width={1124} height={SH} preserveAspectRatio="xMidYMid slice" filter="url(#chb)" style={{mixBlendMode: 'screen' as any}} />}
          </g>
        </svg>
        {[[260, 70, 60], [520, 40, -90], [980, 90, 120], [1240, 30, -50]].map(([y, hh, dx], i) => (
          <div key={i} style={{position: 'absolute', left: 0, top: y, width: 1080, height: hh, overflow: 'hidden'}}>
            <div style={{position: 'absolute', left: dx, top: -y, width: 1080, height: SH, filter: 'saturate(1.6) hue-rotate(20deg)'}}><Pic src={src} /></div>
          </div>
        ))}
        <AbsoluteFill style={{background: 'repeating-linear-gradient(180deg, #0000 0 3px, #0006 3px 5px)'}} />
        <div style={{position: 'absolute', left: 0, right: 0, top: 1060, height: 8, background: acc, opacity: 0.8}} />
        {T(640, undefined, {}, 0.8)}
      </AbsoluteFill>
    );
  } else {
    // chill: mờ chồng mềm, màu nhạt, hạt phim
    scene = (
      <AbsoluteFill style={{background: '#d9d4cc'}}>
        <Pic src={im(0)} style={{filter: 'saturate(0.8) contrast(0.88) brightness(1.06)'}} />
        <Pic src={im(1)} style={{opacity: 0.55, filter: 'saturate(0.75) contrast(0.85) brightness(1.08)',
          WebkitMaskImage: 'linear-gradient(0deg, #000 25%, transparent 75%)', maskImage: 'linear-gradient(0deg, #000 25%, transparent 75%)'}} />
        <AbsoluteFill style={{background: '#f3e7d555', mixBlendMode: 'soft-light'}} />
        <AbsoluteFill style={{mixBlendMode: 'overlay'}}><Overlay e={{kind: 'grain', amount: 80, _i: 1}} dur={1000} theme={th} /></AbsoluteFill>
        {T(620, undefined, {}, 0.35)}
      </AbsoluteFill>
    );
  }

  // ---- timeline nhịp ----
  const N = 16, X0 = 70, X1 = 1010, step = (X1 - X0) / N;
  const ramp = RAMP[k];
  const cuts: number[] = [0];
  let b = 0;
  while (b < N) {
    const part = Math.min(2, Math.floor((b / N) * 3));
    const len = k === 'chia-khung' && b === 0 ? 3 : ramp[part];
    b = Math.min(N, b + len);
    cuts.push(b);
  }
  const strong = (i: number) => i % 4 === 0;
  const bars = Array.from({length: 60}, (_, i) => {
    const t = i / 60, beat = (t * N) % 1;
    const env = k === 'chill' ? 0.35 : k === 'sang-trong' ? 0.45 : 0.6;
    return 18 + 70 * (Math.exp(-beat * 6) * env + 0.25 * Math.abs(Math.sin(i * 1.7)) + (k === 'trailer' ? t * 0.5 : 0));
  });
  return (
    <AbsoluteFill style={{background: '#0b0d12'}}>
      <div style={{position: 'absolute', left: 0, top: 0, width: 1080, height: SH, overflow: 'hidden'}}>{scene}</div>
      <div style={{position: 'absolute', left: 0, top: SH, width: 1080, height: 1920 - SH, background: 'linear-gradient(180deg,#11141b,#07080b)'}}>
        <div style={{position: 'absolute', left: X0, top: 26, display: 'flex', alignItems: 'center', gap: 16}}>
          <div style={{padding: '8px 22px', borderRadius: 40, border: `3px solid ${acc}`, color: acc, fontFamily: 'Be Vietnam Pro', fontWeight: 900, fontSize: 32, letterSpacing: 1}}>♪ THEO NHỊP NHẠC</div>
          <div style={{color: '#ffffffb0', fontFamily: 'Be Vietnam Pro', fontWeight: 700, fontSize: 30, letterSpacing: 4}}>{NAME[k]}</div>
        </div>
        {/* sóng nhạc */}
        <div style={{position: 'absolute', left: X0, top: 110, width: X1 - X0, height: 90, display: 'flex', alignItems: 'center', gap: 4}}>
          {bars.map((v, i) => <div key={i} style={{flex: 1, height: Math.min(90, v), borderRadius: 4, background: '#ffffff30'}} />)}
        </div>
        {/* vạch nhịp */}
        {Array.from({length: N + 1}, (_, i) => (
          <div key={i} style={{position: 'absolute', left: X0 + i * step - (strong(i) ? 5 : 3), top: 102, width: strong(i) ? 10 : 6, height: 106, borderRadius: 4,
            background: cuts.includes(i) ? acc : '#ffffff40'}} />
        ))}
        {/* các cảnh theo độ dài nhịp */}
        {cuts.slice(0, -1).map((c, i) => {
          const x = X0 + c * step + 3, w = (cuts[i + 1] - c) * step - 6;
          const frames = k === 'chia-khung' && i === 0;
          return (
            <div key={i} style={{position: 'absolute', left: x, top: 224, width: w, height: 86, borderRadius: 10, overflow: 'hidden', background: '#222'}}>
              {frames
                ? [0, 1, 2].map((j) => <div key={j} style={{position: 'absolute', left: 0, top: j * 29, width: '100%', height: 26, overflow: 'hidden'}}><Pic src={im(j)} /></div>)
                : <Pic src={im(i + 1)} style={{filter: k === 'chill' ? 'saturate(0.8)' : undefined}} />}
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
