import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"


class FrontendStaticTests(unittest.TestCase):
    def test_static_assets_are_present_and_linked_locally(self):
        index = (FRONTEND / "index.html").read_text(encoding="utf-8")
        for asset in ("index.html", "styles.css", "app.js", "config.js"):
            self.assertTrue((FRONTEND / asset).is_file(), asset)
        self.assertIn('href="styles.css"', index)
        self.assertIn('src="config.js"', index)
        self.assertIn('src="app.js"', index)
        self.assertNotRegex(index, r"https?://")
        self.assertNotRegex(index, r"<script[^>]+src=[\"']https?://")

    def test_static_configuration_does_not_pin_an_api_identifier(self):
        config = (FRONTEND / "config.js").read_text(encoding="utf-8")
        self.assertRegex(config, r"apiUrl:\s*[\"'][\"']")
        self.assertNotIn("execute-api", config)

    def test_frontend_implements_required_upload_and_request_contract(self):
        app = (FRONTEND / "app.js").read_text(encoding="utf-8")
        self.assertIn("5 * 1024 * 1024", app)
        self.assertIn("endsWith(\".gpx\")", app)
        self.assertIn('themeSelect.value', app)
        self.assertIn('languageSelect.value', app)
        self.assertIn('value="forest"', (FRONTEND / "index.html").read_text(encoding="utf-8"))
        self.assertIn('value="es"', (FRONTEND / "index.html").read_text(encoding="utf-8"))
        self.assertIn('headers: { "Content-Type": "application/gpx+xml" }', app)
        self.assertIn("body: gpxFile", app)
        self.assertIn("response.ok", app)
        self.assertIn("image/png", app)
        self.assertIn("URL.createObjectURL(blob)", app)
        self.assertIn("URL.revokeObjectURL", app)
        self.assertIn("if (isGenerating || !gpxFile)", app)
        self.assertIn("if (isGenerating) {", app)
        self.assertIn("themeSelect.disabled = true", app)
        self.assertIn("anotherRouteButton.disabled = true", app)

    def test_local_server_uses_terraform_outputs_and_loopback(self):
        script = (ROOT / "infrastructure/floci/scripts/serve-frontend.sh").read_text(encoding="utf-8")
        self.assertIn('output -raw api_id', script)
        self.assertIn('output -raw api_invoke_url', script)
        self.assertIn('http.server 8080 --bind 127.0.0.1', script)
        self.assertIn("cp -R", script)
        self.assertNotIn("terraform apply", script)

    def test_http_api_cors_is_restricted_to_the_local_frontend(self):
        api_config = (ROOT / "infrastructure/terraform/apigateway.tf").read_text(encoding="utf-8")
        self.assertRegex(api_config, r'allow_origins\s*=\s*\["http://127\.0\.0\.1:8080"\]')
        self.assertRegex(api_config, r'allow_methods\s*=\s*\["POST"\]')
        self.assertRegex(api_config, r'allow_headers\s*=\s*\["content-type"\]')


if __name__ == "__main__":
    unittest.main()
