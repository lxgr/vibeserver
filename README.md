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

### Terms and conditions

It even knows not to take any responsibility for your shenanigans!

<img width="515" alt="image" src="https://github.com/user-attachments/assets/f88cfd15-c09d-49ad-9318-f41f9f536f3e" />

## Feature roadmap

- [ ] Image generation
- [ ] Threads? (but it'll just eat through my token budget faster)
- [ ] Persistence? (probably not)
- [ ] Make it self-hosting (i.e. replace the Python script with an LLM prompt for it, then execute the result)
