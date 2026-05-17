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
prompt = '<|im_start|>user\nExplain in two short paragraphs what LumynaX NZ 3B V1 is, what it is good for, and how it differs from the Tiny seed release.<|im_end|>\n<|im_start|>assistant\n'
encoded = tokenizer(prompt, return_tensors="pt")
output = model.generate(
    **encoded,
    max_new_tokens=192,
    do_sample=False,
    pad_token_id=tokenizer.eos_token_id,
)
generated = tokenizer.decode(
    output[0][encoded["input_ids"].shape[-1]:],
    skip_special_tokens=True,
).strip()
print(generated)
