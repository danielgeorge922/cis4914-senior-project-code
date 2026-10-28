from pathlib import Path
import tkinter as tk
from tkinter import filedialog
import cv2
import albumentations as A
from tqdm import tqdm

# Number of augmented variants to generate per original image
NUM_VARIANTS = 12


def get_data_folder():
	"""Opens a file explorer window to select either the main project root folder
	or the 'preprocessed_data' folder directly, and resolves the correct paths.
	"""
	root = tk.Tk()
	root.withdraw()

	folder_path = filedialog.askdirectory(
	    title="Select Preprocessed Data"
	)

	if not folder_path:
		print("No folder selected. Exiting program.")
		return None, None

	selected_dir = Path(folder_path)
	print(f"\n[Selected Folder]: {selected_dir}")

	# Case 1: User selected preprocessed_data
	if selected_dir.name == "preprocessed_data":
		preprocessed_dir = selected_dir
		project_root = selected_dir.parent
	# Case 2: User selected the project root containing preprocessed_data
	elif (selected_dir / "preprocessed_data").exists():
		project_root = selected_dir
		preprocessed_dir = project_root / "preprocessed_data"
	else:
		print(
		    "[Error] Selected folder is neither the project data nor a valid preprocessed_data directory."
		)
		return None, None

	return project_root, preprocessed_dir


def get_augmentation_pipeline():
	"""Defines a robust, randomized composite augmentation pipeline tailored
	for botanical classification (fruits and leaves) using modern Albumentations syntax.
	"""
	return A.Compose([
	    # Geometric Transformations
	    A.HorizontalFlip(p=0.5),
	    A.VerticalFlip(p=0.5),
	    A.Rotate(
	        limit=30,
	        border_mode=cv2.BORDER_CONSTANT,
	        fill=(255, 255, 255),
	        p=0.7,
	    ),
	    A.Affine(
	        scale=(0.95, 1.05),
	        translate_percent=(-0.08, 0.08),
	        border_mode=cv2.BORDER_CONSTANT,
	        fill=(255, 255, 255),
	        p=0.5,
	    ),
	    
	    # Photometric / Lighting Variations
	    A.RandomBrightnessContrast(
	        brightness_limit=0.2, contrast_limit=0.2, p=0.6
	    ),
	    A.HueSaturationValue(
	        hue_shift_limit=5, sat_shift_limit=15, val_shift_limit=15, p=0.4
	    ),
	    
	    # Camera Sensor Noise / Imperfections
	    A.GaussNoise(std_range=(0.04, 0.15), p=0.3),
	])


def static_augmentation_pipeline(project_root, preprocessed_root):
	"""Loops through preprocessed data, copies originals, and generates
	randomized composite augmented variations into augmented_data.
	"""
	augmented_root = project_root / "augmented_data"

	categories = ["fruit", "leaves"]
	image_extensions = ("*.jpg", "*.jpeg", "*.png", "*.JPG", "*.JPEG", "*.PNG")

	print("\n[Starting Augmentation Pipeline]")
	print(f"Source Directory: {preprocessed_root}")
	print(f"Target Directory: {augmented_root}")
	print(f"Generating {NUM_VARIANTS} augmented variants per image...\n")

	aug_transform = get_augmentation_pipeline()

	for category in categories:
		cat_dir = preprocessed_root / category
		if not cat_dir.exists():
			continue

		for cultivar_dir in cat_dir.iterdir():
			if not cultivar_dir.is_dir():
				continue
			cultivar_name = cultivar_dir.name

			# Set up destination paths matching the tree structure
			out_cultivar_dir = augmented_root / category / cultivar_name
			out_cultivar_dir.mkdir(parents=True, exist_ok=True)

			image_files = []
			for ext in image_extensions:
				image_files.extend(list(cultivar_dir.glob(ext)))

			if not image_files:
				continue

			for img_path in tqdm(image_files, desc=f"[{category.capitalize()}] {cultivar_name}", unit="img"):
				try:
					# Load image using OpenCV (BGR)
					image = cv2.imread(str(img_path))
					if image is None:
						continue

					# Save the base preprocessed original with an '_orig' suffix
					orig_out_path = out_cultivar_dir / f"{img_path.stem}_orig.jpg"
					if not orig_out_path.exists():
						cv2.imwrite(str(orig_out_path), image, [cv2.IMWRITE_JPEG_QUALITY, 95])

					# Generate randomized composite augmented variants
					for i in range(1, NUM_VARIANTS + 1):
						variant_out_path = out_cultivar_dir / f"{img_path.stem}_aug{i}.jpg"

						# Skip if this specific variant already exists (supports safe re-runs)
						if variant_out_path.exists():
							continue

						# Apply the random augmentation pipeline
						augmented = aug_transform(image=image)
						augmented_image = augmented["image"]

						# Save augmented variant
						cv2.imwrite(
						    str(variant_out_path),
						    augmented_image,
						    [cv2.IMWRITE_JPEG_QUALITY, 95],
						)

				except Exception as e:
					print(f"\n  [Error] Processing file {img_path.name}: {e}")

	print("\n[Success] Augmentation Complete!")


if __name__ == "__main__":
	project_root, preprocessed_root = get_data_folder()
	if project_root and preprocessed_root:
		static_augmentation_pipeline(project_root, preprocessed_root)