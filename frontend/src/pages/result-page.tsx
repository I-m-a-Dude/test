import { ResultsMriViewer } from '@/components/results-mri-viewer';
import { Logo } from '@/components/logo';
import { Button } from '@/components/ui/button';
import { Link, useNavigate } from 'react-router-dom';
import { useCineMode } from '@/utils/hooks/use-cine-mode';
import { MetadataViewerDialog } from '@/components/metadata-viewer-dialog';
import { useResultStore } from '@/utils/stores/result-store';
import { useResultsViewerStore } from '@/utils/stores/results-viewer-store';
import { useOverlayStore } from '@/utils/stores/overlay-store'; // NOU
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { BrainCircuit, FileText, Download, Eye, BarChart3, Clock, Target, Palette, Loader2 } from 'lucide-react';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { pages } from '@/utils/pages';
import { useEffect, useState } from 'react';
import { useToast } from '@/utils/hooks/use-toast';

export default function ResultPage() {
  useCineMode();
  const { analysisResult, segmentationFile, inferenceResult, originalFile } = useResultStore();
  const { setCurrentFile } = useResultsViewerStore();

  // NOU: Overlay store
  const {
    overlayFile,
    isLoadingOverlay,
    overlayError,
    downloadOverlayForFolder,
    clearOverlay
  } = useOverlayStore();

  const { toast } = useToast();
  const navigate = useNavigate();

  // MODIFICAT: State pentru toggle între segmentation și overlay
  const [isViewingOverlay, setIsViewingOverlay] = useState(false);

  useEffect(() => {
    // If there is no analysis result, redirect to analysis
    if (!analysisResult) {
      navigate(pages.analysis, { replace: true });
      return;
    }

    // MODIFICAT: Set the appropriate file in the results viewer
    const fileToShow = isViewingOverlay && overlayFile ? overlayFile : segmentationFile;

    if (fileToShow) {
      setCurrentFile(fileToShow);
    }

    // Show appropriate toast
    if (isViewingOverlay && overlayFile) {
      toast({
        title: 'Overlay loaded',
        description: 'Now displaying T1N + AI segmentation overlay.',
      });
    } else if (segmentationFile) {
      toast({
        title: 'Segmentation loaded',
        description: 'Now displaying AI segmentation result.',
      });
    }
  }, [analysisResult, navigate, segmentationFile, overlayFile, isViewingOverlay, setCurrentFile, toast]);

  // Auto-download overlay when we have inference result
  useEffect(() => {
    if (inferenceResult && inferenceResult.folder_name && !overlayFile && !isLoadingOverlay) {
      // Încarcă automat overlay-ul pentru folder
      downloadOverlayForFolder(inferenceResult.folder_name).catch((error) => {
        console.warn('Nu s-a putut încărca overlay-ul automat:', error);
      });
    }
  }, [inferenceResult, overlayFile, isLoadingOverlay, downloadOverlayForFolder]);

  // Render a loading state or null while redirecting to avoid flashing content
  if (!analysisResult) {
    return null;
  }

  // MODIFICAT: Toggle între segmentation și overlay
  const handleToggleView = () => {
    if (isViewingOverlay) {
      // Switch to segmentation
      setIsViewingOverlay(false);
      toast({
        title: 'Segmentation loaded',
        description: 'Now displaying AI segmentation result.',
      });
    } else {
      // Switch to overlay
      if (overlayFile) {
        setIsViewingOverlay(true);
        toast({
          title: 'Overlay loaded',
          description: 'Now displaying T1N + AI segmentation overlay.',
        });
      } else {
        // Încarcă overlay-ul dacă nu e disponibil
        if (inferenceResult?.folder_name) {
          downloadOverlayForFolder(inferenceResult.folder_name).then(() => {
            setIsViewingOverlay(true);
            toast({
              title: 'Overlay loaded',
              description: 'Now displaying T1N + AI segmentation overlay.',
            });
          }).catch((error) => {
            toast({
              title: 'Error loading overlay',
              description: error.message,
              variant: 'destructive',
            });
          });
        }
      }
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

  return (
    <div className="flex flex-col h-screen bg-background text-foreground">
      <header className="flex items-center justify-between p-4 border-b border-border flex-shrink-0">
        <Logo />
        <div className="flex items-center gap-4">
          {/* MODIFICAT: Buton pentru toggle overlay */}
          {segmentationFile && (
            <Button
              variant="outline"
              onClick={handleToggleView}
              disabled={isLoadingOverlay}
              className="rounded-full"
            >
              {isLoadingOverlay ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Loading...
                </>
              ) : (
                <>
                  <Eye className="h-4 w-4 mr-2" />
                  {isViewingOverlay ? 'View Segmentation' : 'View Overlay'}
                </>
              )}
            </Button>
          )}
          <Button variant="outline" asChild className="rounded-full">
            <Link to={pages.analysis}>
              Back to Analysis
            </Link>
          </Button>
        </div>
      </header>

      <main className="flex flex-1 overflow-hidden">
        <div className="flex-1 flex flex-col p-4 overflow-hidden min-w-0">
          <div className="w-full h-full bg-black/20 rounded-lg flex items-center justify-center overflow-hidden relative">
            <ResultsMriViewer />

            {/* MODIFICAT: Indicator pentru tipul de view */}
            {segmentationFile && (
              <div className="absolute top-4 left-4 z-10">
                <Badge
                  variant="outline"
                  className={`${isViewingOverlay 
                    ? 'bg-purple-100 text-purple-800 border-purple-200' 
                    : 'bg-green-100 text-green-800 border-green-200'
                  } backdrop-blur-sm`}
                >
                  {isViewingOverlay ? '🎨 T1N + Segmentation Overlay' : '🎯 AI Segmentation'}
                </Badge>
              </div>
            )}

            {/* Loading overlay indicator */}
            {isLoadingOverlay && (
              <div className="absolute top-4 right-4 z-10">
                <Badge variant="outline" className="bg-blue-100 text-blue-800 border-blue-200 backdrop-blur-sm">
                  <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                  Loading overlay...
                </Badge>
              </div>
            )}

            {/* Error overlay indicator */}
            {overlayError && (
              <div className="absolute top-4 right-4 z-10">
                <Badge variant="outline" className="bg-red-100 text-red-800 border-red-200 backdrop-blur-sm">
                  ❌ Overlay error
                </Badge>
              </div>
            )}
          </div>
        </div>

        <div className="h-full w-full max-w-sm border-l border-border bg-card flex-shrink-0">
          <Card className="w-full h-full overflow-y-auto rounded-none border-none">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BrainCircuit className="h-6 w-6" />
                AI Analysis Results
              </CardTitle>
              <CardDescription>
                Automated analysis results for post-treatment glioma segmentation.
              </CardDescription>
            </CardHeader>

            <CardContent className="space-y-6">
              {/* Performance metrics */}
              {inferenceResult && (
                <div className="space-y-4">
                  <div className="flex items-center gap-2 mb-3">
                    <Clock className="h-4 w-4 text-muted-foreground" />
                    <h3 className="font-semibold text-sm">Performance</h3>
                  </div>

                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div className="bg-muted/30 p-2 rounded">
                      <div className="text-muted-foreground">Preprocess</div>
                      <div className="font-medium">{formatTime(inferenceResult.timing.preprocess_time)}</div>
                    </div>
                    <div className="bg-muted/30 p-2 rounded">
                      <div className="text-muted-foreground">Inference</div>
                      <div className="font-medium">{formatTime(inferenceResult.timing.inference_time)}</div>
                    </div>
                    <div className="bg-muted/30 p-2 rounded">
                      <div className="text-muted-foreground">Postprocess</div>
                      <div className="font-medium">{formatTime(inferenceResult.timing.postprocess_time)}</div>
                    </div>
                    <div className="bg-primary/10 p-2 rounded">
                      <div className="text-muted-foreground">Total</div>
                      <div className="font-semibold">{formatTime(inferenceResult.timing.total_time)}</div>
                    </div>
                  </div>
                </div>
              )}

              {/* Segmentation statistics */}
              {inferenceResult && (
                <>
                  <Separator />
                  <div className="space-y-4">
                    <div className="flex items-center gap-2 mb-3">
                      <Target className="h-4 w-4 text-muted-foreground" />
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
                          <BarChart3 className="h-3 w-3 text-muted-foreground" />
                          <span className="text-xs font-medium">Class distribution:</span>
                        </div>

                        <div className="space-y-2">
                          {Object.entries(inferenceResult.segmentation_info.class_counts)
                            .filter(([classId]) => parseInt(classId) > 0)
                            .map(([classId, count]) => (
                              <div key={classId} className="flex items-center justify-between gap-2">
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

              {/* MODIFICAT: Color Legend pentru ambele view-uri */}
              {segmentationFile && (
                <>
                  <Separator />
                  <div className="space-y-4">
                    <div className="flex items-center gap-2 mb-3">
                      <Palette className="h-4 w-4 text-muted-foreground" />
                      <h3 className="font-semibold text-sm">
                        {isViewingOverlay ? 'Overlay Colors' : 'Segmentation Colors'}
                      </h3>
                    </div>

                    <div className="space-y-2">
                      {isViewingOverlay && (
                        <div className="text-xs text-muted-foreground mb-2">
                          Segmentation overlaid on T1N background
                        </div>
                      )}
                      <div className="flex items-center gap-2">
                        <div className="w-4 h-4 rounded border" style={{ backgroundColor: 'rgb(0, 100, 255)' }}></div>
                        <span className="text-xs">NETC - Non-Enhancing Tumor Core</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="w-4 h-4 rounded border" style={{ backgroundColor: 'rgb(255, 255, 0)' }}></div>
                        <span className="text-xs">SNFH - Surrounding FLAIR Hyperintensity</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="w-4 h-4 rounded border" style={{ backgroundColor: 'rgb(255, 0, 0)' }}></div>
                        <span className="text-xs">ET - Enhancing Tumor</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="w-4 h-4 rounded border" style={{ backgroundColor: 'rgb(128, 0, 128)' }}></div>
                        <span className="text-xs">RC - Resection Cavity</span>
                      </div>
                    </div>
                  </div>
                </>
              )}

              <Separator />

              {/* Analysis text */}
              <div className="space-y-4">
                <div className="flex items-center gap-2 mb-3">
                  <FileText className="h-4 w-4 text-muted-foreground" />
                  <h3 className="font-semibold text-sm">Detailed Report</h3>
                </div>

                <ScrollArea className="h-[calc(100vh-500px)] w-full rounded-md border p-4">
                  {analysisResult ? (
                    <pre className="text-xs whitespace-pre-wrap font-mono leading-relaxed">
                      {analysisResult}
                    </pre>
                  ) : (
                    <p className="text-sm text-muted-foreground">Loading report...</p>
                  )}
                </ScrollArea>
              </div>

              {/* Action buttons */}
              <div className="space-y-3 pt-4">
                <Button variant="outline" className="w-full justify-start gap-2" disabled>
                  <Download className="h-4 w-4" />
                  Export PDF Report
                </Button>
                <Button variant="outline" className="w-full justify-start gap-2" disabled>
                  <Download className="h-4 w-4" />
                  Download Segmentation
                </Button>
                {/* NOU: Buton pentru download overlay */}
                <Button variant="outline" className="w-full justify-start gap-2" disabled>
                  <Download className="h-4 w-4" />
                  Download Overlay
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </main>

      <MetadataViewerDialog />
    </div>
  );
}