"""QLoRA fine-tune for LumynaX-NZ on a single H100 (or any 24GB+ GPU)."""
from __future__ import annotations
import argparse, json
from pathlib import Path

import torch
from datasets import load_dataset
from transformers import (AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig,
                          TrainingArguments)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from trl import SFTTrainer


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base_model", required=True)
    ap.add_argument("--data_dir",   required=True)
    ap.add_argument("--output_dir", required=True)
    ap.add_argument("--epochs", type=float, default=1.5)
    ap.add_argument("--learning_rate", type=float, default=2e-4)
    ap.add_argument("--batch_size", type=int, default=8)
    ap.add_argument("--gradient_accumulation_steps", type=int, default=4)
    ap.add_argument("--max_seq_len", type=int, default=4096)
    ap.add_argument("--lora_r", type=int, default=64)
    ap.add_argument("--lora_alpha", type=int, default=128)
    ap.add_argument("--lora_dropout", type=float, default=0.05)
    ap.add_argument("--bf16", action="store_true")
    args = ap.parse_args()

    print(f"[train_qlora] base={args.base_model}, data={args.data_dir}")
    tok = AutoTokenizer.from_pretrained(args.base_model, trust_remote_code=True)
    if tok.pad_token_id is None: tok.pad_token = tok.eos_token

    bnb = BitsAndBytesConfig(
        load_in_4bit=True, bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16 if args.bf16 else torch.float16,
        bnb_4bit_use_double_quant=True,
    )
    model = AutoModelForCausalLM.from_pretrained(
        args.base_model, quantization_config=bnb,
        device_map="auto", trust_remote_code=True,
        torch_dtype=torch.bfloat16 if args.bf16 else torch.float16,
    )
    model = prepare_model_for_kbit_training(model)
    lora = LoraConfig(
        r=args.lora_r, lora_alpha=args.lora_alpha, lora_dropout=args.lora_dropout,
        bias="none", task_type="CAUSAL_LM",
        target_modules=["q_proj","k_proj","v_proj","o_proj","gate_proj","up_proj","down_proj"],
    )
    model = get_peft_model(model, lora)
    model.print_trainable_parameters()

    train_ds = load_dataset("json", data_files=str(Path(args.data_dir) / "train.jsonl"), split="train")
    eval_ds  = load_dataset("json", data_files=str(Path(args.data_dir) / "eval.jsonl"),  split="train")

    targs = TrainingArguments(
        output_dir=args.output_dir,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        learning_rate=args.learning_rate,
        bf16=args.bf16, fp16=not args.bf16,
        logging_steps=20, save_steps=200, eval_steps=200, eval_strategy="steps",
        save_total_limit=3, warmup_ratio=0.03, lr_scheduler_type="cosine",
        report_to=["tensorboard"], gradient_checkpointing=True,
        ddp_find_unused_parameters=False,
    )

    trainer = SFTTrainer(
        model=model, train_dataset=train_ds, eval_dataset=eval_ds,
        tokenizer=tok, args=targs,
        max_seq_length=args.max_seq_len, dataset_text_field="text",
    )
    trainer.train()
    trainer.save_model(args.output_dir)

    # Save provenance
    (Path(args.output_dir) / "training_args.json").write_text(json.dumps(vars(args), indent=2), encoding="utf-8")
    print(f"[train_qlora] done → {args.output_dir}")


if __name__ == "__main__":
    main()
