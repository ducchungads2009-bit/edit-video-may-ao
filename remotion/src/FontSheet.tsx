/* Bảng mẫu các font có sẵn (render 1 lần -> phong-cach/_font-mau.jpg) để Claude so với chữ trong video mẫu */
import React, {useEffect, useState} from 'react';
import {AbsoluteFill, continueRender, delayRender} from 'remotion';
import {FONTS, fontCss} from './fonts';

export const FontSheet: React.FC = () => {
  const [h] = useState(() => delayRender('fonts'));
  useEffect(() => {
    Promise.all(FONTS.flatMap((f) => f.weights.map((w) => document.fonts.load(`${w} 40px "${f.family}"`, 'Ngày ữ Ặ')))).then(() => continueRender(h));
  }, [h]);
  return (
    <AbsoluteFill style={{background: '#14161c', padding: 30, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, alignContent: 'start'}}>
      {FONTS.map((f) => (
        <div key={f.id} style={{background: '#2a3550', borderRadius: 14, padding: '10px 18px 14px'}}>
          <div style={{fontFamily: 'Be Vietnam Pro', fontSize: 22, color: '#9fb6d6'}}>
            {f.family} · {f.kind} · đậm {f.weights.join('/')}
          </div>
          <div style={{fontFamily: fontCss(f.family), fontWeight: Math.max(...f.weights), fontSize: 50, color: 'white', lineHeight: 1.25, whiteSpace: 'nowrap'}}>
            Giá chỉ 2,5 TỶ
          </div>
          <div style={{fontFamily: fontCss(f.family), fontWeight: f.weights.includes(400) ? 400 : f.weights[0], fontSize: 30, color: '#FFE08A', whiteSpace: 'nowrap'}}>
            Ngày hôm qua thật bất ngờ
          </div>
        </div>
      ))}
    </AbsoluteFill>
  );
};
