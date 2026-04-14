/**
 * VideoPlayer — HTML5 video with seek-to-timestamp support.
 *
 * Props:
 *   src         — video URL (clip or full video)
 *   seekToMs    — seek to this position on change (milliseconds)
 *   onTimeUpdate — called with current position in ms
 */
import { useEffect, useRef } from "react";

interface Props {
  src: string;
  seekToMs?: number | null;
  onTimeUpdate?: (currentMs: number) => void;
}

export function VideoPlayer({ src, seekToMs, onTimeUpdate }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);

  // Seek when seekToMs changes
  useEffect(() => {
    const vid = videoRef.current;
    if (vid && seekToMs != null) {
      vid.currentTime = seekToMs / 1000;
    }
  }, [seekToMs]);

  return (
    <div className="relative w-full bg-black rounded overflow-hidden">
      <video
        ref={videoRef}
        src={src}
        controls
        className="w-full max-h-[60vh] object-contain"
        onTimeUpdate={() => {
          const vid = videoRef.current;
          if (vid && onTimeUpdate) {
            onTimeUpdate(vid.currentTime * 1000);
          }
        }}
        onError={() => {
          // Silently handle missing clips (e.g. still processing)
        }}
      />
    </div>
  );
}
