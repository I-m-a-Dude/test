from monai.transforms import (
    LoadImaged,
    EnsureChannelFirstd,
    Spacingd,
    Orientationd,
    ScaleIntensityRanged,
    CropForegroundd,
    ResizeWithPadOrCropd,
    ConcatItemsd,
    AsDiscreted,  # Use this instead of OneHotd
    EnsureTyped,
    RandRotate90d,
    RandScaleIntensityd,
    RandShiftIntensityd,
    RandGaussianNoised,
    RandFlipd,
    Compose
)



class PreprocessPipeline:

