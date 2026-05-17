import sys
from pathlib import Path

from transformers import AutoModelForCausalLM, AutoTokenizer

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

model_dir = Path(__file__).resolve().parent / "merged_model"
tokenizer = AutoTokenizer.from_pretrained(model_dir)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token
model = AutoModelForCausalLM.from_pretrained(model_dir)
model.generation_config.temperature = None
model.generation_config.top_p = None
model.generation_config.top_k = None
encoded = tokenizer("Aotearoa is", return_tensors="pt")
output = model.generate(
    **encoded,
    max_new_tokens=48,
    do_sample=False,
    pad_token_id=tokenizer.eos_token_id,
)
print(tokenizer.decode(output[0], skip_special_tokens=True).strip())
