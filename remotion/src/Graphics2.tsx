/* Khối đồ họa kiểu "editorial" (học từ bộ seecut/luancut/papercut, tự viết lại):
   cụm chữ 3 tầng, số đếm lên, dấu ✕/✓ đập xuống, tab so sánh, ô số 1·2·3, giấy vở, bong bóng câu hỏi, sao lấp lánh
   + chế độ NGƯỜI NÓI (thu thành thẻ / nửa màn / góc / cửa sổ) với nền giấy be nét đứt. */
import {InkScape} from './Ink';
import {FR} from './frame';
import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig, Easing} from 'remotion';
import * as Icons from 'lucide-react';
import {S, headFont} from './style';
import {fontCss} from './fonts';
import {skinDef} from './skins';

type Theme = {light: string; mid: string; dark: string; gold1: string; gold2: string};
export const MARK = '#F7DC6B'; // vàng bơ bút dạ quang
export const PAPER = '#EFE7D4';
const SERIF = '"Playfair Display", "Be Vietnam Pro", serif';
const bodyFont = () => fontCss(S.style.font);

const useIO = (dur: number, outF = 7) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const out = interpolate(f, [dur - outF, dur], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return {f, fps, out};
};
const pop = (f: number, fps: number, at = 0, damping = 11, stiffness = 190) => spring({frame: f - at, fps, config: {damping, stiffness}});
const fadeUp = (f: number, at: number, len = 9) => interpolate(f - at, [0, len], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic)});

/* ---------- chữ có đánh dấu: **bôi vàng**, __ô đen__ ---------- */
const markParts = (s: string) => {
  const out: {t: string; k: '' | 'mark' | 'box'}[] = [];
  const re = /(\*\*[^*]+\*\*|__[^_]+__)/g;
  let last = 0, m: RegExpExecArray | null;
  while ((m = re.exec(s))) {
    if (m.index > last) out.push({t: s.slice(last, m.index), k: ''});
    out.push({t: m[0].slice(2, -2), k: m[0].startsWith('**') ? 'mark' : 'box'});
    last = m.index + m[0].length;
  }
  if (last < s.length) out.push({t: s.slice(last), k: ''});
  return out;
};
/** vệt bút dạ quang quét từ trái + 2 thanh đen + 2 chấm tay cầm (kiểu "bôi chữ" trong phần mềm) */
export const Marker: React.FC<{children: React.ReactNode; p: number; color?: string; handles?: boolean}> = ({children, p, color = MARK, handles = true}) => (
  <span style={{position: 'relative', display: 'inline-block', padding: '0 0.12em', margin: '0 0.04em'}}>
    <span style={{position: 'absolute', left: 0, top: '8%', bottom: '4%', width: `${p * 100}%`, background: color, zIndex: 0, borderRadius: 4}} />
    {handles && p > 0.98 && (
      <>
        <span style={{position: 'absolute', left: -3, top: '4%', bottom: '0%', width: 5, background: '#111'}} />
        <span style={{position: 'absolute', right: -3, top: '4%', bottom: '0%', width: 5, background: '#111'}} />
        <span style={{position: 'absolute', left: -9, top: '-8%', width: 17, height: 17, borderRadius: 9, background: '#111'}} />
        <span style={{position: 'absolute', right: -9, bottom: '-10%', width: 17, height: 17, borderRadius: 9, background: '#111'}} />
      </>
    )}
    <span style={{position: 'relative', zIndex: 1}}>{children}</span>
  </span>
);
export const MarkText: React.FC<{text: string; f: number; at?: number; color?: string}> = ({text, f, at = 4, color}) => {
  let n = 0;
  return (
    <>
      {markParts(text).map((x, i) => {
        if (!x.k) return <React.Fragment key={i}>{x.t}</React.Fragment>;
        const p = interpolate(f - at - 3 * n++, [0, 7], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic)});
        if (x.k === 'mark') return <Marker key={i} p={p} color={color}>{x.t}</Marker>;
        return (
          <span key={i} style={{background: '#111', color: 'white', padding: '0 0.18em', borderRadius: 6, display: 'inline-block', transform: `scale(${0.85 + 0.15 * p})`, opacity: p}}>
            {x.t}
          </span>
        );
      })}
    </>
  );
};

const posX = (x: number | undefined, align: string | undefined): React.CSSProperties => {
  const al = align || S.style.layout?.align || 'center';
  if (x != null) return {left: x * FR.w, transform: 'translateX(-50%)', alignItems: 'center', textAlign: 'center'};
  const m = Math.max(24, Math.min(240, S.style.layout?.marginX ?? 70));
  return al === 'left' ? {left: m, right: m, alignItems: 'flex-start', textAlign: 'left'} : al === 'right' ? {left: m, right: m, alignItems: 'flex-end', textAlign: 'right'} : {left: m, right: m, alignItems: 'center', textAlign: 'center'};
};

/* ---------- 1. cụm chữ 3 tầng: dòng dẫn nhỏ → chữ lớn có chân in nghiêng → hộp IN HOA ---------- */
export const Phrase: React.FC<{e: any; dur: number; theme: Theme}> = ({e, dur, theme}) => {
  const {f, fps, out} = useIO(dur);
  const big = e.big || e.text || '';
  const onDark = e.dark ?? !e._light;
  const bigColor = e.color || (onDark ? '#FFFFFF' : theme.mid);
  const tSm = 0, tBig = Math.round((e.atBig ?? (e.sm ? 0.25 : 0)) * fps), tTag = Math.round((e.atTag ?? 0.55) * fps);
  const pb = pop(f, fps, tBig, 10, 180);
  const pt = pop(f, fps, tTag, 12, 200);
  return (
    <div style={{position: 'absolute', top: e.y ?? 300, display: 'flex', flexDirection: 'column', gap: 6, opacity: out, ...posX(e.x, e.align)}}>
      {e.sm && (
        <div style={{fontFamily: bodyFont(), fontWeight: 700, fontSize: (e.size ?? 120) * 0.36, color: onDark ? 'rgba(255,255,255,0.92)' : theme.dark, opacity: fadeUp(f, tSm), transform: `translateY(${(1 - fadeUp(f, tSm)) * 18}px)`, textShadow: onDark ? '0 2px 10px rgba(0,0,0,0.55)' : 'none', lineHeight: 1.35}}>
          {e.sm}
        </div>
      )}
      <div
        style={{
          fontFamily: SERIF, fontStyle: 'italic', fontWeight: 700, fontSize: e.size ?? 120, lineHeight: 1.12, color: bigColor,
          opacity: Math.min(1, pb * 1.6), transform: `scale(${0.86 + 0.14 * pb})`, transformOrigin: 'left center',
          textShadow: onDark ? `0 0 18px rgba(255,255,255,0.35), 0 4px 18px rgba(0,0,0,0.5)` : `0 0 0 #fff, 0 0 14px rgba(255,255,255,0.9)`,
          WebkitTextStroke: onDark ? undefined : '0px', whiteSpace: 'pre-line',
        } as any}
      >
        <MarkText text={big} f={f} at={tBig + 5} />
      </div>
      {e.tag && (
        <div style={{opacity: Math.min(1, pt * 1.5), transform: `translateY(${(1 - pt) * 24}px) scale(${0.9 + 0.1 * pt})`}}>
          <span
            style={
              e.tagStyle === 'pill'
                ? {display: 'inline-block', fontFamily: bodyFont(), fontWeight: 700, fontSize: (e.size ?? 120) * 0.3, color: theme.dark, background: 'white', padding: '8px 26px', borderRadius: 999, boxShadow: '0 6px 18px rgba(0,0,0,0.25)'}
                : {display: 'inline-block', fontFamily: bodyFont(), fontWeight: 900, fontSize: (e.size ?? 120) * 0.32, letterSpacing: 2, textTransform: 'uppercase', color: 'white', background: theme.mid, padding: '10px 26px', borderRadius: 10, boxShadow: `0 6px 0 ${theme.dark}, 0 12px 22px rgba(0,0,0,0.3)`, lineHeight: 1.35}
            }
          >
            {e.tag}
          </span>
        </div>
      )}
    </div>
  );
};

/* ---------- 2. số lớn đếm lên ---------- */
const fmtNum = (v: number, dec: number) => {
  const s = v.toFixed(dec);
  const [i, d] = s.split('.');
  return i.replace(/\B(?=(\d{3})+(?!\d))/g, '.') + (d ? ',' + d : '');
};
export const Counter: React.FC<{e: any; dur: number; theme: Theme}> = ({e, dur, theme}) => {
  const {f, fps, out} = useIO(dur);
  const to = Number(String(e.to ?? 0).replace(',', '.')) || 0;
  const from = Number(String(e.from ?? 0).replace(',', '.')) || 0;
  const dec = e.decimals ?? (String(e.to ?? '').match(/[.,](\d+)/)?.[1].length || 0);
  const len = Math.max(6, Math.round((e.count ?? 1.1) * fps));
  const k = interpolate(f, [0, len], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic)});
  const v = from + (to - from) * k;
  const land = pop(f, fps, len, 9, 220);
  const sz = e.size ?? 230;
  const light = !!e._light;
  const color = e.color || (light ? theme.mid : 'white');
  const ink = light ? theme.dark : 'rgba(255,255,255,0.95)';
  const tsh = light ? 'none' : '0 2px 10px rgba(0,0,0,0.5)';
  return (
    <div style={{position: 'absolute', top: e.y ?? 420, display: 'flex', flexDirection: 'column', opacity: out, ...posX(e.x, e.align)}}>
      {e.label && <div style={{fontFamily: bodyFont(), fontWeight: 800, fontSize: sz * 0.2, color: ink, textTransform: 'uppercase', letterSpacing: 2, textShadow: tsh, opacity: fadeUp(f, 0), lineHeight: 1.35}}>{e.label}</div>}
      <div style={{fontFamily: headFont(), fontWeight: 900, fontSize: sz, lineHeight: 1.05, color, transform: `scale(${1 + 0.06 * Math.sin(Math.min(1, land) * Math.PI)})`, textShadow: light ? `0 6px 0 ${theme.dark}33` : `0 6px 0 ${theme.dark}, 0 14px 30px rgba(0,0,0,0.45)`, fontVariantNumeric: 'tabular-nums', whiteSpace: 'nowrap'}}>
        {e.prefix || ''}
        {fmtNum(v, dec)}
        {e.suffix ? <span style={{fontSize: sz * 0.42, marginLeft: 10}}>{e.suffix}</span> : null}
      </div>
      {e.note && <div style={{fontFamily: bodyFont(), fontWeight: 600, fontSize: sz * 0.16, color: ink, textShadow: tsh, opacity: fadeUp(f, len), lineHeight: 1.35}}>{e.note}</div>}
    </div>
  );
};

/* ---------- 3. dấu ✕ / ✓ đập xuống ---------- */
export const Stamp: React.FC<{e: any; dur: number}> = ({e, dur}) => {
  const {f, fps, out} = useIO(dur);
  const k = interpolate(f, [0, 4, 8, 11], [1.9, 0.88, 1.05, 1], {extrapolateRight: 'clamp'});
  const op = interpolate(f, [0, 3], [0, 1], {extrapolateRight: 'clamp'});
  const ok = e.icon === 'check' || e.icon === 'v';
  const color = e.color || (ok ? '#16A34A' : '#E11D2E');
  const size = e.size ?? 260;
  const C = ok ? Icons.Check : Icons.X;
  return (
    <div style={{position: 'absolute', left: (e.x ?? 0.5) * FR.w, top: e.y ?? 600, transform: `translate(-50%, 0) scale(${k}) rotate(${e.rotate ?? -8}deg)`, opacity: op * out, filter: `drop-shadow(0 10px 18px rgba(0,0,0,0.35))`}}>
      {e.ring !== false ? (
        <div style={{width: size, height: size, borderRadius: '50%', border: `${size * 0.06}px solid ${color}`, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(255,255,255,0.12)'}}>
          <C size={size * 0.7} color={color} strokeWidth={3.4} />
        </div>
      ) : (
        <C size={size} color={color} strokeWidth={3.4} />
      )}
      {e.text && <div style={{textAlign: 'center', marginTop: 10, fontFamily: bodyFont(), fontWeight: 900, fontSize: size * 0.2, color, textTransform: 'uppercase', letterSpacing: 2, textShadow: '0 2px 0 white'}}>{e.text}</div>}
    </div>
  );
};

/* ---------- 4. tab so sánh (nền trắng trượt sang tab đang nói) ---------- */
export const Tabs: React.FC<{e: any; dur: number; theme: Theme}> = ({e, dur, theme}) => {
  const {f, fps, out} = useIO(dur);
  const raw: any[] = e.items || [];
  const items: string[] = raw.map((x) => (typeof x === 'string' ? x : x.text));
  const notes: string[] = raw.map((x, i) => (typeof x === 'string' ? e.notes?.[i] : x.note ?? e.notes?.[i]));
  const at: number[] = raw.map((x, i) => (((typeof x === 'object' && x.at != null ? x.at : e.at?.[i]) ?? e.start + i * 1.5) - e.start) * fps);
  let idx = 0;
  at.forEach((a, i) => {
    if (f >= a) idx = i;
  });
  const prevA = at[idx] ?? 0;
  const prev = idx > 0 ? idx - 1 : 0;
  const k = interpolate(f - prevA, [0, 7], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic)});
  const pos = prev + (idx - prev) * (at.length ? k : 1);
  const n = Math.max(1, items.length);
  const w = e.width ?? 940;
  const inn = pop(f, fps, 0, 13, 170);
  return (
    <div style={{position: 'absolute', top: e.y ?? 260, left: (FR.w - w) / 2, width: w, opacity: out, transform: `translateY(${(1 - inn) * -30}px)`}}>
      {e.title && <div style={{textAlign: 'center', fontFamily: SERIF, fontStyle: 'italic', fontWeight: 700, fontSize: 64, color: e._light ? theme.mid : 'white', marginBottom: 14, textShadow: e._light ? 'none' : '0 3px 14px rgba(0,0,0,0.5)'}}>{e.title}</div>}
      <div style={{position: 'relative', display: 'flex', background: `${theme.dark}CC`, borderRadius: 999, padding: 8, boxShadow: '0 10px 30px rgba(0,0,0,0.3)'}}>
        <div style={{position: 'absolute', top: 8, bottom: 8, left: 8 + pos * ((w - 16) / n), width: (w - 16) / n, background: 'white', borderRadius: 999, boxShadow: '0 4px 12px rgba(0,0,0,0.25)'}} />
        {items.map((it, i) => (
          <div key={i} style={{position: 'relative', flex: 1, textAlign: 'center', padding: '20px 10px', fontFamily: bodyFont(), fontWeight: 800, fontSize: e.size ?? 44, color: Math.round(pos) === i ? theme.dark : 'white', lineHeight: 1.35}}>
            {it}
          </div>
        ))}
      </div>
      {notes[idx] && (
        <div style={{marginTop: 18, textAlign: 'center', fontFamily: bodyFont(), fontWeight: 700, fontSize: (e.size ?? 44) * 0.95, color: e._light ? theme.dark : 'white', textShadow: e._light ? 'none' : '0 2px 10px rgba(0,0,0,0.55)', opacity: k, lineHeight: 1.4}}>{notes[idx]}</div>
      )}
    </div>
  );
};

/* ---------- 5. ô số 1·2·3 (bước / ý) ---------- */
export const Tiles: React.FC<{e: any; dur: number; theme: Theme}> = ({e, dur, theme}) => {
  const {f, fps, out} = useIO(dur);
  const raw: any[] = e.items || [];
  const items: string[] = raw.map((x) => (typeof x === 'string' ? x : x.text));
  const at: number[] = raw.map((x, i) => (((typeof x === 'object' && x.at != null ? x.at : e.at?.[i]) ?? e.start + i * 0.6) - e.start) * fps);
  let cur = -1;
  at.forEach((a, i) => {
    if (f >= a) cur = i;
  });
  const cols = e.cols ?? Math.min(3, items.length || 1);
  return (
    <div style={{position: 'absolute', top: e.y ?? 300, left: 50, right: 50, display: 'grid', gridTemplateColumns: `repeat(${cols}, 1fr)`, gap: 22, opacity: out}}>
      {items.map((it, i) => {
        const s = pop(f, fps, at[i], 11, 200);
        if (s <= 0.001) return <div key={i} />;
        const on = i === cur;
        return (
          <div key={i} style={{transform: `scale(${0.6 + 0.4 * s}) translateY(${(1 - s) * 30}px)`, opacity: Math.min(1, s * 1.6), background: on ? theme.mid : 'rgba(255,255,255,0.94)', borderRadius: 28, padding: '22px 18px 26px', boxShadow: on ? `0 8px 0 ${theme.dark}, 0 16px 28px rgba(0,0,0,0.3)` : '0 8px 22px rgba(0,0,0,0.22)', textAlign: 'center'}}>
            <div style={{fontFamily: SERIF, fontStyle: 'italic', fontWeight: 700, fontSize: 92, lineHeight: 1, color: on ? 'white' : theme.mid}}>{i + 1}</div>
            <div style={{marginTop: 8, fontFamily: bodyFont(), fontWeight: 800, fontSize: e.size ?? 38, color: on ? 'white' : theme.dark, lineHeight: 1.35}}>{it}</div>
          </div>
        );
      })}
    </div>
  );
};

/* ---------- 6. thẻ giấy vở (kẹp + băng dính, từng dòng tích) ---------- */
export const Note: React.FC<{e: any; dur: number; theme: Theme}> = ({e, dur, theme}) => {
  const {f, fps, out} = useIO(dur);
  const inn = pop(f, fps, 0, 12, 160);
  const items: {text: string; at?: number}[] = (e.items || []).map((x: any) => (typeof x === 'string' ? {text: x} : x));
  const lh = 78;
  return (
    <div style={{position: 'absolute', top: e.y ?? 260, left: 90, right: 90, opacity: out, transform: `translateY(${(1 - inn) * -40}px) rotate(${(e.rotate ?? -1.5) * inn}deg)`}}>
      <div style={{position: 'relative', background: '#FFFDF6', borderRadius: 18, padding: '70px 44px 36px 110px', boxShadow: '0 18px 40px rgba(0,0,0,0.3)', backgroundImage: `repeating-linear-gradient(180deg, transparent 0 ${lh - 2}px, #BFD6EE ${lh - 2}px ${lh}px)`, backgroundPosition: '0 58px'}}>
        <div style={{position: 'absolute', left: 84, top: 0, bottom: 0, width: 3, background: '#F2A3A3'}} />
        <div style={{position: 'absolute', top: -26, left: '50%', transform: 'translateX(-50%)', width: 150, height: 54, borderRadius: 12, background: '#9AA3AE', boxShadow: 'inset 0 -6px 0 #6B7480, 0 6px 12px rgba(0,0,0,0.3)'}} />
        <div style={{position: 'absolute', top: 10, right: -20, width: 120, height: 40, background: 'rgba(247,220,107,0.85)', transform: 'rotate(18deg)'}} />
        {e.title && <div style={{position: 'absolute', top: 14, left: 110, fontFamily: '"Patrick Hand", ' + bodyFont(), fontSize: 52, color: theme.dark}}>{e.title}</div>}
        {items.map((it, i) => {
          const a = ((it.at ?? e.start + 0.3 + i * 0.7) - e.start) * fps;
          const s = pop(f, fps, a, 12, 200);
          const ck = pop(f, fps, a - 2, 10, 220);
          return (
            <div key={i} style={{position: 'relative', height: lh, display: 'flex', alignItems: 'center', gap: 18, opacity: Math.min(1, s * 1.5), transform: `translateX(${(1 - s) * 40}px)`}}>
              <div style={{position: 'absolute', left: -82, width: 46, height: 46, borderRadius: 23, border: `4px solid ${theme.mid}`, display: 'flex', alignItems: 'center', justifyContent: 'center', transform: `scale(${ck})`}}>
                <Icons.Check size={30} color={theme.mid} strokeWidth={4} />
              </div>
              <span style={{fontFamily: bodyFont(), fontWeight: 700, fontSize: e.size ?? 46, color: '#1F2937', lineHeight: 1.3}}>{it.text}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
};

/* ---------- 7. bong bóng câu hỏi ---------- */
export const Bubble: React.FC<{e: any; dur: number; theme: Theme}> = ({e, dur, theme}) => {
  const {f, fps, out} = useIO(dur);
  const s = pop(f, fps, 0, 10, 210);
  const right = e.side === 'r';
  const bg = e.bg || 'white';
  return (
    <div style={{position: 'absolute', top: e.y ?? 380, left: (e.x ?? (right ? 0.62 : 0.38)) * FR.w, transform: `translateX(-50%) scale(${0.5 + 0.5 * s})`, transformOrigin: right ? '85% 100%' : '15% 100%', opacity: Math.min(1, s * 1.6) * out, maxWidth: 780}}>
      <div style={{position: 'relative', background: bg, borderRadius: 40, padding: '26px 40px', fontFamily: bodyFont(), fontWeight: 800, fontSize: e.size ?? 54, color: e.color || theme.dark, boxShadow: '0 12px 30px rgba(0,0,0,0.28)', lineHeight: 1.35, textAlign: 'center'}}>
        <MarkText text={e.text || ''} f={f} at={6} />
        <div style={{position: 'absolute', bottom: -26, [right ? 'right' : 'left']: 60, width: 0, height: 0, borderLeft: '22px solid transparent', borderRight: '22px solid transparent', borderTop: `30px solid ${bg}`, transform: `skewX(${right ? 20 : -20}deg)`} as any} />
      </div>
    </div>
  );
};

/* ---------- 8. sao lấp lánh ---------- */
const Star4: React.FC<{size: number; color: string}> = ({size, color}) => (
  <svg width={size} height={size} viewBox="-50 -50 100 100">
    <path d="M0,-50 C6,-10 10,-6 50,0 C10,6 6,10 0,50 C-6,10 -10,6 -50,0 C-10,-6 -6,-10 0,-50Z" fill={color} stroke="rgba(0,0,0,0.15)" strokeWidth={2} />
  </svg>
);
export const Spark: React.FC<{e: any; dur: number; theme: Theme}> = ({e, dur, theme}) => {
  const {f, fps, out} = useIO(dur);
  const n = e.count ?? 3;
  const pts = e.points || [[0, 0], [0.09, 0.06], [-0.07, 0.09], [0.05, -0.08]].slice(0, n);
  const size = e.size ?? 70;
  return (
    <>
      {pts.map(([dx, dy]: number[], i: number) => {
        const s = pop(f, fps, i * 4, 9, 230);
        const breathe = 0.78 + 0.22 * (0.5 + 0.5 * Math.sin((f - i * 7) / 6));
        return (
          <div key={i} style={{position: 'absolute', left: ((e.x ?? 0.8) + dx) * FR.w - size / 2, top: (e.y ?? 300) + dy * FR.w - size / 2, transform: `scale(${s * breathe * (i ? 0.7 : 1)}) rotate(${(1 - s) * 90}deg)`, opacity: out, filter: `drop-shadow(0 0 10px ${e.color || 'white'})`}}>
            <Star4 size={size} color={e.color || 'white'} />
          </div>
        );
      })}
    </>
  );
};

/* ================= NGƯỜI NÓI: thẻ / nửa màn / góc / cửa sổ ================= */
export type PresMode = 'full' | 'card' | 'split' | 'corner' | 'window';
type PT = {s: number; cx: number; cy: number; r: number; clip: number; dy: number; frame: number};
const idPT = (): PT => ({s: 1, cx: FR.w / 2, cy: FR.h / 2, r: 0, clip: 0, dy: 0, frame: 0});
export const presTarget = (e: any, faceCy?: number | null): PT => {
  const m: PresMode = e.mode || 'card';
  const s = e.s;
  switch (m) {
    case 'card': return {s: s ?? 0.5, cx: e.x != null ? e.x * FR.w : FR.w / 2, cy: e.y ?? 1290, r: e.r ?? 44, clip: 0, dy: 0, frame: e.frame ?? 10};
    case 'corner': return {s: s ?? 0.3, cx: e.x != null ? e.x * FR.w : FR.w - 36 - (FR.w * (s ?? 0.3)) / 2, cy: e.y ?? 1290, r: 30, clip: 0, dy: 0, frame: 8};
    case 'window': return {s: s ?? 0.64, cx: e.x != null ? e.x * FR.w : FR.w / 2, cy: e.y ?? 1200, r: e.r ?? 26, clip: 0, dy: 0, frame: e.frame ?? 12};
    case 'split': {
      const cut = e.cut ?? 900; // phía trên dành cho đồ họa
      const fy = e.focusY ?? faceCy ?? 720;
      const dy = Math.max(0, Math.min(cut, cut + (FR.h - cut) * 0.4 - fy));
      return {s: 1, cx: FR.w / 2, cy: FR.h / 2, r: 0, clip: cut, dy, frame: 0};
    }
    default: return idPT();
  }
};
const lerp = (a: PT, b: PT, k: number): PT => ({
  s: a.s + (b.s - a.s) * k, cx: a.cx + (b.cx - a.cx) * k, cy: a.cy + (b.cy - a.cy) * k, r: a.r + (b.r - a.r) * k,
  clip: a.clip + (b.clip - a.clip) * k, dy: a.dy + (b.dy - a.dy) * k, frame: a.frame + (b.frame - a.frame) * k,
});
const ease = (x: number) => Easing.inOut(Easing.cubic)(Math.max(0, Math.min(1, x)));

/** trạng thái người nói ở giây t: các khối presenter liền nhau thì chuyển thẳng từ kiểu này sang kiểu kia */
export const presenterAt = (els: any[], t: number, faceCy?: (t: number) => number | null) => {
  const ps = els.filter((e) => e.type === 'presenter').sort((a, b) => a.start - b.start);
  if (!ps.length) return null;
  const i = ps.findIndex((e) => t >= e.start && t < e.end);
  if (i < 0) return null;
  const c = ps[i];
  const fc = faceCy ? faceCy(t) : null;
  const tgt = presTarget(c, fc);
  const prev = ps[i - 1], next = ps[i + 1];
  const inD = c.inDur ?? 0.4, outD = c.outDur ?? 0.35;
  const from = prev && Math.abs(prev.end - c.start) < 0.12 ? presTarget(prev, fc) : idPT();
  let st = lerp(from, tgt, ease((t - c.start) / inD));
  if (!(next && Math.abs(next.start - c.end) < 0.12)) st = lerp(st, idPT(), ease(1 - (c.end - t) / outD));
  const bgOf = (e: any) => e?.bg || 'paper';
  return {st, bg: bgOf(c), bgColor: c.bgColor, show: Math.max(Math.min(1, (1 - st.s) / 0.06), st.clip > 1 ? 1 : 0), e: c};
};

const paperSvg = (line: string, dot: string) =>
  `url("data:image/svg+xml;utf8,${encodeURIComponent(
    `<svg xmlns='http://www.w3.org/2000/svg' width='98' height='98'><path d='M0 0.5H98M0.5 0V98' stroke='${line}' stroke-width='2' stroke-dasharray='7 6' fill='none'/><circle cx='1' cy='1' r='4' fill='${dot}'/></svg>`,
  )}")`;
export const PresenterBg: React.FC<{bg: string; color?: string; show: number}> = ({bg, color, show}) => {
  if (show <= 0) return null;
  if (bg && bg.startsWith('ink')) // tranh thủy mặc làm nền: ink | ink-color | ink-night | ink-dawn
    return (
      <AbsoluteFill style={{opacity: show}}>
        <InkScape pos="full" palette={bg.split('-')[1] || 'mono'} />
      </AbsoluteFill>
    );
  const st: React.CSSProperties =
    bg === 'dark' ? {background: '#0B1220', backgroundImage: paperSvg('rgba(255,255,255,0.18)', 'rgba(255,255,255,0.35)')}
    : bg === 'ocean' ? {background: '#EEF6FD', backgroundImage: paperSvg('rgba(17,112,208,0.35)', 'rgba(17,112,208,0.6)')}
    : bg === 'color' ? {background: color || '#111827'}
    : {background: PAPER, backgroundImage: paperSvg('rgba(0,0,0,0.42)', 'rgba(0,0,0,0.75)')};
  return <AbsoluteFill style={{...st, opacity: show}} />;
};
/** style cho lớp bọc video chính (và lớp người tách nền) */
export const presenterWrap = (st: PT, mode: string) => {
  const outer: React.CSSProperties = st.clip > 0.5 ? {clipPath: `inset(${st.clip}px 0 0 0)`} : {};
  const inner: React.CSSProperties =
    st.s === 1 && st.dy === 0 && st.r === 0 && st.cx === FR.w / 2 && st.cy === FR.h / 2
      ? {}
      : {
          transform: `translate(${st.cx - FR.w / 2}px, ${st.cy - FR.h / 2 + st.dy}px) scale(${st.s})`,
          transformOrigin: '50% 50%',
          borderRadius: st.r / Math.max(0.05, st.s),
          overflow: 'hidden',
          boxShadow: st.frame > 0.2 ? `0 0 0 ${st.frame / st.s}px white, 0 ${30 / st.s}px ${70 / st.s}px rgba(0,0,0,0.38)` : undefined,
        };
  return {outer, inner, bar: mode === 'split' && st.clip > 0.5 ? st.clip : 0};
};

/* ---------- 9. BIỂU ĐỒ ĐỘNG: cột | thanh ngang | tròn (donut) | đường | thanh tiến độ ----------
   data: "Quận 1: 120, Quận 2: 95, Thủ Đức: 60" hoặc [{label, value}]; unit ("tr/m²"), title, max, highlight (nhãn tô nổi) */
const parseData = (d: any): {label: string; value: number; color?: string}[] => {
  if (Array.isArray(d)) return d.map((x) => ({label: String(x.label ?? x.l ?? ''), value: Number(String(x.value ?? x.v ?? 0).replace(',', '.')) || 0, color: x.color}));
  const out: {label: string; value: number}[] = [];
  // "Nhãn: số" lặp lại; số dạng 2,5 / 2.5 / 1.200 (nghìn); nhãn có thể bắt đầu bằng số (2PN, 2024)
  const re = /([^:=\n;]+?)\s*[:=]\s*(-?\d+(?:[.,]\d+)*)/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(String(d || '')))) {
    const label = m[1].replace(/^[\s,;]+/, '').trim();
    let num = m[2];
    num = /^-?\d{1,3}(\.\d{3})+$/.test(num) ? num.replace(/\./g, '') : num.replace(',', '.');
    out.push({label, value: Number(num) || 0});
  }
  return out;
};
const fmtV = (v: number) => (Math.abs(v) >= 1000 || Number.isInteger(Math.round(v * 10) / 10) ? Math.round(v).toLocaleString('vi-VN') : v.toFixed(1).replace('.', ',')); // 144,4 giữ 1 số lẻ
export const Chart: React.FC<{e: any; dur: number; theme: Theme}> = ({e, dur, theme}) => {
  const {f, fps, out} = useIO(dur);
  const data = parseData(e.data);
  const kind = e.kind || 'bar';
  const light = !!e._light || !!skinDef()?.light;
  const ink = light ? theme.dark : 'white';
  const sub = light ? 'rgba(0,0,0,0.55)' : 'rgba(255,255,255,0.75)';
  const ac = e.color || S.style.accent || theme.light;
  const max = e.max ?? Math.max(1, ...data.map((d) => d.value));
  const grow = (i: number) => interpolate(f - 6 - i * 4, [0, 18], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic)});
  const hi = (l: string) => e.highlight && String(e.highlight).toLowerCase() === l.toLowerCase();
  const cardBg = light ? 'rgba(255,255,255,0.95)' : 'rgba(12,16,24,0.72)';
  const inn = pop(f, fps, 0, 14, 170);
  const W0 = e.width ?? 940, H0 = e.height ?? 560;
  let body: React.ReactNode = null;
  // màu từng cột: data[i].color > e.colors[i] > cột âm đỏ > accent
  const colorOf = (d: {value: number; color?: string; label: string}, i: number) =>
    d.color || (Array.isArray(e.colors) && e.colors.length ? e.colors[i % e.colors.length] : '') || (d.value < 0 ? (e.negColor || '#E3141B') : hi(d.label) || !e.highlight ? ac : `${ac}66`);
  const vmin = Math.min(0, ...data.map((d) => d.value));
  if (kind === 'bar' && vmin < 0) {
    // có số âm: trục 0 ở giữa, cột dương đi lên, cột âm đi xuống (đỏ)
    const bw = Math.min(140, (W0 - 80) / Math.max(1, data.length) - 24);
    const BH = H0 - 110, vmax = Math.max(0, ...data.map((d) => d.value)), span = Math.max(1e-6, vmax - vmin);
    const top0 = BH * 0.1 + (BH * 0.78 * vmax) / span;
    const sfx = e.unit && e.unitOnBar !== false ? ' ' + e.unit : '';
    body = (
      <div style={{position: 'relative', height: BH}}>
        <div style={{position: 'absolute', left: 0, right: 0, top: top0, height: 3, background: sub}} />
        <div style={{display: 'flex', justifyContent: 'center', gap: 24, height: '100%'}}>
          {data.map((d, i) => {
            const g = grow(i), neg = d.value < 0, h = (Math.abs(d.value) / span) * BH * 0.78 * g, col = colorOf(d, i);
            return (
              <div key={i} style={{position: 'relative', width: bw, height: '100%'}}>
                <div style={{position: 'absolute', left: 0, width: bw, top: neg ? top0 + 3 : top0 - h, height: h, background: col, borderRadius: neg ? '0 0 10px 10px' : '10px 10px 0 0'}} />
                <div style={{position: 'absolute', left: -60, right: -60, textAlign: 'center', top: neg ? top0 + 10 + h : top0 - h - 54, fontFamily: headFont(), fontWeight: 900, fontSize: 40, color: neg ? col : ink, opacity: g, whiteSpace: 'nowrap'}}>{fmtV(d.value * g)}{sfx}</div>
                <div style={{position: 'absolute', left: -60, right: -60, textAlign: 'center', top: neg ? top0 - 44 : top0 + 10, fontFamily: bodyFont(), fontWeight: 700, fontSize: 30, color: sub}}>{d.label}</div>
              </div>
            );
          })}
        </div>
      </div>
    );
  } else if (kind === 'bar') {
    const bw = Math.min(140, (W0 - 80) / Math.max(1, data.length) - 24);
    body = (
      <div style={{display: 'flex', alignItems: 'flex-end', justifyContent: 'center', gap: 24, height: H0 - 150, borderBottom: `3px solid ${sub}`}}>
        {data.map((d, i) => {
          const g = grow(i);
          return (
            <div key={i} style={{display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'flex-end', height: '100%'}}>
              <div style={{fontFamily: headFont(), fontWeight: 900, fontSize: 40, color: ink, opacity: g, marginBottom: 6}}>{fmtV(d.value * g)}</div>
              <div style={{width: bw, height: `${(d.value / max) * 78 * g}%`, minHeight: 2, background: colorOf(d, i), borderRadius: '10px 10px 0 0'}} />
            </div>
          );
        })}
      </div>
    );
    body = (
      <>
        {body}
        <div style={{display: 'flex', justifyContent: 'center', gap: 24, marginTop: 10}}>
          {data.map((d, i) => <div key={i} style={{width: bw, textAlign: 'center', fontFamily: bodyFont(), fontWeight: 700, fontSize: 30, color: sub, lineHeight: 1.25}}>{d.label}</div>)}
        </div>
      </>
    );
  } else if (kind === 'hbar') {
    body = data.map((d, i) => {
      const g = grow(i);
      return (
        <div key={i} style={{marginBottom: 18}}>
          <div style={{display: 'flex', justifyContent: 'space-between', fontFamily: bodyFont(), fontWeight: 700, fontSize: 36, color: ink, marginBottom: 6}}>
            <span>{d.label}</span>
            <span style={{fontFamily: headFont(), fontWeight: 900}}>{fmtV(d.value * g)}{e.unit ? ' ' + e.unit : ''}</span>
          </div>
          <div style={{height: 26, borderRadius: 13, background: light ? 'rgba(0,0,0,0.08)' : 'rgba(255,255,255,0.12)', overflow: 'hidden'}}>
            <div style={{height: '100%', width: `${(d.value / max) * 100 * g}%`, background: hi(d.label) || !e.highlight ? ac : `${ac}77`, borderRadius: 13}} />
          </div>
        </div>
      );
    });
  } else if (kind === 'donut' || kind === 'progress') {
    const tot = kind === 'progress' ? max : data.reduce((a, d) => a + d.value, 0) || 1;
    const R = 170, C = 2 * Math.PI * R, g = grow(0);
    const palette = Array.isArray(e.colors) && e.colors.length ? e.colors : [...new Set([ac, theme.gold2, '#F472B6', '#34D399', theme.light, '#A78BFA', theme.mid].map((c) => String(c).toUpperCase()))];
    let acc = 0;
    const segs = (kind === 'progress' ? data.slice(0, 1) : data).map((d, i) => {
      const frac = (d.value / tot) * g;
      const el = <circle key={i} r={R} cx={0} cy={0} fill="none" stroke={kind === 'progress' ? ac : palette[i % palette.length]} strokeWidth={56} strokeDasharray={`${frac * C} ${C}`} strokeDashoffset={-acc * C} transform="rotate(-90)" strokeLinecap={kind === 'progress' ? 'round' : 'butt'} />;
      acc += frac;
      return el;
    });
    const main = data[0];
    body = (
      <div style={{display: 'flex', alignItems: 'center', gap: 40, justifyContent: 'center'}}>
        <div style={{position: 'relative', width: 440, height: 440}}>
          <svg width={440} height={440} viewBox="-220 -220 440 440">
            <circle r={R} fill="none" stroke={light ? 'rgba(0,0,0,0.08)' : 'rgba(255,255,255,0.12)'} strokeWidth={56} />
            {segs}
          </svg>
          <div style={{position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center'}}>
            <div style={{fontFamily: headFont(), fontWeight: 900, fontSize: 84, color: ink}}>{main ? (kind === 'progress' ? fmtV(main.value * g) : Math.round((main.value / tot) * 100 * g) + '%') : ''}{kind === 'progress' && e.unit ? <span style={{fontSize: 40}}>{e.unit}</span> : null}</div>
            {main && <div style={{fontFamily: bodyFont(), fontWeight: 700, fontSize: 30, color: sub, textAlign: 'center', maxWidth: 260}}>{main.label}</div>}
          </div>
        </div>
        {kind === 'donut' && data.length > 1 && (
          <div>
            {data.map((d, i) => (
              <div key={i} style={{display: 'flex', alignItems: 'center', gap: 12, marginBottom: 14, opacity: grow(i)}}>
                <span style={{width: 26, height: 26, borderRadius: 6, background: palette[i % palette.length]}} />
                <span style={{fontFamily: bodyFont(), fontWeight: 700, fontSize: 32, color: ink}}>{d.label}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  } else if (kind === 'line') {
    const w = W0 - 80, h = H0 - 170, n = Math.max(2, data.length);
    const min = e.min ?? Math.min(0, ...data.map((d) => d.value));
    const pts = data.map((d, i) => [(i / (n - 1)) * w, h - ((d.value - min) / Math.max(1e-6, max - min)) * h * 0.9]);
    const g = interpolate(f - 6, [0, 30], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.inOut(Easing.cubic)});
    const path = pts.map((p, i) => `${i ? 'L' : 'M'}${p[0]},${p[1]}`).join(' ');
    let len = 0;
    for (let i = 1; i < pts.length; i++) len += Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]);
    body = (
      <>
        <svg width={w} height={h + 20} style={{display: 'block', margin: '0 auto', overflow: 'visible'}}>
          <line x1={0} y1={h} x2={w} y2={h} stroke={sub} strokeWidth={3} />
          <path d={path + ` L${w},${h} L0,${h} Z`} fill={`${ac}33`} opacity={g} />
          <path d={path} fill="none" stroke={ac} strokeWidth={8} strokeLinejoin="round" strokeLinecap="round" strokeDasharray={len} strokeDashoffset={len * (1 - g)} />
          {pts.map((p, i) => (i / (n - 1) <= g + 0.01 ? <circle key={i} cx={p[0]} cy={p[1]} r={12} fill={ac} stroke={light ? 'white' : '#0B1220'} strokeWidth={4} /> : null))}
          {pts.map((p, i) => (i / (n - 1) <= g + 0.01 ? <text key={'t' + i} x={p[0]} y={p[1] - 26} textAnchor="middle" fontFamily="Be Vietnam Pro" fontWeight={900} fontSize={34} fill={ink}>{fmtV(data[i].value)}</text> : null))}
        </svg>
        <div style={{display: 'flex', justifyContent: 'space-between', width: w, margin: '8px auto 0'}}>
          {data.map((d, i) => <span key={i} style={{fontFamily: bodyFont(), fontWeight: 700, fontSize: 28, color: sub}}>{d.label}</span>)}
        </div>
      </>
    );
  }
  const sd = skinDef();
  const cardCss: React.CSSProperties = e.card === false ? {background: 'transparent'} : sd ? {...sd.card(theme, ac), borderRadius: sd.radius(30) as any} : {background: cardBg, borderRadius: 30, boxShadow: '0 18px 40px rgba(0,0,0,0.3)'};
  return (
    <div style={{position: 'absolute', top: e.y ?? 300, left: (FR.w - W0) / 2, width: W0, opacity: out * Math.min(1, inn * 1.4), transform: `translateY(${(1 - inn) * 30}px)`,
      padding: e.card === false ? 0 : '30px 40px 34px', ...cardCss}}>
      {e.title && <div style={{fontFamily: headFont(), fontWeight: 900, fontSize: 48, color: ink, marginBottom: 6, lineHeight: 1.3}}>{e.title}</div>}
      {e.unit && kind !== 'hbar' && kind !== 'progress' && <div style={{fontFamily: bodyFont(), fontWeight: 600, fontSize: 28, color: sub, marginBottom: 14}}>Đơn vị: {e.unit}</div>}
      {body}
      {e.source && <div style={{fontFamily: bodyFont(), fontWeight: 500, fontSize: 24, color: sub, marginTop: 14}}>Nguồn: {e.source}</div>}
    </div>
  );
};
