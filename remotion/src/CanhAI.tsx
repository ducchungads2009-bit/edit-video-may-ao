/* CẢNH AI — khối `canhAI`: một cảnh đồ hoạ động do AI tự viết bằng HTML/SVG/Canvas/WebGL (cách làm của LumReels,
   github.com/lumtekvn/lumreels, MIT) rồi chèn vào video như mọi khối khác.

   Cảnh = thư mục trong dự án (vd `canh/gia-ban/index.html`) theo luật canh-ai/HUONG-DAN.md: gọi
   VideoScene.define({duration, render(t)}) — mỗi khung là hàm thuần của t nên Remotion tua tới khung nào cũng vẽ đúng.
   Nền cảnh trong suốt (`background: transparent`) = lớp phủ đè lên video; nền màu = cảnh chèn kín khung.

   plan.json:
   {"type": "canhAI", "start": 3, "end": 9, "canh": "canh/gia-ban",
    "data": {"gia": "4,2 tỷ", ...},      // dữ liệu đưa vào cảnh (cảnh đọc window.CANH.data) — 1 cảnh dùng lại cho nhiều dự án
    "from": 0,                            // bắt đầu từ giây thứ mấy của cảnh
    "speed": 1,                           // tốc độ chạy cảnh
    "fit": "cover",                       // cover (phủ kín) | contain (vừa khung) — khi khung video khác 9:16
    "fadeIn": 0.25, "fadeOut": 0.25,      // mờ vào / ra (giây), 0 = cắt thẳng
    "opacity": 1, "z": 30}
*/
import React, {useLayoutEffect, useMemo, useRef, useState} from 'react';
import {AbsoluteFill, continueRender, delayRender, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {S} from './style';

type SceneWin = Window & {__scene?: {duration: number; width: number; height: number; ready: Promise<boolean>; seek: (t: number) => Promise<void>}};

const waitFor = async <T,>(get: () => T | undefined | null, ms: number): Promise<T | null> => {
  const t0 = Date.now();
  for (;;) {
    const v = get();
    if (v) return v;
    if (Date.now() - t0 > ms) return null;
    await new Promise((r) => setTimeout(r, 25));
  }
};

export const CanhAI: React.FC<{e: any; dur: number}> = ({e, dur}) => {
  const frame = useCurrentFrame();
  const {fps, width: W, height: H} = useVideoConfig();
  const ref = useRef<HTMLIFrameElement>(null);
  const [loadH] = useState(() => delayRender('Cảnh AI: tải ' + (e.canh || ''), {timeoutInMilliseconds: 90000}));
  const [win, setWin] = useState<SceneWin | null>(null);
  const [failed, setFailed] = useState(false);

  const sw = Number(e.w) || 1080, sh = Number(e.h) || 1920; // cỡ thiết kế của cảnh
  const src = useMemo(() => {
    const st: any = S.style || {};
    const info = {
      data: e.data ?? {},
      w: sw, h: sh, frameW: W, frameH: H, dur,
      style: {font: st.font, heading: st.heading || st.font, fonts: st.fonts, text: st.text, captions: st.captions},
    };
    return staticFile(`${String(e.canh).replace(/\/+$/, '')}/index.html`) + '#canh=' + encodeURIComponent(JSON.stringify(info));
  }, [e.canh, JSON.stringify(e.data ?? {}), sw, sh, W, H, dur]);

  const t = Math.max(0, (Number(e.from) || 0) + (frame / fps) * (Number(e.speed) || 1));
  const tRef = useRef(t);
  tRef.current = t;

  const onLoad = () => {
    const w = ref.current?.contentWindow as SceneWin | null;
    (async () => {
      const sc = w && (await waitFor(() => w.__scene, 15000));
      if (!sc) {
        console.error(`[canhAI] ${e.canh}: cảnh không gọi VideoScene.define (xem canh-ai/HUONG-DAN.md)`);
        setFailed(true);
      } else {
        await Promise.race([sc.ready, new Promise((r) => setTimeout(r, 20000))]);
        try {
          await sc.seek(Math.min(tRef.current, sc.duration)); // khung đầu tiên vẽ luôn trước khi nhả
        } catch (err) {
          console.error('[canhAI] lỗi vẽ', err);
        }
        setWin(w);
      }
      continueRender(loadH);
    })();
  };

  // mỗi khung: tua cảnh tới t rồi mới cho chụp
  useLayoutEffect(() => {
    if (!win?.__scene) return;
    const h = delayRender('Cảnh AI: vẽ khung ' + frame);
    let done = false;
    win.__scene
      .seek(Math.min(t, win.__scene.duration))
      .catch((err) => console.error('[canhAI] lỗi vẽ', err))
      .then(() => new Promise((r) => setTimeout(r, 0)))
      .finally(() => {
        if (!done) {
          done = true;
          continueRender(h);
        }
      });
    return () => {
      if (!done) {
        done = true;
        continueRender(h);
      }
    };
  }, [win, t]);

  const fit = e.fit === 'contain' ? 'contain' : 'cover';
  const k = fit === 'contain' ? Math.min(W / sw, H / sh) : Math.max(W / sw, H / sh);
  const fi = Math.max(0, Number(e.fadeIn ?? 0.25)) * fps, fo = Math.max(0, Number(e.fadeOut ?? 0.25)) * fps;
  const total = Math.max(1, Math.round(dur * fps));
  const op = (e.opacity ?? 1) * (fi > 0 ? interpolate(frame, [0, fi], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}) : 1)
    * (fo > 0 ? interpolate(frame, [total - fo, total], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}) : 1);

  if (failed) return null;
  return (
    <AbsoluteFill style={{opacity: op, pointerEvents: 'none', overflow: 'hidden'}}>
      <iframe
        ref={ref}
        src={src}
        onLoad={onLoad}
        // @ts-ignore — thuộc tính cũ, giữ nền trong suốt trên mọi trình duyệt
        allowTransparency
        style={{
          position: 'absolute', border: 0, background: 'transparent', colorScheme: 'normal',
          width: sw, height: sh, left: (W - sw * k) / 2, top: (H - sh * k) / 2,
          transform: `scale(${k})`, transformOrigin: '0 0',
        }}
      />
    </AbsoluteFill>
  );
};
