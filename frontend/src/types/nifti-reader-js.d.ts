declare module 'nifti-reader-js' {
      export interface NIFTI1 {
        dims: number[];
        datatypeCode: number;
        cal_max: number;
        cal_min: number;
        scl_slope: number;
        scl_inter: number;
        pixDims: number[];
        qform_code: number;
        sform_code: number;
        quatern_b: number;
        quatern_c: number;
        quatern_d: number;
        qoffset_x: number;
        qoffset_y: number;
        qoffset_z: number;
        srow_x: number[];
        srow_y: number[];
        srow_z: number[];
      }

      export type NIFTI2 = NIFTI1;

      export namespace NIFTI1 {
        const TYPE_UINT8: number;
        const TYPE_INT16: number;
        const TYPE_INT32: number;
        const TYPE_FLOAT32: number;
        const TYPE_FLOAT64: number;
        const TYPE_INT8: number;
        const TYPE_UINT16: number;
        const TYPE_UINT32: number;
      }

      export function readHeader(data: ArrayBuffer): NIFTI1 | NIFTI2 | null;
      export function readImage(header: NIFTI1 | NIFTI2, data: ArrayBuffer): ArrayBuffer | null;
      export function isCompressed(data: ArrayBuffer): boolean;
      export function decompress(data: ArrayBuffer): ArrayBuffer;
    }