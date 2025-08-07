
import { useAnalysisStore } from '@/utils/stores/analysis-store';
import {
  Box,
  BrainCircuit,
  Layers,
  AreaChart,
  LineChart,
  GitCompareArrows,
  Download,
  FileText,
} from 'lucide-react';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Slider } from '@/components/ui/slider';
import { useMriStore } from '@/utils/stores/mri-store';
import { Separator } from './ui/separator';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { HistogramChart } from './histogram-chart';
import { ProfileCurveChart } from './profile-curve-chart';
import { useState } from 'react';

export function SegmentationControls() {
  const {
    showHistogram,
    showProfileCurves,
    brightness,
    contrast,
    sliceThickness,
    setShowHistogram,
    setShowProfileCurves,
    setBrightness,
    setContrast,
    setSliceThickness,
    setShowMetadataViewer
  } = useAnalysisStore();
  
  const [localContrast, setLocalContrast] = useState(contrast);
  const [localBrightness, setLocalBrightness] = useState(brightness);
  const [localSliceThickness, setLocalSliceThickness] = useState(sliceThickness);

  const file = useMriStore((state) => state.file);
  const isDisabled = !file;
  
  const handleContrastSliderChange = (value: number[]) => {
    setLocalContrast(value[0]);
  };
  
  const handleContrastInputChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const value = parseInt(event.target.value, 10);
    if (!isNaN(value)) {
      const clampedValue = Math.max(0, Math.min(100, value));
      setLocalContrast(clampedValue);
      setContrast(clampedValue);
    }
  };

  const handleBrightnessSliderChange = (value: number[]) => {
    setLocalBrightness(value[0]);
  };

  const handleBrightnessInputChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const value = parseInt(event.target.value, 10);
     if (!isNaN(value)) {
      const clampedValue = Math.max(0, Math.min(100, value));
      setLocalBrightness(clampedValue);
      setBrightness(clampedValue);
    }
  };

  const handleSliceThicknessSliderChange = (value: number[]) => {
    setLocalSliceThickness(value[0]);
  };

  const handleSliceThicknessInputChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const value = parseFloat(event.target.value);
    if (!isNaN(value)) {
      const clampedValue = Math.max(1, Math.min(10, value));
      setLocalSliceThickness(clampedValue);
      setSliceThickness(clampedValue);
    }
  };


  return (
    <Card className="w-full h-full overflow-y-auto">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <BrainCircuit className="h-6 w-6" />
          Analysis
        </CardTitle>
        <CardDescription>
          Adjust image properties and run advanced analysis.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="space-y-4">
          <h3 className="font-semibold">Image Adjustments</h3>
          <div className="space-y-6 pt-4">
            <div className="space-y-4">
              <Label>Windowing</Label>
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label className="text-xs text-muted-foreground">Contrast</Label>
                  <div className="flex items-center gap-2">
                    <Slider
                      value={[localContrast]}
                      onValueChange={handleContrastSliderChange}
                      onValueCommit={(value) => setContrast(value[0])}
                      max={100}
                      step={1}
                      disabled={isDisabled}
                    />
                    <Input
                      type="number"
                      value={localContrast}
                      onChange={handleContrastInputChange}
                      className="w-20 h-8"
                      disabled={isDisabled}
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label className="text-xs text-muted-foreground">Brightness</Label>
                  <div className="flex items-center gap-2">
                    <Slider
                      value={[localBrightness]}
                      onValueChange={handleBrightnessSliderChange}
                      onValueCommit={(value) => setBrightness(value[0])}
                      max={100}
                      step={1}
                      disabled={isDisabled}
                    />
                    <Input
                      type="number"
                      value={localBrightness}
                      onChange={handleBrightnessInputChange}
                      className="w-20 h-8"
                      disabled={isDisabled}
                    />
                  </div>
                </div>
              </div>
            </div>
            <div className="space-y-3">
              <Label>Slice Thickness</Label>
              <div className="flex items-center gap-2">
                <Slider
                  value={[localSliceThickness]}
                  onValueChange={handleSliceThicknessSliderChange}
                  onValueCommit={(value) => setSliceThickness(value[0])}
                  min={1}
                  max={10}
                  step={0.5}
                  disabled={isDisabled}
                />
                <Input
                  type="number"
                  value={localSliceThickness}
                  onChange={handleSliceThicknessInputChange}
                  min={1}
                  max={10}
                  step={0.5}
                  className="w-20 h-8"
                  disabled={isDisabled}
                />
              </div>
            </div>
          </div>
        </div>
        <Separator />
        <div className="space-y-4">
          <h3 className="font-semibold">Advanced Analysis</h3>
          <div className="space-y-4 pt-4">
             <div className="flex items-center justify-between">
              <Label htmlFor="3d-switch" className="flex items-center gap-2">
                <Box className="h-4 w-4" /> 3D Reconstruction
              </Label>
            </div>
             <div className="flex items-center justify-between">
              <Label htmlFor="mpr-switch" className="flex items-center gap-2">
                <Layers className="h-4 w-4" /> Multi-planar View
              </Label>
            </div>
            <div className="space-y-2">
                <Button
                  variant="outline"
                  className="w-full justify-start gap-2"
                  onClick={() => setShowHistogram(!showHistogram)}
                  disabled={isDisabled}
                >
                  <AreaChart className="h-4 w-4" /> Show Histogram
                </Button>
                {showHistogram && (
                  <div className="h-40 w-full p-2 border rounded-md">
                    <HistogramChart />
                  </div>
                )}
            </div>
             <div className="space-y-2">
                <Button
                  variant="outline"
                  className="w-full justify-start gap-2"
                  onClick={() => setShowProfileCurves(!showProfileCurves)}
                  disabled={isDisabled}
                >
                  <LineChart className="h-4 w-4" /> Show Profile Curves
                </Button>
                 {showProfileCurves && (
                  <div className="h-40 w-full p-2 border rounded-md">
                    <ProfileCurveChart />
                  </div>
                )}
            </div>
          </div>
        </div>
        <Separator />
        <div className="space-y-4">
          <h3 className="font-semibold">Tools</h3>
          <div className="space-y-4 pt-4">
            <Button variant="outline" className="w-full justify-start gap-2" disabled={isDisabled}>
                <GitCompareArrows className="h-4 w-4" /> Study Comparison
            </Button>
             <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" className="w-full justify-start gap-2" disabled={isDisabled}>
                  <Download className="h-4 w-4" /> Export
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent className="w-[--radix-dropdown-menu-trigger-width]">
                <DropdownMenuItem>PNG</DropdownMenuItem>
                <DropdownMenuItem>PDF with measurements</DropdownMenuItem>
                <DropdownMenuItem>DICOM</DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
            <Button variant="outline" className="w-full justify-start gap-2" onClick={() => setShowMetadataViewer(true)} disabled={isDisabled}>
                <FileText className="h-4 w-4" /> Metadata Viewer
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
