import React, { useState, useEffect, useRef } from 'react';
import * as nifti from 'nifti-reader-js';
import pako from 'pako';
import { useResultsViewerStore } from '@/utils/stores/results-viewer-store';
import { useOverlayStore } from '@/utils/stores/overlay-store'; // NOU
import { useAnalysisStore } from '@/utils/stores/analysis-store';
import { Skeleton } from '@/components/ui/skeleton';
import { AlertTriangle } from 'lucide-react';
import { ViewerToolbar } from './viewer-toolbar';
import { cn } from '@/utils/cn';
import { getDataType, calculateAndSetChartData, drawSlice, drawSliceWithSegmentation, drawSliceWithOverlay, isSegmentationFile } from '@/utils/mriUtils';

export function ResultsMriViewer() {
  const { currentFile, slice, zoom, axis, pan, setPan, setMaxSlices, zoomIn, zoomOut } = useResultsViewerStore();
  const { overlayFile } = useOverlayStore(); // NOU: pentru detectarea overlay-ului
  const {
    brightness,
    contrast,
    windowCenter,
    windowWidth,
    sliceThickness,
    useWindowing,
    setHistogramData,
    setProfileCurveData,
    setMetadata,
    setWindowCenter,
    setWindowWidth,
    setIntensityRange,
    setCanvasRef,
  } = useAnalysisStore();

  const [niftiHeader, setNiftiHeader] = useState<nifti.NIFTI1 | nifti.NIFTI2 | null>(null);
  const [niftiImage, setNiftiImage] = useState<ArrayBuffer | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isSegmentation, setIsSegmentation] = useState(false);
  const [isOverlay, setIsOverlay] = useState(false); // NOU: detectare overlay
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const [isPanning, setIsPanning] = useState(false);
  const [panStart, setPanStart] = useState({ x: 0, y: 0 });

  useEffect(() => {
    const loadNiftiFile = async () => {
      setLoading(true);
      setError(null);

      if (!currentFile) {
        setError('No MRI file found.');
        setLoading(false);
        return;
      }

      try {
        console.log(`Loading file: ${currentFile.name}, size: ${currentFile.size} bytes`);

        const fileBuffer = await currentFile.arrayBuffer();
        let niftiBuffer = fileBuffer;

        if (nifti.isCompressed && nifti.isCompressed(niftiBuffer)) {
          console.log('File is compressed, decompressing...');
          niftiBuffer = pako.inflate(new Uint8Array(niftiBuffer)).buffer;
        }

        if (nifti.isNIFTI && !nifti.isNIFTI(niftiBuffer)) {
          setError('The provided file is not a valid NIfTI file.');
          setLoading(false);
          return;
        }

        const header = nifti.readHeader(niftiBuffer);
        if (!header) {
          setError('Failed to read NIfTI header.');
          setLoading(false);
          return;
        }

        console.log('NIfTI Header:', header);

        const image = nifti.readImage(header, niftiBuffer);
        if (!image) {
          setError('Failed to read NIfTI image data.');
          setLoading(false);
          return;
        }

        console.log(`Image data loaded: ${image.byteLength} bytes`);

        // Convert to typed data for detection
        let typedData: Float32Array;
        switch (header.datatype || header.datatypeCode) {
          case nifti.NIFTI1.TYPE_INT16:
            typedData = new Float32Array(new Int16Array(image));
            break;
          case nifti.NIFTI1.TYPE_UINT16:
            typedData = new Float32Array(new Uint16Array(image));
            break;
          case nifti.NIFTI1.TYPE_INT32:
            typedData = new Float32Array(new Int32Array(image));
            break;
          case nifti.NIFTI1.TYPE_UINT32:
            typedData = new Float32Array(new Uint32Array(image));
            break;
          case nifti.NIFTI1.TYPE_FLOAT32:
            typedData = new Float32Array(image);
            break;
          case nifti.NIFTI1.TYPE_FLOAT64:
            const float64Data = new Float64Array(image);
            typedData = new Float32Array(float64Data);
            break;
          default:
            typedData = new Float32Array(image);
        }

        // NOU: Detect if this is overlay (currentFile is the same as overlayFile)
        const overlayDetected = overlayFile && currentFile.name === overlayFile.name;

        // Detect if this is a segmentation file (doar dacă nu e overlay)
        const segmentationDetected = !overlayDetected && isSegmentationFile(currentFile.name, typedData);

        setIsOverlay(overlayDetected);
        setIsSegmentation(segmentationDetected);

        console.log('File type detected:', {
          isOverlay: overlayDetected,
          isSegmentation: segmentationDetected,
          filename: currentFile.name
        });

        setNiftiHeader(header);
        setNiftiImage(image);

        const dims = header.dims || [];
        setMaxSlices({
          axial: dims[3] || 1,
          sagittal: dims[1] || 1,
          coronal: dims[2] || 1,
        });

        const windowing = calculateAndSetChartData(header, image, setHistogramData, setProfileCurveData);
        setWindowCenter(windowing.windowCenter);
        setWindowWidth(windowing.windowWidth);
        setIntensityRange({ min: windowing.min, max: windowing.max });

        console.log('Optimal windowing:', windowing);

        setMetadata({
          'File Name': currentFile.name,
          'File Size': `${(currentFile.size / 1024 / 1024).toFixed(2)} MB`,
          'Description': header.description || 'N/A',
          'Dimensions': `${dims[1]} × ${dims[2]} × ${dims[3]}`,
          'Voxel Size': `${header.pixDims?.[1]?.toFixed(2) || 'N/A'} × ${header.pixDims?.[2]?.toFixed(2) || 'N/A'} × ${header.pixDims?.[3]?.toFixed(2) || 'N/A'} mm`,
          'Data Type': getDataType(header.datatype || header.datatypeCode || 0),
          'Endianness': header.little_endian ? 'Little' : 'Big',
          'Intensity Range': `${windowing.min.toFixed(2)} - ${windowing.max.toFixed(2)}`,
          'Calibration Max': header.cal_max || 0,
          'Calibration Min': header.cal_min || 0,
          'Scaling Slope': header.scl_slope || 1,
          'Scaling Intercept': header.scl_inter || 0,
          'Slice Duration': header.slice_duration || 0,
          'Time Offset': header.toffset || 0,
          'Q-form Code': header.qform_code || 0,
          'S-form Code': header.sform_code || 0,
          'Intent Name': header.intent_name || 'N/A',
          'Is Segmentation': segmentationDetected ? 'Yes' : 'No',
          'Is Overlay': overlayDetected ? 'Yes' : 'No', // NOU
        });

      } catch (err) {
        console.error('Error loading or parsing NIfTI file:', err);
        setError(`Failed to load or parse the NIfTI file: ${err instanceof Error ? err.message : 'Unknown error'}`);
      } finally {
        setLoading(false);
      }
    };

    loadNiftiFile();
  }, [currentFile, overlayFile, setMaxSlices, setHistogramData, setProfileCurveData, setMetadata, setWindowCenter, setWindowWidth, setIntensityRange]);

  useEffect(() => {
    if (!loading && !error && niftiHeader && niftiImage && canvasRef.current) {
      try {
        if (isOverlay) {
          // NOU: Pentru overlay, folosește desenare RGB specială
          console.log('Drawing overlay with RGB rendering');
          drawSliceWithOverlay({
            canvas: canvasRef.current,
            header: niftiHeader,
            image: niftiImage,
            slice,
            axis,
            sliceThickness,
          });
        } else if (isSegmentation) {
          // Pentru segmentare pură, folosește colorare custom
          console.log('Drawing segmentation with color mapping');
          drawSliceWithSegmentation({
            canvas: canvasRef.current,
            header: niftiHeader,
            image: niftiImage,
            slice,
            axis,
            sliceThickness,
            opacity: 0.8,
          });
        } else {
          // Pentru imagini normale (MRI original)
          console.log('Drawing normal MRI image');
          drawSlice({
            canvas: canvasRef.current,
            header: niftiHeader,
            image: niftiImage,
            slice,
            axis,
            brightness,
            contrast,
            windowCenter,
            windowWidth,
            sliceThickness,
            useWindowing,
          });
        }
      } catch (err) {
        console.error('Error drawing slice:', err);
        setError(`Failed to render slice: ${err instanceof Error ? err.message : 'Unknown error'}`);
      }
    }
  }, [slice, axis, loading, error, niftiHeader, niftiImage, brightness, contrast, windowCenter, windowWidth, sliceThickness, useWindowing, isSegmentation, isOverlay]);

  useEffect(() => {
    if (canvasRef.current) {
      setCanvasRef(canvasRef.current);
    }
    return () => setCanvasRef(null);
  }, [setCanvasRef]);

  const handleWheel = (e: React.WheelEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (e.deltaY < 0) {
      zoomIn();
    } else {
      zoomOut();
    }
  };

  const handleMouseDown = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.button !== 0) return;
    e.preventDefault();
    setIsPanning(true);
    setPanStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!isPanning) return;
    e.preventDefault();
    setPan({
        x: e.clientX - panStart.x,
        y: e.clientY - panStart.y,
    });
  };

  const handleMouseUp = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!isPanning) return;
    e.preventDefault();
    setIsPanning(false);
  };

  const handleMouseLeave = (e: React.MouseEvent<HTMLDivElement>) => {
    if (isPanning) {
      handleMouseUp(e);
    }
  };

  const renderContent = () => {
    if (loading) {
      return (
        <div className="flex flex-col items-center justify-center h-full p-4">
          <Skeleton className="w-full h-full" />
          <p className="text-sm text-muted-foreground mt-2">Loading MRI data...</p>
        </div>
      );
    }

    if (error) {
      return (
        <div className="flex flex-col items-center justify-center h-full text-destructive p-4">
          <AlertTriangle className="w-12 h-12 mb-4" />
          <p className="text-lg font-semibold text-center">Error Loading MRI</p>
          <p className="text-center text-sm">{error}</p>
        </div>
      );
    }

    if (niftiHeader && niftiImage) {
       const maxSlices = useResultsViewerStore.getState().maxSlices;
       return (
        <>
            <canvas
                ref={canvasRef}
                className="transition-transform duration-200"
                style={{
                    transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
                    imageRendering: 'pixelated'
                }}
            />
            <div className="absolute top-2 left-2 bg-black/80 text-white text-xs px-2 py-1 rounded backdrop-blur">
                Slice: {Math.round(slice) + 1} / {maxSlices[axis]}
            </div>
            <div className="absolute top-2 right-2 bg-black/80 text-white text-xs px-2 py-1 rounded capitalize backdrop-blur">
                {axis} View
            </div>
            <div className="absolute bottom-2 left-2 bg-black/80 text-white text-xs px-2 py-1 rounded backdrop-blur">
                {/* MODIFICAT: Text diferit pentru overlay */}
                {isOverlay ? (
                  'T1N + Segmentation Overlay'
                ) : isSegmentation ? (
                  'Segmentation View'
                ) : useWindowing ? (
                  `WC: ${windowCenter.toFixed(0)} WW: ${windowWidth.toFixed(0)}`
                ) : (
                  `B: ${brightness}% C: ${contrast}%`
                )}
            </div>
            <div className="absolute bottom-2 right-2 bg-black/80 text-white text-xs px-2 py-1 rounded backdrop-blur">
                Zoom: {(zoom * 100).toFixed(0)}%
            </div>
        </>
       );
    }

    return null;
  };

  return (
    <div className="w-full h-full flex flex-col items-center justify-center p-4 gap-4 bg-black rounded-lg">
      <div
        className={cn(
            "relative w-full max-w-[512px] aspect-square overflow-hidden rounded-md border border-border bg-black flex items-center justify-center",
             isPanning ? 'cursor-grabbing' : 'cursor-grab'
        )}
        onWheel={handleWheel}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseLeave}
      >
        {renderContent()}
      </div>
      <ViewerToolbar />
    </div>
  );
}