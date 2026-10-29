from pathlib import Path
import tkinter as tk
from tkinter import filedialog
import numpy as np
from PIL import Image
from rembg import new_session, remove
from tqdm import tqdm

# Maximum dimension for faster CPU processing
MAX_DIMENSION = 1200

# Final image size
NUM_PIXELS = 224

def get_data_folder():
	"""Opens a file explorer window to select the root dataset folder,
	validates its structure, and lists the detected cultivars.
	"""
	# Initialize Tkinter and hide the main root window
	root = tk.Tk()
	root.withdraw()

	# Open file explorer
	folder_path = filedialog.askdirectory(
		title="Select Main Mango Dataset Folder"
	)

	# Exit if nothing selected
	if not folder_path:
		print("No folder selected. Exiting program.")
		return None

	root_dir = Path(folder_path)
	print(f"\n[Selected Root Directory]: {root_dir}")

	# Define subdirectories
	fruit_dir = root_dir / "fruit"
	leaves_dir = root_dir / "leaves"

	# Validate structure
	if not fruit_dir.exists() or not leaves_dir.exists():
		print('Invalid folder structure. Main data folder should have a "leaves" and a "fruit" folder')
		return None

	return root_dir

def preprocessing_pipeline(root_dir):
	"""Batch dataset pipeline using the modular preprocess_single_image function
	without blur segregation.
	"""
	preprocessed_root = root_dir / "preprocessed_data"
	image_extensions = ("*.jpg", "*.jpeg", "*.png", "*.JPG", "*.JPEG", "*.PNG")

	print("\nInitializing Preprocessing")
	print(f"Saving to: {preprocessed_root}\n")
	
	cpu_session = new_session("u2netp")

	for category in ["fruit", "leaves"]:
		cat_dir = root_dir / category
		if not cat_dir.exists():
			continue

		for cultivar_dir in cat_dir.iterdir():
			if not cultivar_dir.is_dir():
				continue
			cultivar_name = cultivar_dir.name

			out_cultivar_dir = preprocessed_root / category / cultivar_name
			out_cultivar_dir.mkdir(parents=True, exist_ok=True)

			image_files = []
			for ext in image_extensions:
				image_files.extend(list(cultivar_dir.glob(ext)))

			if not image_files:
				continue

			for img_path in tqdm(image_files, desc=f"[{category.capitalize()}] {cultivar_name}", unit="img"):
				try:
					# Skip processing if the preprocessed file already exists
					out_path = out_cultivar_dir / f"{img_path.stem}.jpg"
					if out_path.exists():
						continue

					# Process directly via shared modular function
					final_img = preprocess_single_image(img_path, session=cpu_session)

					# Save final preprocessed image
					final_img.save(out_path, "JPEG", quality=95)

				except Exception as e:
					print(f"\n  [Error] Processing file {img_path.name}: {e}")

	print("\nPreprocessing complete!")
	print(f"Processed dataset saved to: {preprocessed_root}")


def preprocess_single_image(img_path, session=None):
	"""Core shared function: Takes a single image path, pre-scales,

	removes background, tight-crops, and letterboxes to 224x224.
	Returns a PIL Image ready for classification or saving.
	"""
	# Load image via PIL
	pil_img = Image.open(img_path).convert("RGB")

	# Pre-scale large images to speed up processing
	w, h = pil_img.size
	if max(w, h) > MAX_DIMENSION:
		scale_factor = MAX_DIMENSION / float(max(w, h))
		new_size = (int(w * scale_factor), int(h * scale_factor))
		resampling_filter = (
		    Image.Resampling.LANCZOS if hasattr(Image, "Resampling") else Image.ANTIALIAS
		)
		pil_img = pil_img.resize(new_size, resampling_filter)

	# Background removal
	input_rgba = pil_img.convert("RGBA")
	if session:
		output_removed = remove(input_rgba, session=session)
	else:
		output_removed = remove(input_rgba)

	# Crop to remove excess dead space
	bbox = output_removed.getbbox()
	if bbox:
		output_removed = output_removed.crop(bbox)

	# Composite onto a pure white background
	white_bg = Image.new("RGBA", output_removed.size, (255, 255, 255, 255))
	combined = Image.alpha_composite(white_bg, output_removed).convert("RGB")

	# Resize. Preserve aspect ratio
	final_img = letterbox_resize(
	    combined, target_size=(NUM_PIXELS, NUM_PIXELS), bg_color=(255, 255, 255)
	)

	return final_img


def letterbox_resize(image, target_size=(NUM_PIXELS, NUM_PIXELS), bg_color=(255, 255, 255)):
	"""Resizes an image to target_size while preserving its original aspect ratio,
	padding the remaining area with the specified background color.
	"""
	w, h = image.size
	target_w, target_h = target_size

	# Compute scaling factor
	scale = min(target_w / w, target_h / h)
	new_w = int(w * scale)
	new_h = int(h * scale)

	# Resize image
	resampling_filter = (
		Image.Resampling.LANCZOS if hasattr(Image, "Resampling") else Image.ANTIALIAS
	)
	resized_img = image.resize((new_w, new_h), resampling_filter)

	# Create background canvas
	new_img = Image.new("RGB", target_size, bg_color)

	# Center the resized image on the canvas
	paste_x = (target_w - new_w) // 2
	paste_y = (target_h - new_h) // 2
	new_img.paste(resized_img, (paste_x, paste_y))

	return new_img


def run_inference_preprocessing(image_path, session=None):
	"""Inference helper function: Processes a single user-uploaded image
	without folder loops, returning a numpy array ready for the model.
	"""
	try:
		processed_img = preprocess_single_image(image_path, session=session)
		img_array = np.array(processed_img, dtype=np.float32) / 255.0
		return img_array
	except Exception as e:
		print(f"[Error] Inference preprocessing failed for {image_path}: {e}")
		return None


if __name__ == "__main__":
	dataset_root = get_data_folder()
	if dataset_root:
		preprocessing_pipeline(dataset_root)