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