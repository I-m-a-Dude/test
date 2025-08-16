from monai.transforms import (
    Compose,
    AsDiscreted,
    KeepLargestConnectedComponentd,
    FillHolesd
)



class PostprocessPipeline: