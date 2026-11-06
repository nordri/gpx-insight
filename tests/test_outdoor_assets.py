import unittest
from pathlib import Path
from PIL import Image
from rendering.outdoor import ASSET_DIR, scenic_header, footer_landscape, slope_distribution

class OutdoorAssetsTests(unittest.TestCase):
    def test_assets_exist(self):
        self.assertTrue((ASSET_DIR / "mountain-header.jpg").is_file())
        self.assertTrue((ASSET_DIR / "mountain-footer.png").is_file())

    def test_header_and_footer_keep_canvas_size(self):
        image=Image.new("RGB",(1080,1920),"#101F1D")
        scenic_header(image)
        footer_landscape(image)
        self.assertEqual(image.size,(1080,1920))

    def test_slope_distribution_handles_empty_data(self):
        image=Image.new("RGB",(1080,1920))
        from PIL import ImageDraw
        slope_distribution(ImageDraw.Draw(image),50,200,900,{})

if __name__=="__main__":
    unittest.main()
