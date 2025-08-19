import { MriViewer } from '@/components/mri-viewer';
      import { Logo } from '@/components/logo';
      import { Button } from '@/components/ui/button';
      import { Link, useNavigate } from 'react-router-dom';
      import { useCineMode } from '@/utils/hooks/use-cine-mode';
      import { MetadataViewerDialog } from '@/components/metadata-viewer-dialog';
      import { useResultStore } from '@/utils/stores/result-store';
      import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
      import { BrainCircuit, FileText, Download, Eye, BarChart3, Clock, Target } from 'lucide-react';
      import { ScrollArea } from '@/components/ui/scroll-area';
      import { Badge } from '@/components/ui/badge';
      import { Separator } from '@/components/ui/separator';
      import { pages } from '@/utils/pages';
      import { useEffect, useState } from 'react';
      import { useMriStore } from '@/utils/stores/mri-store';
      import { useToast } from '@/utils/hooks/use-toast';

      export default function ResultPage() {
        useCineMode();
        const { analysisResult, fileName, segmentationFile, inferenceResult } = useResultStore();
        const { file, setFile, setLastKnownBackendFile } = useMriStore();
        const { toast } = useToast();
        const navigate = useNavigate();
        const [isViewingSegmentation, setIsViewingSegmentation] = useState(false);
        const [originalFile, setOriginalFile] = useState<File | null>(null);

        useEffect(() => {
          // If there is no analysis result OR the result is for a different file, redirect.
          if (!analysisResult || (file && fileName !== file.name)) {
            navigate(pages.analysis, { replace: true });
          } else {
            // Store original file and automatically switch to segmentation if available
            if (segmentationFile && !isViewingSegmentation) {
              setOriginalFile(file);
              setFile(segmentationFile);
              setLastKnownBackendFile(segmentationFile.name);
              setIsViewingSegmentation(true);

              toast({
                title: 'Segmentation loaded',
                description: 'The AI segmentation result is now displayed.',
              });
            }
          }
        }, [analysisResult, fileName, file, navigate, segmentationFile, isViewingSegmentation, setFile, setLastKnownBackendFile, toast]);

        // Render a loading state or null while redirecting to avoid flashing content
        if (!analysisResult || (file && fileName !== file.name && !segmentationFile)) {
          return null;
        }

        const handleToggleView = () => {
          if (isViewingSegmentation && originalFile) {
            // Switch back to original file
            setFile(originalFile);
            setLastKnownBackendFile(originalFile.name);
            setIsViewingSegmentation(false);
            toast({
              title: 'Original file loaded',
              description: 'The original MRI file is now displayed.',
            });
          } else if (!isViewingSegmentation && segmentationFile) {
            // Switch to segmentation
            if (!originalFile) {
              setOriginalFile(file);
            }
            setFile(segmentationFile);
            setLastKnownBackendFile(segmentationFile.name);
            setIsViewingSegmentation(true);
            toast({
              title: 'Segmentation loaded',
              description: 'The AI segmentation result is now displayed.',
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

        return (
          <div className="flex flex-col h-screen bg-background text-foreground">
            <header className="flex items-center justify-between p-4 border-b border-border flex-shrink-0">
              <Logo />
              <div className="flex items-center gap-4">
                {segmentationFile && (
                  <Button
                    variant="outline"
                    onClick={handleToggleView}
                    className="rounded-full"
                  >
                    <Eye className="h-4 w-4 mr-2" />
                    {isViewingSegmentation ? 'View Original' : 'View Segmentation'}
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
                  <MriViewer />

                  {/* Indicator for view type */}
                  {segmentationFile && (
                    <div className="absolute top-4 left-4 z-10">
                      <Badge
                        variant="outline"
                        className={`${isViewingSegmentation 
                          ? 'bg-green-100 text-green-800 border-green-200' 
                          : 'bg-blue-100 text-blue-800 border-blue-200'
                        } backdrop-blur-sm`}
                      >
                        {isViewingSegmentation ? '🎯 AI Segmentation' : '📊 Original MRI'}
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
                      AI Analysis Result
                    </CardTitle>
                    <CardDescription>
                      The automated analysis result for post-treatment glioma segmentation.
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
                    </div>
                  </CardContent>
                </Card>
              </div>
            </main>

            <MetadataViewerDialog />
          </div>
        );
      }