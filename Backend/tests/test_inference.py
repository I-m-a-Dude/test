from unittest import TestCase
from unittest.mock import patch, MagicMock
from pathlib import Path
import torch


class TestInference(TestCase):

    def setUp(self):
        """Setup before each test"""
        print(f"\n{'=' * 60}")
        print(f"🧠 STARTING INFERENCE TEST: {self._testMethodName}")
        print(f"{'=' * 60}")

        # Clear any existing global service
        try:
            import src.services.inference as inf
            inf._inference_service = None
            print("✅ Reset global inference service state")
        except:
            print("⚠️ Could not reset inference service (module might not be loaded)")

    @patch('src.services.inference.ML_AVAILABLE', True)
    @patch('src.services.inference.get_preprocessor')
    @patch('src.services.inference.get_postprocessor')
    @patch('src.services.inference.get_model_wrapper')
    def test_create_inference_service(self, mock_get_model_wrapper, mock_get_postprocessor, mock_get_preprocessor):
        """Test creating inference service"""
        print("📋 Testing inference service creation...")

        from src.services.inference import create_inference_service, GliomaInferenceService

        # Mock dependencies
        mock_preprocessor = MagicMock()
        mock_postprocessor = MagicMock()
        mock_model_wrapper = MagicMock()

        mock_get_preprocessor.return_value = mock_preprocessor
        mock_get_postprocessor.return_value = mock_postprocessor
        mock_get_model_wrapper.return_value = mock_model_wrapper

        print("✅ Mocked all dependencies:")
        print("   🔧 Preprocessor")
        print("   🔧 Postprocessor")
        print("   🔧 Model wrapper")

        print("🔄 Creating inference service...")
        service = create_inference_service()

        print(f"✅ Service type: {type(service).__name__}")
        print(f"✅ Is GliomaInferenceService: {isinstance(service, GliomaInferenceService)}")
        print(f"✅ Has preprocessor: {hasattr(service, 'preprocessor')}")
        print(f"✅ Has postprocessor: {hasattr(service, 'postprocessor')}")
        print(f"✅ Has model_wrapper: {hasattr(service, 'model_wrapper')}")
        print("🎉 Inference service creation successful!")

        self.assertIsInstance(service, GliomaInferenceService)
        self.assertEqual(service.preprocessor, mock_preprocessor)
        self.assertEqual(service.postprocessor, mock_postprocessor)
        self.assertEqual(service.model_wrapper, mock_model_wrapper)

    @patch('src.services.inference.create_inference_service')
    def test_run_inference_on_folder(self, mock_create_service):
        """Test running inference on folder"""
        print("📋 Testing inference on folder...")

        from src.services.inference import run_inference_on_folder

        # Mock the service and its pipeline method
        mock_service = MagicMock()
        mock_create_service.return_value = mock_service

        # Mock successful inference result
        mock_result = {
            "success": True,
            "folder_name": "test_patient",
            "timing": {
                "preprocess_time": 2.5,
                "inference_time": 1.8,
                "postprocess_time": 0.7,
                "total_time": 5.0
            },
            "segmentation": {
                "shape": [128, 128, 128],
                "classes_found": [1, 2, 3],
                "class_counts": {1: 15000, 2: 8500, 3: 3200},
                "total_segmented_voxels": 26700
            },
            "saved_path": "/mock/results/test_patient-seg.nii.gz"
        }

        mock_service.run_inference_pipeline.return_value = mock_result

        print("✅ Mocked service with successful result:")
        print(f"   📁 Folder: {mock_result['folder_name']}")
        print(f"   ⏱️ Total time: {mock_result['timing']['total_time']}s")
        print(f"   🎯 Classes found: {mock_result['segmentation']['classes_found']}")

        # Test folder path
        test_folder = Path("/mock/test_patient")

        print("🔄 Running inference on folder...")
        result = run_inference_on_folder(test_folder, save_result=True)

        print(f"✅ Result success: {result.get('success', 'N/A')}")
        print(f"✅ Folder name: {result.get('folder_name', 'N/A')}")
        print(f"✅ Total time: {result.get('timing', {}).get('total_time', 'N/A')}s")
        print(f"✅ Classes found: {result.get('segmentation', {}).get('classes_found', 'N/A')}")
        print(f"✅ Saved path: {result.get('saved_path', 'N/A')}")
        print("🎉 Folder inference test successful!")

        # Verify the service was called correctly
        mock_service.run_inference_pipeline.assert_called_once_with(
            test_folder, True, force_reprocess=False, create_overlay=True
        )

        self.assertTrue(result['success'])
        self.assertEqual(result['folder_name'], 'test_patient')
        self.assertIn('timing', result)

    @patch('src.services.inference.create_inference_service')
    def test_run_inference_on_preprocessed(self, mock_create_service):
        """Test running inference on preprocessed data"""
        print("📋 Testing inference on preprocessed data...")

        from src.services.inference import run_inference_on_preprocessed

        # Mock the service
        mock_service = MagicMock()
        mock_create_service.return_value = mock_service

        # Mock successful inference result
        mock_result = {
            "success": True,
            "folder_name": "preprocessed_patient",
            "timing": {
                "total_time": 3.2
            },
            "segmentation": {
                "shape": [128, 128, 128],
                "classes_found": [1, 2, 4],
                "class_counts": {1: 12000, 2: 7500, 4: 2800}
            },
            "segmentation_array": torch.zeros(128, 128, 128)
        }

        mock_service.run_inference_from_preprocessed.return_value = mock_result

        print("✅ Mocked service with preprocessed result:")
        print(f"   📁 Folder: {mock_result['folder_name']}")
        print(f"   ⏱️ Total time: {mock_result['timing']['total_time']}s")
        print(f"   🎯 Classes found: {mock_result['segmentation']['classes_found']}")

        # Create mock preprocessed tensor
        print("🔄 Creating mock preprocessed tensor...")
        mock_tensor = torch.randn(4, 128, 128, 128)  # 4 modalities
        print(f"✅ Tensor shape: {list(mock_tensor.shape)}")

        print("🔄 Running inference on preprocessed data...")
        result = run_inference_on_preprocessed(mock_tensor, "preprocessed_patient")

        print(f"✅ Result success: {result.get('success', 'N/A')}")
        print(f"✅ Folder name: {result.get('folder_name', 'N/A')}")
        print(f"✅ Total time: {result.get('timing', {}).get('total_time', 'N/A')}s")
        print(f"✅ Segmentation shape: {result.get('segmentation', {}).get('shape', 'N/A')}")
        print("🎉 Preprocessed inference test successful!")

        # Verify the service was called correctly
        mock_service.run_inference_from_preprocessed.assert_called_once_with(
            mock_tensor, "preprocessed_patient"
        )

        self.assertTrue(result['success'])
        self.assertEqual(result['folder_name'], 'preprocessed_patient')

    @patch('src.services.inference.ML_AVAILABLE', True)
    @patch('src.services.inference.get_preprocessor')
    @patch('src.services.inference.get_postprocessor')
    @patch('src.services.inference.get_model_wrapper')
    def test_get_inference_service(self, mock_get_model_wrapper, mock_get_postprocessor, mock_get_preprocessor):
        """Test getting inference service (singleton pattern)"""
        print("📋 Testing inference service singleton...")

        from src.services.inference import get_inference_service, GliomaInferenceService

        # Mock dependencies
        mock_preprocessor = MagicMock()
        mock_postprocessor = MagicMock()
        mock_model_wrapper = MagicMock()

        mock_get_preprocessor.return_value = mock_preprocessor
        mock_get_postprocessor.return_value = mock_postprocessor
        mock_get_model_wrapper.return_value = mock_model_wrapper

        print("✅ Mocked dependencies for singleton test")

        print("🔄 Getting first service instance...")
        service1 = get_inference_service()

        print(f"✅ Service1 type: {type(service1).__name__}")
        print(f"✅ Service1 ID: {id(service1)}")

        print("🔄 Getting second service instance...")
        service2 = get_inference_service()

        print(f"✅ Service2 type: {type(service2).__name__}")
        print(f"✅ Service2 ID: {id(service2)}")

        is_same_instance = service1 is service2
        print(f"✅ Same instance (singleton): {is_same_instance}")

        self.assertIsInstance(service1, GliomaInferenceService)
        self.assertIsInstance(service2, GliomaInferenceService)
        self.assertIs(service1, service2)
        print("🎉 Singleton pattern working correctly!")

    @patch('src.services.inference.ML_AVAILABLE', False)
    def test_inference_service_ml_unavailable(self):
        """Test inference service when ML is not available"""
        print("📋 Testing inference service when ML unavailable...")

        from src.services.inference import create_inference_service

        print("🚫 ML_AVAILABLE set to False")
        print("🔄 Attempting to create inference service...")

        try:
            service = create_inference_service()
            print("❌ Service creation should have failed")
            creation_failed = False
        except ImportError as e:
            print(f"✅ Correctly failed with ImportError: {e}")
            creation_failed = True
        except Exception as e:
            print(f"✅ Failed with exception (expected): {type(e).__name__}: {e}")
            creation_failed = True

        print("🎉 ML unavailable handling working correctly!")
        self.assertTrue(creation_failed)

    def tearDown(self):
        """Clean up after each test"""
        print(f"\n🧹 CLEANUP: {self._testMethodName}")

        # Reset global service
        try:
            import src.services.inference as inf
            inf._inference_service = None
            print("✅ Reset global inference service")
        except:
            print("⚠️ Could not reset inference service")

        print("✅ Inference test cleanup completed")
        print(f"🏁 FINISHED: {self._testMethodName}")
        print(f"{'=' * 60}\n")