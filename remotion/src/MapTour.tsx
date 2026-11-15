/* Khối BẢN ĐỒ KỂ CHUYỆN (kiểu "bí ẩn bản đồ"): nền ẢNH VỆ TINH thật, viền quốc gia phát sáng neon tự vẽ ra, từng VÙNG
   (tỉnh / nhóm tỉnh / quần đảo…) viền trắng tự vẽ + tô màu trong suốt + tên vùng lớn, camera bay / zoom lần lượt tới từng vùng,
   nhãn tên tỉnh (hộp trắng) bật ra, ảnh chân dung tròn + bảng tên cam, đường kẻ tự vẽ (tuyến, hướng di chuyển…).
   element: {type: 'mapTour', basemap: sat | dark | positron | liberty (mặc định sat), dim (0–1 làm tối nền, 0.15),
     glow: {geo, color '#d7ff3a', at 0.3, draw 1.6, width 3} (viền phát sáng — thường là cả nước),
     regions: [{name, label?, color, at (giây trong khối), geo (Polygon/MultiPolygon — scripts/ban_do.py --vung tự điền),
                opacity 0.55, glow?: true, labelRotate (độ), labelSize, labelLng/labelLat, focus (false = không bay tới),
                tags: [{name, lng, lat, at?}], badges: [{img, name, lng, lat, at?, size?}]}],
     lines: [{coords: [[lng, lat]...], at, dur 1.2, color '#ffd400', width 6, glow true}],
     shots: [{at, target: 'all' | <số vùng> | [lng, lat, zoom], dz?, fly?}] (bỏ trống = tự: toàn cảnh -> từng vùng -> toàn cảnh),
     drift (zoom chậm liên tục, 0.04/giây), frame: full | card}
   Kiểu GEOlayers: terrain (ĐỊA HÌNH 3D, số = độ nổi), hillshade, globe (mở đầu từ QUẢ ĐỊA CẦU), colors (màu bản đồ khi nền không
   phải vệ tinh), pitch / bearing (nghiêng / xoay camera), region.extrude (VÙNG NỔI KHỐI: true | mét), BẢN ĐỒ SỐ LIỆU: region.value +
   scale {from, to} (màu theo số) + legend {title, unit} + extrudeBy: 'value' (khối cao theo số); valueLabel = chữ hiện dưới tên vùng.
   Ảnh vệ tinh: Sentinel-2 cloudless 2016 của EOX (CC BY 4.0, ghi nguồn ở góc) — cần mạng lúc xem trước / xuất. */
import React, {useEffect, useRef, useState} from 'react';
import {AbsoluteFill, continueRender, delayRender, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import * as mlNS from 'maplibre-gl';
import {FR} from './frame';
import {merc, unmerc, sliceLine} from './MapBlock';
import {mediaSrc} from './Media';
import {S as STY} from './style';
import {addTerrain, addGlobe, applyColors, DEM_CREDIT, MapFx} from './mapfx';

const maplibregl: any = (mlNS as any).Map ? mlNS : ((mlNS as any).default?.Map ? (mlNS as any).default : ((globalThis as any).maplibregl || mlNS));
const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
const ease = (x: number) => (x <= 0 ? 0 : x >= 1 ? 1 : x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2);
const SAT = 'https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless_3857/default/g/{z}/{y}/{x}.jpg';
const SAT_CREDIT = 'Sentinel-2 cloudless – s2maps.eu by EOX IT Services GmbH (Copernicus Sentinel data 2016)';
const PALETTE = ['#2ecc71', '#1e3a8a', '#7c3aed', '#b91c1c', '#ea7a16', '#0f766e', '#be185d', '#ca8a04', '#2563eb'];

type LL = [number, number];
type Geo = {type: 'Polygon' | 'MultiPolygon'; coordinates: any};
type Tag = {name: string; lng: number; lat: number; at?: number};
type Badge = {img?: string; name?: string; lng: number; lat: number; at?: number; size?: number};
type Region = {keep?: boolean; value?: number; valueLabel?: string; extrude?: boolean | number; name?: string; label?: string; color?: string; at?: number; geo?: Geo; opacity?: number; glow?: boolean; labelRotate?: number; labelSize?: number; labelLng?: number; labelLat?: number; focus?: boolean; tags?: Tag[]; badges?: Badge[]};
type Line = {coords: LL[]; at?: number; dur?: number; color?: string; width?: number; glow?: boolean};
type Shot = {at: number; target?: 'all' | number | [number, number, number]; dz?: number; fly?: number};
export type MapTourEl = MapFx & {pitch?: number; bearing?: number; extrudeBy?: string; scale?: {from?: string; to?: string; min?: number; max?: number}; legend?: {title?: string; unit?: string} | false; basemap?: string; dim?: number; glow?: {geo?: Geo; color?: string; at?: number; draw?: number; width?: number}; regions?: Region[]; lines?: Line[]; shots?: Shot[]; drift?: number; frame?: string};

/* ---- hình học ---- */
const ringsOf = (g?: Geo): LL[][] => (!g ? [] : g.type === 'Polygon' ? g.coordinates : g.type === 'MultiPolygon' ? g.coordinates.flat() : []);
const outerRings = (g?: Geo): LL[][] => (!g ? [] : g.type === 'Polygon' ? [g.coordinates[0]] : g.type === 'MultiPolygon' ? g.coordinates.map((p: any) => p[0]) : []);
type BB = [number, number, number, number]; // merc x0, y0, x1, y1
const bbOf = (pts: LL[]): BB | null => {
  if (!pts.length) return null;
  let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
  for (const p of pts) {
    const [x, y] = merc(p);
    x0 = Math.min(x0, x); y0 = Math.min(y0, y); x1 = Math.max(x1, x); y1 = Math.max(y1, y);
  }
  return [x0, y0, x1, y1];
};
const joinBB = (a: BB | null, b: BB | null): BB | null => (!a ? b : !b ? a : [Math.min(a[0], b[0]), Math.min(a[1], b[1]), Math.max(a[2], b[2]), Math.max(a[3], b[3])]);
const ringArea = (r: LL[]) => {
  let s = 0;
  for (let i = 1; i < r.length; i++) s += (r[i - 1][0] * r[i][1] - r[i][0] * r[i - 1][1]);
  return Math.abs(s / 2);
};
/** điểm đặt tên vùng: tâm khung của vòng lớn nhất */
const labelPoint = (r: Region): LL | null => {
  if (isFinite(r.labelLng as number) && isFinite(r.labelLat as number)) return [r.labelLng!, r.labelLat!];
  const rs = outerRings(r.geo);
  if (!rs.length) return null;
  const big = rs.reduce((a, b) => (ringArea(b) > ringArea(a) ? b : a));
  const b = bbOf(big)!;
  return unmerc([(b[0] + b[2]) / 2, (b[1] + b[3]) / 2]);
};

export const MapTour: React.FC<{e: MapTourEl; dur: number}> = ({e: e0, dur}) => {
  const e = {...((STY.style as any).mapTour || {}), ...e0} as MapTourEl;
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = f / fps, D = dur / fps;
  const box = useRef<HTMLDivElement>(null);
  const [map, setMap] = useState<any>(null);
  const [fail, setFail] = useState('');
  const [, tick] = useState(0);
  const last = useRef<Record<string, number>>({});
  const card = e.frame === 'card';
  const W = card ? Math.min(960, FR.w - 120) : FR.w, H = card ? Math.min(1100, FR.h - 120) : FR.h;
  const regs: Region[] = (e.regions || []).filter((r) => r);
  const n = regs.length;
  // mốc từng vùng: không ghi -> chia đều sau đoạn mở đầu
  const step = n ? Math.max(1.2, (D - 2.2 - 1.6) / n) : 0;
  const atOf = (i: number) => (isFinite(regs[i].at as number) ? (regs[i].at as number) : 2.0 + i * step);
  const lines = (e.lines || []).filter((l) => l && l.coords?.length > 1);
  const glow = e.glow?.geo ? e.glow : null;
  const key = JSON.stringify([e.basemap, regs.map((r) => [r.geo ? ringsOf(r.geo).length : 0, r.color, r.glow, r.value, r.extrude]), lines.length, !!glow, card, e.terrain, e.hillshade, e.globe, e.colors, e.extrudeBy, e.scale]);

  /* ---- khung camera ---- */
  const padT = 0.2, padB = 0.3, padX = 0.12;
  const camFor = (b: BB | null, dz = 0) => {
    if (!b) return {x: 106, y: merc([106, 16])[1], z: 4.5 + dz};
    const wpx = Math.max(1e-6, (b[2] - b[0]) / 360) * 512, hpx = Math.max(1e-6, (b[3] - b[1]) / 360) * 512;
    const z = Math.max(1.5, Math.min(13.5, Math.log2(Math.min((W * (1 - 2 * padX)) / wpx, (H * (1 - padT - padB)) / hpx))));
    const sc = (512 * Math.pow(2, z)) / 360; // px / độ merc
    return {x: (b[0] + b[2]) / 2, y: (b[1] + b[3]) / 2 - (((padB - padT) / 2) * H) / sc, z: z + dz};
  };
  const regBB = regs.map((r) => {
    let b = bbOf(ringsOf(r.geo).flat());
    for (const x of [...(r.tags || []), ...(r.badges || [])]) if (isFinite(x.lng) && isFinite(x.lat)) b = joinBB(b, bbOf([[x.lng, x.lat]]));
    return b;
  });
  const allBB = [...regBB, glow ? bbOf(outerRings(glow.geo).flat()) : null, ...lines.map((l) => bbOf(l.coords))].reduce(joinBB, null as BB | null);
  /* ---- bản đồ số liệu: màu theo giá trị + chiều cao khối ---- */
  const vals = regs.map((r) => (typeof r.value === 'number' && isFinite(r.value) ? r.value : null));
  const hasVal = vals.some((v) => v != null);
  const vmin = e.scale?.min ?? Math.min(...(vals.filter((v) => v != null) as number[]));
  const vmax = e.scale?.max ?? Math.max(...(vals.filter((v) => v != null) as number[]));
  const hex = (c: string) => {
    const m = /^#?([0-9a-f]{6})/i.exec(c || '');
    const n2 = m ? parseInt(m[1], 16) : 0;
    return [(n2 >> 16) & 255, (n2 >> 8) & 255, n2 & 255];
  };
  const mix = (a: string, b: string, k: number) => '#' + hex(a).map((x, j) => Math.round(x + (hex(b)[j] - x) * k).toString(16).padStart(2, '0')).join('');
  const vk = (v: number | null) => (v == null || !isFinite(vmax - vmin) ? 0 : vmax > vmin ? (v - vmin) / (vmax - vmin) : 1);
  const colOf = (r: Region, i: number) => r.color || (hasVal && vals[i] != null ? mix(e.scale?.from || '#fde68a', e.scale?.to || '#b91c1c', vk(vals[i])) : PALETTE[i % PALETTE.length]);
  const spanM = allBB ? Math.max(((allBB[2] - allBB[0]) / 360) * 40075016, ((allBB[3] - allBB[1]) / 360) * 40075016) : 100000;
  const hOf = (r: Region, i: number) => {
    if (e.extrudeBy === 'value' && vals[i] != null) return spanM * 0.035 * (0.15 + 0.85 * vk(vals[i]));
    if (typeof r.extrude === 'number') return r.extrude;
    return r.extrude ? spanM * 0.015 : 0;
  };
  const anyX = regs.some((r, i) => hOf(r, i) > 0);
  const P0 = e.pitch ?? (anyX || e.terrain ? 50 : 0);
  const fmtV = (v: number) => (Math.abs(v) >= 1000 ? v.toLocaleString('vi-VN') : String(Math.round(v * 100) / 100).replace('.', ','));
  const shots: Shot[] = (e.shots && e.shots.length ? e.shots : (() => {
    const c0 = camFor(allBB);
    const L: Shot[] = e.globe
      ? [{at: 0, target: [unmerc([c0.x, c0.y])[0] - 40, unmerc([c0.x, c0.y])[1] * 0.4, 1.75]}, {at: 0.05, target: 'all', fly: 2.6}]
      : [{at: 0, target: 'all', dz: -1.6}, {at: 0.05, target: 'all', fly: 1.7}];
    // bản đồ số liệu dựng khối: giữ toàn cảnh để so sánh (không bay vào từng vùng), trừ vùng ghi focus: true
    const overview = hasVal && e.extrudeBy === 'value';
    regs.forEach((r, i) => {
      if ((overview ? r.focus === true : r.focus !== false) && regBB[i]) L.push({at: Math.max(0.1, atOf(i) - 0.55), target: i});
    });
    if (L.length > 2 && D - (L[L.length - 1].at + 0.55) > 3.2) L.push({at: D - 2.3, target: 'all', fly: 1.4});
    return L;
  })()).slice().sort((a, b) => a.at - b.at);
  const stateOf = (s: Shot) => {
    const tg = s.target ?? 'all';
    if (Array.isArray(tg)) return {x: tg[0], y: merc([tg[0], tg[1]])[1], z: tg[2] + (s.dz || 0)};
    return camFor(tg === 'all' ? allBB : regBB[tg as number] || allBB, s.dz || 0);
  };
  const DR = e.drift ?? 0.04;
  const camAt = (tt: number) => {
    let j = 0;
    for (let i = 0; i < shots.length; i++) if (shots[i].at <= tt) j = i;
    const cur = stateOf(shots[j]);
    const curZ = cur.z + DR * Math.max(0, tt - shots[j].at);
    if (j === 0) return {...cur, z: curZ};
    const pv = stateOf(shots[j - 1]);
    const from = {...pv, z: pv.z + DR * Math.max(0, shots[j].at - shots[j - 1].at)};
    const fly = Math.max(0.2, shots[j].fly ?? 1.25);
    const k = ease((tt - shots[j].at) / fly);
    const zmin = Math.min(from.z, cur.z);
    const dpx = (Math.hypot(cur.x - from.x, cur.y - from.y) / 360) * 512 * Math.pow(2, zmin);
    const dip = Math.max(0, Math.min(3, Math.log2(Math.max(1, dpx / (0.7 * W))))) * 0.55;
    return {x: from.x + (cur.x - from.x) * k, y: from.y + (cur.y - from.y) * k, z: from.z + (curZ - from.z) * k - dip * Math.sin(Math.PI * k)};
  };

  /* ---- tạo bản đồ ---- */
  useEffect(() => {
    if (!box.current) return;
    const h = delayRender('Tải bản đồ vệ tinh', {timeoutInMilliseconds: 60000});
    let done = false;
    const finish = () => {
      if (!done) {
        done = true;
        continueRender(h);
      }
    };
    const sat = (e.basemap || 'sat') === 'sat';
    const style: any = sat
      ? {version: 8, sources: {sat: {type: 'raster', tiles: [SAT], tileSize: 256, maxzoom: 14}}, layers: [{id: 'nen', type: 'background', paint: {'background-color': '#0b1626'}}, {id: 'sat', type: 'raster', source: 'sat', paint: {'raster-fade-duration': 0, 'raster-saturation': 0.12, 'raster-contrast': 0.08}}]}
      : `https://tiles.openfreemap.org/styles/${['positron', 'liberty', 'bright', 'dark', 'fiord'].includes(e.basemap || '') ? e.basemap : 'dark'}`;
    const c0 = camAt(0);
    const m = new maplibregl.Map({container: box.current, style, center: unmerc([c0.x, c0.y]), zoom: c0.z, interactive: false, fadeDuration: 0, attributionControl: false, preserveDrawingBuffer: true, pixelRatio: 1} as any);
    m.on('error', (ev: any) => {
      if (!m.isStyleLoaded()) {
        setFail('Không tải được bản đồ (cần mạng): ' + (ev?.error?.message || ''));
        finish();
      }
    });
    m.on('load', () => {
      for (const L of m.getStyle().layers || []) if (L.type === 'symbol') m.setLayoutProperty(L.id, 'visibility', 'none');
      applyColors(m, e);
      addTerrain(m, e, true);
      addGlobe(m, e, true);
      const dim = e.dim ?? 0.15;
      if (dim > 0) m.addLayer({id: 'dim', type: 'background', paint: {'background-color': '#000814', 'background-opacity': Math.min(0.85, dim)}});
      const EMPTY = {type: 'Feature', properties: {}, geometry: {type: 'MultiLineString', coordinates: []}};
      const neon = (id: string, color: string, w: number) => {
        m.addSource(id, {type: 'geojson', data: EMPTY});
        m.addLayer({id: id + 'a', type: 'line', source: id, layout: {'line-join': 'round', 'line-cap': 'round'}, paint: {'line-color': color, 'line-width': w * 6, 'line-blur': w * 5, 'line-opacity': 0.55}});
        m.addLayer({id: id + 'b', type: 'line', source: id, layout: {'line-join': 'round', 'line-cap': 'round'}, paint: {'line-color': color, 'line-width': w * 2.2, 'line-blur': w * 0.8, 'line-opacity': 0.9}});
        m.addLayer({id: id + 'c', type: 'line', source: id, layout: {'line-join': 'round', 'line-cap': 'round'}, paint: {'line-color': '#fbffe0', 'line-width': Math.max(1.2, w * 0.7)}});
      };
      regs.forEach((r, i) => {
        const col = colOf(r, i);
        m.addSource('f' + i, {type: 'geojson', data: r.geo ? {type: 'Feature', properties: {}, geometry: r.geo} : EMPTY});
        m.addLayer({id: 'f' + i, type: 'fill', source: 'f' + i, paint: {'fill-color': col, 'fill-opacity': 0}});
        if (hOf(r, i) > 0) m.addLayer({id: 'x' + i, type: 'fill-extrusion', source: 'f' + i, paint: {'fill-extrusion-color': col, 'fill-extrusion-height': 0, 'fill-extrusion-opacity': 0.88, 'fill-extrusion-vertical-gradient': true}});
        if (r.glow) neon('g' + i, col, 2.4);
        m.addSource('l' + i, {type: 'geojson', data: EMPTY});
        m.addLayer({id: 'l' + i + 's', type: 'line', source: 'l' + i, layout: {'line-join': 'round'}, paint: {'line-color': '#000', 'line-width': 6, 'line-blur': 4, 'line-opacity': 0.35}});
        m.addLayer({id: 'l' + i, type: 'line', source: 'l' + i, layout: {'line-join': 'round'}, paint: {'line-color': '#ffffff', 'line-width': 2.6}});
      });
      if (glow) neon('glow', glow.color || '#d7ff3a', glow.width ?? 3);
      lines.forEach((l, i) => {
        if (l.glow !== false) neon('k' + i, l.color || '#ffd400', (l.width ?? 6) / 2.4);
        else {
          m.addSource('k' + i, {type: 'geojson', data: EMPTY});
          m.addLayer({id: 'k' + i, type: 'line', source: 'k' + i, layout: {'line-join': 'round', 'line-cap': 'round'}, paint: {'line-color': l.color || '#ffd400', 'line-width': l.width ?? 6}});
        }
      });
      last.current = {};
      setMap(m);
      m.once('idle', finish);
      // địa hình / quả địa cầu: bản đồ có thể vẽ liên tục, không bao giờ 'idle' -> đợi đủ ô bản đồ rồi cho dựng (tối đa 20 giây)
      const poll = () => {
        if (done) return;
        if (m.areTilesLoaded && m.areTilesLoaded()) finish();
        else setTimeout(poll, 250);
      };
      setTimeout(poll, 600);
      setTimeout(finish, 20000);
    });
    return () => {
      finish();
      try {
        m.remove();
      } catch {}
      setMap(null);
    };
  }, [key]); // eslint-disable-line react-hooks/exhaustive-deps

  /* ---- mỗi khung: camera + nét vẽ + độ tô ---- */
  useEffect(() => {
    if (!map) return;
    const h = delayRender('Vẽ khung bản đồ vệ tinh', {timeoutInMilliseconds: 60000});
    const c = camAt(t);
    // nghiêng dần sau phần bay vào (địa hình / khối nổi mới thấy 3D); xoay nhẹ theo thời gian
    const tilt = ease(interpolate(t, [0.6, 2.4], [0, 1], clamp));
    map.jumpTo({center: unmerc([c.x, c.y]), zoom: c.z, pitch: P0 * tilt, bearing: (e.bearing ?? 0) + (P0 ? -10 + 14 * (t / Math.max(1, D)) : 0)});
    const setDraw = (id: string, rings: LL[][], k: number) => {
      const q = Math.round(k * 400) / 400;
      if (last.current[id] === q) return;
      last.current[id] = q;
      map.getSource(id)?.setData({type: 'Feature', properties: {}, geometry: {type: 'MultiLineString', coordinates: q <= 0 ? [] : rings.map((r) => sliceLine(r, q))}});
    };
    regs.forEach((r, i) => {
      const a = atOf(i);
      const rings = ringsOf(r.geo);
      setDraw('l' + i, rings, ease((t - a) / 0.9));
      if (r.glow) setDraw('g' + i, outerRings(r.geo), ease((t - a) / 0.9));
      const fo = interpolate(t, [a + 0.3, a + 0.85], [0, r.opacity ?? 0.55], clamp);
      if (last.current['f' + i] !== fo) {
        last.current['f' + i] = fo;
        map.setPaintProperty('f' + i, 'fill-opacity', hOf(r, i) > 0 ? fo * 0.4 : fo);
      }
      const hh = hOf(r, i);
      if (hh > 0) {
        const xk = ease(interpolate(t, [a + 0.4, a + 1.4], [0, 1], clamp));
        if (last.current['x' + i] !== xk) {
          last.current['x' + i] = xk;
          map.setPaintProperty('x' + i, 'fill-extrusion-height', hh * xk);
        }
      }
    });
    if (glow) setDraw('glow', outerRings(glow.geo), ease((t - (glow.at ?? 0.3)) / (glow.draw ?? 1.6)));
    lines.forEach((l, i) => setDraw('k' + i, [l.coords], ease((t - (l.at ?? 1)) / (l.dur ?? 1.2))));
    map.triggerRepaint();
    let done = false;
    const fin = () => {
      if (done) return;
      done = true;
      tick((x) => x + 1);
      continueRender(h);
    };
    map.once('idle', fin);
    // chờ ô bản đồ (cả địa hình) tải đủ: phải thấy "đủ" 3 lần liền (sau khi bản đồ đã bắt đầu vẽ khung mới)
    let ok = 0;
    const tp = () => {
      if (done) return;
      ok = map.areTilesLoaded && map.areTilesLoaded() ? ok + 1 : 0;
      if (ok >= 3) fin();
      else setTimeout(tp, 120);
    };
    setTimeout(tp, 350);
    const to = setTimeout(fin, 8000);
    return () => {
      clearTimeout(to);
      fin();
    };
  }, [map, f]); // eslint-disable-line react-hooks/exhaustive-deps

  const pop = (at: number, stiff = 170) => spring({frame: f - Math.round(at * fps), fps, config: {damping: 11, stiffness: stiff}});
  const proj = (p: LL) => (map ? map.project(p) : null);
  const out = interpolate(f, [dur - 8, dur], [1, 0], clamp);
  const appear = spring({frame: f, fps, config: {damping: 16, stiffness: 120}});
  return (
    <AbsoluteFill style={{opacity: out, ...(card ? {alignItems: 'center', justifyContent: 'center'} : {})}}>
      <div style={{position: 'relative', width: W, height: H, overflow: 'hidden', background: '#0b1626', ...(card ? {borderRadius: 44, boxShadow: '0 30px 80px rgba(0,0,0,.5)', border: '4px solid rgba(255,255,255,.85)', transform: `scale(${0.85 + 0.15 * appear})`, opacity: appear} : {})}}>
        <div ref={box} style={{position: 'absolute', inset: 0, width: W, height: H}} />
        {fail && <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', color: '#fff', background: '#1f2937', fontSize: 36, padding: 60, textAlign: 'center', fontFamily: 'sans-serif'}}>🛰 {fail}</AbsoluteFill>}
        {!n && !glow && !lines.length && <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', color: '#cbd5e1', fontSize: 40, fontFamily: 'sans-serif', textAlign: 'center', padding: 60}}>🛰 Thêm vùng cho bản đồ (tên tỉnh / quốc gia)</AbsoluteFill>}
        {map && regs.map((r, i) => {
          const a = atOf(i);
          // nhãn tỉnh + ảnh chân dung của vùng cũ tắt dần khi sang vùng kế (keep: true = giữ lại)
          const nextAt = !(r as any).keep && i + 1 < n ? atOf(i + 1) - 0.5 : Infinity;
          const gone = isFinite(nextAt) ? 1 - interpolate(t, [nextAt, nextAt + 0.35], [0, 1], clamp) : 1;
          const lp = labelPoint(r);
          const items: React.ReactNode[] = [];
          const nm = r.label ?? r.name;
          // khung chữ tên vùng (để nhãn tỉnh / ảnh tròn né ra)
          let lbox: number[] | null = null;
          if (lp && nm) {
            const q0 = proj(lp);
            const fs = r.labelSize ?? 56;
            if (q0) lbox = [q0.x - (nm.length * fs * 0.32), q0.y - fs * 0.8, q0.x + (nm.length * fs * 0.32), q0.y + fs * 0.8];
          }
          const dodge = (x: number, y: number, w: number, h: number, up: number) => {
            // hộp [x - w/2, y - up, x + w/2, y - up + h] đè tên vùng -> dời xuống dưới tên
            if (!lbox) return y;
            const b = [x - w / 2, y - up, x + w / 2, y - up + h];
            return b[0] < lbox[2] && lbox[0] < b[2] && b[1] < lbox[3] && lbox[1] < b[3] ? lbox[3] + up + 8 : y;
          };
          if (lp && nm) {
            const k = pop(a + 0.55, 140);
            const q = proj(lp);
            if (k > 0.01 && q)
              items.push(
                <div key="n" style={{position: 'absolute', left: q.x, top: q.y, transform: `translate(-50%, -50%) rotate(${r.labelRotate ?? 0}deg) scale(${k})`, fontFamily: `"${(e as any).font || (STY.style as any).heading || 'Be Vietnam Pro'}", "Be Vietnam Pro", sans-serif`, fontWeight: 700, fontSize: r.labelSize ?? 56, color: '#fff', textTransform: 'uppercase', whiteSpace: 'nowrap', letterSpacing: 1, textShadow: '0 3px 0 rgba(0,0,0,.55), 0 0 22px rgba(0,0,0,.7)'}}>
                  {nm}
                  {(r.valueLabel || vals[i] != null) && (
                    <div style={{fontSize: (r.labelSize ?? 56) * 0.62, color: '#ffe14d', marginTop: 2, textTransform: 'none'}}>
                      {r.valueLabel ?? fmtV(vals[i] as number) + (e.legend && e.legend.unit ? ' ' + e.legend.unit : '')}
                    </div>
                  )}
                </div>,
              );
          }
          (r.tags || []).forEach((g, j) => {
            if (!isFinite(g.lng) || !isFinite(g.lat)) return;
            const k = pop(g.at ?? a + 0.95 + 0.18 * j) * gone;
            const q0 = proj([g.lng, g.lat]);
            if (k <= 0.01 || !q0) return;
            const q = {x: q0.x, y: dodge(q0.x, q0.y, g.name.length * 17 + 30, 52, 52)};
            items.push(
              <div key={'t' + j} style={{position: 'absolute', left: q.x, top: q.y, transform: `translate(-50%, -100%) scale(${k})`, transformOrigin: '50% 100%', display: 'flex', flexDirection: 'column', alignItems: 'center'}}>
                <div style={{background: '#fff', color: '#111', fontFamily: '"Be Vietnam Pro", sans-serif', fontWeight: 600, fontSize: 30, padding: '5px 14px', borderRadius: 7, whiteSpace: 'nowrap', boxShadow: '0 4px 14px rgba(0,0,0,.45)'}}>{g.name}</div>
                <div style={{width: 0, height: 0, borderLeft: '9px solid transparent', borderRight: '9px solid transparent', borderTop: '11px solid #fff'}} />
              </div>,
            );
          });
          (r.badges || []).forEach((b, j) => {
            if (!isFinite(b.lng) || !isFinite(b.lat)) return;
            const k = pop(b.at ?? a + 1.3 + 0.35 * j, 150) * gone;
            const q0 = proj([b.lng, b.lat]);
            if (k <= 0.01 || !q0) return;
            const S = b.size ?? 170;
            const q = {x: q0.x, y: dodge(q0.x, q0.y, S, S + 30, S / 2)};
            items.push(
              <div key={'b' + j} style={{position: 'absolute', left: q.x, top: q.y, transform: `translate(-50%, -50%) scale(${k})`, display: 'flex', flexDirection: 'column', alignItems: 'center'}}>
                <div style={{width: S, height: S, borderRadius: '50%', border: '7px solid #fff', overflow: 'hidden', background: '#d9dee5', boxShadow: '0 10px 30px rgba(0,0,0,.55)'}}>
                  {b.img ? <img src={mediaSrc(b.img)} style={{width: '100%', height: '100%', objectFit: 'cover'}} /> : null}
                </div>
                {b.name ? <div style={{marginTop: -18, background: 'linear-gradient(180deg, #ff8a1f, #f06a00)', color: '#fff', fontFamily: '"Be Vietnam Pro", sans-serif', fontWeight: 800, fontSize: 26, padding: '6px 16px', borderRadius: 6, transform: 'rotate(-5deg)', whiteSpace: 'nowrap', border: '2px solid #fff', boxShadow: '0 6px 16px rgba(0,0,0,.4)'}}>{b.name}</div> : null}
              </div>,
            );
          });
          return <React.Fragment key={i}>{items}</React.Fragment>;
        })}
        {hasVal && e.legend !== false && map && (() => {
          const k = spring({frame: f - Math.round(fps * 1.2), fps, config: {damping: 14, stiffness: 120}});
          const lg = e.legend || {};
          return (
            <div style={{position: 'absolute', left: 40, bottom: Math.round(H * 0.2), width: 360, padding: '14px 18px', borderRadius: 14, background: 'rgba(8,14,26,.72)', color: '#fff', fontFamily: '"Be Vietnam Pro", sans-serif', opacity: k, transform: `translateY(${(1 - k) * 30}px)`}}>
              {lg.title && <div style={{fontWeight: 800, fontSize: 26, marginBottom: 8}}>{lg.title}</div>}
              <div style={{height: 16, borderRadius: 8, background: `linear-gradient(90deg, ${e.scale?.from || '#fde68a'}, ${e.scale?.to || '#b91c1c'})`}} />
              <div style={{display: 'flex', justifyContent: 'space-between', fontSize: 20, marginTop: 6, opacity: 0.9}}>
                <span>{fmtV(vmin)}{lg.unit ? ' ' + lg.unit : ''}</span>
                <span>{fmtV(vmax)}{lg.unit ? ' ' + lg.unit : ''}</span>
              </div>
            </div>
          );
        })()}
        <div style={{position: 'absolute', right: 14, bottom: 10, fontSize: 16, color: 'rgba(255,255,255,.6)', fontFamily: 'sans-serif', textShadow: '0 1px 2px #000', textAlign: 'right'}}>{(e.basemap || 'sat') === 'sat' ? SAT_CREDIT : '© OpenFreeMap © OpenStreetMap'}{e.terrain ? <><br />{DEM_CREDIT}</> : null}</div>
      </div>
    </AbsoluteFill>
  );
};
