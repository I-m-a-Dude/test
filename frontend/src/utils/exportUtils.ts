// Export utilities for MRI images

export interface ExportOptions {
  canvas?: HTMLCanvasElement;
  filename?: string;
  metadata?: Record<string, unknown>;
  includeMetadata?: boolean;
  // Video-specific options
  duration?: number; // Duration in seconds for MP4 export
  fps?: number; // Frames per second for MP4 export
}

/**
 * Export canvas as PNG image
 */
export const exportAsPNG = async (options: ExportOptions): Promise<void> => {
  const { canvas, filename = 'mri-image' } = options;

  if (!canvas) {
    throw new Error('Canvas is required for export');
  }

  try {
    // Create a link element and trigger download
    const link = document.createElement('a');
    link.download = `${filename}.png`;
    link.href = canvas.toDataURL('image/png');

    // Trigger download
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    console.log('PNG export completed successfully');
  } catch (error) {
    console.error('Error exporting PNG:', error);
    throw new Error('Failed to export PNG image');
  }
};

/**
 * Export canvas as JPEG image
 */
export const exportAsJPEG = async (options: ExportOptions): Promise<void> => {
  const { canvas, filename = 'mri-image' } = options;

  if (!canvas) {
    throw new Error('Canvas is required for export');
  }

  try {
    // Create a link element and trigger download
    const link = document.createElement('a');
    link.download = `${filename}.jpg`;
    link.href = canvas.toDataURL('image/jpeg', 0.95); // High quality JPEG

    // Trigger download
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    console.log('JPEG export completed successfully');
  } catch (error) {
    console.error('Error exporting JPEG:', error);
    throw new Error('Failed to export JPEG image');
  }
};

/**
 * Export canvas as MP4 video using MediaRecorder API
 */
export const exportAsMP4 = async (options: ExportOptions): Promise<void> => {
  const {
    canvas,
    filename = 'mri-video',
    duration = 5, // Default 5 seconds
    fps = 30 // Default 30 fps
  } = options;

  if (!canvas) {
    throw new Error('Canvas is required for export');
  }

  try {
    // Check if MediaRecorder is supported
    if (!window.MediaRecorder) {
      throw new Error('MediaRecorder API is not supported in this browser');
    }

    console.log(`Starting MP4 export: ${duration}s at ${fps}fps`);

    // Get canvas stream
    const stream = canvas.captureStream(fps);

    // Setup MediaRecorder
    const mediaRecorder = new MediaRecorder(stream, {
      mimeType: 'video/webm;codecs=vp9', // Use WebM as fallback, will convert filename
    });

    const chunks: Blob[] = [];

    // Collect video data
    mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        chunks.push(event.data);
      }
    };

    // Handle recording completion
    mediaRecorder.onstop = () => {
      const blob = new Blob(chunks, { type: 'video/webm' });

      // Create download link
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${filename}.webm`; // Note: Browser MediaRecorder typically outputs WebM

      // Trigger download
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      // Cleanup
      URL.revokeObjectURL(url);

      console.log('MP4 export completed successfully');
    };

    // Handle errors
    mediaRecorder.onerror = (event) => {
      console.error('MediaRecorder error:', event);
      throw new Error('Failed to record video');
    };

    // Start recording
    mediaRecorder.start();

    // Stop recording after specified duration
    setTimeout(() => {
      mediaRecorder.stop();

      // Stop all tracks to release the stream
      stream.getTracks().forEach(track => track.stop());
    }, duration * 1000);

  } catch (error) {
    console.error('Error exporting MP4:', error);
    throw new Error(`Failed to export MP4 video: ${error instanceof Error ? error.message : 'Unknown error'}`);
  }
};

/**
 * Export animated MP4 with slice progression
 * This creates a cine-mode video showing different slices
 */
export const exportAsAnimatedMP4 = async (
  options: ExportOptions & {
    onRenderFrame?: (slice: number) => void;
    totalSlices?: number;
    sliceDelay?: number; // Delay between slices in ms
  }
): Promise<void> => {
  const {
    canvas,
    filename = 'mri-cine',
    duration = 10,
    fps = 24,
    totalSlices = 100,
    sliceDelay = 100,
    onRenderFrame
  } = options;

  if (!canvas || !onRenderFrame) {
    throw new Error('Canvas and onRenderFrame callback are required for animated export');
  }

  try {
    console.log(`Starting animated MP4 export: ${totalSlices} slices over ${duration}s`);

    const stream = canvas.captureStream(fps);
    const mediaRecorder = new MediaRecorder(stream, {
      mimeType: 'video/webm;codecs=vp9',
    });

    const chunks: Blob[] = [];

    mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        chunks.push(event.data);
      }
    };

    mediaRecorder.onstop = () => {
      const blob = new Blob(chunks, { type: 'video/webm' });

      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${filename}-animated.webm`;

      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      URL.revokeObjectURL(url);
      console.log('Animated MP4 export completed successfully');
    };

    mediaRecorder.onerror = (event) => {
      console.error('MediaRecorder error:', event);
      throw new Error('Failed to record animated video');
    };

    // Start recording
    mediaRecorder.start();

    // Animate through slices
    let currentSlice = 0;
    const sliceInterval = setInterval(() => {
      onRenderFrame(currentSlice);
      currentSlice = (currentSlice + 1) % totalSlices;
    }, sliceDelay);

    // Stop recording after duration
    setTimeout(() => {
      clearInterval(sliceInterval);
      mediaRecorder.stop();
      stream.getTracks().forEach(track => track.stop());
    }, duration * 1000);

  } catch (error) {
    console.error('Error exporting animated MP4:', error);
    throw new Error(`Failed to export animated MP4: ${error instanceof Error ? error.message : 'Unknown error'}`);
  }
};

/**
 * Get current timestamp for filenames
 */
export const getTimestampedFilename = (baseName: string): string => {
  const now = new Date();
  const timestamp = now.toISOString()
    .replace(/[:.]/g, '-')
    .slice(0, -5); // Remove milliseconds and Z

  return `${baseName}-${timestamp}`;
};

/**
 * Validate export options
 */
export const validateExportOptions = (options: ExportOptions): void => {
  if (!options.canvas) {
    throw new Error('Canvas element is required for export');
  }

  if (!options.canvas.width || !options.canvas.height) {
    throw new Error('Canvas must have valid dimensions');
  }
};