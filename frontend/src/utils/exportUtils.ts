// Export utilities for MRI images
  // Note: Install jsPDF for PDF export functionality: npm install jspdf

  export interface ExportOptions {
    canvas?: HTMLCanvasElement;
    filename?: string;
    metadata?: Record<string, unknown>;
    includeMetadata?: boolean;
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
   * Create PDF report using browser APIs only
   */
  export const exportAsPDF = async (options: ExportOptions): Promise<void> => {
    const { canvas, filename = 'mri-report', metadata, includeMetadata = true } = options;

    if (!canvas) {
      throw new Error('Canvas is required for export');
    }

    try {
      // Try to use jsPDF if available, otherwise fallback to simple implementation
      if (typeof window !== 'undefined' && 'jsPDF' in (window as unknown as Record<string, unknown>)) {
        const { jsPDF } = (window as unknown as Record<string, unknown>);

        // Create new PDF document
        const pdf = new (jsPDF as new (options: {
          orientation: string;
          unit: string;
          format: string;
        }) => {
          setFontSize: (size: number) => void;
          setFont: (font: string, style: string) => void;
          text: (text: string | string[], x: number, y: number) => void;
          addImage: (data: string, format: string, x: number, y: number, w: number, h: number) => void;
          addPage: () => void;
          splitTextToSize: (text: string, maxWidth: number) => string[];
          save: (filename: string) => void;
        })({
          orientation: 'portrait',
          unit: 'mm',
          format: 'a4'
        });

        // Add title
        pdf.setFontSize(20);
        pdf.setFont('helvetica', 'bold');
        pdf.text('MRI Analysis Report', 20, 25);

        // Add timestamp
        pdf.setFontSize(10);
        pdf.setFont('helvetica', 'normal');
        pdf.text(`Generated on: ${new Date().toLocaleString()}`, 20, 35);

        // Add image
        const imgData = canvas.toDataURL('image/png');
        const imgWidth = 120; // mm
        const imgHeight = (canvas.height / canvas.width) * imgWidth;

        pdf.addImage(imgData, 'PNG', 20, 45, imgWidth, imgHeight);

        // Add metadata if provided
        if (includeMetadata && metadata) {
          let yPosition = 45 + imgHeight + 20;

          pdf.setFontSize(14);
          pdf.setFont('helvetica', 'bold');
          pdf.text('Image Information', 20, yPosition);
          yPosition += 10;

          pdf.setFontSize(10);
          pdf.setFont('helvetica', 'normal');

          Object.entries(metadata).forEach(([key, value]) => {
            if (yPosition > 280) { // Check if we need a new page
              pdf.addPage();
              yPosition = 20;
            }

            const valueStr = Array.isArray(value) ? value.join(', ') : String(value);
            const text = `${key}: ${valueStr}`;

            // Handle long text by wrapping
            const splitText = pdf.splitTextToSize(text, 170);
            splitText.forEach((line) => {
              pdf.text(line, 20, yPosition);
              yPosition += 5;
            });
          });
        }

        // Save the PDF
        pdf.save(`${filename}.pdf`);

        console.log('PDF export completed successfully');
      } else {
        // Fallback: Open image in new window for manual save
        console.warn('jsPDF not available, opening image in new window');
        const imgData = canvas.toDataURL('image/png');
        const newWindow = window.open();
        if (newWindow) {
          newWindow.document.write(`
            <html>
              <head><title>MRI Report - ${filename}</title></head>
              <body style="margin: 20px; font-family: Arial, sans-serif;">
                <h1>MRI Analysis Report</h1>
                <p>Generated on: ${new Date().toLocaleString()}</p>
                <img src="${imgData}" style="max-width: 100%; height: auto;" />
                ${includeMetadata && metadata ? `
                  <h2>Image Information</h2>
                  <table border="1" style="border-collapse: collapse; width: 100%;">
                    ${Object.entries(metadata).map(([key, value]) =>
                      `<tr><td style="padding: 5px;"><strong>${key}</strong></td><td style="padding: 5px;">${Array.isArray(value) ? value.join(', ') : String(value)}</td></tr>`
                    ).join('')}
                  </table>
                ` : ''}
                <p><em>Right-click and "Save As" to download this report, or use Ctrl+P to print as PDF.</em></p>
              </body>
            </html>
          `);
        }
      }
    } catch (error) {
      console.error('Error exporting PDF:', error);
      throw new Error('Failed to export PDF report');
    }
  };

  /**
   * Export as DICOM (placeholder implementation)
   * Note: Full DICOM export would require a proper DICOM library
   */
  export const exportAsDICOM = async (): Promise<void> => {
    try {
      console.warn('DICOM export is not yet fully implemented');
      alert('DICOM export functionality is coming soon. Please use PNG or PDF export for now.');
    } catch (error) {
      console.error('Error exporting DICOM:', error);
      throw new Error('DICOM export is not yet implemented');
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