// frontend/src/pages/result-page.tsx
import { ResultsMriViewer } from '@/components/results-mri-viewer';
import { Logo } from '@/components/logo';
import { Button } from '@/components/ui/button';
import { Link, useNavigate } from 'react-router-dom';
import { useCineMode } from '@/utils/hooks/use-cine-mode';
import { MetadataViewerDialog } from '@/components/metadata-viewer-dialog';
import { useResultStore } from '@/utils/stores/result-store';
import { useResultsViewerStore } from '@/utils/stores/results-viewer-store';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { BrainCircuit, FileText, Download, BarChart3, Clock, Target, Palette } from 'lucide-react';
import { ScrollArea, ScrollBar } from '@/components/ui/scroll-area'; // FIXED: Added ScrollBar import
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { pages } from '@/utils/pages';
import { useEffect } from 'react';
import { useToast } from '@/utils/hooks/use-toast';

export default function ResultPage() {
  useCineMode();
  const { analysisResult, overlayFile, inferenceResult, originalFile } = useResultStore();
  const { setCurrentFile } = useResultsViewerStore();
  const { toast } = useToast();
  const navigate = useNavigate();

  useEffect(() => {
    // If there is no analysis result, redirect to analysis
    if (!analysisResult) {
      navigate(pages.analysis, { replace: true });
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

  // Render a loading state or null while redirecting to avoid flashing content
  if (!analysisResult) {
    return null;
  }

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

              {/* AI Overlay Color Legend - afișat mereu când există overlay */}
              {overlayFile && (
                <>
                  <Separator />
                  <div className="space-y-4">
                    <div className="flex items-center gap-2 mb-3">
                      <Palette className="h-4 w-4 text-muted-foreground" />
                      <h3 className="font-semibold text-sm">AI Overlay Legend</h3>
                    </div>

                    <div className="space-y-2">
                      <div className="text-xs text-muted-foreground mb-2">
                        T1N background + colored segmentation overlay
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="w-4 h-4 rounded border" style={{ backgroundColor: 'rgb(100, 180, 255)' }}></div>
                        <span className="text-xs">NETC - Non-Enhancing Tumor Core</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="w-4 h-4 rounded border" style={{ backgroundColor: 'rgb(255, 255, 150)' }}></div>
                        <span className="text-xs">SNFH - Surrounding FLAIR Hyperintensity</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="w-4 h-4 rounded border" style={{ backgroundColor: 'rgb(255, 100, 100)' }}></div>
                        <span className="text-xs">ET - Enhancing Tumor</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="w-4 h-4 rounded border" style={{ backgroundColor: 'rgb(200, 100, 200)' }}></div>
                        <span className="text-xs">RC - Resection Cavity</span>
                      </div>
                    </div>
                  </div>
                </>
              )}

              <Separator />

              {/* Analysis text - FIXED: Added horizontal scroll */}
              <div className="space-y-4">
                <div className="flex items-center gap-2 mb-3">
                  <FileText className="h-4 w-4 text-muted-foreground" />
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
                  {/* FIXED: Add horizontal scrollbar */}
                  <ScrollBar orientation="horizontal" />
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
                  Download AI Overlay
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