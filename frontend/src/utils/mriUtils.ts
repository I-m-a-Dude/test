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

// // Color mapping for segmentation classes
// const SEGMENTATION_COLORS = {
//   0: [0, 0, 0],       // Background - black
//   1: [0, 100, 255],   // NETC - blue
//   2: [255, 255, 0],   // SNFH - yellow
//   3: [255, 0, 0],     // ET - red
//   4: [128, 0, 128],   // RC - purple
// };

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
      { const float64Data = new Float64Array(image);
      typedData = new Float32Array(float64Data);
      break; }
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


// Enhanced drawSliceWithOverlay function with intelligent color mapping
// Înlocuiește funcția existentă din frontend/src/utils/mriUtils.ts

/**
 * Aplică hot colormap pentru overlay-uri grayscale
 * Mapează intensitățile la culorile: negru → roșu → galben → alb
 */
const applyHotColormap = (intensity: number, minVal: number, maxVal: number): [number, number, number] => {
  // Normalizează intensitatea la intervalul [0, 1]
  const normalizedIntensity = maxVal > minVal ? (intensity - minVal) / (maxVal - minVal) : 0;

  // Clamp la [0, 1]
  const t = Math.max(0, Math.min(1, normalizedIntensity));

  let r: number, g: number, b: number;

  if (t < 0.25) {
    // Negru → Roșu închis (0-25%)
    const localT = t / 0.25;
    r = Math.round(localT * 128);
    g = 0;
    b = 0;
  } else if (t < 0.5) {
    // Roșu închis → Roșu (25-50%)
    const localT = (t - 0.25) / 0.25;
    r = Math.round(128 + localT * 127);
    g = 0;
    b = 0;
  } else if (t < 0.75) {
    // Roșu → Galben (50-75%)
    const localT = (t - 0.5) / 0.25;
    r = 255;
    g = Math.round(localT * 255);
    b = 0;
  } else {
    // Galben → Alb (75-100%)
    const localT = (t - 0.75) / 0.25;
    r = 255;
    g = 255;
    b = Math.round(localT * 255);
  }

  return [r, g, b];
};

/**
 * Detectează robust tipul de overlay
 */
const detectOverlayType = (
  header: nifti.NIFTI1 | nifti.NIFTI2,
  image: ArrayBuffer,
  filename: string
): { isRGB: boolean; isGrayscale: boolean; bytesPerVoxel: number } => {
  const dims = header.dims;
  const xDim = dims[1];
  const yDim = dims[2];
  const zDim = dims[3];

  const totalVoxels = xDim * yDim * zDim;
  const bytesPerVoxel = image.byteLength / totalVoxels;

  // Detectare prin filename
  const lowerFilename = filename.toLowerCase();
  const hasOverlayKeyword = lowerFilename.includes('-overlay') || lowerFilename.includes('_overlay');

  // Detectare prin dimensiuni
  const hasRGBDimension = dims.length >= 5 && dims[4] === 3;
  const hasRGBBytes = Math.abs(bytesPerVoxel - 3) < 0.1; // ~3 bytes per voxel pentru RGB

  // Logica de decizie
  const isRGB = hasOverlayKeyword && (hasRGBDimension || hasRGBBytes);
  const isGrayscale = hasOverlayKeyword && !isRGB;

  console.log('[OVERLAY DETECT]', {
    filename: lowerFilename,
    bytesPerVoxel,
    hasOverlayKeyword,
    hasRGBDimension,
    hasRGBBytes,
    isRGB,
    isGrayscale
  });

  return { isRGB, isGrayscale, bytesPerVoxel };
};

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
  filename, // ADDED: Pentru detectarea corectă
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

  // FIXED: Folosește filename-ul transmis explicit
  const actualFilename = filename || canvas.title || 'overlay';
  console.log('[OVERLAY] Using filename for detection:', actualFilename);

  // Detectare inteligentă a tipului de overlay
  const overlayType = detectOverlayType(header, image, actualFilename);

  // ADDED: Verificare rapidă a datelor pentru confirmare RGB
  if (overlayType.isRGB) {
    const testData = new Uint8Array(image.slice(0, Math.min(100, image.byteLength)));
    console.log('[OVERLAY RGB TEST] Primii bytes:', Array.from(testData.slice(0, 15)));

    // Verifică dacă datele par să aibă pattern RGB (valori diverse pe grupuri de 3)
    const hasVariation = testData.some(val => val > 10); // Cel puțin unele valori > 10
    console.log('[OVERLAY RGB TEST] Are variație în culori:', hasVariation);
  }

  console.log('[OVERLAY] Processing overlay:', {
    type: overlayType.isRGB ? 'RGB' : overlayType.isGrayscale ? 'Grayscale' : 'Standard',
    dimensions: [xDim, yDim, zDim],
    bytesPerVoxel: overlayType.bytesPerVoxel
  });

  // Convertire date bazată pe tip
  let typedData: Uint8Array | Float32Array;

  if (overlayType.isRGB) {
    // Pentru RGB overlay, datele sunt deja uint8
    typedData = new Uint8Array(image);
  } else {
    // Pentru grayscale overlay sau date standard, convertim la Float32
    switch (header.datatype || header.datatypeCode) {
      case nifti.NIFTI1.TYPE_INT16:
        typedData = new Float32Array(new Int16Array(image));
        break;
      case nifti.NIFTI1.TYPE_UINT16:
        typedData = new Float32Array(new Uint16Array(image));
        break;
      case nifti.NIFTI1.TYPE_FLOAT32:
        typedData = new Float32Array(image);
        break;
      default:
        typedData = new Float32Array(new Uint8Array(image));
    }
  }

  // Pentru grayscale overlay, calculăm min/max pentru colormap
  let dataMin = 0, dataMax = 255;
  if (overlayType.isGrayscale && typedData instanceof Float32Array) {
    // Găsește min/max din datele non-zero pentru colormap optim
    const nonZeroValues = Array.from(typedData).filter(val => val > 0);
    if (nonZeroValues.length > 0) {
      dataMin = Math.min(...nonZeroValues);
      dataMax = Math.max(...nonZeroValues);
    }
    console.log('[OVERLAY] Grayscale range for colormap:', { dataMin, dataMax });
  }

  // Funcție pentru citirea voxel-ilor
  const getVoxelValue = (x: number, y: number, z: number): [number, number, number] => {
    if (x < 0 || x >= xDim || y < 0 || y >= yDim || z < 0 || z >= zDim) {
      return [0, 0, 0];
    }

    if (overlayType.isRGB) {
      // RGB overlay: citește 3 bytes consecutivi
      const baseIndex = ((z * yDim + y) * xDim + x) * 3;
      const typedDataUint8 = typedData as Uint8Array;

      if (baseIndex + 2 < typedDataUint8.length) {
        return [
          typedDataUint8[baseIndex] || 0,     // R
          typedDataUint8[baseIndex + 1] || 0, // G
          typedDataUint8[baseIndex + 2] || 0  // B
        ];
      }
      return [0, 0, 0];
    } else {
      // Grayscale overlay sau date standard
      const index = z * (xDim * yDim) + y * xDim + x;
      const typedDataFloat = typedData as Float32Array;
      const intensity = typedDataFloat[index] || 0;

      if (overlayType.isGrayscale && intensity > 0) {
        // Aplică hot colormap pentru grayscale overlay
        return applyHotColormap(intensity, dataMin, dataMax);
      } else {
        // Date standard - grayscale normal
        const grayValue = Math.max(0, Math.min(255, intensity));
        return [grayValue, grayValue, grayValue];
      }
    }
  };

  // Calculează dimensiunile slice-ului
  let sliceWidth: number, sliceHeight: number;

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

  const sliceData = new Uint8ClampedArray(sliceWidth * sliceHeight * 4);
  const currentSlice = Math.round(slice);

  console.log('[OVERLAY] Rendering slice:', {
    axis, currentSlice, sliceWidth, sliceHeight, sliceThickness
  });

  try {
    // Procesare optimizată pentru fiecare axă
    for (let j = 0; j < sliceHeight; j++) {
      for (let i = 0; i < sliceWidth; i++) {
        let avgR = 0, avgG = 0, avgB = 0;
        let samples = 0;

        // Averaging pentru slice thickness
        const halfThickness = Math.floor(sliceThickness / 2);

        for (let k = -halfThickness; k <= halfThickness; k++) {
          let sliceIndex: number;
          let voxelCoords: [number, number, number];

          if (axis === 'axial') {
            sliceIndex = Math.min(Math.max(currentSlice + k, 0), zDim - 1);
            voxelCoords = [i, j, sliceIndex];
          } else if (axis === 'coronal') {
            sliceIndex = Math.min(Math.max(currentSlice + k, 0), yDim - 1);
            voxelCoords = [i, sliceIndex, zDim - 1 - j]; // Flip Z
          } else { // sagittal
            sliceIndex = Math.min(Math.max(currentSlice + k, 0), xDim - 1);
            voxelCoords = [sliceIndex, i, zDim - 1 - j]; // Flip Z
          }

          const [r, g, b] = getVoxelValue(...voxelCoords);
          avgR += r; avgG += g; avgB += b;
          samples++;
        }

        const finalR = avgR / samples;
        const finalG = avgG / samples;
        const finalB = avgB / samples;

        // Aplică ajustări de brightness/contrast
        let adjustedR: number, adjustedG: number, adjustedB: number;

        if (overlayType.isRGB || overlayType.isGrayscale) {
          // Pentru overlay-uri, aplică ajustări simple
          const brightnessFactor = brightness / 100;
          const contrastFactor = contrast / 100;
          const midpoint = 127.5;

          adjustedR = Math.max(0, Math.min(255,
            midpoint + (finalR * brightnessFactor - midpoint) * contrastFactor));
          adjustedG = Math.max(0, Math.min(255,
            midpoint + (finalG * brightnessFactor - midpoint) * contrastFactor));
          adjustedB = Math.max(0, Math.min(255,
            midpoint + (finalB * brightnessFactor - midpoint) * contrastFactor));
        } else {
          // Pentru date standard, folosește windowing sau brightness/contrast
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
        sliceData[index] = Math.round(adjustedR);     // R
        sliceData[index + 1] = Math.round(adjustedG); // G
        sliceData[index + 2] = Math.round(adjustedB); // B
        sliceData[index + 3] = 255;                   // A (opaque)
      }
    }

    // Setează canvas și desenează
    canvas.width = sliceWidth;
    canvas.height = sliceHeight;

    context.filter = 'none';
    context.imageSmoothingEnabled = false;
    context.clearRect(0, 0, sliceWidth, sliceHeight);

    const imageData = new ImageData(sliceData, sliceWidth, sliceHeight);
    context.putImageData(imageData, 0, 0);

    console.log('[OVERLAY] Successfully rendered overlay with', overlayType.isRGB ? 'RGB colors' : overlayType.isGrayscale ? 'hot colormap' : 'standard grayscale');

  } catch (error) {
    console.error('[OVERLAY ERROR] Failed to render overlay:', error);
    throw new Error(`Failed to draw overlay slice: ${error.message}`);
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