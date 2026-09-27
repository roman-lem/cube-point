/**
 * The only time source of the timer: ms since 1970, as precise and monotonic as
 * performance.now() within the page, and comparable with moments saved before a reload.
 * Neither Date.now() nor a bare performance.now() is used in the timer: performance.now()
 * counts from the page load, and mixing it with this scale gives garbage.
 */
export function timerNow(): number {
  return performance.timeOrigin + performance.now()
}
