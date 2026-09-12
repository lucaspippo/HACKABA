export type MessageBodySignals = {
  partCount: number;
  noticeCount: number;
  isRunning: boolean;
};

export function hasVisibleBody({ partCount, noticeCount, isRunning }: MessageBodySignals): boolean {
  return isRunning || partCount > 0 || noticeCount > 0;
}
