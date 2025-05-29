import numpy as np
import rasterio
import os
import sys

def load_image(path):
    with rasterio.open(path) as src:
        image = src.read()  # shape: [bands, height, width]
        profile = src.profile
    return image.astype(np.float32), profile

def normalize_image(img):
    norm_img = np.zeros_like(img)
    for b in range(img.shape[0]):
        band = img[b]
        min_val, max_val = np.min(band), np.max(band)
        if max_val - min_val > 0:
            norm_img[b] = (band - min_val) / (max_val - min_val)
    return norm_img

def detect_changes(before_img, after_img, threshold=0.1):
    assert before_img.shape == after_img.shape, "Image dimensions must match"

    before = normalize_image(before_img)
    after = normalize_image(after_img)

    diff = np.abs(before - after)
    mean_diff = np.mean(diff, axis=0)

    change_mask = mean_diff > threshold
    added_mask = ((after > before).mean(axis=0) > 0.5) & change_mask
    removed_mask = ((before > after).mean(axis=0) > 0.5) & change_mask

    return added_mask, removed_mask

def create_masked_image(added_mask, removed_mask):
    h, w = added_mask.shape
    mask = np.zeros((h, w, 3), dtype=np.uint8)
    mask[added_mask] = [0, 255, 0]     # Green
    mask[removed_mask] = [255, 0, 0]   # Red
    return mask

def save_mask_as_tif(mask, reference_profile, output_path='change_mask123.tif'):
    profile = reference_profile.copy()
    profile.update({
        'count': 3,
        'dtype': 'uint8',
        'photometric': 'RGB',
        'interleave': 'pixel'
    })
    mask_tif = mask.transpose(2, 0, 1)  # [H, W, 3] -> [3, H, W]

    with rasterio.open(output_path, 'w', **profile) as dst:
        dst.write(mask_tif)

    print(f"[INFO] GeoTIFF change mask saved to {output_path}")

def check_format_compatibility(before_path, after_path):
    before_ext = os.path.splitext(before_path)[1].lower()
    after_ext = os.path.splitext(after_path)[1].lower()
    allowed = ['.tif', '.img']
    if before_ext != after_ext or before_ext not in allowed:
        print(f"[ERROR] Input formats must match and be either .tif or .img (got: '{before_ext}', '{after_ext}')")
        sys.exit(1)

def main(before_path, after_path, output_path='change_mask123.tif'):
    check_format_compatibility(before_path, after_path)

    before_img, before_profile = load_image(before_path)
    after_img, _ = load_image(after_path)

    print(f"[INFO] Loaded images with shape: {before_img.shape}")

    added_mask, removed_mask = detect_changes(before_img, after_img)
    print(f"[INFO] Detected changes — Added: {np.sum(added_mask)}, Removed: {np.sum(removed_mask)}")

    masked_image = create_masked_image(added_mask, removed_mask)
    save_mask_as_tif(masked_image, before_profile, output_path)

if __name__ == "__main__":
    # Replace these with your actual file paths
    before_input = 'E:/CID/CD/data/mumbai_rail_50cm_data/05-11-2017_crop_image.img'
    after_input = 'E:/CID/CD/data/mumbai_rail_50cm_data/26-10-2021_crop_image.img'
    output_mask = 'E:/CID/CD/data/change_masked.tif'

    if os.path.exists(before_input) and os.path.exists(after_input):
        main(before_input, after_input, output_mask)
    else:
        print("[ERROR] Input files not found. Please ensure both files exist.")
