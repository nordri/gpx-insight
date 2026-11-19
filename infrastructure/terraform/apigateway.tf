resource "aws_apigatewayv2_api" "gpx_insight" {
  name          = "gpx-insight"
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins = ["http://127.0.0.1:8080"]
    allow_methods = ["POST"]
    allow_headers = ["content-type"]
  }
}

resource "aws_apigatewayv2_integration" "gpx_insight" {
  api_id                 = aws_apigatewayv2_api.gpx_insight.id
  integration_type       = "AWS_PROXY"
  integration_method     = "POST"
  integration_uri        = aws_lambda_function.gpx_insight.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "generate" {
  api_id             = aws_apigatewayv2_api.gpx_insight.id
  route_key          = "POST /v1/generate"
  authorization_type = "NONE"
  target             = "integrations/${aws_apigatewayv2_integration.gpx_insight.id}"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.gpx_insight.id
  name        = "$default"
  auto_deploy = true

  depends_on = [
    aws_apigatewayv2_route.generate,
  ]
}

resource "aws_lambda_permission" "apigateway" {
  statement_id  = "AllowHttpApiInvokeGpxGenerate"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.gpx_insight.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.gpx_insight.execution_arn}/$default/POST/v1/generate"
}
