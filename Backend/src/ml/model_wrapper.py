# -*- coding: utf-8 -*-
"""
Model wrapper pentru MedNeXt cu MONAI
"""
import torch
import numpy as np
from pathlib import Path
from typing import Optional, Dict, Any
import logging

try:
    from monai.networks.nets import MedNeXt
except ImportError:
    print("AVERTISMENT: MONAI nu este instalat. Instalează cu: pip install monai")
    MedNeXt = None

from src.core.config import (
    MODEL_PATH, NUM_CHANNELS, NUM_CLASSES, INIT_FILTERS,
    SPATIAL_DIMS, KERNEL_SIZE, DEEP_SUPERVISION
)

logger = logging.getLogger(__name__)


class MedNeXtWrapper:
    """
    Wrapper pentru modelul MedNeXt din MONAI
    Gestionează încărcarea, inferența și management-ul device-ului
    """

    def __init__(self):
        self.model = None
        self.device = None
        self.is_loaded = False
        self.model_path = MODEL_PATH

        # Inițializează device-ul
        self._setup_device()

    def _setup_device(self) -> None:
        """Configurează device-ul (CUDA sau CPU)"""
        if torch.cuda.is_available():
            self.device = torch.device('cuda')
            gpu_name = torch.cuda.get_device_name(0)
            gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1024 ** 3
            print(f"[ML] GPU detectat: {gpu_name} ({gpu_memory:.1f}GB)")
        else:
            self.device = torch.device('cpu')
            print("[ML] Folosește CPU pentru inferență")

        logger.info(f"Device configurat: {self.device}")

    def _create_model(self) -> torch.nn.Module:
        """
        Creează instanța modelului MedNeXt cu parametrii din config

        Returns:
            Model MedNeXt inițializat
        """
        if MedNeXt is None:
            raise ImportError("MONAI nu este disponibil. Instalează cu: pip install monai")

        print(f"[ML] Creează model MedNeXt:")
        print(f"    - Input channels: {NUM_CHANNELS}")
        print(f"    - Output classes: {NUM_CLASSES}")
        print(f"    - Init filters: {INIT_FILTERS}")
        print(f"    - Spatial dims: {SPATIAL_DIMS}")
        print(f"    - Kernel size: {KERNEL_SIZE}")
        print(f"    - Deep supervision: {DEEP_SUPERVISION}")

        model = MedNeXt(
            in_channels=NUM_CHANNELS,
            out_channels=NUM_CLASSES,
            init_filters=INIT_FILTERS,
            spatial_dims=SPATIAL_DIMS,
            kernel_size=KERNEL_SIZE,
            deep_supervision=DEEP_SUPERVISION
        ).to(self.device)

        # Afișează numărul de parametri
        total_params = sum(p.numel() for p in model.parameters())
        trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)

        print(f"[ML] Model creat cu succes:")
        print(f"    - Total parametri: {total_params:,}")
        print(f"    - Parametri antrenabili: {trainable_params:,}")
        print(f"    - Device: {self.device}")

        return model

    def load_model(self, model_path: Optional[Path] = None) -> bool:
        """
        Încarcă modelul din fișierul .pth

        Args:
            model_path: Calea către fișierul model (opțional)

        Returns:
            True dacă încărcarea a reușit
        """
        if model_path is None:
            model_path = self.model_path

        try:
            print(f"[ML] Încarcă model din: {model_path}")

            # Verifică dacă fișierul există
            if not model_path.exists():
                raise FileNotFoundError(f"Modelul nu există: {model_path}")

            # Creează modelul
            self.model = self._create_model()

            # Încarcă state dict
            checkpoint = torch.load(model_path, map_location=self.device)

            # Gestionează diferite formate de checkpoint
            if isinstance(checkpoint, dict):
                if 'model_state_dict' in checkpoint:
                    state_dict = checkpoint['model_state_dict']
                    print("[ML] Încărcat din checkpoint cu model_state_dict")
                elif 'state_dict' in checkpoint:
                    state_dict = checkpoint['state_dict']
                    print("[ML] Încărcat din checkpoint cu state_dict")
                else:
                    state_dict = checkpoint
                    print("[ML] Încărcat direct din dicționar")
            else:
                state_dict = checkpoint
                print("[ML] Încărcat model direct")

            # Încarcă weights în model
            self.model.load_state_dict(state_dict, strict=True)

            # Setează modelul în modul evaluare
            self.model.eval()

            self.is_loaded = True
            print(f"[ML] Model încărcat cu succes!")

            # Afișează informații despre checkpoint dacă sunt disponibile
            if isinstance(checkpoint, dict):
                if 'epoch' in checkpoint:
                    print(f"    - Epoca: {checkpoint['epoch']}")
                if 'loss' in checkpoint:
                    print(f"    - Loss: {checkpoint['loss']:.4f}")
                if 'accuracy' in checkpoint:
                    print(f"    - Accuracy: {checkpoint['accuracy']:.4f}")

            return True

        except Exception as e:
            logger.error(f"Eroare la încărcarea modelului: {str(e)}")
            print(f"[ML] EROARE la încărcarea modelului: {str(e)}")
            self.model = None
            self.is_loaded = False
            return False

    def predict(self, input_tensor: torch.Tensor) -> torch.Tensor:
        """
        Execută inferența pe input tensor

        Args:
            input_tensor: Tensor de input (B, C, H, W, D)

        Returns:
            Tensor cu predicțiile (B, NUM_CLASSES, H, W, D)

        Raises:
            RuntimeError: Dacă modelul nu este încărcat
        """
        if not self.is_loaded or self.model is None:
            raise RuntimeError("Modelul nu este încărcat. Apelează load_model() mai întâi.")

        try:
            # Verifică input shape
            expected_channels = NUM_CHANNELS
            if input_tensor.shape[1] != expected_channels:
                raise ValueError(
                    f"Input tensor are {input_tensor.shape[1]} canale, "
                    f"dar modelul așteaptă {expected_channels}"
                )

            print(f"[ML] Inferență pe tensor shape: {list(input_tensor.shape)}")

            # Mută tensorul pe device
            input_tensor = input_tensor.to(self.device)

            # Inferența
            with torch.no_grad():
                start_time = torch.cuda.Event(enable_timing=True) if self.device.type == 'cuda' else None
                end_time = torch.cuda.Event(enable_timing=True) if self.device.type == 'cuda' else None

                if self.device.type == 'cuda':
                    start_time.record()

                output = self.model(input_tensor)

                if self.device.type == 'cuda':
                    end_time.record()
                    torch.cuda.synchronize()
                    inference_time = start_time.elapsed_time(end_time) / 1000.0  # în secunde
                    print(f"[ML] Timp inferență GPU: {inference_time:.2f}s")
                else:
                    print(f"[ML] Inferența pe CPU completă")

            print(f"[ML] Output shape: {list(output.shape)}")

            return output

        except Exception as e:
            logger.error(f"Eroare la inferență: {str(e)}")
            raise RuntimeError(f"Eroare la inferență: {str(e)}")

    def get_model_info(self) -> Dict[str, Any]:
        """
        Returnează informații despre model

        Returns:
            Dicționar cu informații despre model
        """
        info = {
            "is_loaded": self.is_loaded,
            "device": str(self.device),
            "model_path": str(self.model_path),
            "config": {
                "in_channels": NUM_CHANNELS,
                "out_channels": NUM_CLASSES,
                "init_filters": INIT_FILTERS,
                "spatial_dims": SPATIAL_DIMS,
                "kernel_size": KERNEL_SIZE,
                "deep_supervision": DEEP_SUPERVISION
            }
        }

        if self.is_loaded and self.model is not None:
            total_params = sum(p.numel() for p in self.model.parameters())
            trainable_params = sum(p.numel() for p in self.model.parameters() if p.requires_grad)

            info.update({
                "total_parameters": total_params,
                "trainable_parameters": trainable_params,
                "memory_usage_mb": torch.cuda.memory_allocated() / 1024 ** 2 if torch.cuda.is_available() else 0
            })

        return info

    def unload_model(self) -> bool:
        """
        Descarcă modelul din memorie și eliberează resursele

        Returns:
            True dacă descărcarea a reușit
        """
        try:
            memory_before = 0
            if torch.cuda.is_available():
                memory_before = torch.cuda.memory_allocated() / 1024 ** 2

            if self.model is not None:
                print("[ML] Descărcare model din memorie...")

                # Mută modelul pe CPU înainte de ștergere (eliberează GPU memory)
                if self.device.type == 'cuda':
                    self.model.cpu()

                # Șterge modelul
                del self.model
                self.model = None

            self.is_loaded = False

            # Curăță cache-ul CUDA complet
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.synchronize()

                memory_after = torch.cuda.memory_allocated() / 1024 ** 2
                memory_freed = memory_before - memory_after

                print(f"[ML] Model descărcat cu succes!")
                print(f"    - Memorie GPU înainte: {memory_before:.1f}MB")
                print(f"    - Memorie GPU după: {memory_after:.1f}MB")
                print(f"    - Memorie eliberată: {memory_freed:.1f}MB")
            else:
                print("[ML] Model descărcat cu succes din memoria CPU!")

            return True

        except Exception as e:
            logger.error(f"Eroare la descărcarea modelului: {str(e)}")
            print(f"[ML] EROARE la descărcarea modelului: {str(e)}")
            return False

    def get_memory_usage(self) -> Dict[str, float]:
        """
        Returnează informații despre utilizarea memoriei

        Returns:
            Dict cu utilizarea memoriei în MB
        """
        memory_info = {
            "cpu_model_loaded": self.is_loaded,
            "gpu_available": torch.cuda.is_available()
        }

        if torch.cuda.is_available():
            memory_info.update({
                "gpu_allocated_mb": torch.cuda.memory_allocated() / 1024 ** 2,
                "gpu_reserved_mb": torch.cuda.memory_reserved() / 1024 ** 2,
                "gpu_total_mb": torch.cuda.get_device_properties(0).total_memory / 1024 ** 2,
                "gpu_free_mb": (torch.cuda.get_device_properties(
                    0).total_memory - torch.cuda.memory_reserved()) / 1024 ** 2
            })

        return memory_info

    def force_cleanup(self) -> None:
        """
        Forțează cleanup complet al tuturor resurselor
        """
        print("[ML] Cleanup forțat al tuturor resurselor...")

        try:
            # Descarcă modelul
            self.unload_model()

            # Cleanup agresiv pentru CUDA
            if torch.cuda.is_available():
                for device_id in range(torch.cuda.device_count()):
                    with torch.cuda.device(device_id):
                        torch.cuda.empty_cache()
                        torch.cuda.synchronize()

                print("[ML] Cleanup CUDA complet")

            # Reset variabile
            self.model = None
            self.is_loaded = False

            print("[ML] Cleanup forțat completat")

        except Exception as e:
            print(f"[ML] Eroare la cleanup forțat: {str(e)}")

    def __del__(self):
        """Destructor - cleanup automat"""
        try:
            if hasattr(self, 'is_loaded') and self.is_loaded:
                print("[ML] Destructor: cleanup automat model")
                self.force_cleanup()
        except:
            pass  # Ignoră erorile în destructor


# Instanță globală singleton
_model_wrapper = None


def get_model_wrapper() -> MedNeXtWrapper:
    """
    Returnează instanța globală a model wrapper-ului (singleton pattern)

    Returns:
        Instanța MedNeXtWrapper
    """
    global _model_wrapper
    if _model_wrapper is None:
        _model_wrapper = MedNeXtWrapper()
    return _model_wrapper


def ensure_model_loaded() -> bool:
    """
    Asigură că modelul este încărcat

    Returns:
        True dacă modelul este încărcat cu succes
    """
    wrapper = get_model_wrapper()
    if not wrapper.is_loaded:
        return wrapper.load_model()
    return True


def unload_global_model() -> bool:
    """
    Descarcă modelul global și eliberează memoria

    Returns:
        True dacă descărcarea a reușit
    """
    global _model_wrapper
    if _model_wrapper is not None:
        success = _model_wrapper.unload_model()
        return success
    return True


def force_global_cleanup() -> None:
    """
    Forțează cleanup complet al tuturor resurselor globale
    """
    global _model_wrapper
    if _model_wrapper is not None:
        _model_wrapper.force_cleanup()
        _model_wrapper = None

    print("[ML] Cleanup global complet")


def get_global_memory_usage() -> Dict:
    """
    Returnează utilizarea globală de memorie

    Returns:
        Dict cu informații despre memorie
    """
    wrapper = get_model_wrapper()
    return wrapper.get_memory_usage()