# -*- coding: utf-8 -*-
"""
Model wrapper pentru MedNeXt cu MONAI - cu cleanup agresiv
"""
import torch
import numpy as np
from pathlib import Path
from typing import Optional, Dict, Any
import logging
import gc
import time

try:
    from monai.networks.nets import MedNeXt
except ImportError:
    print("AVERTISMENT: MONAI nu este instalat. Instaleaza cu: pip install monai")
    MedNeXt = None

from src.core.config import (
    MODEL_PATH, NUM_CHANNELS, NUM_CLASSES, INIT_FILTERS,
    SPATIAL_DIMS, KERNEL_SIZE, DEEP_SUPERVISION
)

logger = logging.getLogger(__name__)


class MedNeXtWrapper:
    """
    Wrapper pentru modelul MedNeXt din MONAI cu cleanup agresiv
    Gestioneaza incarcarea, inferenta si management-ul device-ului
    """

    def __init__(self):
        self.model = None
        self.device = None
        self.is_loaded = False
        self.model_path = MODEL_PATH
        self.inference_count = 0
        self.max_inferences_before_cleanup = 5  # Cleanup preventiv dupA 5 inferente

        # Initializeaza device-ul
        self._setup_device()

    def _setup_device(self) -> None:
        """Configureaza device-ul (CUDA sau CPU)"""
        if torch.cuda.is_available():
            self.device = torch.device('cuda')
            gpu_name = torch.cuda.get_device_name(0)
            gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1024 ** 3
            print(f"[ML] GPU detectat: {gpu_name} ({gpu_memory:.1f}GB)")
        else:
            self.device = torch.device('cpu')
            print("[ML] Foloseste CPU pentru inferenta")

        logger.info(f"Device configurat: {self.device}")

    def _create_model(self) -> torch.nn.Module:
        """
        Creeaza instanta modelului MedNeXt cu parametrii din config

        Returns:
            Model MedNeXt initializat
        """
        if MedNeXt is None:
            raise ImportError("MONAI nu este disponibil. Instaleaza cu: pip install monai")

        print(f"[ML] Creeaza model MedNeXt:")
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

        # Afiseaza numarul de parametri
        total_params = sum(p.numel() for p in model.parameters())
        trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)

        print(f"[ML] Model creat cu succes:")
        print(f"    - Total parametri: {total_params:,}")
        print(f"    - Parametri antrenabili: {trainable_params:,}")
        print(f"    - Device: {self.device}")

        return model

    def force_gpu_cleanup(self) -> None:
        """
        CLEANUP AGRESIV - Forteaza eliberarea completA a memoriei GPU
        """
        print("[CLEANUP] ⚡ Cleanup GPU agresiv incepe...")
        cleanup_start = time.time()

        # MemoreazA starea initialA
        initial_memory = 0
        if torch.cuda.is_available():
            initial_memory = torch.cuda.memory_allocated() / 1024 ** 2
            print(f"[CLEANUP] Memorie initialA: {initial_memory:.1f}MB")

        try:
            # 1. MODEL CLEANUP - MutA pe CPU inainte de stergere
            if hasattr(self, 'model') and self.model is not None:
                print("[CLEANUP] 🧠 Cleanup model...")

                # MutA toate parametrii pe CPU
                if self.device.type == 'cuda':
                    self.model.cpu()
                    print("[CLEANUP] Model mutat pe CPU")

                # sterge toate referintele
                del self.model
                self.model = None
                print("[CLEANUP] Model sters")

            # 2. CLEAR ALL GPU CACHE - Multiple passes pentru memoria indrAzneatA
            if torch.cuda.is_available():
                print("[CLEANUP] 💾 Cleanup cache CUDA...")

                # Primul val de cleanup
                torch.cuda.empty_cache()
                torch.cuda.synchronize()

                # Multiple passes pentru memoria care nu vrea sA plece
                for i in range(5):
                    torch.cuda.empty_cache()
                    if i % 2 == 0:
                        torch.cuda.synchronize()
                    time.sleep(0.01)  # LasA timp pentru cleanup

                print("[CLEANUP] Cache CUDA golit")

            # 3. PYTHON GARBAGE COLLECTION - Agresiv
            print("[CLEANUP] 🗑️ Garbage collection Python...")

            # Multiple passes de garbage collection
            for i in range(3):
                collected = gc.collect()
                if collected > 0:
                    print(f"[CLEANUP] GC pass {i + 1}: {collected} obiecte colectate")

            # DezactiveazA temporar GC automat pentru cleanup controlat
            gc.disable()
            time.sleep(0.05)
            gc.enable()

            # Final cleanup
            gc.collect()

            # 4. RESET MEMORY STATS (informativ)
            if torch.cuda.is_available():
                torch.cuda.reset_peak_memory_stats()
                print("[CLEANUP] Memory stats resetate")

            # 5. FINAL VERIFICATION
            final_memory = 0
            if torch.cuda.is_available():
                # ForteazA o ultimA sincronizare
                torch.cuda.synchronize()
                final_memory = torch.cuda.memory_allocated() / 1024 ** 2
                memory_freed = initial_memory - final_memory

                print(f"[CLEANUP] ✅ Cleanup complet!")
                print(f"    - Memorie initialA: {initial_memory:.1f}MB")
                print(f"    - Memorie finalA: {final_memory:.1f}MB")
                print(f"    - Memorie eliberatA: {memory_freed:.1f}MB")
            else:
                print(f"[CLEANUP] ✅ Cleanup CPU complet!")

            cleanup_time = time.time() - cleanup_start
            print(f"[CLEANUP] Timp total cleanup: {cleanup_time:.2f}s")

        except Exception as e:
            print(f"[CLEANUP ERROR] ❌ Eroare in cleanup agresiv: {str(e)}")
            logger.error(f"Eroare cleanup agresiv: {str(e)}")

            # Emergency cleanup in caz de eroare
            try:
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    torch.cuda.synchronize()
                gc.collect()
                print("[CLEANUP] Emergency cleanup executat")
            except:
                print("[CLEANUP] Emergency cleanup a esuat")

    def load_model(self, model_path: Optional[Path] = None) -> bool:
        """
        incarcA modelul din fisierul .pth cu cleanup preventiv

        Args:
            model_path: Calea cAtre fisierul model (optional)

        Returns:
            True dacA incArcarea a reusit
        """
        if model_path is None:
            model_path = self.model_path

        try:
            print(f"[ML] incarcA model din: {model_path}")

            # Cleanup preventiv inainte de incArcare
            if self.is_loaded:
                print("[ML] Cleanup preventiv inainte de reincArcare...")
                self.force_gpu_cleanup()

            # VerificA dacA fisierul existA
            if not model_path.exists():
                raise FileNotFoundError(f"Modelul nu existA: {model_path}")

            # CreeazA modelul
            self.model = self._create_model()

            # incarcA state dict
            checkpoint = torch.load(model_path, map_location=self.device)

            # GestioneazA diferite formate de checkpoint
            if isinstance(checkpoint, dict):
                if 'model_state_dict' in checkpoint:
                    state_dict = checkpoint['model_state_dict']
                    print("[ML] incArcat din checkpoint cu model_state_dict")
                elif 'state_dict' in checkpoint:
                    state_dict = checkpoint['state_dict']
                    print("[ML] incArcat din checkpoint cu state_dict")
                else:
                    state_dict = checkpoint
                    print("[ML] incArcat direct din dictionar")
            else:
                state_dict = checkpoint
                print("[ML] incArcat model direct")

            # incarcA weights in model
            self.model.load_state_dict(state_dict, strict=True)

            # SeteazA modelul in modul evaluare
            self.model.eval()

            # Reset contorul de inferente
            self.inference_count = 0
            self.is_loaded = True

            print(f"[ML] ✅ Model incArcat cu succes!")

            # AfiseazA informatii despre checkpoint dacA sunt disponibile
            if isinstance(checkpoint, dict):
                if 'epoch' in checkpoint:
                    print(f"    - Epoca: {checkpoint['epoch']}")
                if 'loss' in checkpoint:
                    print(f"    - Loss: {checkpoint['loss']:.4f}")
                if 'accuracy' in checkpoint:
                    print(f"    - Accuracy: {checkpoint['accuracy']:.4f}")

            return True

        except Exception as e:
            logger.error(f"Eroare la incArcarea modelului: {str(e)}")
            print(f"[ML] ❌ EROARE la incArcarea modelului: {str(e)}")

            # Cleanup in caz de eroare
            self.force_gpu_cleanup()
            self.model = None
            self.is_loaded = False
            return False

    def predict(self, input_tensor: torch.Tensor) -> torch.Tensor:
        """
        ExecutA inferenta pe input tensor cu cleanup preventiv

        Args:
            input_tensor: Tensor de input (B, C, H, W, D)

        Returns:
            Tensor cu predictiile (B, NUM_CLASSES, H, W, D)

        Raises:
            RuntimeError: DacA modelul nu este incArcat
        """
        if not self.is_loaded or self.model is None:
            raise RuntimeError("Modelul nu este incArcat. ApeleazA load_model() mai intAi.")

        try:
            # VerificA input shape
            expected_channels = NUM_CHANNELS
            if input_tensor.shape[1] != expected_channels:
                raise ValueError(
                    f"Input tensor are {input_tensor.shape[1]} canale, "
                    f"dar modelul asteaptA {expected_channels}"
                )

            print(f"[ML] Inferenta #{self.inference_count + 1} pe tensor shape: {list(input_tensor.shape)}")

            # CLEANUP PREVENTIV dacA am ajuns la limita
            if self.inference_count >= self.max_inferences_before_cleanup:
                print(f"[ML] 🔄 Cleanup preventiv dupA {self.inference_count} inferente")
                self.force_gpu_cleanup()

                # ReincarcA modelul pentru a fi siguri
                if not self.load_model():
                    raise RuntimeError("ReincArcarea modelului dupA cleanup a esuat")

            # MutA tensorul pe device
            input_tensor = input_tensor.to(self.device)

            # Inferenta cu timing
            with torch.no_grad():
                start_time = torch.cuda.Event(enable_timing=True) if self.device.type == 'cuda' else None
                end_time = torch.cuda.Event(enable_timing=True) if self.device.type == 'cuda' else None

                if self.device.type == 'cuda':
                    start_time.record()

                # INFERENtA PROPRIU-ZISA
                output = self.model(input_tensor)

                if self.device.type == 'cuda':
                    end_time.record()
                    torch.cuda.synchronize()
                    inference_time = start_time.elapsed_time(end_time) / 1000.0  # in secunde
                    print(f"[ML] ✅ Timp inferentA GPU: {inference_time:.2f}s")
                else:
                    print(f"[ML] ✅ InferentA pe CPU completA")

            print(f"[ML] Output shape: {list(output.shape)}")

            # IncrementeazA contorul
            self.inference_count += 1

            # Cleanup usor dupA fiecare inferentA
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            return output

        except Exception as e:
            logger.error(f"Eroare la inferentA: {str(e)}")
            print(f"[ML] ❌ EROARE la inferentA: {str(e)}")

            # Cleanup in caz de eroare
            print("[ML] 🚨 Cleanup de urgentA dupA eroare...")
            self.force_gpu_cleanup()

            raise RuntimeError(f"Eroare la inferentA: {str(e)}")

    def get_model_info(self) -> Dict[str, Any]:
        """
        Returneaza informatii despre model

        Returns:
            Dictionar cu informatii despre model
        """
        info = {
            "is_loaded": self.is_loaded,
            "device": str(self.device),
            "model_path": str(self.model_path),
            "inference_count": self.inference_count,
            "max_inferences_before_cleanup": self.max_inferences_before_cleanup,
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
        DescarcA modelul din memorie folosind cleanup agresiv

        Returns:
            True dacA descArcarea a reusit
        """
        try:
            print("[ML] 🔄 incepe descArcarea modelului...")

            # Foloseste cleanup agresiv
            self.force_gpu_cleanup()

            # Reset toate flag-urile
            self.is_loaded = False
            self.inference_count = 0

            print("[ML] ✅ Model descArcat cu succes!")
            return True

        except Exception as e:
            logger.error(f"Eroare la descArcarea modelului: {str(e)}")
            print(f"[ML] ❌ EROARE la descArcarea modelului: {str(e)}")
            return False

    def get_memory_usage(self) -> Dict[str, float]:
        """
        Returneaza informatii despre utilizarea memoriei

        Returns:
            Dict cu utilizarea memoriei in MB
        """
        memory_info = {
            "cpu_model_loaded": self.is_loaded,
            "gpu_available": torch.cuda.is_available(),
            "inference_count": self.inference_count,
            "max_inferences_before_cleanup": self.max_inferences_before_cleanup
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
        Alias pentru force_gpu_cleanup() pentru compatibilitate
        """
        self.force_gpu_cleanup()

    def __del__(self):
        """Destructor cu cleanup automat agresiv"""
        try:
            if hasattr(self, 'is_loaded') and self.is_loaded:
                print("[ML] 🧹 Destructor: cleanup automat model")
                self.force_gpu_cleanup()
        except:
            pass  # IgnorA erorile in destructor


# Instanta globala singleton cu cleanup imbunAtAtit
_model_wrapper = None


def get_model_wrapper() -> MedNeXtWrapper:
    """
    Returneaza instanta globala a model wrapper-ului (singleton pattern) cu cleanup

    Returns:
        Instanta MedNeXtWrapper
    """
    global _model_wrapper
    if _model_wrapper is None:
        _model_wrapper = MedNeXtWrapper()
    return _model_wrapper


def ensure_model_loaded() -> bool:
    """
    Asigura ca modelul este incarcat cu cleanup preventiv

    Returns:
        True daca modelul este incarcat cu succes
    """
    wrapper = get_model_wrapper()
    if not wrapper.is_loaded:
        return wrapper.load_model()
    return True


def unload_global_model() -> bool:
    """
    Descarca modelul global si elibereaza memoria folosind cleanup agresiv

    Returns:
        True daca descarcarea a reusit
    """
    global _model_wrapper
    if _model_wrapper is not None:
        success = _model_wrapper.unload_model()
        return success
    return True


def force_global_cleanup() -> None:
    """
    Forteaza cleanup agresiv complet al tuturor resurselor globale
    """
    global _model_wrapper
    if _model_wrapper is not None:
        _model_wrapper.force_gpu_cleanup()
        _model_wrapper = None

    print("[ML] ✅ Cleanup global agresiv complet")


def get_global_memory_usage() -> Dict:
    """
    Returneaza utilizarea globala de memorie

    Returns:
        Dict cu informatii despre memorie
    """
    wrapper = get_model_wrapper()
    return wrapper.get_memory_usage()