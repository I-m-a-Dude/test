import { useAnalysisStore } from '@/utils/stores/analysis-store';
import {
  BrainCircuit,
  AreaChart,
  LineChart,
  FileText,
  RotateCcw,
  Sliders,
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
import { Switch } from '@/components/ui/switch';
import { useMriStore } from '@/utils/stores/mri-store';
import { Separator } from './ui/separator';
import { HistogramChart } from './histogram-chart';
import { ProfileCurveChart } from './profile-curve-chart';
import { useState } from 'react';

export function SegmentationControls() {
  const {
    showHistogram,
    showProfileCurves,
    brightness,
    contrast,
    windowCenter,
    windowWidth,
    sliceThickness,
    intensityRange,
    useWindowing,
    metadata,
    setShowHistogram,
    setShowProfileCurves,
    setBrightness,
    setContrast,
    setWindowCenter,
    setWindowWidth,
    setSliceThickness,
    setShowMetadataViewer,
    setUseWindowing,
    resetWindowing,
    resetBrightness,
  } = useAnalysisStore();

  // Local state for smooth UI updates
  const [localBrightness, setLocalBrightness] = useState(brightness);
  const [localContrast, setLocalContrast] = useState(contrast);
  const [localWindowCenter, setLocalWindowCenter] = useState(windowCenter);
  const [localWindowWidth, setLocalWindowWidth] = useState(windowWidth);
  const [localSliceThickness, setLocalSliceThickness] = useState(sliceThickness);

  const file = useMriStore((state) => state.file);
  const isDisabled = !file;

  // Simple brightness/contrast handlers
  const handleBrightnessSliderChange = (value: number[]) => {
    setLocalBrightness(value[0]);
  };

  const handleBrightnessInputChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const value = parseInt(event.target.value, 10);
    if (!isNaN(value)) {
      const clampedValue = Math.max(0, Math.min(200, value));
      setLocalBrightness(clampedValue);
      setBrightness(clampedValue);
    }
  };

  const handleContrastSliderChange = (value: number[]) => {
    setLocalContrast(value[0]);
  };

  const handleContrastInputChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const value = parseInt(event.target.value, 10);
     if (!isNaN(value)) {
      const clampedValue = Math.max(0, Math.min(200, value));
      setLocalContrast(clampedValue);
      setContrast(clampedValue);
    }
  };

  // Professional windowing handlers
  const centerMin = intensityRange.min;
  const centerMax = intensityRange.max;
  const widthMin = 1;
  const widthMax = intensityRange.max - intensityRange.min;

  const handleWindowCenterSliderChange = (value: number[]) => {
    setLocalWindowCenter(value[0]);
  };

  const handleWindowCenterInputChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const value = parseFloat(event.target.value);
    if (!isNaN(value)) {
      const clampedValue = Math.max(centerMin, Math.min(centerMax, value));
      setLocalWindowCenter(clampedValue);
      setWindowCenter(clampedValue);
    }
  };

  const handleWindowWidthSliderChange = (value: number[]) => {
    setLocalWindowWidth(value[0]);
  };

  const handleWindowWidthInputChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const value = parseFloat(event.target.value);
     if (!isNaN(value)) {
      const clampedValue = Math.max(widthMin, Math.min(widthMax, value));
      setLocalWindowWidth(clampedValue);
      setWindowWidth(clampedValue);
    }
  };

  // Slice thickness handlers
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

  const handleResetControls = () => {
    if (useWindowing) {
      resetWindowing();
      setLocalWindowCenter(windowCenter);
      setLocalWindowWidth(windowWidth);
    } else {
      resetBrightness();
      setLocalBrightness(100);
      setLocalContrast(100);
    }
  };

  return (
    <Card className="w-full h-full overflow-y-auto">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <BrainCircuit className="h-6 w-6" />
          MRI Analysis
        </CardTitle>
        <CardDescription>
          Adjust visualization settings and run advanced analysis.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold">Image Adjustments</h3>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={handleResetControls}
                disabled={isDisabled}
              >
                <RotateCcw className="h-3 w-3 mr-1" />
                Reset
              </Button>
            </div>
          </div>

          {/* Toggle between simple and professional controls */}
          <div className="flex items-center justify-between p-3 bg-muted/30 rounded-md">
            <div className="flex items-center gap-2">
              <Sliders className="h-4 w-4" />
              <Label className="text-sm">
                {useWindowing ? 'Professional Mode' : 'Simple Mode'}
              </Label>
            </div>
            <Switch
              checked={useWindowing}
              onCheckedChange={setUseWindowing}
              disabled={isDisabled}
            />
          </div>

          <div className="space-y-6 pt-2">
            {!useWindowing ? (
              // Simple brightness/contrast controls
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label className="text-sm">Brightness</Label>
                  <div className="flex items-center gap-2">
                    <Slider
                      value={[localBrightness]}
                      onValueChange={handleBrightnessSliderChange}
                      onValueCommit={(value) => setBrightness(value[0])}
                      min={0}
                      max={200}
                      step={1}
                      disabled={isDisabled}
                    />
                    <Input
                      type="number"
                      value={localBrightness}
                      onChange={handleBrightnessInputChange}
                      className="w-16 h-8"
                      disabled={isDisabled}
                    />
                    <span className="text-xs text-muted-foreground">%</span>
                  </div>
                </div>
                <div className="space-y-2">
                  <Label className="text-sm">Contrast</Label>
                  <div className="flex items-center gap-2">
                    <Slider
                      value={[localContrast]}
                      onValueChange={handleContrastSliderChange}
                      onValueCommit={(value) => setContrast(value[0])}
                      min={0}
                      max={200}
                      step={1}
                      disabled={isDisabled}
                    />
                    <Input
                      type="number"
                      value={localContrast}
                      onChange={handleContrastInputChange}
                      className="w-16 h-8"
                      disabled={isDisabled}
                    />
                    <span className="text-xs text-muted-foreground">%</span>
                  </div>
                </div>
              </div>
            ) : (
              // Professional windowing controls
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label className="text-sm">Window Center (WC)</Label>
                  <div className="flex items-center gap-2">
                    <Slider
                      value={[localWindowCenter]}
                      onValueChange={handleWindowCenterSliderChange}
                      onValueCommit={(value) => setWindowCenter(value[0])}
                      min={centerMin}
                      max={centerMax}
                      step={(centerMax - centerMin) / 1000}
                      disabled={isDisabled}
                    />
                    <Input
                      type="number"
                      value={localWindowCenter.toFixed(0)}
                      onChange={handleWindowCenterInputChange}
                      className="w-20 h-8"
                      disabled={isDisabled}
                    />
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Range: {centerMin.toFixed(0)} - {centerMax.toFixed(0)}
                  </p>
                </div>
                <div className="space-y-2">
                  <Label className="text-sm">Window Width (WW)</Label>
                  <div className="flex items-center gap-2">
                    <Slider
                      value={[localWindowWidth]}
                      onValueChange={handleWindowWidthSliderChange}
                      onValueCommit={(value) => setWindowWidth(value[0])}
                      min={widthMin}
                      max={widthMax}
                      step={widthMax / 1000}
                      disabled={isDisabled}
                    />
                    <Input
                      type="number"
                      value={localWindowWidth.toFixed(0)}
                      onChange={handleWindowWidthInputChange}
                      className="w-20 h-8"
                      disabled={isDisabled}
                    />
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Range: {widthMin} - {widthMax.toFixed(0)}
                  </p>
                </div>

                {/* Preset windows for professional mode */}
                <div className="space-y-2">
                  <Label className="text-sm">Presets</Label>
                  <div className="grid grid-cols-2 gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      className="text-xs"
                      onClick={() => {
                        const brainCenter = (intensityRange.min + intensityRange.max) / 2;
                        const brainWidth = (intensityRange.max - intensityRange.min) * 0.6;
                        setWindowCenter(brainCenter);
                        setWindowWidth(brainWidth);
                        setLocalWindowCenter(brainCenter);
                        setLocalWindowWidth(brainWidth);
                      }}
                      disabled={isDisabled}
                    >
                      Brain
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      className="text-xs"
                      onClick={() => {
                        const softCenter = intensityRange.min + (intensityRange.max - intensityRange.min) * 0.3;
                        const softWidth = (intensityRange.max - intensityRange.min) * 0.4;
                        setWindowCenter(softCenter);
                        setWindowWidth(softWidth);
                        setLocalWindowCenter(softCenter);
                        setLocalWindowWidth(softWidth);
                      }}
                      disabled={isDisabled}
                    >
                      Soft Tissue
                    </Button>
                  </div>
                </div>
              </div>
            )}

            {/* Slice thickness (always visible) */}
            <div className="space-y-3">
              <Label className="text-sm">Slice Thickness</Label>
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
                  className="w-16 h-8"
                  disabled={isDisabled}
                />
              </div>
              <p className="text-xs text-muted-foreground">
                Average multiple slices for smoother visualization
              </p>
            </div>
          </div>
        </div>

        <Separator />
        <div className="space-y-4">
          <h3 className="font-semibold">Advanced Analysis</h3>
          <div className="space-y-4 pt-2">
            <div className="space-y-2">
                <Button
                  variant="outline"
                  className="w-full justify-start gap-2"
                  onClick={() => setShowHistogram(!showHistogram)}
                  disabled={isDisabled}
                >
                  <AreaChart className="h-4 w-4" />
                  {showHistogram ? 'Hide' : 'Show'} Histogram
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
                  <LineChart className="h-4 w-4" />
                  {showProfileCurves ? 'Hide' : 'Show'} Profile Curves
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
          <div className="space-y-4 pt-2">
            <Button
              variant="outline"
              className="w-full justify-start gap-2"
              onClick={() => setShowMetadataViewer(true)}
              disabled={isDisabled}
            >
                <FileText className="h-4 w-4" /> View Metadata
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}