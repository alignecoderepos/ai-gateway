# AI Gateway

AI Gateway is a powerful proxy service for Large Language Models (LLMs) that enables you to govern, secure, and optimize your AI traffic.

## Features

- **Multi-Provider Support**: Unified API for OpenAI, Anthropic, Google Gemini, AWS Bedrock, Azure OpenAI, and Mistral.
- **Intelligent Routing**: Route requests based on cost, latency, or custom rules with fallback strategies.
- **Content Guardrails**: Apply safety filters to both inputs and outputs.
- **Usage Tracking**: Monitor token usage, costs, and usage patterns.
- **Rate Limiting**: Control traffic at the user or application level.
- **Caching**: Reduce costs and latency with prompt caching.
- **Telemetry**: Track metrics and logs for observability.
- **OAuth & API Keys**: Secure your AI endpoints with robust authentication.

## Installation

### Using pip

```bash
pip install ai-gateway
```

### Using Docker

```bash
docker pull example/ai-gateway
docker run -p 8000:8000 -v ./config.yaml:/app/config.yaml example/ai-gateway
```

### From Source

```bash
git clone https://github.com/example/ai-gateway.git
cd ai-gateway
pip install -e .
```

## Quick Start

1. Create a configuration file:

```yaml
# config.yaml
environment: development
log_level: INFO

http:
  host: 0.0.0.0
  port: 8000
  workers: 1
  cors:
    allow_origins: ["*"]

# Add your API keys
openai_api_key: "your-openai-api-key"
anthropic_api_key: "your-anthropic-api-key"
```

2. Start the server:

```bash
ai-gateway serve
```

3. Make a request:

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [{"role": "user", "content": "Hello, world!"}]
  }'
```

## Routing Models

AI Gateway allows you to define routing strategies for directing requests to different providers. This can be based on percentage distribution, latency optimization, or custom rules.

Example configuration in config.yaml:

```yaml
routers:
  - name: gpt4-router
    type: fallback
    targets:
      - model: openai/gpt-4
        provider: openai
      - model: anthropic/claude-3-opus
        provider: anthropic
```

Then you can use it in your request:

```json
{
  "model": "router/gpt4-router",
  "messages": [{"role": "user", "content": "Hello, world!"}]
}
```

## Documentation

For full documentation, visit [docs.example.com/ai-gateway](https://docs.example.com/ai-gateway).

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the Apache License 2.0 - see the LICENSE file for details.