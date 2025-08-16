from monai.networks.nets import MedNeXt


class ModelWrapper:
    def __init__(self, model_name: str, in_channels: int = 1, out_channels: int = 1):
        if model_name == "MedNeXt":
            self.model = MedNeXt(
                in_channels=in_channels,
                out_channels=out_channels,
                init_filters=32,
                spatial_dims=3,
                kernel_size=3,
                deep_supervision=False
            )
        else:
            raise ValueError(f"Model {model_name} is not supported.")

    def load_weights(self, checkpoint_path: str):
        """Load model weights from checkpoint"""
        import torch
        checkpoint = torch.load(checkpoint_path, map_location='cpu')
        self.model.load_state_dict(checkpoint['model_state_dict'] if 'model_state_dict' in checkpoint else checkpoint)

    def predict(self, x):
        """Run inference on input tensor"""
        import torch
        self.model.eval()
        with torch.no_grad():
            return self.model(x)

    def to(self, device):
        """Move model to specified device"""
        self.model.to(device)
        return self