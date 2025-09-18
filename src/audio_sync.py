"""
Audio-slide synchronization module for creating perfectly timed slideshows.
"""
import os
import logging
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from moviepy.editor import AudioFileClip

try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False
    logging.warning("librosa not available. Install with 'pip install librosa' for advanced audio analysis.")

logger = logging.getLogger(__name__)


class AudioSyncManager:
    """Manages audio-slide synchronization with multiple detection methods."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.audio_config = config.get('audio', {})
        self.sync_config = self.audio_config.get('sync', {})
    
    def calculate_slide_timings(self, audio: AudioFileClip, num_images: int) -> List[float]:
        """
        Calculate optimal slide transition timings based on audio analysis.
        
        Args:
            audio: The audio clip to analyze
            num_images: Number of images/slides
            
        Returns:
            List of timestamps (in seconds) for slide transitions
        """
        if not self.sync_config.get('enabled', False):
            # Default even distribution
            return self._even_distribution(audio.duration, num_images)
        
        sync_mode = self.sync_config.get('mode', 'auto')
        
        logger.info(f"Calculating slide timings using '{sync_mode}' mode")
        
        if sync_mode == 'manual':
            return self._manual_timestamps(audio.duration, num_images)
        elif sync_mode == 'auto':
            return self._auto_detection(audio, num_images)
        elif sync_mode == 'beat_detection':
            return self._beat_detection(audio, num_images)
        else:
            logger.warning(f"Unknown sync mode '{sync_mode}', using even distribution")
            return self._even_distribution(audio.duration, num_images)
    
    def _even_distribution(self, duration: float, num_images: int) -> List[float]:
        """Create evenly distributed slide timings."""
        if num_images <= 1:
            return [0.0]
        
        slide_duration = duration / num_images
        timings = [i * slide_duration for i in range(num_images)]
        
        logger.info(f"Even distribution: {slide_duration:.2f}s per slide")
        return timings
    
    def _manual_timestamps(self, duration: float, num_images: int) -> List[float]:
        """Use manually specified timestamps."""
        manual_times = self.sync_config.get('timestamps', [])
        
        if not manual_times:
            logger.warning("Manual mode selected but no timestamps provided, using even distribution")
            return self._even_distribution(duration, num_images)
        
        # Ensure we have enough timestamps
        if len(manual_times) < num_images:
            logger.warning(f"Not enough timestamps ({len(manual_times)}) for {num_images} images")
            # Pad with even distribution for remaining slides
            last_time = manual_times[-1] if manual_times else 0
            remaining_duration = duration - last_time
            remaining_slides = num_images - len(manual_times)
            
            if remaining_slides > 0:
                slide_duration = remaining_duration / remaining_slides
                for i in range(remaining_slides):
                    manual_times.append(last_time + (i + 1) * slide_duration)
        
        # Truncate if too many timestamps
        timings = manual_times[:num_images]
        
        # Ensure first timestamp is 0
        if timings[0] != 0:
            timings = [0.0] + timings
            timings = timings[:num_images]
        
        logger.info(f"Manual timestamps: {timings}")
        return timings
    
    def _auto_detection(self, audio: AudioFileClip, num_images: int) -> List[float]:
        """Automatically detect slide transitions based on audio features."""
        try:
            # Get audio data
            audio_data = audio.to_soundarray()
            
            # Handle the case where audio_data might be empty or malformed
            if audio_data is None or len(audio_data) == 0:
                logger.warning("No audio data available for analysis")
                return self._even_distribution(audio.duration, num_images)
            
            # Convert stereo to mono safely
            if len(audio_data.shape) > 1 and audio_data.shape[1] > 1:
                audio_data = np.mean(audio_data, axis=1)
            elif len(audio_data.shape) > 1:
                audio_data = audio_data.flatten()
            
            # Ensure we have a valid 1D array
            if len(audio_data.shape) != 1:
                logger.warning("Unexpected audio data shape, falling back to even distribution")
                return self._even_distribution(audio.duration, num_images)
            
            sample_rate = audio.fps
            duration = audio.duration
            
            # Detect silence/pause points
            silence_points = self._detect_silence_points(audio_data, sample_rate)
            
            if len(silence_points) >= num_images - 1:
                # We have enough silence points
                timings = self._select_best_silence_points(silence_points, num_images, duration)
            else:
                # Not enough natural breaks, use hybrid approach
                timings = self._hybrid_timing(silence_points, num_images, duration)
            
            logger.info(f"Auto-detected timings: {[f'{t:.2f}s' for t in timings]}")
            return timings
            
        except Exception as e:
            logger.error(f"Error in auto detection: {e}")
            return self._even_distribution(audio.duration, num_images)
    
    def _detect_silence_points(self, audio_data: np.ndarray, sample_rate: int) -> List[float]:
        """Detect points of silence/low audio activity."""
        auto_config = self.sync_config.get('auto', {})
        silence_threshold = auto_config.get('silence_threshold', -40)  # dB
        
        # Calculate RMS energy in windows
        window_size = int(0.1 * sample_rate)  # 100ms windows
        hop_size = int(0.05 * sample_rate)    # 50ms hop
        
        silence_points = []
        
        for i in range(0, len(audio_data) - window_size, hop_size):
            window = audio_data[i:i + window_size]
            
            # Calculate RMS and convert to dB
            rms = np.sqrt(np.mean(window ** 2))
            if rms > 0:
                db = 20 * np.log10(rms)
                
                # Check if below silence threshold
                if db < silence_threshold:
                    timestamp = i / sample_rate
                    silence_points.append(timestamp)
        
        # Merge nearby silence points
        merged_points = []
        if silence_points:
            current_start = silence_points[0]
            current_end = silence_points[0]
            
            for point in silence_points[1:]:
                if point - current_end < 0.5:  # Within 500ms
                    current_end = point
                else:
                    # Add midpoint of silence region
                    merged_points.append((current_start + current_end) / 2)
                    current_start = point
                    current_end = point
            
            # Add final point
            merged_points.append((current_start + current_end) / 2)
        
        logger.info(f"Detected {len(merged_points)} silence points")
        return merged_points
    
    def _select_best_silence_points(self, silence_points: List[float], 
                                   num_images: int, duration: float) -> List[float]:
        """Select the best silence points for slide transitions."""
        auto_config = self.sync_config.get('auto', {})
        min_duration = auto_config.get('min_slide_duration', 3)
        max_duration = auto_config.get('max_slide_duration', 15)
        
        # Always start with 0
        timings = [0.0]
        
        # Filter silence points that create reasonable slide durations
        candidates = []
        for point in silence_points:
            if point > min_duration:  # Must be after minimum duration
                candidates.append(point)
        
        # Select points that create balanced slide durations
        selected_points = []
        last_time = 0.0
        
        for candidate in candidates:
            slide_duration = candidate - last_time
            
            if min_duration <= slide_duration <= max_duration:
                selected_points.append(candidate)
                last_time = candidate
                
                if len(selected_points) >= num_images - 1:
                    break
        
        # Add selected points to timings
        timings.extend(selected_points[:num_images - 1])
        
        # If we don't have enough points, fill with even distribution
        while len(timings) < num_images:
            remaining_duration = duration - timings[-1]
            remaining_slides = num_images - len(timings)
            next_time = timings[-1] + (remaining_duration / remaining_slides)
            timings.append(next_time)
        
        return timings[:num_images]
    
    def _hybrid_timing(self, silence_points: List[float], 
                      num_images: int, duration: float) -> List[float]:
        """Create hybrid timing using available silence points and even distribution."""
        timings = [0.0]
        
        # Use available silence points
        useful_points = [p for p in silence_points if p > 2.0]  # At least 2s from start
        
        # Take up to num_images-2 points (leave room for start and calculated points)
        max_points = min(len(useful_points), num_images - 2)
        selected_points = useful_points[:max_points]
        
        if selected_points:
            timings.extend(selected_points)
            timings.sort()
        
        # Fill remaining with even distribution
        while len(timings) < num_images:
            if len(timings) == 1:
                # Add point based on available silence or even distribution
                remaining_duration = duration - timings[-1]
                remaining_slides = num_images - len(timings)
                next_time = timings[-1] + (remaining_duration / remaining_slides)
            else:
                # Continue pattern
                avg_gap = (timings[-1] - timings[0]) / (len(timings) - 1)
                next_time = timings[-1] + avg_gap
            
            if next_time < duration:
                timings.append(next_time)
            else:
                break
        
        return timings[:num_images]
    
    def _beat_detection(self, audio: AudioFileClip, num_images: int) -> List[float]:
        """Use beat detection for slide timing (requires librosa)."""
        if not LIBROSA_AVAILABLE:
            logger.warning("Beat detection requires librosa. Install with: pip install librosa")
            return self._even_distribution(audio.duration, num_images)
        
        try:
            # Load audio for librosa
            audio_data = audio.to_soundarray()
            if len(audio_data.shape) > 1:
                audio_data = np.mean(audio_data, axis=1)
            
            sample_rate = audio.fps
            
            # Detect beats
            tempo, beat_frames = librosa.beat.beat_track(
                y=audio_data, 
                sr=sample_rate,
                hop_length=512
            )
            
            # Convert beat frames to time
            beat_times = librosa.frames_to_time(beat_frames, sr=sample_rate)
            
            beat_config = self.sync_config.get('beat_detection', {})
            slides_per_beat = beat_config.get('slides_per_beat', 4)
            
            # Select every Nth beat for slide transitions
            slide_beats = beat_times[::slides_per_beat]
            
            # Ensure we start with 0 and have the right number of slides
            timings = [0.0]
            timings.extend(slide_beats[1:num_images])
            
            # Pad or trim to exact number needed
            while len(timings) < num_images:
                if len(timings) > 1:
                    avg_gap = (timings[-1] - timings[-2])
                    timings.append(timings[-1] + avg_gap)
                else:
                    timings.append(audio.duration / 2)
            
            timings = timings[:num_images]
            
            logger.info(f"Beat-based timings at {tempo:.1f} BPM: {[f'{t:.2f}s' for t in timings]}")
            return timings
            
        except Exception as e:
            logger.error(f"Error in beat detection: {e}")
            return self._even_distribution(audio.duration, num_images)
    
    def get_slide_durations(self, timings: List[float], total_duration: float) -> List[float]:
        """Calculate individual slide durations from timing points."""
        durations = []
        
        for i in range(len(timings)):
            if i < len(timings) - 1:
                duration = timings[i + 1] - timings[i]
            else:
                # Last slide duration
                duration = total_duration - timings[i]
            
            durations.append(max(0.5, duration))  # Minimum 0.5s per slide
        
        return durations
    
    def validate_timings(self, timings: List[float], duration: float) -> List[float]:
        """Validate and fix timing issues."""
        if not timings:
            return [0.0]
        
        # Ensure first timing is 0
        if timings[0] != 0.0:
            timings = [0.0] + timings
        
        # Sort timings
        timings.sort()
        
        # Remove duplicates
        unique_timings = []
        for timing in timings:
            if not unique_timings or timing != unique_timings[-1]:
                unique_timings.append(timing)
        
        # Ensure all timings are within audio duration
        valid_timings = [t for t in unique_timings if t < duration]
        
        # Ensure minimum gaps between slides
        min_gap = 0.5
        filtered_timings = [valid_timings[0]]  # Always keep first
        
        for timing in valid_timings[1:]:
            if timing - filtered_timings[-1] >= min_gap:
                filtered_timings.append(timing)
        
        return filtered_timings