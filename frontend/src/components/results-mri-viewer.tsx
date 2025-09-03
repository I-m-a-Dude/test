import React, { useState, useEffect, useRef } from 'react';
import * as nifti from 'nifti-reader-js';
import pako from 'pako';
import { useResultsViewerStore } from '@/utils/stores/results-viewer-store';
import { useAnalysisStore } from '@/utils/stores/analysis-store';
import { Skeleton } from '@/components/ui/skeleton';
import { AlertTriangle } from 'lucide-react';
import { ViewerToolbar } from './viewer-toolbar';
import { cn } from '@/utils/cn';
import { getDataType, calculateAndSetChartData, drawSlice, drawSliceWithOverlay } from '@/utils/mriUtils';

export function ResultsMriViewer() {
  const { currentFile, slice, zoom, axis, pan, setPan, setMaxSlices, zoomIn, zoomOut } = useResultsViewerStore();
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
  const [isOverlay, setIsOverlay] = useState(false);
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

        // Detectează doar overlay-ul
        const overlayDetected = currentFile.name.toLowerCase().includes('-overlay') ||
                               currentFile.name.toLowerCase().includes('_overlay');

        setIsOverlay(overlayDetected);

        console.log('File type detection:', {
          isOverlay: overlayDetected,
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

        // Pentru overlay RGB, setează windowing fix în loc să calculezi
        let windowing;
        if (overlayDetected) {
          // Pentru overlay RGB, folosește range-ul standard RGB [0-255]
          windowing = {
            windowCenter: 127.5,  // Mijlocul range-ului RGB
            windowWidth: 255,     // Width-ul complet RGB
            min: 0,
            max: 255
          };
          console.log('Using fixed RGB windowing for overlay:', windowing);
        } else {
          // Pentru date MRI normale, calculează windowing-ul normal
          windowing = calculateAndSetChartData(header, image, setHistogramData, setProfileCurveData);
          console.log('Calculated windowing for MRI data:', windowing);
        }

        setWindowCenter(windowing.windowCenter);
        setWindowWidth(windowing.windowWidth);
        setIntensityRange({ min: windowing.min, max: windowing.max });

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
          'File Type': overlayDetected ? 'Overlay (T1N + Segmentation)' : 'MRI Data',
        });

      } catch (err) {
        console.error('Error loading or parsing NIfTI file:', err);
        setError(`Failed to load or parse the NIfTI file: ${err instanceof Error ? err.message : 'Unknown error'}`);
      } finally {
        setLoading(false);
      }
    };

    loadNiftiFile();
  }, [currentFile, setMaxSlices, setHistogramData, setProfileCurveData, setMetadata, setWindowCenter, setWindowWidth, setIntensityRange]);

  useEffect(() => {
    if (!loading && !error && niftiHeader && niftiImage && canvasRef.current) {
      try {
        // Folosește funcția corectă în funcție de tipul fișierului
        if (isOverlay) {
          // Pentru overlay: desenează direct cu culorile existente
          drawSliceWithOverlay({
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
        } else {
          // Pentru date MRI normale
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
  }, [slice, axis, loading, error, niftiHeader, niftiImage, brightness, contrast, windowCenter, windowWidth, sliceThickness, useWindowing, isOverlay]);

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
                {isOverlay ? (
                  'AI Overlay (T1N + Segmentation)'
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