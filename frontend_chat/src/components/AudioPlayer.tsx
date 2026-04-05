import { useState, useRef, useEffect } from 'react';
import { Play, Pause, Volume2, VolumeX } from 'lucide-react';

interface AudioPlayerProps {
  audioBlob?: Blob;
  audioUrl?: string;
  autoPlay?: boolean;
  onEnded?: () => void;
}

function AudioPlayer({ audioBlob, audioUrl, autoPlay = false, onEnded }: AudioPlayerProps) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [progress, setProgress] = useState(0);
  const [duration, setDuration] = useState(0);

  // Create object URL from blob if provided
  useEffect(() => {
    if (audioBlob && audioRef.current) {
      const url = URL.createObjectURL(audioBlob);
      audioRef.current.src = url;

      return () => {
        URL.revokeObjectURL(url);
      };
    } else if (audioUrl && audioRef.current) {
      audioRef.current.src = audioUrl;
    }
  }, [audioBlob, audioUrl]);

  // Auto-play if enabled
  useEffect(() => {
    if (autoPlay && audioRef.current) {
      audioRef.current.play().catch(console.error);
    }
  }, [autoPlay, audioBlob, audioUrl]);

  const handlePlayPause = () => {
    if (!audioRef.current) return;

    if (isPlaying) {
      audioRef.current.pause();
    } else {
      audioRef.current.play().catch(console.error);
    }
  };

  const handleToggleMute = () => {
    if (!audioRef.current) return;
    audioRef.current.muted = !isMuted;
    setIsMuted(!isMuted);
  };

  const handleTimeUpdate = () => {
    if (!audioRef.current) return;
    const percent = (audioRef.current.currentTime / audioRef.current.duration) * 100;
    setProgress(percent || 0);
  };

  const handleLoadedMetadata = () => {
    if (!audioRef.current) return;
    setDuration(audioRef.current.duration);
  };

  const handleSeek = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!audioRef.current) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const percent = (e.clientX - rect.left) / rect.width;
    audioRef.current.currentTime = percent * audioRef.current.duration;
  };

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  if (!audioBlob && !audioUrl) {
    return null;
  }

  return (
    <div className="audio-player">
      <audio
        ref={audioRef}
        onPlay={() => setIsPlaying(true)}
        onPause={() => setIsPlaying(false)}
        onEnded={() => {
          setIsPlaying(false);
          setProgress(0);
          onEnded?.();
        }}
        onTimeUpdate={handleTimeUpdate}
        onLoadedMetadata={handleLoadedMetadata}
      />

      <button
        className="audio-play-btn"
        onClick={handlePlayPause}
        title={isPlaying ? 'Pause' : 'Play'}
      >
        {isPlaying ? <Pause size={16} /> : <Play size={16} />}
      </button>

      <div className="audio-progress-container" onClick={handleSeek}>
        <div
          className="audio-progress-bar"
          style={{ width: `${progress}%` }}
        />
      </div>

      <span className="audio-time">
        {formatTime((progress / 100) * duration)} / {formatTime(duration)}
      </span>

      <button
        className="audio-mute-btn"
        onClick={handleToggleMute}
        title={isMuted ? 'Unmute' : 'Mute'}
      >
        {isMuted ? <VolumeX size={16} /> : <Volume2 size={16} />}
      </button>
    </div>
  );
}

export default AudioPlayer;
