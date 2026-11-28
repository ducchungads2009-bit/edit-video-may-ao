/* Chữ tự do theo phong cách + nhãn dán (icon/emoji). Dùng cho element "text" (các look mới) và "sticker". */
import React from 'react';
import {FR} from './frame';
import {AbsoluteFill, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import * as Icons from 'lucide-react';
import {Marker} from './Graphics2';
import {Img, staticFile} from 'remotion';
import {EASES, S, TextAnim, TextOut, TextStyle, animStyle, fontCss, fontWeight, shadowCss, splitHl} from './style';

/** kiểu chữ động từng ký tự / từ (kinetic typography) */
export const KINETIC = ['stagger', 'wave', 'flip3d', 'maskUp', 'typeCursor', 'glitch', 'scramble', 'rise', 'spoken'];
const hash = (n: number) => {
  const x = Math.sin(n * 91.345 + 12.9898) * 43758.5453;
  return x - Math.floor(x);
};
const POOL = 'ABCDEFGHIKLMNOPQRSTUVXYĐ0123456789#%&@*';

/** vẽ chữ từng ký tự / từng từ theo kiểu kinetic. segs = đoạn có/không tô màu */
const Kinetic: React.FC<{segs: {t: string; hl: boolean}[]; anim: string; f: number; fps: number; hlColor: string; colorOf?: (w: string) => string; size: number; ease?: string; color: string; wt?: number[]}> = ({segs, anim, f, fps, hlColor: hlc0, colorOf, size, ease, color, wt}) => {
  let hlColor = hlc0;
  const cfg = EASES[ease || ''] || EASES.spring;
  const byWord = anim === 'maskUp' || anim === 'rise' || anim === 'spoken';
  let k = 0;
  const total = segs.reduce((n, s) => n + Array.from(s.t).length, 0);
  const typed = Math.floor(f * 1.4);
  const unit = (u: string, key: string, hl: boolean): React.ReactNode => {
    const i = k++;
    const base: React.CSSProperties = {display: 'inline-block', color: hl ? hlColor : undefined, whiteSpace: 'pre'};
    switch (anim) {
      case 'stagger': {
        const sp = spring({frame: f - i * 1.5, fps, config: cfg});
        return <span key={key} style={{...base, transform: `translateY(${(1 - sp) * size * 0.5}px) scale(${0.3 + 0.7 * sp})`, opacity: Math.min(1, sp * 1.6)}}>{u}</span>;
      }
      case 'wave': {
        const sp = spring({frame: f - i * 1.5, fps, config: cfg});
        const w = Math.sin(f * 0.22 - i * 0.55) * size * 0.07 * sp;
        return <span key={key} style={{...base, transform: `translateY(${(1 - sp) * size * 0.5 + w}px)`, opacity: Math.min(1, sp * 1.6)}}>{u}</span>;
      }
      case 'flip3d': {
        const sp = spring({frame: f - i * 2, fps, config: cfg});
        return <span key={key} style={{...base, transformOrigin: '50% 100%', transform: `perspective(600px) rotateX(${(1 - sp) * -95}deg)`, opacity: Math.min(1, sp * 2)}}>{u}</span>;
      }
      case 'maskUp': {
        const sp = spring({frame: f - i * 3, fps, config: cfg});
        return (
          <span key={key} style={{display: 'inline-block', overflow: 'hidden', verticalAlign: 'bottom', paddingTop: size * 0.14, marginTop: -size * 0.14, color: hl ? hlColor : undefined}}>
            <span style={{display: 'inline-block', transform: `translateY(${(1 - sp) * 115}%)`}}>{u}</span>
          </span>
        );
      }
      case 'rise': {
        const sp = spring({frame: f - i * 3, fps, config: EASES[ease || ''] || EASES.smooth});
        return <span key={key} style={{...base, transform: `translateY(${(1 - sp) * 60}px)`, opacity: sp, filter: sp < 0.97 ? `blur(${(1 - sp) * 10}px)` : undefined}}>{u}</span>;
      }
      case 'spoken': {
        // từng từ hiện đúng lúc được đọc (wt = giây của từng từ, tính từ lúc khối hiện), từ đang đọc phóng nhẹ
        const at = (wt && wt[i] != null ? wt[i] : i * 0.3) * fps;
        const sp = spring({frame: f - at, fps, config: {damping: 14, stiffness: 220}});
        const nx = (wt && wt[i + 1] != null ? wt[i + 1] : (i + 1) * 0.3) * fps;
        const cur = f >= at && f < nx;
        return <span key={key} style={{...base, opacity: f < at ? 0.0 : 1, transform: `translateY(${(1 - sp) * 20}px) scale(${cur ? 1.08 : 1})`, color: cur && !hl ? hlColor : base.color}}>{u}</span>;
      }
      case 'typeCursor':
        return i < typed ? <span key={key} style={{color: hl ? hlColor : undefined, whiteSpace: 'pre'}}>{u}</span> : null;
      case 'glitch': {
        const burst = f < 14 || f % 45 < 4;
        const r = hash(i * 7 + Math.floor(f / 2));
        const on = burst && r > 0.55;
        const sp = Math.min(1, Math.max(0, (f - i * 0.6) / 4));
        return (
          <span key={key} style={{...base, opacity: sp, transform: on ? `translate(${(hash(i + f) - 0.5) * size * 0.3}px, ${(hash(i * 3 + f) - 0.5) * size * 0.15}px)` : undefined, textShadow: on ? `${-size * 0.05}px 0 #ff2a55, ${size * 0.05}px 0 #22e6ff` : undefined}}>
            {u}
          </span>
        );
      }
      case 'scramble': {
        const rev = i * 1.2 + 8;
        const ch = f >= rev || /\s/.test(u) ? u : POOL[Math.floor(hash(i * 13 + Math.floor(f / 2)) * POOL.length)];
        return <span key={key} style={{...base, opacity: f >= i * 0.5 ? 1 : 0, color: f >= rev ? base.color : hl ? hlColor : color, filter: f >= rev ? undefined : 'brightness(1.4)'}}>{ch}</span>;
      }
    }
    return <span key={key} style={base}>{u}</span>;
  };
  const out: React.ReactNode[] = [];
  segs.forEach((s, si) => {
    hlColor = s.hl && colorOf ? colorOf(s.t) : hlc0;
    const parts = s.t.normalize('NFC').split(/(\s+)/);
    parts.forEach((w, wi) => {
      if (!w) return;
      if (/^\s+$/.test(w)) {
        if (anim === 'typeCursor') { if (k < typed) out.push(w); k += Array.from(w).length; } else out.push(w);
        return;
      }
      if (byWord) out.push(unit(w, `${si}-${wi}`, s.hl));
      else out.push(<span key={`${si}-${wi}`} style={{display: 'inline-block', whiteSpace: 'nowrap'}}>{Array.from(w).map((c, ci) => unit(c, `${si}-${wi}-${ci}`, s.hl))}</span>);
    });
  });
  if (anim === 'typeCursor') {
    const blink = typed < total || Math.floor(f / 8) % 2 === 0;
    out.push(<span key="cur" style={{display: 'inline-block', width: Math.max(4, size * 0.07), height: size * 0.95, marginLeft: size * 0.06, verticalAlign: '-0.12em', background: color, opacity: blink ? 1 : 0}} />);
  }
  return <>{out}</>;
};

type Theme = {light: string; mid: string; dark: string; gold1: string; gold2: string};

export type TextProps = TextStyle & {
  text: string;
  y: number;
  x?: number; // 0–1, tâm theo chiều ngang (mặc định giữa)
  width?: number; // bề ngang tối đa (px)
  align?: 'center' | 'left' | 'right';
  font?: string;
  italic?: boolean;
  rotate?: number;
  hl?: string[] | string; // từ khóa tô màu
  dur: number;
  theme: Theme;
};

/** look nào do khối chữ mới vẽ (các look cũ box/gold/tag vẫn dùng khối cũ trừ khi có thông số mới) */
export const NEW_LOOKS = ['outline', 'clean', 'shadow', 'solid', 'highlight', 'neon', 'skew', 'tape', 'pill2', 'dashed', 'chat'];

/* đo bề rộng chữ (tự co chữ cho vừa khung) */
let _cv: CanvasRenderingContext2D | null = null;
const measureW = (txt: string, font: string) => {
  try {
    if (!_cv) _cv = document.createElement('canvas').getContext('2d');
    if (!_cv) return txt.length * 0.56;
    _cv.font = font;
    return _cv.measureText(txt).width;
  } catch {
    return txt.length * 0.56;
  }
};
/* số chạy: "2,55 tỷ" -> số đầu tiên đếm từ 0 lên trong k (0..1) */
const countUp = (s: string, k: number) => {
  const m = s.match(/(\d+(?:[.,]\d+)?)/);
  if (!m || k >= 1) return s;
  const raw = m[1], dec = (raw.split(/[.,]/)[1] || '').length, sep = raw.includes(',') ? ',' : '.';
  const v = parseFloat(raw.replace(',', '.')) * (1 - Math.pow(1 - k, 3));
  return s.replace(raw, v.toFixed(dec).replace('.', sep));
};

export const StyledText: React.FC<TextProps> = (p) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const d = S.style.text || {};
  const t = p.theme;
  const look = p.look || d.look || 'plain';
  let size = p.size ?? d.size ?? 80;
  const font = p.font || S.style.heading || S.style.font;
  const weight = fontWeight(font, p.weight ?? d.weight ?? 900);
  const color = p.color || d.color || 'white';
  const bg = p.bg || d.bg || t.mid;
  const strokeColor = p.strokeColor || d.strokeColor || (look === 'outline' ? '#000' : t.dark);
  const stroke = p.stroke ?? d.stroke ?? (look === 'outline' ? Math.round(size / 5) : look === 'plain' ? Math.round(size / 7) : 0);
  const shadow = p.shadow || d.shadow || (look === 'outline' || look === 'solid' || look === 'highlight' ? 'none' : look === 'neon' ? 'glow' : look === 'shadow' ? 'hard' : 'soft');
  const anim: TextAnim = (p.anim || d.anim || 'pop') as TextAnim;
  const out: TextOut = (p.out || d.out || 'fade') as TextOut;
  const upper = p.upper ?? d.upper ?? false;
  const hlColor = p.hlColor || d.hlColor || t.gold1;
  const hlStyle = (p as any).hlStyle || (d as any).hlStyle || 'color';
  const radius = p.radius ?? d.radius ?? 18;
  const P = p as any;
  let text = upper ? p.text.toUpperCase() : p.text;
  // count: số đầu tiên trong chữ chạy từ 0 lên (countDur giây, mặc định 0.9)
  if (P.count) text = countUp(text, f / Math.max(1, (P.countDur ?? 0.9) * fps));
  const hl = upper && p.hl ? (Array.isArray(p.hl) ? p.hl : [p.hl]).map((s) => s.toUpperCase()) : p.hl;
  // hlColors: màu riêng cho từng từ khoá {"từ": "#màu"} (bôi đen chữ khi sửa trên khung hình rồi chọn màu)
  const hlc: Record<string, string> = Object.fromEntries(Object.entries(P.hlColors || {}).map(([k, v]) => [upper ? k.toUpperCase() : k, v as string]));
  const colorOf = (w: string) => hlc[w] || Object.entries(hlc).find(([k]) => k.toLowerCase() === w.toLowerCase())?.[1] || hlColor;
  // tự co chữ cho vừa khung (width): chọn cỡ lớn nhất mà chữ xuống dòng ≤ maxLines (mặc định 2) và không dòng nào tràn
  if (P.autofit && P.width) {
    const fw = (px: number) => `${p.italic ? 'italic ' : ''}${fontWeight(font, p.weight ?? d.weight ?? 900)} ${px}px ${fontCss(font)}`;
    const padX = look === 'solid' || ['skew', 'tape', 'pill2', 'dashed', 'chat'].includes(look) ? size * 0.9 : 24;
    const avail = P.width - padX, maxL = P.maxLines ?? (text.split(/\s+/).length > 6 ? 3 : 2), sp = p.spacing ?? d.spacing ?? 0;
    const linesAt = (px: number) => {
      let n = 0;
      for (const para of text.split('\n')) {
        let cur = '';
        n++;
        for (const wd of para.split(/\s+/).filter(Boolean)) {
          const nx = cur ? cur + ' ' + wd : wd;
          if (measureW(nx, fw(px)) + sp * nx.length > avail && cur) { n++; cur = wd; } else cur = nx;
          if (measureW(wd, fw(px)) + sp * wd.length > avail) return 99;
        }
      }
      return n;
    };
    let lo = Math.round(size * 0.3), hi = size;
    if (linesAt(hi) > maxL) {
      while (hi - lo > 1) { const mid = (lo + hi) >> 1; if (linesAt(mid) <= maxL) lo = mid; else hi = mid; }
      size = lo;
    }
  }

  const segs = splitHl(text, hl);
  // gõ từng ký tự / hiện từng từ
  const total = text.length;
  const nChars = anim === 'type' ? Math.min(total, Math.floor(f * 1.6)) : total;
  let used = 0, wordIdx = 0;
  const glow = look === 'neon' ? shadowCss('glow', color) : shadowCss(shadow, look === 'shadow' ? strokeColor : 'rgba(0,0,0,0.55)');
  const strokeCss: React.CSSProperties = stroke > 0 ? ({WebkitTextStroke: `${stroke}px ${strokeColor}`, paintOrder: 'stroke fill'} as any) : {};
  const ease = (p as any).ease || d.ease;
  const children = KINETIC.includes(anim) ? [<Kinetic key="k" segs={segs} anim={anim} f={f} fps={fps} hlColor={hlColor} colorOf={colorOf} size={size} ease={ease} color={color} wt={P.wt} />] : segs.map((s, i) => {
    let str = s.t;
    if (anim === 'type') {
      str = str.slice(0, Math.max(0, nChars - used));
      used += s.t.length;
    }
    const segStyle: React.CSSProperties = s.hl ? {color: colorOf(s.t)} : {};
    if (anim === 'words') {
      const parts = str.split(/(\s+)/);
      return (
        <span key={i} style={segStyle}>
          {parts.map((w, j) => {
            if (/^\s+$/.test(w) || !w) return w;
            const k = wordIdx++;
            const pop = spring({frame: f - k * 4, fps, config: {damping: 12, stiffness: 200}});
            return (
              <span key={j} style={{display: 'inline-block', transform: `scale(${0.5 + 0.5 * pop}) translateY(${(1 - pop) * 30}px)`, opacity: Math.min(1, pop * 2)}}>
                {w}
              </span>
            );
          })}
        </span>
      );
    }
    if (s.hl && hlStyle === 'marker') {
      const k = Math.max(0, Math.min(1, (f - 5 - i * 2) / 7));
      return <Marker key={i} p={k} color={p.hlColor || d.hlColor || undefined}><span style={{color: '#111', textShadow: 'none', WebkitTextStroke: '0px'} as any}>{str}</span></Marker>;
    }
    if (s.hl && hlStyle === 'box')
      return (
        <span key={i} style={{background: '#111', color: 'white', padding: '0 0.18em', borderRadius: 8}}>
          {str}
        </span>
      );
    return (
      <span key={i} style={segStyle}>
        {str}
      </span>
    );
  });

  const padV = Math.round(size * 0.16), padH = Math.round(size * 0.42);
  const extraLook: Record<string, React.CSSProperties> = {
    skew: {background: bg, padding: `${padV}px ${padH}px ${Math.round(size * 0.1)}px`, transform: 'skewX(-10deg)', borderRadius: 4, boxShadow: `8px 8px 0 ${strokeColor}`},
    tape: {background: bg, padding: `${padV}px ${padH}px ${Math.round(size * 0.1)}px`, transform: 'rotate(-2deg)', borderRadius: 2, boxShadow: '0 6px 14px rgba(0,0,0,0.35)', clipPath: 'polygon(1% 4%, 4% 0, 96% 3%, 100% 0, 99% 96%, 96% 100%, 3% 97%, 0 100%)'},
    pill2: {background: `linear-gradient(90deg, ${strokeColor} 0 32%, ${bg} 32% 100%)`, padding: `${padV}px ${padH}px ${Math.round(size * 0.1)}px`, borderRadius: 999},
    dashed: {border: `${Math.max(3, Math.round(size / 18))}px dashed ${bg}`, padding: `${padV}px ${padH}px ${Math.round(size * 0.1)}px`, borderRadius: radius},
    chat: {background: bg, padding: `${padV}px ${padH}px ${Math.round(size * 0.12)}px`, borderRadius: `${size * 0.5}px ${size * 0.5}px ${size * 0.5}px 6px`, boxShadow: '0 8px 20px rgba(0,0,0,0.35)'},
  };
  const lookCss: React.CSSProperties = extraLook[look] ? extraLook[look] :
    look === 'solid'
      ? {background: bg, padding: `${Math.round(size * 0.18)}px ${Math.round(size * 0.45)}px ${Math.round(size * 0.12)}px`, borderRadius: radius}
      : look === 'highlight'
        ? ({background: `linear-gradient(180deg, transparent 60%, ${bg} 60%, ${bg} 97%, transparent 97%)`, WebkitBoxDecorationBreak: 'clone', boxDecorationBreak: 'clone', padding: '0 10px'} as any)
        : {};
  const block: React.CSSProperties = {
    fontFamily: fontCss(font),
    fontWeight: weight,
    fontStyle: p.italic ? 'italic' : 'normal',
    fontSize: size,
    // chữ in hoa có dấu chồng (Ư, Ễ, Ố) cần giãn dòng ≥ 1,35 kẻo bị cắt dấu khi xuống dòng
    lineHeight: look === 'highlight' ? 1.4 : upper && text.includes('\n') ? 1.35 : upper ? 1.28 : 1.18,
    letterSpacing: p.spacing ?? d.spacing ?? 0,
    color,
    textAlign: p.align || S.style.layout?.align || 'center',
    whiteSpace: 'pre-wrap',
    textShadow: glow,
    paddingTop: Math.round(size * 0.12), // chừa chỗ cho dấu tiếng Việt
    ...strokeCss,
  };
  // tô chữ: gradient 2 màu (grad) hoặc lồng ảnh (fillSrc) — chữ trong suốt, nền cắt theo nét chữ
  const fillCss: React.CSSProperties | null = P.grad && P.grad.length >= 2
    ? ({backgroundImage: `linear-gradient(${P.gradAngle ?? 180}deg, ${P.grad.join(', ')})`, WebkitBackgroundClip: 'text', backgroundClip: 'text', color: 'transparent', WebkitTextFillColor: 'transparent'} as any)
    : P.fillSrc
      ? ({backgroundImage: `url(${/^(https?:|\/|blob:|data:)/.test(P.fillSrc) ? P.fillSrc : staticFile(P.fillSrc)})`, backgroundSize: 'cover', backgroundPosition: `${50 + Math.sin(f / 40) * 20}% 50%`, WebkitBackgroundClip: 'text', backgroundClip: 'text', color: 'transparent', WebkitTextFillColor: 'transparent'} as any)
      : null;
  const a = animStyle(anim, out, f, p.dur, fps, (p as any).inDur ? (p as any).inDur * fps : undefined, (p as any).outDur ? (p as any).outDur * fps : undefined, {ease, mblur: (p as any).mblur ?? d.mblur});
  const w = p.width ?? 960;
  const al = p.align || S.style.layout?.align || 'center';
  const mx = al === 'center' ? 60 : Math.max(24, Math.min(240, S.style.layout?.marginX ?? 60));
  const pos: React.CSSProperties =
    p.x != null
      ? {position: 'absolute', top: p.y, left: p.x * FR.w, width: w, marginLeft: -w / 2, display: 'flex', justifyContent: 'center'}
      : {position: 'absolute', top: p.y, left: 0, right: 0, padding: `0 ${mx}px`, display: 'flex', justifyContent: al === 'left' ? 'flex-start' : al === 'right' ? 'flex-end' : 'center'};
  return (
    <AbsoluteFill>
      <div style={pos}>
        <div style={{maxWidth: w, transform: `rotate(${p.rotate || 0}deg)`}}>
          <div style={{...a, transformOrigin: 'center'}}>
            {P.fillSrc ? <Img src={/^(https?:|\/|blob:|data:)/.test(P.fillSrc) ? P.fillSrc : staticFile(P.fillSrc)} style={{position: 'absolute', width: 1, height: 1, opacity: 0}} /> : null}
            {P.curve ? (
              <CurvedText text={text} curve={P.curve} size={size} block={block} fill={fillCss ? undefined : color} stroke={stroke} strokeColor={strokeColor} w={w} f={f} anim={anim} fps={fps} />
            ) : look === 'highlight' ? (
              <div style={{...block, ...(fillCss || {})}}>
                <span style={lookCss}>{children}</span>
              </div>
            ) : fillCss && lookCss.background ? (
              <div style={{...lookCss, display: 'inline-block'}}><div style={{...block, ...fillCss, textShadow: 'none'}}>{children}</div></div>
            ) : (
              <div style={{...block, ...lookCss, ...(fillCss ? {...fillCss, textShadow: 'none', filter: shadow !== 'none' && look !== 'neon' ? 'drop-shadow(0 1px 1px rgba(0,0,0,0.7)) drop-shadow(0 3px 4px rgba(0,0,0,0.45)) drop-shadow(0 8px 18px rgba(0,0,0,0.5))' : undefined} : {})}}>{children}</div>
            )}
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

/** chữ chạy theo đường cong (curve -100..100: âm = cong xuống, ±100 = gần nửa vòng tròn) */
const CurvedText: React.FC<{text: string; curve: number; size: number; block: React.CSSProperties; fill?: string; stroke: number; strokeColor: string; w: number; f: number; anim: string; fps: number}> = ({text, curve, size, block, fill, stroke, strokeColor, w, f, anim, fps}) => {
  const id = React.useMemo(() => 'cv' + Math.random().toString(36).slice(2, 8), []);
  const W = Math.max(300, w), k = Math.max(-1, Math.min(1, curve / 100));
  const h = Math.abs(k) * W * 0.45, H = h + size * 1.6;
  const y0 = k > 0 ? H - size * 0.35 : size * 1.1;
  const d = `M ${W * 0.04} ${y0} Q ${W / 2} ${k > 0 ? y0 - h * 2 : y0 + h * 2} ${W * 0.96} ${y0}`;
  const prog = ['type', 'typeCursor'].includes(anim) ? Math.min(1, f / Math.max(1, text.length / 1.6)) : 1;
  return (
    <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} style={{overflow: 'visible', display: 'block'}}>
      <defs><path id={id} d={d} /></defs>
      <text style={{fontFamily: block.fontFamily as string, fontWeight: block.fontWeight as any, fontStyle: block.fontStyle as any, letterSpacing: block.letterSpacing as any, filter: block.textShadow && block.textShadow !== 'none' ? 'drop-shadow(0 6px 10px rgba(0,0,0,0.5))' : undefined}} fontSize={size}
        fill={fill || 'white'} stroke={stroke > 0 ? strokeColor : undefined} strokeWidth={stroke > 0 ? stroke : undefined} paintOrder="stroke" textAnchor="middle">
        <textPath href={`#${id}`} startOffset="50%">{text.replace(/\n/g, ' ').slice(0, Math.ceil(text.length * prog))}</textPath>
      </text>
    </svg>
  );
};

/** nhãn dán: icon lucide (vd ArrowDown, Flame, Heart) hoặc emoji, có hiệu ứng lặp */
export const Sticker: React.FC<{icon: string; size?: number; color?: string; x?: number; y: number; anim?: TextAnim; out?: TextOut; loop?: string; rotate?: number; dur: number; inDur?: number; outDur?: number}> = (p) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const size = p.size ?? 150;
  const a = animStyle((p.anim || 'bounce') as TextAnim, (p.out || 'pop') as TextOut, f, p.dur, fps, p.inDur ? p.inDur * fps : undefined, p.outDur ? p.outDur * fps : undefined);
  const lp = p.loop || 'bob';
  const loopT =
    lp === 'bob'
      ? `translateY(${Math.sin(f / 6) * 14}px)`
      : lp === 'pulse'
        ? `scale(${1 + Math.sin(f / 5) * 0.08})`
        : lp === 'spin'
          ? `rotate(${f * 6}deg)`
          : lp === 'shake'
            ? `rotate(${Math.sin(f * 1.3) * 8}deg)`
            : '';
  const Cmp = (Icons as any)[p.icon];
  const x = (p.x ?? 0.5) * FR.w;
  return (
    <AbsoluteFill>
      <div style={{position: 'absolute', top: p.y, left: x - size / 2, width: size, height: size, ...a}}>
        <div style={{width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', transform: `${loopT} rotate(${p.rotate || 0}deg)`}}>
          {Cmp ? (
            <Cmp size={size} color={p.color || S.style.icons?.color || 'white'} strokeWidth={S.style.icons?.stroke ?? 2.6} fill={S.style.icons?.kind === 'filled' ? p.color || S.style.icons?.color || 'white' : 'none'} style={{filter: 'drop-shadow(0 8px 14px rgba(0,0,0,0.5))'}} />
          ) : (
            <span style={{fontSize: size * 0.86, lineHeight: 1, filter: 'drop-shadow(0 8px 14px rgba(0,0,0,0.45))'}}>{p.icon}</span>
          )}
        </div>
      </div>
    </AbsoluteFill>
  );
};


/** icon theo phong cách: tên lucide (ArrowDown…) hoặc emoji; màu/nét/đặc theo style.icons */
export const StyleIcon: React.FC<{name: string; size: number; color?: string}> = ({name, size, color}) => {
  const ic = S.style.icons || {};
  const C = (Icons as any)[name];
  if (!C && /^[A-Z][A-Za-z0-9]+$/.test(name)) {
    const D = Icons.Sparkles;
    return <D size={size} color={color || ic.color || 'white'} strokeWidth={ic.stroke ?? 2.6} />;
  }
  if (!C) return <span style={{fontSize: size * 0.95, lineHeight: 1, display: 'block'}}>{name}</span>;
  const c = color || ic.color || 'white';
  return <C size={size} color={c} strokeWidth={ic.stroke ?? 2.6} fill={ic.kind === 'filled' ? c : 'none'} />;
};
