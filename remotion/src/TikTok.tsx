import React, {useEffect, useState} from 'react';
import {
  AbsoluteFill,
  OffthreadVideo,
  continueRender,
  delayRender,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import '@fontsource/be-vietnam-pro/800.css';
import '@fontsource/be-vietnam-pro/900.css';

export type Word = {w: string; start: number; end: number};

export type TikTokProps = {
  videoSrc: string; // file in /public
  durationSec: number;
  day: number;
  totalDays: number;
  hook: string; // dùng *chữ* để tô vàng
  pages: Word[][]; // tạo bằng build_props.py
  captionsFrom: number; // giây bắt đầu hiện phụ đề
  captionTop: number; // vị trí dọc (px)
  cta: string;
  accent: string;
};

const FONT = '"Be Vietnam Pro", sans-serif';

// Biến **từ** trong chuỗi thành phần tô màu
const renderMarked = (s: string, accent: string) =>
  s.split(/(\*[^*]+\*)/g).map((part, i) =>
    part.startsWith('*') ? (
      <span key={i} style={{color: accent}}>
        {part.slice(1, -1)}
      </span>
    ) : (
      <span key={i}>{part}</span>
    ),
  );

const useFonts = () => {
  const [handle] = useState(() => delayRender('fonts'));
  useEffect(() => {
    Promise.all([
      document.fonts.load(`800 60px "Be Vietnam Pro"`, 'Ngày ữ'),
      document.fonts.load(`900 60px "Be Vietnam Pro"`, 'Ngày ữ'),
    ]).then(() => continueRender(handle));
  }, [handle]);
};


const DayBadge: React.FC<{day: number; total: number; accent: string}> = ({day, total, accent}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const pop = spring({frame, fps, config: {damping: 12}});
  const fill = interpolate(frame, [8, 30], [(day - 1) / total, day / total], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  return (
    <div style={{position: 'absolute', top: 150, left: 70, right: 160, transform: `scale(${pop})`, transformOrigin: 'left top'}}>
      <div
        style={{
          display: 'inline-block',
          background: accent,
          color: '#111',
          fontFamily: FONT,
          fontWeight: 900,
          fontSize: 52,
          padding: '10px 26px',
          borderRadius: 18,
          letterSpacing: 1,
        }}
      >
        NGÀY {day}/{total}
      </div>
      <div style={{marginTop: 18, height: 14, borderRadius: 7, background: 'rgba(255,255,255,0.25)', overflow: 'hidden'}}>
        <div style={{width: `${fill * 100}%`, height: '100%', background: accent}} />
      </div>
    </div>
  );
};

const Hook: React.FC<{text: string; accent: string}> = ({text, accent}) => {
  if (!text) return null;
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const inS = spring({frame, fps, config: {damping: 10, stiffness: 120}});
  const out = interpolate(frame, [2.4 * fps, 2.8 * fps], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  if (out <= 0) return null;
  return (
    <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', padding: '0 80px', opacity: out}}>
      <div
        style={{
          transform: `scale(${0.6 + 0.4 * inS}) rotate(-2deg)`,
          background: 'rgba(0,0,0,0.78)',
          borderRadius: 28,
          padding: '36px 44px',
          color: 'white',
          fontFamily: FONT,
          fontWeight: 900,
          fontSize: 76,
          lineHeight: 1.18,
          textAlign: 'center',
        }}
      >
        {renderMarked(text, accent)}
      </div>
    </AbsoluteFill>
  );
};

const Captions: React.FC<{pages: Word[][]; accent: string; top: number; hideBefore: number}> = ({
  pages,
  accent,
  top,
  hideBefore,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = frame / fps;
  if (t < hideBefore) return null;
  const page = pages.find((p) => t >= p[0].start && t < p[p.length - 1].end);
  if (!page) return null;
  const pageStartFrame = page[0].start * fps;
  const pop = spring({frame: frame - pageStartFrame, fps, config: {damping: 14, stiffness: 200}});
  return (
    <div
      style={{
        position: 'absolute',
        top,
        left: 40,
        right: 130, // chừa cột icon bên phải của TikTok
        textWrap: 'balance' as any,
        textAlign: 'center',
        transform: `scale(${0.85 + 0.15 * pop})`,
      }}
    >
      {page.map((w, i) => {
        const active = t >= w.start && t < w.end;
        return (
          <span
            key={i}
            style={{
              display: 'inline-block',
              margin: '0 14px',
              fontFamily: FONT,
              fontWeight: 900,
              fontSize: 70,
              lineHeight: 1.2,
              textTransform: 'uppercase',
              color: active ? accent : 'white',
              transform: active ? 'scale(1.12)' : 'scale(1)',
              WebkitTextStroke: '10px black',
              paintOrder: 'stroke fill',
              textShadow: '0 8px 24px rgba(0,0,0,0.6)',
            }}
          >
            {w.w}
          </span>
        );
      })}
    </div>
  );
};

const CTA: React.FC<{text: string; accent: string}> = ({text, accent}) => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();
  const start = durationInFrames - 2.5 * fps;
  if (frame < start) return null;
  const s = spring({frame: frame - start, fps, config: {damping: 12}});
  return (
    <div style={{position: 'absolute', top: 1000, left: 60, right: 160, display: 'flex', justifyContent: 'center'}}>
      <div
        style={{
          transform: `translateY(${(1 - s) * 200}px)`,
          opacity: s,
          background: 'white',
          color: '#111',
          fontFamily: FONT,
          fontWeight: 800,
          fontSize: 46,
          whiteSpace: 'nowrap',
          padding: '24px 36px',
          borderRadius: 999,
          border: `8px solid ${accent}`,
          textAlign: 'center',
        }}
      >
        {text}
      </div>
    </div>
  );
};

export const TikTok: React.FC<TikTokProps> = (p) => {
  useFonts();
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  // zoom chậm cho đỡ tĩnh
  const zoom = interpolate(frame, [0, durationInFrames], [1.0, 1.08]);
  return (
    <AbsoluteFill style={{background: 'black'}}>
      <AbsoluteFill style={{transform: `scale(${zoom})`}}>
        <OffthreadVideo src={staticFile(p.videoSrc)} style={{width: '100%', height: '100%', objectFit: 'cover'}} />
      </AbsoluteFill>
      <DayBadge day={p.day} total={p.totalDays} accent={p.accent} />
      <Hook text={p.hook} accent={p.accent} />
      <Captions pages={p.pages} accent={p.accent} top={p.captionTop} hideBefore={p.captionsFrom} />
      <CTA text={p.cta} accent={p.accent} />
    </AbsoluteFill>
  );
};
