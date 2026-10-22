from PIL import Image

# Same detector and steps as ml-models/scripts/crop_fruit.py, so uploads match the retrieval gallery.
MODEL = "google/owlvit-base-patch32"


class FruitCropper:
    """Crops each photo to the mango (dropping the label card and ruler) with OWL-ViT."""

    def __init__(self):
        import torch
        from transformers import AutoModelForZeroShotObjectDetection, AutoProcessor

        self.torch = torch
        self.processor = AutoProcessor.from_pretrained(MODEL)
        self.model = AutoModelForZeroShotObjectDetection.from_pretrained(MODEL).eval()

    def crop(self, image: Image.Image) -> Image.Image:
        small = image.copy()
        small.thumbnail((1024, 1024))
        inputs = self.processor(text=[["a mango fruit"]], images=small, return_tensors="pt")
        with self.torch.no_grad():
            outputs = self.model(**inputs)
        result = self.processor.post_process_grounded_object_detection(
            outputs, threshold=0.0, target_sizes=[(small.height, small.width)]
        )[0]
        if len(result["scores"]) == 0:
            return image
        scale = image.width / small.width
        x0, y0, x1, y1 = (float(v) * scale for v in result["boxes"][int(result["scores"].argmax())])
        # Keep a 10% margin around the box.
        dx, dy = (x1 - x0) * 0.10, (y1 - y0) * 0.10
        crop = image.crop((
            int(max(0, x0 - dx)), int(max(0, y0 - dy)),
            int(min(image.width, x1 + dx)), int(min(image.height, y1 + dy)),
        ))
        crop.thumbnail((1024, 1024))
        return crop


class NoCrop:
    """The classifier was trained on whole photos."""

    def crop(self, image: Image.Image) -> Image.Image:
        return image
