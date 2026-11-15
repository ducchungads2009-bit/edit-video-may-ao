import React from 'react';
import {Composition, Sequence} from 'remotion';
import {TikTok, TikTokProps} from './TikTok';
import {EditPlan, PlanProps, AudioPlan} from './EditPlan';
import {FontSheet} from './FontSheet';
import {StylePreview} from './StylePreview';
import {BeatPreview} from './BeatPreview';
import {fmtOf} from './frame';
import challenge from '../../samples/challenge-plan.json';
import review from '../../samples/review-plan.json';

const fromSec = ({props}: {props: {durationSec: number; format?: string}}) => {
  const F = fmtOf(props.format); // khung hình: 9:16 | 4:5 | 1:1 | 16:9
  return {durationInFrames: Math.max(1, Math.round(props.durationSec * 30)), width: F.w, height: F.h};
};

/* Bộ dựng nhanh (scripts/dung_nhanh.py): chỉ dựng các khúc có đồ hoạ — __ranges = [[khung đầu, khung cuối), ...] của video thật,
   nối liền nhau thành 1 video ngắn; phần còn lại ffmpeg lấy thẳng từ video gốc. */
type PartialProps = PlanProps & {__ranges: [number, number][]};
const Partial: React.FC<PartialProps> = (p) => {
  let cum = 0;
  return (
    <>
      {p.__ranges.map(([a, b]) => {
        const from = cum;
        cum += b - a;
        return (
          <Sequence key={a} from={from} durationInFrames={b - a}>
            <Sequence from={-a}>
              <EditPlan {...p} />
            </Sequence>
          </Sequence>
        );
      })}
    </>
  );
};
const fromRanges = ({props}: {props: PartialProps}) => {
  const F = fmtOf((props as any).format);
  return {durationInFrames: Math.max(1, (props.__ranges || []).reduce((s, [a, b]) => s + b - a, 0)), width: F.w, height: F.h};
};

export const Root: React.FC = () => (
  <>
    {/* Video thử thách: phụ đề kiểu TikTok + nhãn NGÀY X/Y */}
    <Composition id="challenge" component={TikTok} width={1080} height={1920} fps={30} durationInFrames={300}
      defaultProps={challenge as unknown as TikTokProps} calculateMetadata={fromSec} />
    {/* Video review căn: thẻ giá, nhãn icon, checklist, CTA */}
    <Composition id="review" component={EditPlan} width={1080} height={1920} fps={30} durationInFrames={300}
      defaultProps={review as unknown as PlanProps} calculateMetadata={fromSec} />
    <Composition id="partial" component={Partial} width={1080} height={1920} fps={30} durationInFrames={300}
      defaultProps={{...(review as unknown as PlanProps), __ranges: [[0, 30]]} as PartialProps} calculateMetadata={fromRanges} />
    <Composition id="audio" component={AudioPlan} width={1080} height={1920} fps={30} durationInFrames={300}
      defaultProps={review as unknown as PlanProps} calculateMetadata={fromSec} />
    {/* Bảng mẫu font */}
    <Composition id="fontsheet" component={FontSheet} width={1080} height={1960} fps={30} durationInFrames={1} />
    {/* Ảnh minh họa bộ phong cách (phong-cach/<tên>/demo.jpg) */}
    <Composition id="stylepreview" component={StylePreview} width={1080} height={1920} fps={30} durationInFrames={60} defaultProps={{style: {}, theme: null}} />
    {/* Ảnh minh họa bộ phong cách dựng theo nhịp nhạc */}
    <Composition id="beatpreview" component={BeatPreview} width={1080} height={1920} fps={30} durationInFrames={60} defaultProps={{style: {}, theme: null, preset: 'chia-khung'}} />
  </>
);
