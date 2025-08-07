'use client';

import React, { useState, useEffect, useRef } from 'react';
import * as nifti from 'nifti-reader-js';
import pako from 'pako';
import { useMriStore } from '@/utils/stores/mri-store';
import { useViewStore } from '@/utils/stores/view-store';
import { useAnalysisStore } from '@/utils/stores/analysis-store';
import { Skeleton } from '@/components/ui/skeleton';
import { AlertTriangle } from 'lucide-react';
import { ViewerToolbar } from './viewer-toolbar';
import { cn } from '@/utils/cn';
import { getDataType, calculateAndSetChartData, drawSlice } from '@/utils/mriUtils';

export function MriViewer() {
  const file = useMriStore((state) => state.file);
  const { slice, zoom, axis, pan, setPan, setMaxSlices, zoomIn, zoomOut } = useViewStore();
  const { 
    brightness, 
    contrast, 
    sliceThickness,
    setHistogramData, 
    setProfileCurveData, 
    setMetadata 
  } = useAnalysisStore();

  const [niftiHeader, setNiftiHeader] = useState<nifti.NIFTI1 | nifti.NIFTI2 | null>(null);
  const [niftiImage, setNiftiImage] = useState<ArrayBuffer | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  
  const [isPanning, setIsPanning] = useState(false);
  const [panStart, setPanStart] = useState({ x: 0, y: 0 });

  useEffect(() => {
    const loadNiftiFile = async () => {
      setLoading(true);
      setError(null);
      if (!file) {
        setError('No MRI file found. Please go back and upload a file first.');
        setLoading(false);
        return;
      }

      try {
        const fileBuffer = await file.arrayBuffer();
        let niftiBuffer = fileBuffer;

        if (nifti.isCompressed(niftiBuffer)) {
          niftiBuffer = pako.inflate(new Uint8Array(niftiBuffer)).buffer;
        }

        if (nifti.isNIFTI(niftiBuffer)) {
          const header = nifti.readHeader(niftiBuffer);
          const image = nifti.readImage(header, niftiBuffer);
          setNiftiHeader(header);
          setNiftiImage(image);

          setMaxSlices({
            axial: header.dims[3],
            sagittal: header.dims[1],
            coronal: header.dims[2],
          });
          
          calculateAndSetChartData(header, image, setHistogramData, setProfileCurveData);
          setMetadata({
            'Description': header.description,
            'Dimensions': header.dims,
            'Voxel Size': header.pixDims,
            'Data Type': getDataType(header.datatype),
            'Endianness': header.little_endian ? 'Little' : 'Big',
            'Calibration Max': header.cal_max,
            'Calibration Min': header.cal_min,
            'Slice Duration': header.slice_duration,
            'Time Offset': header.toffset,
            'Q-form Code': header.qform_code,
            'S-form Code': header.sform_code,
            'Quaternion B': header.quatern_b,
            'Quaternion C': header.quatern_c,
            'Quaternion D': header.quatern_d,
            'Q-offset X': header.qoffset_x,
            'Q-offset Y': header.qoffset_y,
            'Q-offset Z': header.qoffset_z,
            'S-Row X': header.srow_x,
            'S-Row Y': header.srow_y,
            'S-Row Z': header.srow_z,
            'Intent Name': header.intent_name,
          });

        } else {
          setError('The provided file is not a valid NIfTI file.');
        }
      } catch (err) {
        console.error('Error loading or parsing NIfTI file:', err);
        setError('Failed to load or parse the NIfTI file.');
      } finally {
        setLoading(false);
      }
    };

    loadNiftiFile();
  }, [file, setMaxSlices, setHistogramData, setProfileCurveData, setMetadata]);
  
  
  useEffect(() => {
    if (!loading && !error && niftiHeader && niftiImage && canvasRef.current) {
      drawSlice({
        canvas: canvasRef.current,
        header: niftiHeader,
        image: niftiImage,
        slice,
        axis,
        brightness,
        contrast,
        sliceThickness,
      });
    }
  }, [slice, axis, loading, error, niftiHeader, niftiImage, brightness, contrast, sliceThickness]);

  const handleWheel = (e: React.WheelEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (e.deltaY < 0) {
      zoomIn();
    } else {
      zoomOut();
    }
  };
  
  const handleMouseDown = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.button !== 0) return; // Only pan on left-click
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
      return <Skeleton className="w-full h-full" />;
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
    
    if (niftiHeader) {
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
            <div className="absolute top-2 left-2 bg-black/50 text-white text-xs px-2 py-1 rounded">
                Slice: {Math.round(slice) + 1} / {useViewStore.getState().maxSlices[axis]}
            </div>
             <div className="absolute top-2 right-2 bg-black/50 text-white text-xs px-2 py-1 rounded capitalize">
                {axis} View
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
