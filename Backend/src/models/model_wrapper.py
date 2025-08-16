"""
Model wrapper pentru încărcarea și rularea modelului MedNeXt antrenat.
Bazat pe arhitectura din notebook pentru BraTS2024 Adult Glioma Post Treatment.
"""

import torch
import torch.nn as nn
from pathlib import Path
import logging
from typing import Union, Tuple, Optional
import time

try:
    from monai.networks.nets import MedNeXt
except ImportError:
    raise ImportError("MONAI nu este instalat. Rulează: pip install monai")

logger = logging.getLogger(__name__)


class ModelWrapper:
    """
    Wrapper pentru modelul MedNeXt antrenat pe BraTS2024.

    Gestionează încărcarea modelului, device management și inferența.
    Thread-safe pentru utilizare în FastAPI.
    """

    # Constante din notebook
    NUM_CHANNELS = 4  # T1n, T1c, T2w, T2f
    NUM_CLASSES = 5  # Background, NETC, SNFH, ET, RC
    IMG_SIZE = (128, 128, 128)  # Dimensiunea pentru inferență

    LABEL_MAPPING = {
        0: "Background",
        1: "Non-enhancing Tumor Core (NETC)",
        2: "Surrounding Non-enhancing FLAIR Hyperintensity (SNFH)",
        3: "Enhancing Tissue (ET)",
        4: "Resection Cavity (RC)"
    }

    def __init__(self, model_path: Union[str, Path], device: Optional[str] = None):
        """
        Inițializează wrapper-ul cu modelul antrenat.

        Args:
            model_path: Calea către fișierul .pth cu weights
            device: Device pentru inferență ('cuda', 'cpu', sau None pentru auto-detect)
        """
        self.model_path = Path(model_path)
        self.device = self._setup_device(device)
        self.model = None
        self.is_loaded = False

        logger.info(f"Wrapper inițializat pentru model: {self.model_path}")
        logger.info(f"Device selectat: {self.device}")

    def _setup_device(self, device: Optional[str]) -> torch.device:
        """Configurează device-ul pentru inferență."""
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"

        torch_device = torch.device(device)

        if torch_device.type == "cuda" and not torch.cuda.is_available():
            logger.warning("CUDA solicitat dar nu e disponibil. Folosesc CPU.")
            torch_device = torch.device("cpu")

        return torch_device

    def _create_model(self) -> nn.Module:
        """
        Creează arhitectura modelului MedNeXt cu parametrii din notebook.
        """
        try:
            model = MedNeXt(
                in_channels=self.NUM_CHANNELS,  # 4 modalități
                out_channels=self.NUM_CLASSES,  # 5 clase
                init_filters=32,  # Filtri inițiali
                spatial_dims=3,  # 3D segmentation
                kernel_size=3,  # 3x3x3 convolutions
                deep_supervision=False  # Fără deep supervision
            )

            logger.info(f"Model MedNeXt creat cu succes:")
            logger.info(f"  - Input channels: {self.NUM_CHANNELS}")
            logger.info(f"  - Output classes: {self.NUM_CLASSES}")
            logger.info(f"  - Spatial dims: 3D")
            logger.info(f"  - Init filters: 32")

            return model

        except Exception as e:
            logger.error(f"Eroare la crearea modelului: {e}")
            raise

    def load_model(self) -> None:
        """
        Încarcă modelul din fișierul .pth și îl mutăm pe device.
        """
        if not self.model_path.exists():
            raise FileNotFoundError(f"Modelul nu există la: {self.model_path}")

        try:
            start_time = time.time()
            logger.info(f"Încărcarea modelului din: {self.model_path}")

            # Creează arhitectura
            self.model = self._create_model()

            # Încarcă weights
            state_dict = torch.load(
                self.model_path,
                map_location=self.device,
                weights_only=True  # Securitate
            )

            self.model.load_state_dict(state_dict)
            self.model.to(self.device)
            self.model.eval()  # Mod evaluare

            # Optimizări pentru inferență
            if self.device.type == "cuda":
                torch.backends.cudnn.benchmark = True
                torch.backends.cuda.matmul.allow_tf32 = True
                torch.backends.cudnn.allow_tf32 = True

            self.is_loaded = True
            load_time = time.time() - start_time

            # Calculează numărul de parametri
            total_params = sum(p.numel() for p in self.model.parameters())
            trainable_params = sum(p.numel() for p in self.model.parameters() if p.requires_grad)

            logger.info(f"Model încărcat cu succes în {load_time:.2f}s")
            logger.info(f"Parametri totali: {total_params:,}")
            logger.info(f"Parametri antrenabili: {trainable_params:,}")
            logger.info(f"Dimensiune așteptată input: {self.IMG_SIZE}")

        except Exception as e:
            logger.error(f"Eroare la încărcarea modelului: {e}")
            raise

    def predict(self, input_tensor: torch.Tensor) -> torch.Tensor:
        """
        Rulează inferența pe un tensor de input preprocesat.

        Args:
            input_tensor: Tensor (1, 4, D, H, W) sau (4, D, H, W)

        Returns:
            torch.Tensor: Logits raw (1, 5, D, H, W)
        """
        if not self.is_loaded:
            raise RuntimeError("Modelul nu este încărcat. Rulează load_model() primul.")

        # Validare input
        if input_tensor.dim() == 4:  # (4, D, H, W)
            input_tensor = input_tensor.unsqueeze(0)  # (1, 4, D, H, W)
        elif input_tensor.dim() != 5:
            raise ValueError(f"Input trebuie să aibă 4 sau 5 dimensiuni, primite: {input_tensor.dim()}")

        if input_tensor.shape[1] != self.NUM_CHANNELS:
            raise ValueError(f"Input trebuie să aibă {self.NUM_CHANNELS} canale, primite: {input_tensor.shape[1]}")

        try:
            start_time = time.time()

            # Mută pe device și asigură tipul corect
            input_tensor = input_tensor.to(self.device, dtype=torch.float32)

            # Inferență cu optimizări
            with torch.no_grad():
                if self.device.type == "cuda":
                    # Folosește autocast pentru FP16 pe GPU
                    with torch.autocast(device_type="cuda", dtype=torch.float16):
                        logits = self.model(input_tensor)
                else:
                    # CPU standard
                    logits = self.model(input_tensor)

            inference_time = time.time() - start_time
            logger.info(f"Inferență completă în {inference_time:.3f}s")
            logger.info(f"Output shape: {logits.shape}")

            return logits.cpu()  # Returnează pe CPU pentru flexibilitate

        except Exception as e:
            logger.error(f"Eroare la inferență: {e}")
            raise

    def get_predictions(self, input_tensor: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Rulează inferența și returnează și probabilități și clase.

        Args:
            input_tensor: Input tensor preprocesat

        Returns:
            Tuple[torch.Tensor, torch.Tensor]: (probabilities, class_predictions)
        """
        logits = self.predict(input_tensor)

        # Calculează probabilitățile cu softmax
        probabilities = torch.softmax(logits, dim=1)

        # Extrage clasele cu argmax
        class_predictions = torch.argmax(probabilities, dim=1, keepdim=True)

        return probabilities, class_predictions

    def get_model_info(self) -> dict:
        """
        Returnează informații despre model pentru debugging.
        """
        info = {
            "model_path": str(self.model_path),
            "device": str(self.device),
            "is_loaded": self.is_loaded,
            "num_channels": self.NUM_CHANNELS,
            "num_classes": self.NUM_CLASSES,
            "expected_input_size": self.IMG_SIZE,
            "label_mapping": self.LABEL_MAPPING
        }

        if self.is_loaded and self.model:
            total_params = sum(p.numel() for p in self.model.parameters())
            info["total_parameters"] = total_params
            info["model_architecture"] = "MedNeXt"

        return info

    def __repr__(self) -> str:
        return f"ModelWrapper(path={self.model_path}, device={self.device}, loaded={self.is_loaded})"