import { useViewStore } from '@/utils/stores/view-store';
import { useAnalysisStore } from '@/utils/stores/analysis-store';
import { Button } from '@/components/ui/button';
import { ZoomIn, ZoomOut, RotateCcw, Scan, Play, Pause } from 'lucide-react';
import { Slider } from '@/components/ui/slider';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useMriStore } from '@/utils/stores/mri-store';
import type {ViewAxis} from '@/types/view-types';

export function ViewerToolbar() {
  const { 
    slice, 
    maxSlices, 
    axis, 
    setSlice, 
    setAxis,
    zoomIn, 
    zoomOut,
    resetView,
  } = useViewStore();

  const { isCineMode, setIsCineMode } = useAnalysisStore();

  const file = useMriStore(state => state.file);
  const isDisabled = !file;
  
  return (
    <div className="w-full max-w-xl space-y-4 p-4 bg-card/80 rounded-md border border-border backdrop-blur-sm">
      <div className="flex items-center gap-4">
        <Scan className="w-5 h-5 text-muted-foreground" />
        <Slider
          value={[slice]}
          onValueChange={(value) => setSlice(value[0])}
          max={maxSlices[axis] > 0 ? maxSlices[axis] - 1 : 0}
          step={1}
          disabled={isDisabled || maxSlices[axis] === 0}
        />
      </div>
       <div className="flex justify-between items-center gap-4">
        <div className="flex items-center gap-2">
            <Tabs value={axis} onValueChange={(value) => setAxis(value as ViewAxis)} className="w-auto">
              <TabsList>
                <TabsTrigger value="axial" disabled={isDisabled}>Axial</TabsTrigger>
                <TabsTrigger value="sagittal" disabled={isDisabled}>Sagittal</TabsTrigger>
                <TabsTrigger value="coronal" disabled={isDisabled}>Coronal</TabsTrigger>
              </TabsList>
            </Tabs>
            <Button variant="outline" size="icon" onClick={() => setIsCineMode(!isCineMode)} disabled={isDisabled}>
              {isCineMode ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
              <span className="sr-only">{isCineMode ? 'Pause Cine Mode' : 'Play Cine Mode'}</span>
            </Button>
        </div>
        <div className="flex justify-center gap-2">
            <Button variant="outline" size="icon" onClick={zoomIn} disabled={isDisabled}>
            <ZoomIn className="h-4 w-4" />
            <span className="sr-only">Zoom In</span>
            </Button>
            <Button variant="outline" size="icon" onClick={zoomOut} disabled={isDisabled}>
            <ZoomOut className="h-4 w-4" />
            <span className="sr-only">Zoom Out</span>
            </Button>
            <Button variant="outline" size="icon" onClick={resetView} disabled={isDisabled}>
            <RotateCcw className="h-4 w-4" />
            <span className="sr-only">Reset View</span>
            </Button>
        </div>
      </div>
    </div>
  );
}