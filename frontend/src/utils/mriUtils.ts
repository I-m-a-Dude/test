import * as nifti from 'nifti-reader-js';
import type { ViewAxis } from '@/types/view-types';
import type { HistogramData, ProfileCurveData } from '@/types/analysis-types';

type DrawSliceParams = {
  canvas: HTMLCanvasElement;
  header: nifti.NIFTI1 | nifti.NIFTI2;
  image: ArrayBuffer;
  slice: number;
  axis: ViewAxis;
  brightness?: number;
  contrast?: number;
  windowCenter?: number;
  windowWidth?: number;
  sliceThickness: number;
  useWindowing?: boolean;
};

// Color mapping for segmentation classes
const SEGMENTATION_COLORS = {
  0: [0, 0, 0],       // Background - black
  1: [0, 100, 255],   // NETC - blue
  2: [255, 255, 0],   // SNFH - yellow
  3: [255, 0, 0],     // ET - red
  4: [128, 0, 128],   // RC - purple
};

export const getDataType = (code: number): string => {
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

// Calculate optimal window center and width for brain MRI
export const calculateOptimalWindowing = (typedData: Float32Array): { windowCenter: number; windowWidth: number; min: number; max: number } => {
  // Remove zero values (background) for better statistics
  const nonZeroValues = Array.from(typedData).filter(val => val > 0);

  if (nonZeroValues.length === 0) {
    return { windowCenter: 0, windowWidth: 1, min: 0, max: 1 };
  }

  nonZeroValues.sort((a, b) => a - b);

  const min = nonZeroValues[0];
  const max = nonZeroValues[nonZeroValues.length - 1];

  // Calculate percentiles for better windowing
  const p1 = nonZeroValues[Math.floor(nonZeroValues.length * 0.01)];
  const p99 = nonZeroValues[Math.floor(nonZeroValues.length * 0.99)];

  // For brain MRI, use percentile-based windowing
  const windowCenter = (p1 + p99) / 2;
  const windowWidth = p99 - p1;

  return { windowCenter, windowWidth, min, max };
};


export const isSegmentationFile = (filename: string, typedData: Float32Array): boolean => {
  // FIXED: Overlay-urile NU sunt segmentări - au deja culorile aplicate
  if (filename.toLowerCase().includes('-overlay') || filename.toLowerCase().includes('_overlay')) {
    return false; // Overlay-urile nu sunt segmentări pure
  }

  const filenameIndicators = [
    'seg', 'segmentation', '_seg', '-seg',
    'mask', '_mask', '-mask'
  ];

  const lowerFilename = filename.toLowerCase();
  const hasSegKeyword = filenameIndicators.some(indicator =>
    lowerFilename.includes(indicator)
  );

  if (hasSegKeyword) return true;

  // Check data characteristics - segmentation usually has small integer values
  const uniqueValues = new Set();
  const sampleSize = Math.min(1000, typedData.length);

  for (let i = 0; i < sampleSize; i += 10) {
    const value = Math.round(typedData[i]);
    uniqueValues.add(value);

    // If we find too many unique values or values outside expected range, not segmentation
    if (uniqueValues.size > 10 || value > 10 || value < 0) {
      return false;
    }
  }

  // If we have only a few integer values (typical for segmentation), likely segmentation
  return uniqueValues.size <= 5;
};

// Apply windowing/leveling to convert intensity to display value
const applyWindowing = (intensity: number, windowCenter: number, windowWidth: number): number => {
  const minWindow = windowCenter - windowWidth / 2;
  const maxWindow = windowCenter + windowWidth / 2;

  if (intensity <= minWindow) {
    return 0;
  } else if (intensity >= maxWindow) {
    return 255;
  } else {
    return Math.round(((intensity - minWindow) / windowWidth) * 255);
  }
};

// Apply simple brightness/contrast adjustments
const applyBrightnessContrast = (intensity: number, brightness: number, contrast: number, minVal: number, maxVal: number): number => {
  // Normalize intensity to 0-255 range first
  const normalizedIntensity = ((intensity - minVal) / (maxVal - minVal)) * 255;

  // Apply brightness (shift)
  let adjustedValue = normalizedIntensity * (brightness / 100);

  // Apply contrast (scale around midpoint)
  const midpoint = 127.5;
  adjustedValue = midpoint + (adjustedValue - midpoint) * (contrast / 100);

  // Clamp to 0-255
  return Math.max(0, Math.min(255, Math.round(adjustedValue)));
};

export const drawSlice = ({
  canvas,
  header,
  image,
  slice,
  axis,
  brightness = 100,
  contrast = 100,
  windowCenter = 0,
  windowWidth = 1,
  sliceThickness,
  useWindowing = false,
}: DrawSliceParams): void => {
  const context = canvas.getContext('2d');
  if (!context) {
    throw new Error('Could not get canvas 2D context');
  }

  const dims = header.dims;
  if (!dims || dims.length < 4) {
    throw new Error('Invalid header dimensions');
  }

  const xDim = dims[1];
  const yDim = dims[2];
  const zDim = dims[3];

  if (xDim <= 0 || yDim <= 0 || zDim <= 0) {
    throw new Error('Invalid dimension values');
  }

  let sliceData: Uint8ClampedArray;
  let sliceWidth: number;
  let sliceHeight: number;

  // Convert to appropriate typed array based on datatype
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

  // Apply scaling if present
  const sclSlope = header.scl_slope || 1;
  const sclInter = header.scl_inter || 0;

  if (sclSlope !== 1 || sclInter !== 0) {
    for (let i = 0; i < typedData.length; i++) {
      typedData[i] = typedData[i] * sclSlope + sclInter;
    }
  }

  // Calculate min/max for simple brightness/contrast mode
  let dataMin = typedData[0];
  let dataMax = typedData[0];
  if (!useWindowing) {
    for (let i = 1; i < typedData.length; i++) {
      if (typedData[i] < dataMin) dataMin = typedData[i];
      if (typedData[i] > dataMax) dataMax = typedData[i];
    }
  }

  const getVoxel = (x: number, y: number, z: number): number => {
    if (x < 0 || x >= xDim || y < 0 || y >= yDim || z < 0 || z >= zDim) {
      return 0;
    }
    const index = z * (xDim * yDim) + y * xDim + x;
    return typedData[index] || 0;
  };

  const currentSlice = Math.round(slice);

  try {
    if (axis === 'axial') {
      sliceWidth = xDim;
      sliceHeight = yDim;
      sliceData = new Uint8ClampedArray(sliceWidth * sliceHeight * 4);

      for (let j = 0; j < sliceHeight; j++) {
        for (let i = 0; i < sliceWidth; i++) {
          let avgValue = 0;
          const halfThickness = Math.floor(sliceThickness / 2);
          let samples = 0;

          for (let k = -halfThickness; k <= halfThickness; k++) {
            const sliceIndex = Math.min(Math.max(currentSlice + k, 0), zDim - 1);
            avgValue += getVoxel(i, j, sliceIndex);
            samples++;
          }

          const intensity = avgValue / samples;
          let pixelValue: number;

          if (useWindowing) {
            pixelValue = applyWindowing(intensity, windowCenter, windowWidth);
          } else {
            pixelValue = applyBrightnessContrast(intensity, brightness, contrast, dataMin, dataMax);
          }

          const index = (j * sliceWidth + i) * 4;
          sliceData[index] = pixelValue;     // R
          sliceData[index + 1] = pixelValue; // G
          sliceData[index + 2] = pixelValue; // B
          sliceData[index + 3] = 255;       // A
        }
      }
    } else if (axis === 'coronal') {
      sliceWidth = xDim;
      sliceHeight = zDim;
      sliceData = new Uint8ClampedArray(sliceWidth * sliceHeight * 4);

      for (let j = 0; j < sliceHeight; j++) {
        for (let i = 0; i < sliceWidth; i++) {
          let avgValue = 0;
          const halfThickness = Math.floor(sliceThickness / 2);
          let samples = 0;

          for (let k = -halfThickness; k <= halfThickness; k++) {
            const sliceIndex = Math.min(Math.max(currentSlice + k, 0), yDim - 1);
            avgValue += getVoxel(i, sliceIndex, zDim - 1 - j); // Flip Z for proper orientation
            samples++;
          }

          const intensity = avgValue / samples;
          let pixelValue: number;

          if (useWindowing) {
            pixelValue = applyWindowing(intensity, windowCenter, windowWidth);
          } else {
            pixelValue = applyBrightnessContrast(intensity, brightness, contrast, dataMin, dataMax);
          }

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

      for (let j = 0; j < sliceHeight; j++) {
        for (let i = 0; i < sliceWidth; i++) {
          let avgValue = 0;
          const halfThickness = Math.floor(sliceThickness / 2);
          let samples = 0;

          for (let k = -halfThickness; k <= halfThickness; k++) {
            const sliceIndex = Math.min(Math.max(currentSlice + k, 0), xDim - 1);
            avgValue += getVoxel(sliceIndex, i, zDim - 1 - j); // Flip Z for proper orientation
            samples++;
          }

          const intensity = avgValue / samples;
          let pixelValue: number;

          if (useWindowing) {
            pixelValue = applyWindowing(intensity, windowCenter, windowWidth);
          } else {
            pixelValue = applyBrightnessContrast(intensity, brightness, contrast, dataMin, dataMax);
          }

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

    // Don't apply additional filtering
    context.filter = 'none';
    context.imageSmoothingEnabled = false;

    const imageData = new ImageData(sliceData, sliceWidth, sliceHeight);
    context.putImageData(imageData, 0, 0);
  } catch (error) {
    console.error('Error in drawSlice:', error);
    throw new Error('Failed to draw slice');
  }
};

// Draw slice with segmentation coloring
export const drawSliceWithSegmentation = ({
  canvas,
  header,
  image,
  slice,
  axis,
  sliceThickness = 1,
  opacity = 0.7,
}: {
  canvas: HTMLCanvasElement;
  header: nifti.NIFTI1 | nifti.NIFTI2;
  image: ArrayBuffer;
  slice: number;
  axis: ViewAxis;
  sliceThickness?: number;
  opacity?: number;
}): void => {
  const context = canvas.getContext('2d');
  if (!context) {
    throw new Error('Could not get canvas 2D context');
  }

  const dims = header.dims;
  if (!dims || dims.length < 4) {
    throw new Error('Invalid header dimensions');
  }

  const xDim = dims[1];
  const yDim = dims[2];
  const zDim = dims[3];

  if (xDim <= 0 || yDim <= 0 || zDim <= 0) {
    throw new Error('Invalid dimension values');
  }

  let sliceData: Uint8ClampedArray;
  let sliceWidth: number;
  let sliceHeight: number;

  // Convert to appropriate typed array
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

  // Apply scaling if present
  const sclSlope = header.scl_slope || 1;
  const sclInter = header.scl_inter || 0;

  if (sclSlope !== 1 || sclInter !== 0) {
    for (let i = 0; i < typedData.length; i++) {
      typedData[i] = typedData[i] * sclSlope + sclInter;
    }
  }

  const getVoxel = (x: number, y: number, z: number): number => {
    if (x < 0 || x >= xDim || y < 0 || y >= yDim || z < 0 || z >= zDim) {
      return 0;
    }
    const index = z * (xDim * yDim) + y * xDim + x;
    return Math.round(typedData[index] || 0); // Round to get integer class values
  };

  const currentSlice = Math.round(slice);

  try {
    if (axis === 'axial') {
      sliceWidth = xDim;
      sliceHeight = yDim;
      sliceData = new Uint8ClampedArray(sliceWidth * sliceHeight * 4);

      for (let j = 0; j < sliceHeight; j++) {
        for (let i = 0; i < sliceWidth; i++) {
          let avgValue = 0;
          const halfThickness = Math.floor(sliceThickness / 2);
          let samples = 0;

          for (let k = -halfThickness; k <= halfThickness; k++) {
            const sliceIndex = Math.min(Math.max(currentSlice + k, 0), zDim - 1);
            avgValue += getVoxel(i, j, sliceIndex);
            samples++;
          }

          const classValue = Math.round(avgValue / samples);
          const color = SEGMENTATION_COLORS[classValue as keyof typeof SEGMENTATION_COLORS] || [128, 128, 128];

          const index = (j * sliceWidth + i) * 4;

          if (classValue === 0) {
            // Background - transparent black
            sliceData[index] = 0;     // R
            sliceData[index + 1] = 0; // G
            sliceData[index + 2] = 0; // B
            sliceData[index + 3] = 0; // A (transparent)
          } else {
            // Colored segmentation with opacity
            sliceData[index] = color[0];     // R
            sliceData[index + 1] = color[1]; // G
            sliceData[index + 2] = color[2]; // B
            sliceData[index + 3] = Math.round(255 * opacity); // A
          }
        }
      }
    } else if (axis === 'coronal') {
      sliceWidth = xDim;
      sliceHeight = zDim;
      sliceData = new Uint8ClampedArray(sliceWidth * sliceHeight * 4);

      for (let j = 0; j < sliceHeight; j++) {
        for (let i = 0; i < sliceWidth; i++) {
          let avgValue = 0;
          const halfThickness = Math.floor(sliceThickness / 2);
          let samples = 0;

          for (let k = -halfThickness; k <= halfThickness; k++) {
            const sliceIndex = Math.min(Math.max(currentSlice + k, 0), yDim - 1);
            avgValue += getVoxel(i, sliceIndex, zDim - 1 - j);
            samples++;
          }

          const classValue = Math.round(avgValue / samples);
          const color = SEGMENTATION_COLORS[classValue as keyof typeof SEGMENTATION_COLORS] || [128, 128, 128];

          const index = (j * sliceWidth + i) * 4;

          if (classValue === 0) {
            sliceData[index] = 0;
            sliceData[index + 1] = 0;
            sliceData[index + 2] = 0;
            sliceData[index + 3] = 0;
          } else {
            sliceData[index] = color[0];
            sliceData[index + 1] = color[1];
            sliceData[index + 2] = color[2];
            sliceData[index + 3] = Math.round(255 * opacity);
          }
        }
      }
    } else { // sagittal
      sliceWidth = yDim;
      sliceHeight = zDim;
      sliceData = new Uint8ClampedArray(sliceWidth * sliceHeight * 4);

      for (let j = 0; j < sliceHeight; j++) {
        for (let i = 0; i < sliceWidth; i++) {
          let avgValue = 0;
          const halfThickness = Math.floor(sliceThickness / 2);
          let samples = 0;

          for (let k = -halfThickness; k <= halfThickness; k++) {
            const sliceIndex = Math.min(Math.max(currentSlice + k, 0), xDim - 1);
            avgValue += getVoxel(sliceIndex, i, zDim - 1 - j);
            samples++;
          }

          const classValue = Math.round(avgValue / samples);
          const color = SEGMENTATION_COLORS[classValue as keyof typeof SEGMENTATION_COLORS] || [128, 128, 128];

          const index = (j * sliceWidth + i) * 4;

          if (classValue === 0) {
            sliceData[index] = 0;
            sliceData[index + 1] = 0;
            sliceData[index + 2] = 0;
            sliceData[index + 3] = 0;
          } else {
            sliceData[index] = color[0];
            sliceData[index + 1] = color[1];
            sliceData[index + 2] = color[2];
            sliceData[index + 3] = Math.round(255 * opacity);
          }
        }
      }
    }

    canvas.width = sliceWidth;
    canvas.height = sliceHeight;

    context.filter = 'none';
    context.imageSmoothingEnabled = false;

    const imageData = new ImageData(sliceData, sliceWidth, sliceHeight);
    context.putImageData(imageData, 0, 0);
  } catch (error) {
    console.error('Error in drawSliceWithSegmentation:', error);
    throw new Error('Failed to draw segmentation slice');
  }
};

// Înlocuiește funcția drawSliceWithOverlay în frontend/src/utils/mriUtils.ts

export const drawSliceWithOverlay = ({
  canvas,
  header,
  image,
  slice,
  axis,
  brightness = 100,
  contrast = 100,
  windowCenter = 0,
  windowWidth = 1,
  sliceThickness = 1,
  useWindowing = false,
}: DrawSliceParams): void => {
  const context = canvas.getContext('2d');
  if (!context) {
    throw new Error('Could not get canvas 2D context');
  }

  const dims = header.dims;
  if (!dims || dims.length < 4) {
    throw new Error('Invalid header dimensions');
  }

  const xDim = dims[1];
  const yDim = dims[2];
  const zDim = dims[3];

  // DEBUG: Log informații despre dimensiuni
  console.log('[OVERLAY DEBUG] Dimensions:', {
    dims: dims,
    xDim, yDim, zDim,
    imageByteLength: image.byteLength,
    expectedSize: xDim * yDim * zDim * 3, // Pentru RGB
    slice, axis
  });

  // FIXED: Verifică mai atent formatul RGB
  const isRGBFormat = dims.length >= 5 && dims[4] === 3;
  const hasRGBData = image.byteLength === (xDim * yDim * zDim * 3);

  console.log('[OVERLAY DEBUG] Format detection:', {
    isRGBFormat,
    hasRGBData,
    bytesPerVoxel: image.byteLength / (xDim * yDim * zDim)
  });

  let typedData: Uint8Array;
  typedData = new Uint8Array(image);

  const getVoxelRGB = (x: number, y: number, z: number): [number, number, number] => {
    if (x < 0 || x >= xDim || y < 0 || y >= yDim || z < 0 || z >= zDim) {
      return [0, 0, 0];
    }

    if (hasRGBData) {
      // FIXED: Format RGB corect - (x, y, z, channel)
      const baseIndex = ((z * yDim + y) * xDim + x) * 3;
      return [
        typedData[baseIndex] || 0,     // R
        typedData[baseIndex + 1] || 0, // G
        typedData[baseIndex + 2] || 0  // B
      ];
    } else {
      // FIXED: Fallback pentru grayscale
      const index = z * (xDim * yDim) + y * xDim + x;
      const value = typedData[index] || 0;

      // Interpretează ca culori de overlay direct
      return [value, value, value]; // Grayscale
    }
  };

  let sliceData: Uint8ClampedArray;
  let sliceWidth: number;
  let sliceHeight: number;
  const currentSlice = Math.round(slice);

  // FIXED: Calculează dimensiunile corecte pentru fiecare axă
  if (axis === 'axial') {
    sliceWidth = xDim;
    sliceHeight = yDim;
  } else if (axis === 'coronal') {
    sliceWidth = xDim;
    sliceHeight = zDim;
  } else { // sagittal
    sliceWidth = yDim;
    sliceHeight = zDim;
  }

  // DEBUG: Log dimensiuni slice
  console.log('[OVERLAY DEBUG] Slice dimensions:', {
    axis, sliceWidth, sliceHeight, currentSlice
  });

  sliceData = new Uint8ClampedArray(sliceWidth * sliceHeight * 4);

  try {
    if (axis === 'axial') {
      for (let j = 0; j < sliceHeight; j++) {
        for (let i = 0; i < sliceWidth; i++) {
          let avgR = 0, avgG = 0, avgB = 0;
          const halfThickness = Math.floor(sliceThickness / 2);
          let samples = 0;

          for (let k = -halfThickness; k <= halfThickness; k++) {
            const sliceIndex = Math.min(Math.max(currentSlice + k, 0), zDim - 1);
            const [r, g, b] = getVoxelRGB(i, j, sliceIndex);
            avgR += r;
            avgG += g;
            avgB += b;
            samples++;
          }

          const finalR = avgR / samples;
          const finalG = avgG / samples;
          const finalB = avgB / samples;

          // FIXED: Pentru overlay RGB, aplică ajustări mai simple
          let adjustedR, adjustedG, adjustedB;

          // Pentru overlay RGB, valorile sunt deja în range 0-255, aplică doar brightness/contrast simplu
          if (hasRGBData) {
            // Ajustări simple pentru RGB overlay
            const brightnessFactor = brightness / 100;
            const contrastFactor = contrast / 100;

            adjustedR = Math.max(0, Math.min(255, (finalR * brightnessFactor - 127.5) * contrastFactor + 127.5));
            adjustedG = Math.max(0, Math.min(255, (finalG * brightnessFactor - 127.5) * contrastFactor + 127.5));
            adjustedB = Math.max(0, Math.min(255, (finalB * brightnessFactor - 127.5) * contrastFactor + 127.5));
          } else {
            // Pentru date normale, folosește windowing/brightness obișnuit
            if (useWindowing) {
              adjustedR = applyWindowing(finalR, windowCenter, windowWidth);
              adjustedG = applyWindowing(finalG, windowCenter, windowWidth);
              adjustedB = applyWindowing(finalB, windowCenter, windowWidth);
            } else {
              adjustedR = applyBrightnessContrast(finalR, brightness, contrast, 0, 255);
              adjustedG = applyBrightnessContrast(finalG, brightness, contrast, 0, 255);
              adjustedB = applyBrightnessContrast(finalB, brightness, contrast, 0, 255);
            }
          }

          const index = (j * sliceWidth + i) * 4;
          sliceData[index] = adjustedR;     // R
          sliceData[index + 1] = adjustedG; // G
          sliceData[index + 2] = adjustedB; // B
          sliceData[index + 3] = 255;      // A
        }
      }
    } else if (axis === 'coronal') {
      for (let j = 0; j < sliceHeight; j++) {
        for (let i = 0; i < sliceWidth; i++) {
          let avgR = 0, avgG = 0, avgB = 0;
          const halfThickness = Math.floor(sliceThickness / 2);
          let samples = 0;

          for (let k = -halfThickness; k <= halfThickness; k++) {
            const sliceIndex = Math.min(Math.max(currentSlice + k, 0), yDim - 1);
            const [r, g, b] = getVoxelRGB(i, sliceIndex, zDim - 1 - j);
            avgR += r; avgG += g; avgB += b;
            samples++;
          }

          const finalR = avgR / samples;
          const finalG = avgG / samples;
          const finalB = avgB / samples;

          let adjustedR, adjustedG, adjustedB;

          if (hasRGBData) {
            // Ajustări simple pentru RGB overlay
            const brightnessFactor = brightness / 100;
            const contrastFactor = contrast / 100;

            adjustedR = Math.max(0, Math.min(255, (finalR * brightnessFactor - 127.5) * contrastFactor + 127.5));
            adjustedG = Math.max(0, Math.min(255, (finalG * brightnessFactor - 127.5) * contrastFactor + 127.5));
            adjustedB = Math.max(0, Math.min(255, (finalB * brightnessFactor - 127.5) * contrastFactor + 127.5));
          } else {
            if (useWindowing) {
              adjustedR = applyWindowing(finalR, windowCenter, windowWidth);
              adjustedG = applyWindowing(finalG, windowCenter, windowWidth);
              adjustedB = applyWindowing(finalB, windowCenter, windowWidth);
            } else {
              adjustedR = applyBrightnessContrast(finalR, brightness, contrast, 0, 255);
              adjustedG = applyBrightnessContrast(finalG, brightness, contrast, 0, 255);
              adjustedB = applyBrightnessContrast(finalB, brightness, contrast, 0, 255);
            }
          }

          const index = (j * sliceWidth + i) * 4;
          sliceData[index] = adjustedR;
          sliceData[index + 1] = adjustedG;
          sliceData[index + 2] = adjustedB;
          sliceData[index + 3] = 255;
        }
      }
    } else { // sagittal
      for (let j = 0; j < sliceHeight; j++) {
        for (let i = 0; i < sliceWidth; i++) {
          let avgR = 0, avgG = 0, avgB = 0;
          const halfThickness = Math.floor(sliceThickness / 2);
          let samples = 0;

          for (let k = -halfThickness; k <= halfThickness; k++) {
            const sliceIndex = Math.min(Math.max(currentSlice + k, 0), xDim - 1);
            const [r, g, b] = getVoxelRGB(sliceIndex, i, zDim - 1 - j);
            avgR += r; avgG += g; avgB += b;
            samples++;
          }

          const finalR = avgR / samples;
          const finalG = avgG / samples;
          const finalB = avgB / samples;

          let adjustedR, adjustedG, adjustedB;

          if (hasRGBData) {
            // Ajustări simple pentru RGB overlay
            const brightnessFactor = brightness / 100;
            const contrastFactor = contrast / 100;

            adjustedR = Math.max(0, Math.min(255, (finalR * brightnessFactor - 127.5) * contrastFactor + 127.5));
            adjustedG = Math.max(0, Math.min(255, (finalG * brightnessFactor - 127.5) * contrastFactor + 127.5));
            adjustedB = Math.max(0, Math.min(255, (finalB * brightnessFactor - 127.5) * contrastFactor + 127.5));
          } else {
            if (useWindowing) {
              adjustedR = applyWindowing(finalR, windowCenter, windowWidth);
              adjustedG = applyWindowing(finalG, windowCenter, windowWidth);
              adjustedB = applyWindowing(finalB, windowCenter, windowWidth);
            } else {
              adjustedR = applyBrightnessContrast(finalR, brightness, contrast, 0, 255);
              adjustedG = applyBrightnessContrast(finalG, brightness, contrast, 0, 255);
              adjustedB = applyBrightnessContrast(finalB, brightness, contrast, 0, 255);
            }
          }

          const index = (j * sliceWidth + i) * 4;
          sliceData[index] = adjustedR;
          sliceData[index + 1] = adjustedG;
          sliceData[index + 2] = adjustedB;
          sliceData[index + 3] = 255;
        }
      }
    }

    // CRITICAL FIX: Setează dimensiunile EXACT CORECTE pentru canvas
    console.log('[OVERLAY DEBUG] Setting canvas size:', { sliceWidth, sliceHeight });
    canvas.width = sliceWidth;
    canvas.height = sliceHeight;

    // FIXED: Dezactivează complet orice filtru sau smooth
    context.filter = 'none';
    context.imageSmoothingEnabled = false;

    // FIXED: Curăță canvas-ul complet înainte
    context.clearRect(0, 0, sliceWidth, sliceHeight);

    const imageData = new ImageData(sliceData, sliceWidth, sliceHeight);
    context.putImageData(imageData, 0, 0);

    console.log('[OVERLAY DEBUG] Successfully rendered overlay slice');

  } catch (error) {
    console.error('[OVERLAY ERROR]', error);
    throw new Error('Failed to draw overlay slice: ' + error.message);
  }
};





export const calculateAndSetChartData = (
  header: nifti.NIFTI1 | nifti.NIFTI2,
  image: ArrayBuffer,
  setHistogramData: (data: HistogramData[]) => void,
  setProfileCurveData: (data: ProfileCurveData[]) => void
): { windowCenter: number; windowWidth: number; min: number; max: number } => {
  try {
    // Convert to appropriate typed array
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

    if (typedData.length === 0) {
      throw new Error('Empty image data');
    }

    // Apply scaling if present
    const sclSlope = header.scl_slope || 1;
    const sclInter = header.scl_inter || 0;

    if (sclSlope !== 1 || sclInter !== 0) {
      for (let i = 0; i < typedData.length; i++) {
        typedData[i] = typedData[i] * sclSlope + sclInter;
      }
    }

    const windowing = calculateOptimalWindowing(typedData);

    // Histogram - focus on non-zero values
    const nonZeroValues = Array.from(typedData).filter(val => val > 0);
    const numBins = 100;
    const binSize = (windowing.max - windowing.min) / numBins;
    const bins = new Array(numBins).fill(0);

    for (let i = 0; i < nonZeroValues.length; i++) {
      const binIndex = Math.floor((nonZeroValues[i] - windowing.min) / binSize);
      if (binIndex >= 0 && binIndex < numBins) {
        bins[binIndex]++;
      }
    }

    const histogramData = bins.map((count, i) => ({
      value: Math.round(windowing.min + (i * binSize)),
      count,
    }));
    setHistogramData(histogramData);

    // Profile Curve (center line on axial view)
    const dims = header.dims || [];
    const xDim = dims[1] || 1;
    const yDim = dims[2] || 1;
    const zDim = dims[3] || 1;
    const centerZ = Math.floor(zDim / 2);
    const centerY = Math.floor(yDim / 2);

    const profileCurveData: ProfileCurveData[] = [];
    for (let i = 0; i < xDim; i++) {
      const voxelIndex = centerZ * (xDim * yDim) + centerY * xDim + i;
      profileCurveData.push({
        position: i,
        intensity: typedData[voxelIndex] || 0,
      });
    }
    setProfileCurveData(profileCurveData);

    return windowing;
  } catch (error) {
    console.error('Error calculating chart data:', error);
    // Set default empty data on error
    setHistogramData([]);
    setProfileCurveData([]);
    return { windowCenter: 0, windowWidth: 1, min: 0, max: 1 };
  }
};