from unittest import TestCase
from unittest.mock import patch, MagicMock
import tempfile
from pathlib import Path


class TestMedNeXtWrapper(TestCase):

    def setUp(self):
        """Reset global state before each test"""
        print(f"\n{'=' * 60}")
        print(f"🧪 STARTING TEST: {self._testMethodName}")
        print(f"{'=' * 60}")

        # Clear any existing global wrapper
        import src.ml.model_wrapper as mw
        mw._model_wrapper = None
        print("✅ Reset global model wrapper state")

    def test_get_model_wrapper(self):
        """Test that get_model_wrapper returns a MedNeXtWrapper instance"""
        print("📋 Testing singleton pattern and wrapper instantiation...")

        from src.ml.model_wrapper import get_model_wrapper, MedNeXtWrapper

        print("🔄 Getting first wrapper instance...")
        wrapper = get_model_wrapper()

        print(f"✅ Wrapper type: {type(wrapper).__name__}")
        print(f"✅ Is loaded: {wrapper.is_loaded}")

        self.assertIsInstance(wrapper, MedNeXtWrapper)
        self.assertFalse(wrapper.is_loaded)  # Should not be loaded initially

        print("🔄 Getting second wrapper instance (testing singleton)...")
        wrapper2 = get_model_wrapper()

        is_same_instance = wrapper is wrapper2
        print(f"✅ Same instance (singleton): {is_same_instance}")

        # Test singleton behavior - should return same instance
        self.assertIs(wrapper, wrapper2)
        print("🎉 Singleton pattern working correctly!")

    @patch('src.ml.model_wrapper.MODEL_PATH')
    def test_ensure_model_loaded_no_model_file(self, mock_model_path):
        """Test ensure_model_loaded when model file doesn't exist"""
        print("📋 Testing model loading when file doesn't exist...")

        from src.ml.model_wrapper import ensure_model_loaded

        # Create a non-existent path
        mock_model_path.exists.return_value = False
        print("🚫 Mocked model file as non-existent")

        print("🔄 Attempting to load model...")
        result = ensure_model_loaded()

        print(f"✅ Load result: {result}")
        print("🎉 Correctly handled missing model file!")

        # Should return False when model file doesn't exist
        self.assertFalse(result)

    @patch('torch.load')
    @patch('src.ml.model_wrapper.MODEL_PATH')
    def test_ensure_model_loaded_success(self, mock_model_path, mock_torch_load):
        """Test successful model loading"""
        print("📋 Testing successful model loading...")

        from src.ml.model_wrapper import ensure_model_loaded, get_model_wrapper

        # Mock model file exists
        mock_model_path.exists.return_value = True
        print("✅ Mocked model file as existing")

        # Mock torch.load to return fake state dict
        fake_weights = {'layer1.weight': 'fake_weights', 'layer2.bias': 'fake_bias'}
        mock_torch_load.return_value = fake_weights
        print(f"✅ Mocked torch.load with fake weights: {list(fake_weights.keys())}")

        # Mock the model creation and loading
        wrapper = get_model_wrapper()
        print("🔄 Got wrapper instance for testing...")

        with patch.object(wrapper, '_create_model') as mock_create_model:
            mock_model = MagicMock()
            mock_model.load_state_dict = MagicMock()
            mock_model.eval = MagicMock()
            mock_create_model.return_value = mock_model

            print("🔄 Attempting to load model...")
            result = ensure_model_loaded()

            print(f"✅ Load result: {result}")
            print(f"✅ Model creation called: {mock_create_model.called}")
            print("🎉 Model loading simulation successful!")

            # Should return True on successful load
            self.assertTrue(result)

    def test_unload_global_model(self):
        """Test unloading the global model"""
        print("📋 Testing model unloading...")

        from src.ml.model_wrapper import unload_global_model, get_model_wrapper

        # Get wrapper instance
        wrapper = get_model_wrapper()
        print("🔄 Got wrapper instance")

        # Mock that model is loaded
        wrapper.is_loaded = True
        wrapper.model = MagicMock()
        print("✅ Mocked model as loaded")
        print(f"✅ Initial loaded state: {wrapper.is_loaded}")

        print("🔄 Attempting to unload model...")
        result = unload_global_model()

        print(f"✅ Unload result: {result}")
        print(f"✅ Final loaded state: {wrapper.is_loaded}")
        print("🎉 Model unloading successful!")

        # Should return True and model should be unloaded
        self.assertTrue(result)
        self.assertFalse(wrapper.is_loaded)

    def test_force_global_cleanup(self):
        """Test force cleanup doesn't raise exceptions"""
        print("📋 Testing force cleanup safety...")

        from src.ml.model_wrapper import force_global_cleanup

        print("🔄 Executing force cleanup...")

        # Should not raise any exceptions
        try:
            force_global_cleanup()
            cleanup_success = True
            print("✅ Cleanup executed without exceptions")
        except Exception as e:
            cleanup_success = False
            print(f"❌ Cleanup failed with exception: {e}")

        print("🎉 Force cleanup safety verified!")
        self.assertTrue(cleanup_success)

    @patch('torch.cuda.is_available')
    def test_get_global_memory_usage_cpu_only(self, mock_cuda_available):
        """Test memory usage when CUDA is not available"""
        print("📋 Testing memory usage reporting (CPU only)...")

        from src.ml.model_wrapper import get_global_memory_usage

        mock_cuda_available.return_value = False
        print("🚫 Mocked CUDA as unavailable")

        print("🔄 Getting memory usage info...")
        memory_info = get_global_memory_usage()

        print(f"✅ Memory info type: {type(memory_info)}")
        print(f"✅ GPU available: {memory_info.get('gpu_available', 'N/A')}")
        print(f"✅ Keys in memory info: {list(memory_info.keys())}")
        print("🎉 CPU-only memory reporting working!")

        # Should return dict with basic info
        self.assertIsInstance(memory_info, dict)
        self.assertIn('gpu_available', memory_info)
        self.assertFalse(memory_info['gpu_available'])

    @patch('torch.cuda.memory_allocated')
    @patch('torch.cuda.memory_reserved')
    @patch('torch.cuda.get_device_properties')
    @patch('torch.cuda.is_available')
    def test_get_global_memory_usage_with_gpu(self, mock_cuda_available,
                                              mock_get_device_props,
                                              mock_memory_reserved,
                                              mock_memory_allocated):
        """Test memory usage when CUDA is available"""
        print("📋 Testing memory usage reporting (with GPU)...")

        from src.ml.model_wrapper import get_global_memory_usage

        # Mock CUDA availability and memory functions
        mock_cuda_available.return_value = True
        allocated_bytes = 1024 * 1024 * 100  # 100MB
        reserved_bytes = 1024 * 1024 * 200  # 200MB
        total_bytes = 1024 * 1024 * 1024 * 8  # 8GB

        mock_memory_allocated.return_value = allocated_bytes
        mock_memory_reserved.return_value = reserved_bytes

        print("✅ Mocked CUDA as available")
        print(f"✅ Mocked allocated memory: {allocated_bytes // (1024 * 1024)} MB")
        print(f"✅ Mocked reserved memory: {reserved_bytes // (1024 * 1024)} MB")
        print(f"✅ Mocked total memory: {total_bytes // (1024 * 1024 * 1024)} GB")

        # Mock device properties
        mock_device_props = MagicMock()
        mock_device_props.total_memory = total_bytes
        mock_get_device_props.return_value = mock_device_props

        print("🔄 Getting memory usage info...")
        memory_info = get_global_memory_usage()

        print(f"✅ Memory info keys: {list(memory_info.keys())}")
        print(f"✅ GPU available: {memory_info.get('gpu_available', 'N/A')}")
        print(f"✅ GPU allocated MB: {memory_info.get('gpu_allocated_mb', 'N/A')}")
        print(f"✅ GPU reserved MB: {memory_info.get('gpu_reserved_mb', 'N/A')}")
        print(f"✅ GPU total MB: {memory_info.get('gpu_total_mb', 'N/A')}")
        print("🎉 GPU memory reporting working!")

        # Should return dict with GPU info
        self.assertIsInstance(memory_info, dict)
        self.assertTrue(memory_info['gpu_available'])
        self.assertIn('gpu_allocated_mb', memory_info)
        self.assertIn('gpu_reserved_mb', memory_info)
        self.assertIn('gpu_total_mb', memory_info)

    def tearDown(self):
        """Clean up after each test"""
        print(f"\n🧹 CLEANUP: {self._testMethodName}")

        # Force cleanup to reset state
        try:
            from src.ml.model_wrapper import force_global_cleanup
            force_global_cleanup()
            print("✅ Cleanup completed successfully")
        except Exception as e:
            print(f"⚠️ Cleanup had minor issues: {e}")

        print(f"🏁 FINISHED: {self._testMethodName}")
        print(f"{'=' * 60}\n")