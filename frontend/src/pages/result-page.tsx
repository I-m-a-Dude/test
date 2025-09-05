// frontend/src/pages/result-page.tsx
import {ResultsMriViewer} from '@/components/results-mri-viewer';
import {Logo} from '@/components/logo';
import {Button} from '@/components/ui/button';
import {Link, useNavigate} from 'react-router-dom';
import {useCineMode} from '@/utils/hooks/use-cine-mode';
import {MetadataViewerDialog} from '@/components/metadata-viewer-dialog';
import {useResultStore} from '@/utils/stores/result-store';
import {useResultsViewerStore} from '@/utils/stores/results-viewer-store';
import {Card, CardContent, CardDescription, CardHeader, CardTitle} from '@/components/ui/card';
import {BarChart3, BrainCircuit, Clock, Download, FileText, Palette, Target} from 'lucide-react';
import {ScrollArea, ScrollBar} from '@/components/ui/scroll-area';
import {Badge} from '@/components/ui/badge';
import {Separator} from '@/components/ui/separator';
import {pages} from '@/utils/pages';
import {useEffect, useState} from 'react';
import {useToast} from '@/utils/hooks/use-toast';

export default function ResultPage() {
    useCineMode();
    const {analysisResult, overlayFile, inferenceResult, originalFile} = useResultStore();
    const {setCurrentFile} = useResultsViewerStore();
    const {toast} = useToast();
    const navigate = useNavigate();

    // ADĂUGAT STATE PENTRU DOWNLOAD
    const [downloadingOverlay, setDownloadingOverlay] = useState(false);

    useEffect(() => {
        // If there is no analysis result, redirect to analysis
        if (!analysisResult) {
            navigate(pages.analysis, {replace: true});
            return;
        }

        // Always load overlay file in results (dacă există)
        if (overlayFile) {
            setCurrentFile(overlayFile);
            toast({
                title: 'AI Analysis Results Loaded',
                description: 'Displaying T1N + AI segmentation overlay.',
                duration: 3000,
            });
        } else if (originalFile) {
            // Fallback la original dacă nu există overlay
            setCurrentFile(originalFile);
            toast({
                title: 'Analysis Results Loaded',
                description: 'Overlay not available, showing original file.',
                variant: 'destructive',
            });
        }
    }, [analysisResult, navigate, overlayFile, originalFile, setCurrentFile, toast]);

    // ADĂUGAT HANDLER PENTRU DOWNLOAD OVERLAY
    const handleDownloadOverlay = async () => {
        if (!inferenceResult?.folder_name) {
            toast({
                title: 'Cannot download overlay',
                description: 'No analysis results available for download.',
                variant: 'destructive',
            });
            return;
        }

        setDownloadingOverlay(true);

        try {
            console.log(`[DOWNLOAD] Downloading overlay for folder: ${inferenceResult.folder_name}`);

            const response = await fetch(`http://localhost:8000/inference/results/${encodeURIComponent(inferenceResult.folder_name)}/download-overlay`);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: Failed to download overlay`);
            }

            const blob = await response.blob();
            const filename = `${inferenceResult.folder_name}-overlay.nii.gz`;

            // Declanșează download-ul
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = filename;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            window.URL.revokeObjectURL(url);

            toast({
                title: 'Overlay downloaded successfully! 🎉',
                description: `${filename} has been saved to your downloads.`,
                duration: 4000,
            });

        } catch (error) {
            console.error('[DOWNLOAD] Overlay download failed:', error);

            toast({
                title: 'Download failed',
                description: error instanceof Error ? error.message : 'Unknown error occurred',
                variant: 'destructive',
                duration: 6000,
            });
        } finally {
            setDownloadingOverlay(false);
        }
    };

    // ADĂUGAT HANDLER PENTRU DOWNLOAD PDF
    const handleDownloadPDF = () => {
    if (!analysisResult) {
        toast({
            title: 'Cannot export PDF',
            description: 'No analysis report available.',
            variant: 'destructive',
        });
        return;
    }

    import('jspdf').then(({jsPDF}) => {
        try {
            const doc = new jsPDF();
            const pageWidth = doc.internal.pageSize.getWidth();
            const pageHeight = doc.internal.pageSize.getHeight();
            const margin = 20;
            const maxLineWidth = pageWidth - margin * 2;

            // Colors from app theme (dark mode colors)
            const primaryColor = [63, 131, 248]; // Blue primary
            const secondaryColor = [100, 116, 139]; // Gray
            const textColor = [15, 23, 42]; // Dark text

            // Header Section
            doc.setFillColor(...primaryColor);
            doc.rect(0, 0, pageWidth, 40, 'F');

            // App name and logo area
            doc.setTextColor(255, 255, 255);
            doc.setFontSize(24);
            doc.setFont('helvetica', 'bold');
            doc.text('MediView', margin, 25);

            doc.setFontSize(12);
            doc.setFont('helvetica', 'normal');
            doc.text('AI-Powered MRI Analysis Platform', margin, 32);

            // Report title
            doc.setTextColor(...textColor);
            doc.setFontSize(18);
            doc.setFont('helvetica', 'bold');
            doc.text('Automated Segmentation Report', margin, 55);

            // Patient/Study Information Box
            doc.setDrawColor(...secondaryColor);
            doc.setLineWidth(1);
            doc.rect(margin, 65, maxLineWidth, 25);

            doc.setFontSize(10);
            doc.setFont('helvetica', 'bold');
            doc.text('Study Information:', margin + 5, 72);

            doc.setFont('helvetica', 'normal');
            const studyInfo = [
                `Dataset: ${inferenceResult?.folder_name || 'Unknown'}`,
                `Analysis Date: ${new Date().toLocaleDateString('en-US')}`,
                `Processing Time: ${inferenceResult?.timing?.total_time?.toFixed(2) || 'N/A'}s`,
                `Generated by: MediView AI System`
            ];

            studyInfo.forEach((info, index) => {
                doc.text(info, margin + 5, 78 + (index * 4));
            });

            // Performance Metrics Section
            if (inferenceResult) {
                doc.setFontSize(14);
                doc.setFont('helvetica', 'bold');
                doc.setTextColor(...primaryColor);
                doc.text('Performance Metrics', margin, 105);

                doc.setDrawColor(...primaryColor);
                doc.setLineWidth(0.5);
                doc.line(margin, 108, margin + 60, 108);

                doc.setFontSize(10);
                doc.setTextColor(...textColor);
                doc.setFont('helvetica', 'normal');

                const metrics = [
                    `Preprocessing: ${inferenceResult.timing.preprocess_time.toFixed(2)}s`,
                    `AI Inference: ${inferenceResult.timing.inference_time.toFixed(2)}s`,
                    `Postprocessing: ${inferenceResult.timing.postprocess_time.toFixed(2)}s`,
                    `Total Time: ${inferenceResult.timing.total_time.toFixed(2)}s`
                ];

                metrics.forEach((metric, index) => {
                    doc.text(`• ${metric}`, margin + 5, 115 + (index * 5));
                });

                // Segmentation Results
                doc.setFontSize(14);
                doc.setFont('helvetica', 'bold');
                doc.setTextColor(...primaryColor);
                doc.text('Segmentation Results', margin, 145);

                doc.line(margin, 148, margin + 70, 148);

                doc.setFontSize(10);
                doc.setTextColor(...textColor);
                doc.setFont('helvetica', 'normal');

                const segInfo = [
                    `Volume Dimensions: ${inferenceResult.segmentation_info.shape.join(' × ')}`,
                    `Total Segmented Voxels: ${inferenceResult.segmentation_info.total_segmented_voxels.toLocaleString()}`,
                    `Detected Classes: ${inferenceResult.segmentation_info.classes_found.filter(c => c > 0).length}`
                ];

                segInfo.forEach((info, index) => {
                    doc.text(`• ${info}`, margin + 5, 155 + (index * 5));
                });
            }

            // Main Report Content
            doc.setFontSize(14);
            doc.setFont('helvetica', 'bold');
            doc.setTextColor(...primaryColor);
            doc.text('Detailed Analysis Report', margin, 180);

            doc.line(margin, 183, margin + 80, 183);

            // Format and add main content
            doc.setFontSize(9);
            doc.setTextColor(...textColor);
            doc.setFont('helvetica', 'normal');

            const textLines = doc.splitTextToSize(analysisResult, maxLineWidth);
            const startY = 190;
            let currentY = startY;

            textLines.forEach((line: string) => {
                if (currentY > pageHeight - 30) {
                    doc.addPage();
                    currentY = 30;
                }
                doc.text(line, margin, currentY);
                currentY += 4;
            });

            // Footer
            const footerY = pageHeight - 15;
            doc.setFontSize(8);
            doc.setTextColor(...secondaryColor);
            doc.setFont('helvetica', 'italic');
            doc.text('Generated by MediView AI Analysis Platform', margin, footerY);
            doc.text(`Report ID: ${Date.now()}`, pageWidth - margin - 30, footerY);

            // Disclaimer
            doc.setFontSize(7);
            doc.text('This analysis is generated by AI and should be validated by qualified medical professionals.', margin, footerY + 5);

            // Save file
            const filename = `MediView-Report-${inferenceResult?.folder_name || 'Analysis'}-${new Date().toISOString().slice(0, 10)}.pdf`;
            doc.save(filename);

            toast({
                title: 'PDF exported successfully',
                description: `${filename} has been saved to your downloads.`,
                duration: 4000,
            });
        } catch (error) {
            console.error('[PDF EXPORT] Failed:', error);
            toast({
                title: 'Export failed',
                description: error instanceof Error ? error.message : 'Unknown error occurred',
                variant: 'destructive',
            });
        }
    });
};

    const handleDownloadGIF = async () => {
  // Verifică ce fișier să folosească (prioritate: overlay, apoi original)
  const fileToUse = overlayFile || originalFile;

  if (!fileToUse || !inferenceResult?.folder_name) {
    toast({
      title: 'Cannot create GIF',
      description: 'No file available for GIF creation.',
      variant: 'destructive',
    });
    return;
  }

  try {
    toast({
      title: 'Creating GIF animation...',
      description: 'This may take a few moments. Please wait.',
      duration: 2000,
    });

    // Import nifti-reader-js pentru citirea datelor
    const nifti = await import('nifti-reader-js');
    const pako = await import('pako');

    // Import gif.js.optimized
    const { default: GIF } = await import('gif.js.optimized');

    console.log('[GIF] Starting GIF creation with file:', fileToUse.name);

    // 1. LOAD & PARSE NIFTI FILE
    const fileBuffer = await fileToUse.arrayBuffer();
    let niftiBuffer = fileBuffer;

    // Decompress dacă e necesar
    if (nifti.isCompressed && nifti.isCompressed(niftiBuffer)) {
      console.log('[GIF] Decompressing file...');
      niftiBuffer = pako.inflate(new Uint8Array(niftiBuffer)).buffer;
    }

    // Verifică dacă e fișier NIfTI valid
    if (nifti.isNIFTI && !nifti.isNIFTI(niftiBuffer)) {
      throw new Error('Invalid NIfTI file');
    }

    const header = nifti.readHeader(niftiBuffer);
    const image = nifti.readImage(header, niftiBuffer);

    if (!header || !image) {
      throw new Error('Failed to read NIfTI data');
    }

    console.log('[GIF] NIfTI loaded:', {
      dims: header.dims,
      datatype: header.datatype
    });

    // 2. CONFIGURARE GIF
    const dims = header.dims;
    const zDim = dims[3] || 1;  // Numărul de slice-uri axiale

    // Determină dimensiunile canvas-ului bazat pe orientarea axială
    const canvasWidth = Math.min(dims[1] || 256, 1024);   // Max 512px width
    const canvasHeight = Math.min(dims[2] || 256, 1024);  // Max 512px height

    const gif = new GIF({
      workers: 2,
      quality: 10,
      width: canvasWidth,
      height: canvasHeight,
      workerScript: '/gif.worker.js',
    });

    console.log('[GIF] Canvas size:', { canvasWidth, canvasHeight });
    console.log('[GIF] Total slices to process:', zDim);

    // 3. CREATE CANVAS pentru renderare
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');

    if (!ctx) {
      throw new Error('Could not create canvas context');
    }

    canvas.width = canvasWidth;
    canvas.height = canvasHeight;

    // 4. IMPORT DRAWING FUNCTIONS
    const { drawSlice, drawSliceWithOverlay } = await import('@/utils/mriUtils');

    // Detectează tipul de fișier
    const isOverlay = fileToUse.name.toLowerCase().includes('overlay');
    const drawFunction = isOverlay ? drawSliceWithOverlay : drawSlice;

    console.log('[GIF] Using draw function:', isOverlay ? 'drawSliceWithOverlay' : 'drawSlice');

    // 5. GENERARE FRAMES
    const totalFrames = Math.min(zDim, 100); // Limitează la max 100 frame-uri
    const sliceStep = zDim > totalFrames ? zDim / totalFrames : 1;

    for (let frameIndex = 0; frameIndex < totalFrames; frameIndex++) {
      const sliceIndex = Math.floor(frameIndex * sliceStep);

      try {
        // Renderează slice-ul curent
        drawFunction({
          canvas: canvas,
          header: header,
          image: image,
          slice: sliceIndex,
          axis: 'axial', // Folosește mereu axial pentru GIF
          brightness: 100, // Setări standard
          contrast: 100,
          windowCenter: 128,
          windowWidth: 256,
          sliceThickness: 1,
          useWindowing: false,
          filename: fileToUse.name
        });

        // Adaugă frame-ul la GIF
        gif.addFrame(canvas, {
          delay: 150,  // 150ms între frame-uri (6.7 FPS)
          copy: true   // Important: copiază datele canvas-ului
        });

        console.log(`[GIF] Processed frame ${frameIndex + 1}/${totalFrames} (slice ${sliceIndex})`);

      } catch (drawError) {
        console.warn(`[GIF] Failed to draw slice ${sliceIndex}:`, drawError);
        // Continuă cu următorul frame
      }
    }

    console.log('[GIF] All frames added, rendering GIF...');

    // 6. CONFIGURARE DOWNLOAD
    gif.on('finished', (blob) => {
      try {
        const filename = `${inferenceResult.folder_name}-animation.gif`;

        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);

        console.log('[GIF] Download triggered for:', filename);

        toast({
          title: 'GIF animation created! 🎬',
          description: `${filename} has been saved to your downloads. (High quality 800px)`,
          duration: 4000,
        });
      } catch (downloadError) {
        console.error('[GIF] Download failed:', downloadError);
        toast({
          title: 'Download failed',
          description: 'GIF was created but download failed.',
          variant: 'destructive',
        });
      }
    });

    gif.on('progress', (progress) => {
      console.log(`[GIF] Rendering progress: ${(progress * 100).toFixed(1)}%`);
    });

    // 7. START RENDERING
    gif.render();

  } catch (error) {
    console.error('[GIF CREATION] Failed:', error);

    let errorMessage = 'Unknown error occurred';
    if (error instanceof Error) {
      errorMessage = error.message;
    }

    toast({
      title: 'GIF creation failed',
      description: errorMessage,
      variant: 'destructive',
      duration: 6000,
    });
  }
};



    const formatTime = (seconds: number) => {
        return `${seconds.toFixed(2)}s`;
    };

    const formatClassCount = (count: number) => {
        return count.toLocaleString();
    };

    const getClassColor = (classId: number) => {
        const colors = {
            1: 'bg-blue-100 text-blue-800 border-blue-200', // NETC
            2: 'bg-yellow-100 text-yellow-800 border-yellow-200', // SNFH
            3: 'bg-red-100 text-red-800 border-red-200', // ET
            4: 'bg-purple-100 text-purple-800 border-purple-200', // RC
        };
        return colors[classId as keyof typeof colors] || 'bg-gray-100 text-gray-800 border-gray-200';
    };

    const getClassName = (classId: number) => {
        const names = {
            1: 'NETC',
            2: 'SNFH',
            3: 'ET',
            4: 'RC'
        };
        return names[classId as keyof typeof names] || `Class ${classId}`;
    };

    // ADĂUGAT HELPER PENTRU STATUS DOWNLOAD
    const canDownloadOverlay =
        !downloadingOverlay &&
        inferenceResult?.folder_name &&
        overlayFile;

    return (
        <div className="flex flex-col h-screen bg-background text-foreground">
            <header className="flex items-center justify-between p-4 border-b border-border flex-shrink-0">
                <Logo/>
                <div className="flex items-center gap-4">
                    <Button variant="outline" asChild className="rounded-full">
                        <Link to={pages.analysis}>
                            Back to Analysis
                        </Link>
                    </Button>
                </div>
            </header>

            <main className="flex flex-1 overflow-hidden">
                <div className="flex-1 flex flex-col p-4 overflow-hidden min-w-0">
                    <div
                        className="w-full h-full bg-black/20 rounded-lg flex items-center justify-center overflow-hidden relative">
                        <ResultsMriViewer/>

                        {/* Fixed indicator - show overlay status */}
                        {overlayFile && (
                            <div className="absolute top-4 left-4 z-10">
                                <Badge
                                    variant="outline"
                                    className="bg-green-100 text-green-800 border-green-200 backdrop-blur-sm"
                                >
                                    🎯 AI Overlay (T1N + Segmentation)
                                </Badge>
                            </div>
                        )}
                    </div>
                </div>

                <div className="h-full w-full max-w-sm border-l border-border bg-card flex-shrink-0">
                    <Card className="w-full h-full overflow-y-auto rounded-none border-none">
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                <BrainCircuit className="h-6 w-6"/>
                                AI Analysis Results
                            </CardTitle>
                            <CardDescription>
                                Automated analysis results for post-treatment glioma segmentation.
                            </CardDescription>
                        </CardHeader>

                        <CardContent className="space-y-6">
                            {/* ADĂUGAT INDICATOR PENTRU OVERLAY AVAILABILITY */}
                            {overlayFile && (
                                <div
                                    className="flex items-center gap-2 p-3 bg-green-50 border border-green-200 rounded-md">
                                    <div className="flex items-center gap-2">
                                        <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                                        <span className="text-sm font-medium text-green-800">AI Overlay Available</span>
                                    </div>
                                    <Badge variant="outline"
                                           className="text-xs bg-green-100 text-green-700 border-green-300">
                                        T1N + Segmentation
                                    </Badge>
                                </div>
                            )}

                            {/* Performance metrics */}
                            {inferenceResult && (
                                <div className="space-y-4">
                                    <div className="flex items-center gap-2 mb-3">
                                        <Clock className="h-4 w-4 text-muted-foreground"/>
                                        <h3 className="font-semibold text-sm">Performance</h3>
                                    </div>

                                    <div className="grid grid-cols-2 gap-2 text-xs">
                                        <div className="bg-muted/30 p-2 rounded">
                                            <div className="text-muted-foreground">Preprocess</div>
                                            <div
                                                className="font-medium">{formatTime(inferenceResult.timing.preprocess_time)}</div>
                                        </div>
                                        <div className="bg-muted/30 p-2 rounded">
                                            <div className="text-muted-foreground">Inference</div>
                                            <div
                                                className="font-medium">{formatTime(inferenceResult.timing.inference_time)}</div>
                                        </div>
                                        <div className="bg-muted/30 p-2 rounded">
                                            <div className="text-muted-foreground">Postprocess</div>
                                            <div
                                                className="font-medium">{formatTime(inferenceResult.timing.postprocess_time)}</div>
                                        </div>
                                        <div className="bg-primary/10 p-2 rounded">
                                            <div className="text-muted-foreground">Total</div>
                                            <div
                                                className="font-semibold">{formatTime(inferenceResult.timing.total_time)}</div>
                                        </div>
                                    </div>
                                </div>
                            )}

                            {/* Segmentation statistics */}
                            {inferenceResult && (
                                <>
                                    <Separator/>
                                    <div className="space-y-4">
                                        <div className="flex items-center gap-2 mb-3">
                                            <Target className="h-4 w-4 text-muted-foreground"/>
                                            <h3 className="font-semibold text-sm">Segmentation Statistics</h3>
                                        </div>

                                        <div className="space-y-3">
                                            <div className="flex justify-between text-sm">
                                                <span className="text-muted-foreground">Total volume:</span>
                                                <span className="font-medium">
                          {inferenceResult.segmentation_info.shape.join(' × ')}
                        </span>
                                            </div>

                                            <div className="flex justify-between text-sm">
                                                <span className="text-muted-foreground">Segmented voxels:</span>
                                                <span className="font-medium">
                          {formatClassCount(inferenceResult.segmentation_info.total_segmented_voxels)}
                        </span>
                                            </div>
                                        </div>

                                        {/* Class distribution */}
                                        {Object.entries(inferenceResult.segmentation_info.class_counts)
                                            .filter(([classId]) => parseInt(classId) > 0)
                                            .length > 0 && (
                                            <div className="space-y-2">
                                                <div className="flex items-center gap-2 mb-2">
                                                    <BarChart3 className="h-3 w-3 text-muted-foreground"/>
                                                    <span className="text-xs font-medium">Class distribution:</span>
                                                </div>

                                                <div className="space-y-2">
                                                    {Object.entries(inferenceResult.segmentation_info.class_counts)
                                                        .filter(([classId]) => parseInt(classId) > 0)
                                                        .map(([classId, count]) => (
                                                            <div key={classId}
                                                                 className="flex items-center justify-between gap-2">
                                                                <Badge
                                                                    variant="outline"
                                                                    className={`text-xs ${getClassColor(parseInt(classId))}`}
                                                                >
                                                                    {getClassName(parseInt(classId))}
                                                                </Badge>
                                                                <span className="text-xs font-mono">
                                  {formatClassCount(count)}
                                </span>
                                                            </div>
                                                        ))
                                                    }
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                </>
                            )}

                            {/* AI Overlay Color Legend - afișat mereu când există overlay */}
                            {overlayFile && (
                                <>
                                    <Separator/>
                                    <div className="space-y-4">
                                        <div className="flex items-center gap-2 mb-3">
                                            <Palette className="h-4 w-4 text-muted-foreground"/>
                                            <h3 className="font-semibold text-sm">AI Overlay Legend</h3>
                                        </div>

                                        <div className="space-y-2">
                                            <div className="text-xs text-muted-foreground mb-2">
                                                T1N background + colored segmentation overlay
                                            </div>
                                            <div className="flex items-center gap-2">
                                                <div className="w-4 h-4 rounded border"
                                                     style={{backgroundColor: 'rgb(100, 180, 255)'}}></div>
                                                <span className="text-xs">NETC - Non-Enhancing Tumor Core</span>
                                            </div>
                                            <div className="flex items-center gap-2">
                                                <div className="w-4 h-4 rounded border"
                                                     style={{backgroundColor: 'rgb(255, 255, 150)'}}></div>
                                                <span className="text-xs">SNFH - Surrounding FLAIR Hyperintensity</span>
                                            </div>
                                            <div className="flex items-center gap-2">
                                                <div className="w-4 h-4 rounded border"
                                                     style={{backgroundColor: 'rgb(255, 100, 100)'}}></div>
                                                <span className="text-xs">ET - Enhancing Tumor</span>
                                            </div>
                                            <div className="flex items-center gap-2">
                                                <div className="w-4 h-4 rounded border"
                                                     style={{backgroundColor: 'rgb(200, 100, 200)'}}></div>
                                                <span className="text-xs">RC - Resection Cavity</span>
                                            </div>
                                        </div>
                                    </div>
                                </>
                            )}

                            <Separator/>

                            {/* Analysis text */}
                            <div className="space-y-4">
                                <div className="flex items-center gap-2 mb-3">
                                    <FileText className="h-4 w-4 text-muted-foreground"/>
                                    <h3 className="font-semibold text-sm">Detailed Report</h3>
                                </div>

                                <ScrollArea className="h-[calc(100vh-500px)] w-full rounded-md border p-4">
                                    {analysisResult ? (
                                        <pre className="text-xs whitespace-pre font-mono leading-relaxed min-w-max">
                      {analysisResult}
                    </pre>
                                    ) : (
                                        <p className="text-sm text-muted-foreground">Loading report...</p>
                                    )}
                                    <ScrollBar orientation="horizontal"/>
                                </ScrollArea>
                            </div>

                            {/* ACTUALIZAT - Action buttons */}
                            <div className="space-y-3 pt-4">
                                <Button
                                    variant="outline"
                                    className="w-full justify-start gap-2"
                                    onClick={handleDownloadPDF}
                                >
                                    <Download className="h-4 w-4"/>
                                    Export PDF Report
                                </Button>

                                <Button
                                    variant="outline"
                                    className="w-full justify-start gap-2"
                                    disabled={!canDownloadOverlay}
                                    onClick={handleDownloadOverlay}
                                >
                                    <Download className="h-4 w-4"/>
                                    {downloadingOverlay ? 'Downloading Overlay...' : 'Download AI Overlay'}
                                </Button>

                                {/* NOU - Download GIF Button */}
                                <Button
                                    variant="outline"
                                    className="w-full justify-start gap-2"
                                    onClick={handleDownloadGIF}
                                >
                                    <Download className="h-4 w-4"/>
                                    Export GIF Animation
                                </Button>
                            </div>

                        </CardContent>
                    </Card>
                </div>
            </main>

            <MetadataViewerDialog/>
        </div>
    );
}