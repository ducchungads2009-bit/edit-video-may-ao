/* Ảnh minh họa cho 1 bộ phong cách: khung nền (ảnh từ video mẫu) + tiêu đề, chữ nhấn, nhãn dán, phụ đề theo style */
import React, {useEffect, useState} from 'react';
import {AbsoluteFill, Img, continueRender, delayRender, staticFile} from 'remotion';
import {FONTS} from './fonts';
import {S, Style} from './style';
import {StyledText, Sticker} from './Styled';
import {Captions, brollArea} from './Media';
import {InkScape} from './Ink';
import {DemoBlocks} from './EditPlan';
import {FrameOverlay} from './skins';
import {Overlay, Shape, Text3D} from './AE';

export type PreviewProps = {style: Style; theme: any; bg?: string; title?: string; sub?: string; blocks?: boolean};

const W = (w: string, start: number, end: number) => ({w, start, end});

export const StylePreview: React.FC<PreviewProps> = (p) => {
  S.style = p.style || {};
  const [h] = useState(() => delayRender('fonts'));
  useEffect(() => {
    const names = [p.style?.font, p.style?.heading, p.style?.captions?.font, 'Be Vietnam Pro'].filter(Boolean) as string[];
    const jobs: Promise<any>[] = [];
    names.forEach((n) => {
      const f = FONTS.find((x) => x.family.toLowerCase() === n.toLowerCase());
      f?.weights.forEach((w) => jobs.push(document.fonts.load(`${w} 40px "${f.family}"`, 'Ngày ữ Ặ')));
    });
    Promise.all(jobs).catch(() => null).then(() => continueRender(h));
  }, [h]);
  const th = p.theme || {light: '#4FB3FF', mid: '#1F6FC0', dark: '#0A2F6B', gold1: '#FFE9A0', gold2: '#F2B526'};
  const tx = p.style?.text || {};
  // dựng ở khung 40 (chữ đã hiện xong), phụ đề: từ thứ 2 đang được đọc
  const cap = [[W('căn', 0.9, 1.25), W('hộ', 1.25, 1.6), W('view', 1.6, 2.0), W('sông', 2.0, 2.4)]];
  const A = brollArea({});
  const half = A.area !== 'full';
  // minh họa bố cục chia khung: người nói (bóng) ở phần còn lại, cảnh trám (phong cảnh) nửa trên/dưới hoà mờ vào
  const F = Math.min(A.feather, A.h * 0.6);
  const free0 = A.area === 'bottom' ? 0 : A.h, free1 = A.area === 'bottom' ? 1920 - A.h : 1920;
  const hy = free0 + (free1 - free0) * (A.area === 'bottom' ? 0.42 : 0.38);
  const g = A.area === 'bottom' ? `linear-gradient(180deg, transparent 0px, black ${F}px)` : `linear-gradient(0deg, transparent 0px, black ${F}px)`;
  const seam = (p.style?.broll as any)?.seam;
  const splitDemo = half && (
    <>
      <div style={{position: 'absolute', left: 540 - 130, top: hy - 150, width: 260, height: 300, borderRadius: 130, background: 'linear-gradient(180deg, #d9b99b, #a07c5f)'}} />
      <div style={{position: 'absolute', left: 540 - 330, top: hy + 170, width: 660, height: 900, borderRadius: '330px 330px 0 0', background: `linear-gradient(180deg, ${th.mid}, ${th.dark || '#111'})`}} />
      <div style={{position: 'absolute', left: 0, width: 1080, top: A.top, height: A.h, WebkitMaskImage: F > 0 ? g : undefined, maskImage: F > 0 ? g : undefined,
        background: 'linear-gradient(180deg, #8ec5fc 0%, #f6d2a2 46%, #e9967a 58%, #3a6f8f 60%, #1f3b57 100%)'}}>
        <div style={{position: 'absolute', left: 620, top: A.h * 0.4, width: 160, height: 160, borderRadius: 80, background: '#fff3c4', boxShadow: '0 0 80px #ffe08a'}} />
        <div style={{position: 'absolute', left: 0, right: 0, top: A.h * 0.5, height: A.h * 0.12, background: 'linear-gradient(180deg, #2c3e50, #3a6f8f)', clipPath: 'polygon(0 100%, 0 40%, 12% 10%, 25% 55%, 40% 20%, 55% 60%, 70% 5%, 85% 45%, 100% 25%, 100% 100%)'}} />
      </div>
      {seam && <div style={{position: 'absolute', left: 140, right: 140, top: A.top + (A.area === 'bottom' ? F * 0.5 : A.h - F * 0.5) - 1, height: 3, background: `linear-gradient(90deg, transparent, ${seam}, transparent)`}} />}
    </>
  );
  // phong cách kiểu AE: hiện lớp phủ ưa dùng + hình vẽ / chữ 3D theo ghi chú đồ họa
  const ef: any = (p.style as any)?.effects || {};
  const gn = String((p.style as any)?.graphics?.ghiChu || '');
  const ov = Array.isArray(ef.overlay) ? ef.overlay[0] : null;
  const ae = (
    <>
      {ov && ov !== 'filmburn' && ov !== 'confetti' && <AbsoluteFill style={{mixBlendMode: (ov === 'grain' ? 'overlay' : ov === 'dust' ? 'normal' : 'screen') as any}}><Overlay e={{kind: ov, amount: 85, _i: 99}} dur={1000} theme={th} /></AbsoluteFill>}
      {ov === 'confetti' || (Array.isArray(ef.overlay) && ef.overlay.includes('confetti')) ? <Overlay e={{kind: 'confetti', amount: 100, seed: 3}} dur={1000} theme={th} /> : null}
      {!half && /text3d/.test(gn) && p.blocks === false && <Text3D e={{text: '2,5 TỶ', face: /chrome/.test(gn) ? 'chrome' : 'gold', motion: 'tilt', y: 1020, size: 150}} dur={1000} theme={th} />}
      {!half && /shape|khoanh|mũi tên|gạch chân|callout|chú thích/.test(gn) && (
        /callout|chú thích/.test(gn) && !/khoanh|circle/.test(gn)
          ? <Shape e={{kind: 'callout', x: 330, y: 840, x2: 600, y2: 740, text: 'Ban công rộng', color: S.style.accent}} dur={1000} theme={th} />
          : <>
              <Shape e={{kind: 'circle', x: 540, y: 1135, w: 440, h: 260, color: S.style.accent, width: 9}} dur={1000} theme={th} />
              <Shape e={{kind: 'arrow', x: 120, y: 1330, x2: 300, y2: 1190, bend: -0.3, color: S.style.accent, width: 9}} dur={1000} theme={th} />
            </>
      )}
    </>
  );
  const capTop = half ? (A.area === 'bottom' ? 1000 : 1440) : 1400;
  return (
    <AbsoluteFill style={{background: `radial-gradient(120% 80% at 30% 20%, ${th.mid}66, transparent 60%), linear-gradient(160deg, #3b4a63, ${th.dark || '#1b2333'})`}}>
      {p.bg && <Img src={staticFile(p.bg)} style={{width: '100%', height: '100%', objectFit: 'cover', filter: 'brightness(0.7) blur(7px)', transform: 'scale(1.05)'}} />}
      {(p.style as any)?.backdrop?.type === 'ink' && <InkScape pos="full" palette={(p.style as any).backdrop.palette || 'color'} />}
      {splitDemo}
      <StyledText text={p.title || 'Giá chỉ 2,5 tỷ'} hl={['2,5 tỷ']} y={half && A.area === 'bottom' ? 1280 : 330} dur={1000} theme={th} anim="none" out="none" size={tx.size ?? 110} />
      <StyledText text={p.sub || 'Ngày hôm qua thật bất ngờ'} y={half && A.area === 'bottom' ? 1530 : 600} dur={1000} theme={th} anim="none" out="none" size={60} look={(tx.look as any) || 'clean'} upper={false} />
      {p.blocks !== false && !half && <DemoBlocks theme={th} />}
      {p.blocks === false && !half && (p.style as any)?.icons?.kind !== 'none' && <Sticker icon="👇" y={900} dur={1000} anim="none" out="none" loop="none" size={150} />}
      {ae}
      <Captions pages={cap as any} top={capTop} from={0} theme={th} />
      <FrameOverlay />
    </AbsoluteFill>
  );
};
