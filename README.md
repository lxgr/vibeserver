# Vibeserver

Delegation is the key to success, and web servers are no exception.

Vibeserver is a ~mostly~ occasionally RFC 2616 and W3C HTML compliant webserver that will answer all requests by invoking an LLM which generates the response on-the-fly – or crash trying.

## Setup

- Install [uv](https://github.com/astral-sh/uv) or otherwise install the Python packages [llm](https://llm.datasette.io/en/stable/) and your preferred model adapter. I've successfully tested [llm-mlx](https://github.com/ml-explore/mlx-lm) locally on a Macbook Pro and [llm-openrouter](https://github.com/simonw/llm-openrouter) as an API-based service.
  - For API-based models, you'll need to set up an API key
  - Local models have to be instlled per your plugin's instructions. For `mlx-llm`, running `llm install llm-mlx` and then `llm mlx download-model <modelname>` should do the trick. Non-thinking models work best for acceptable latency.
- Configure your desired port number as `PORT` and model name as `MODEL_NAME`.

## Examples

### APIs
```
➜  ~ curl http://localhost:3000/api/myip
{
  "ip": "2<redacted>:1"
}%
```

### Blog posts

`http://localhost:3000/blog/2025/05/go-got-it-wrong-why-null-strings-are-essential.html`:
<img width="1061" alt="image" src="https://github.com/user-attachments/assets/55e01489-d1db-4bc4-8c68-a1778d81a22f" />

### Guestbook

Leave a message!

<img width="1004" alt="image" src="https://github.com/user-attachments/assets/17f4238e-f534-4c7f-92c6-bb491c72d23e" />

### 3D graphics

It knows GLSL!

<img width="812" alt="image" src="https://github.com/user-attachments/assets/38aadd20-1f4f-4b99-a573-c6dc1d286df9" />

### Creepypasta

<img width="1266" alt="image" src="https://github.com/user-attachments/assets/8611d3ad-b6a5-43bf-85af-a33b7235c68d" />

## Feature roadmap

- [ ] Image generation
- [ ] Threads? (but it'll just eat through my token budget faster)
- [ ] Persistence? (probably not)
- [ ] Make it self-hosting (i.e. replace the Python script with an LLM prompt for it, then execute the result)

## Warnings

The output of this web server is inherently unpredictable. It might generate things you do not agree with or want to have hosted on your website.

It will also serve *all* incoming requests, including those for robots.txt, and it might happily invite crawlers in that could then quickly churn through a prepaid LLM API key's budget, or rack up high costs on a billed one.

Access control is accordingly advisable for several resons.

See also [license.txt].
