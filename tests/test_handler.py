import base64
import json
import unittest
from io import BytesIO
from unittest.mock import patch

from PIL import Image

from handler import DEFAULT_MAX_GPX_SIZE_BYTES, lambda_handler


FIXTURE = b'<gpx xmlns="http://www.topografix.com/GPX/1/1"><trk><trkseg><trkpt lat="0" lon="0"/></trkseg></trk></gpx>'
SENSITIVE_BODY = b"PRIVATE-GPX-CONTENT"


def make_png() -> bytes:
    image = Image.new("RGB", (1080, 1920), "#123456")
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def make_event(
    body: str,
    *,
    method: str = "POST",
    path: str = "/v1/generate",
    content_type: str = "application/gpx+xml",
    is_base64_encoded: bool = False,
    query_parameters: dict | None = None,
) -> dict:
    return {
        "version": "2.0",
        "rawPath": path,
        "headers": {"content-type": content_type},
        "queryStringParameters": query_parameters,
        "requestContext": {"http": {"method": method}},
        "body": body,
        "isBase64Encoded": is_base64_encoded,
    }


class LambdaHandlerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.png = make_png()

    def assert_json_error(self, response, status_code: int, code: str):
        self.assertEqual(response["statusCode"], status_code)
        self.assertEqual(response["headers"]["Content-Type"], "application/json")
        self.assertFalse(response["isBase64Encoded"])
        payload = json.loads(response["body"])
        self.assertEqual(payload["code"], code)
        self.assertIsInstance(payload["message"], str)
        self.assertNotIn("Traceback", response["body"])

    def assert_valid_png_response(self, response):
        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(response["headers"]["Content-Type"], "image/png")
        self.assertTrue(response["isBase64Encoded"])
        png = base64.b64decode(response["body"], validate=True)
        self.assertTrue(png.startswith(b"\x89PNG\r\n\x1a\n"))
        with Image.open(BytesIO(png)) as image:
            self.assertEqual(image.format, "PNG")
            self.assertEqual(image.size, (1080, 1920))
            image.verify()

    def test_valid_base64_request_returns_png(self):
        event = make_event(
            base64.b64encode(FIXTURE).decode("ascii"),
            is_base64_encoded=True,
            query_parameters={"theme": "alpine", "lang": "es"},
        )
        with patch("handler.generate_story", return_value=self.png) as generate:
            response = lambda_handler(event, None)

        generate.assert_called_once_with(FIXTURE, theme="alpine", lang="es")
        self.assert_valid_png_response(response)

    def test_valid_text_body_returns_png(self):
        event = make_event(FIXTURE.decode("utf-8"), content_type="application/gpx+xml; charset=utf-8")
        with patch("handler.generate_story", return_value=self.png) as generate:
            response = lambda_handler(event, None)

        generate.assert_called_once_with(FIXTURE, theme="forest", lang="en")
        self.assert_valid_png_response(response)

    def test_method_not_allowed_returns_json(self):
        response = lambda_handler(make_event("gpx", method="GET"), None)
        self.assert_json_error(response, 405, "METHOD_NOT_ALLOWED")

    def test_wrong_path_returns_not_found_json(self):
        response = lambda_handler(make_event("gpx", path="/v1/other"), None)
        self.assert_json_error(response, 404, "NOT_FOUND")

    def test_wrong_content_type_returns_json(self):
        response = lambda_handler(make_event("gpx", content_type="text/plain"), None)
        self.assert_json_error(response, 415, "UNSUPPORTED_MEDIA_TYPE")

    def test_empty_body_returns_json(self):
        response = lambda_handler(make_event(""), None)
        self.assert_json_error(response, 400, "EMPTY_BODY")

    def test_invalid_base64_returns_json(self):
        response = lambda_handler(make_event("not base64!", is_base64_encoded=True), None)
        self.assert_json_error(response, 400, "INVALID_BODY_ENCODING")

    def test_decoded_payload_over_limit_returns_413(self):
        oversized = b"x" * (DEFAULT_MAX_GPX_SIZE_BYTES + 1)
        event = make_event(base64.b64encode(oversized).decode("ascii"), is_base64_encoded=True)
        with patch("handler.generate_story") as generate:
            response = lambda_handler(event, None)

        generate.assert_not_called()
        self.assert_json_error(response, 413, "PAYLOAD_TOO_LARGE")

    def test_invalid_gpx_returns_422_without_echoing_content(self):
        event = make_event(SENSITIVE_BODY.decode("ascii"))
        response = lambda_handler(event, None)

        self.assert_json_error(response, 422, "INVALID_GPX")
        self.assertNotIn(SENSITIVE_BODY.decode("ascii"), response["body"])

    def test_invalid_theme_and_language_return_400(self):
        invalid_requests = (
            ({"theme": "unknown"}, "INVALID_PARAMETERS"),
            ({"lang": "fr"}, "INVALID_PARAMETERS"),
        )
        for parameters, code in invalid_requests:
            with self.subTest(parameters=parameters):
                event = make_event(FIXTURE.decode("utf-8"), query_parameters=parameters)
                with patch("handler.generate_story") as generate:
                    response = lambda_handler(event, None)
                generate.assert_not_called()
                self.assert_json_error(response, 400, code)

    def test_unexpected_service_error_is_hidden_from_response(self):
        event = make_event(SENSITIVE_BODY.decode("ascii"))
        with patch("handler.generate_story", side_effect=RuntimeError("secret /private/path")):
            response = lambda_handler(event, None)

        self.assert_json_error(response, 500, "INTERNAL_ERROR")
        self.assertNotIn("secret", response["body"])
        self.assertNotIn("/private/path", response["body"])
        self.assertNotIn(SENSITIVE_BODY.decode("ascii"), response["body"])

    def test_malformed_http_api_event_returns_json(self):
        response = lambda_handler({"version": "1.0"}, None)
        self.assert_json_error(response, 400, "INVALID_REQUEST")


if __name__ == "__main__":
    unittest.main()
