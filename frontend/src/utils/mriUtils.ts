import * as nifti from 'nifti-reader-js';
import type { ViewAxis } from '@/types/view-types';
import type { HistogramData, ProfileCurveData } from '@/types/analysis-types';

type DrawSliceParams = {
  canvas: HTMLCanvasElement;
  header: nifti.NIFTI1 | nifti.NIFTI2;
  image: ArrayBuffer;
  slice: number;
  axis: ViewAxis;
  brightness: number;
  contrast: number;
  sliceThickness: number;
};

export const getDataType = (code: number) => {
  switch (code) {
    case nifti.NIFTI1.TYPE_UINT8:
      return '8-bit unsigned integer';
    case nifti.NIFTI1.TYPE_INT16:
      return '16-bit signed integer';
    case nifti.NIFTI1.TYPE_INT32:
      return '32-bit signed integer';
    case nifti.NIFTI1.TYPE_FLOAT32:
      return '32-bit float';
    case nifti.NIFTI1.TYPE_FLOAT64:
      return '64-bit float';
    case nifti.NIFTI1.TYPE_INT8:
      return '8-bit signed integer';
    case nifti.NIFTI1.TYPE_UINT16:
      return '16-bit unsigned integer';
    case nifti.NIFTI1.TYPE_UINT32:
      return '32-bit unsigned integer';
    default:
      return 'Unknown';
  }
};


export const drawSlice = ({
  canvas,
  header,
  image,
  slice,
  axis,
  brightness,
  contrast,
  sliceThickness,
}: DrawSliceParams) => {
  const context = canvas.getContext('2d');
  if (!context) return;

  const dims = header.dims;
  const xDim = dims[1];
  const yDim = dims[2];
  const zDim = dims[3];

  let sliceData: Uint8ClampedArray;
  let sliceWidth: number;
  let sliceHeight: number;

  const typedData = new Float32Array(image);

  let i, j;

  const getVoxel = (x: number, y: number, z: number) => {
    return typedData[z * (xDim * yDim) + y * xDim + x];
  };

  const currentSlice = Math.round(slice);

  if (axis === 'axial') {
    sliceWidth = xDim;
    sliceHeight = yDim;
    sliceData = new Uint8ClampedArray(sliceWidth * sliceHeight * 4);
    
    for (j = 0; j < sliceHeight; j++) {
      for (i = 0; i < sliceWidth; i++) {
        let avgValue = 0;
        const halfThickness = Math.floor(sliceThickness / 2);
        for(let k = -halfThickness; k <= halfThickness; k++) {
            const sliceIndex = Math.min(Math.max(currentSlice + k, 0), zDim - 1);
            avgValue += getVoxel(i, j, sliceIndex);
        }
        const pixelValue = avgValue / sliceThickness;
        const index = (j * sliceWidth + i) * 4;
        sliceData[index] = pixelValue;
        sliceData[index + 1] = pixelValue;
        sliceData[index + 2] = pixelValue;
        sliceData[index + 3] = 255;
      }
    }
  } else if (axis === 'coronal') {
    sliceWidth = xDim;
    sliceHeight = zDim;
    sliceData = new Uint8ClampedArray(sliceWidth * sliceHeight * 4);

    for (j = 0; j < sliceHeight; j++) {
      for (i = 0; i < sliceWidth; i++) {
         let avgValue = 0;
        const halfThickness = Math.floor(sliceThickness / 2);
        for(let k = -halfThickness; k <= halfThickness; k++) {
            const sliceIndex = Math.min(Math.max(currentSlice + k, 0), yDim - 1);
            avgValue += getVoxel(i, sliceIndex, j);
        }
        const pixelValue = avgValue / sliceThickness;
        const index = (j * sliceWidth + i) * 4;
        sliceData[index] = pixelValue;
        sliceData[index + 1] = pixelValue;
        sliceData[index + 2] = pixelValue;
        sliceData[index + 3] = 255;
      }
    }
  } else { // sagittal
    sliceWidth = yDim;
    sliceHeight = zDim;
    sliceData = new Uint8ClampedArray(sliceWidth * sliceHeight * 4);

    for (j = 0; j < sliceHeight; j++) {
      for (i = 0; i < sliceWidth; i++) {
         let avgValue = 0;
        const halfThickness = Math.floor(sliceThickness / 2);
        for(let k = -halfThickness; k <= halfThickness; k++) {
            const sliceIndex = Math.min(Math.max(currentSlice + k, 0), xDim - 1);
            avgValue += getVoxel(sliceIndex, i, j);
        }
        const pixelValue = avgValue / sliceThickness;
        const index = (j * sliceWidth + i) * 4;
        sliceData[index] = pixelValue;
        sliceData[index + 1] = pixelValue;
        sliceData[index + 2] = pixelValue;
        sliceData[index + 3] = 255;
      }
    }
  }

  canvas.width = sliceWidth;
  canvas.height = sliceHeight;
  
  context.filter = `brightness(${brightness}%) contrast(${contrast}%)`;

  const imageData = new ImageData(sliceData, sliceWidth, sliceHeight);
  context.putImageData(imageData, 0, 0);
};

export const calculateAndSetChartData = (
  header: nifti.NIFTI1 | nifti.NIFTI2,
  image: ArrayBuffer,
  setHistogramData: (data: HistogramData[]) => void,
  setProfileCurveData: (data: ProfileCurveData[]) => void
) => {
    const typedData = new Float32Array(image);
    let min = typedData[0];
    let max = typedData[0];
    for (let i = 1; i < typedData.length; i++) {
        if (typedData[i] < min) min = typedData[i];
        if (typedData[i] > max) max = typedData[i];
    }
    
    // Histogram
    const numBins = 100;
    const binSize = (max - min) / numBins;
    const bins = new Array(numBins).fill(0);

    for (let i = 0; i < typedData.length; i++) {
        const binIndex = Math.floor((typedData[i] - min) / binSize);
        if(binIndex >= 0 && binIndex < numBins) {
            bins[binIndex]++;
        }
    }
    const histogramData = bins.map((count, i) => ({
        value: Math.round(((i * binSize + min) / max) * 100),
        count,
    }));
    setHistogramData(histogramData);


    // Profile Curve (center line on axial view)
    const dims = header.dims;
    const xDim = dims[1];
    const yDim = dims[2];
    const zDim = dims[3];
    const centerZ = Math.floor(zDim / 2);
    const centerY = Math.floor(yDim / 2);
    
    const profileCurveData = [];
    for (let i = 0; i < xDim; i++) {
        const voxelIndex = centerZ * (xDim * yDim) + centerY * xDim + i;
        profileCurveData.push({
            position: i,
            intensity: typedData[voxelIndex],
        });
    }
    setProfileCurveData(profileCurveData);
};
