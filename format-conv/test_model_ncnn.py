"""
Memory-efficient YOLOv8 NCNN inference on MOVA0571.avi
Processes video with NCNN framework for mobile/edge deployment
"""
import gc
from ultralytics import YOLO
from pathlib import Path

# Configuration
MODEL_PATH = "../Model/v0-20250827.1a_ncnn_model"  # NCNN model directory
VIDEO_PATH = "Vids/MOVA0571.avi"
OUTPUT_NAME = "mova_test_ncnn"

# Detection parameters (optimized)
CONF_THRESHOLD = 0.15
IOU_THRESHOLD = 0.3

def main():
    print("="*70)
    print("🚀 MEMORY-EFFICIENT YOLOV8 NCNN INFERENCE - MOVA0571.AVI")
    print("="*70)
    
    # Verify paths
    model_path = Path(MODEL_PATH)
    video_path = Path(VIDEO_PATH)
    
    if not model_path.exists():
        print(f"❌ Error: NCNN model directory not found at {model_path}")
        print(f"💡 Export your model to NCNN format using:")
        print(f"   from ultralytics import YOLO")
        print(f"   model = YOLO('path/to/model.pt')")
        print(f"   model.export(format='ncnn')")
        print(f"   This creates a directory with .param and .bin files")
        return
    
    # Verify NCNN model files exist (.param and .bin are required)
    param_file = model_path / "model.ncnn.param"
    bin_file = model_path / "model.ncnn.bin"
    
    if not param_file.exists():
        print(f"❌ Error: NCNN .param file not found: {param_file}")
        print(f"💡 The NCNN model requires both .param (structure) and .bin (weights) files")
        return
    
    if not bin_file.exists():
        print(f"❌ Error: NCNN .bin file not found: {bin_file}")
        print(f"💡 The NCNN model requires both .param (structure) and .bin (weights) files")
        return
    
    if not video_path.exists():
        print(f"❌ Error: Video not found at {video_path}")
        return
    
    print(f"\n📁 Model Directory: {model_path}")
    print(f"   - Structure file: model.ncnn.param ✓")
    print(f"   - Weights file: model.ncnn.bin ✓")
    print(f"📁 Video: {video_path}")
    print(f"📊 Settings: conf={CONF_THRESHOLD}, iou={IOU_THRESHOLD}")
    print(f"💾 Memory optimization: ENABLED")
    print(f"🔧 NCNN mobile framework: ENABLED")
    print("\n" + "-"*70)
    
    # Load NCNN model
    print("\n⏳ Loading YOLOv8 NCNN model...")
    try:
        model = YOLO(str(model_path), task='detect')
        print("✓ NCNN model loaded successfully")
    except Exception as e:
        print(f"❌ Failed to load NCNN model: {e}")
        print("💡 Make sure the NCNN model directory contains:")
        print("   - model.ncnn.param (network structure)")
        print("   - model.ncnn.bin (model weights)")
        print(f"\n📂 Current directory contents:")
        for file in model_path.iterdir():
            print(f"   - {file.name}")
        return
    
    # Run inference with memory-efficient settings
    print("\n🎬 Starting video processing with NCNN...")
    print("💡 Processing with memory optimization...")
    print("-"*70 + "\n")
    
    try:
        results = model.predict(
            source=str(video_path),
            conf=CONF_THRESHOLD,
            iou=IOU_THRESHOLD,
            save=True,
            save_txt=True,
            save_conf=True,
            project="runs/detect",
            name=OUTPUT_NAME,
            exist_ok=True,
            max_det=300,
            verbose=True,
            stream=True,  # Stream results to reduce memory usage
            vid_stride=1,  # Process every frame
        )
        
        # Process results in streaming mode to manage memory
        frame_count = 0
        for r in results:
            frame_count += 1
            
            # Periodically force garbage collection every 500 frames
            if frame_count % 500 == 0:
                gc.collect()
                print(f"💾 Memory cleanup at frame {frame_count}")
        
        print("\n" + "-"*70)
        print(f"\n✅ Processing complete! Processed {frame_count} frames")
        print(f"📁 Output saved to: runs/detect/{OUTPUT_NAME}/")
        print(f"   - Annotated video: MOVA0571.avi")
        print(f"   - Detection labels: labels/*.txt")
        print(f"\n🔧 NCNN Performance benefits:")
        print(f"   - Optimized for ARM processors")
        print(f"   - Mobile/embedded device support")
        print(f"   - Vulkan GPU acceleration")
        print(f"   - Low memory footprint")
        print(f"   - Fast inference on edge devices")
        
    except MemoryError as e:
        print(f"\n❌ Memory Error: {e}")
        print("💡 The video is too large. Consider:")
        print("   1. Closing other applications")
        print("   2. Processing in smaller segments")
        print("   3. Using a machine with more RAM")
    except Exception as e:
        print(f"\n❌ Error during processing: {e}")
        print(f"Type: {type(e).__name__}")
    finally:
        # Clean up
        gc.collect()
    
    print("\n" + "="*70)

if __name__ == "__main__":
    main()
