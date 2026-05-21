"""Full SFT for LumynaX-NZ on 8× H100. Uses DeepSpeed ZeRO-3 via accelerate."""
from __future__ import annotations
import argparse, json
from pathlib import Path

import torch
from datasets import load_dataset
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments
from trl import SFTTrainer


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base_model", required=True)
    ap.add_argument("--data_dir", required=True)
    ap.add_argument("--output_dir", required=True)
    ap.add_argument("--epochs", type=float, default=3.0)
    ap.add_argument("--learning_rate", type=float, default=1e-5)
    ap.add_argument("--batch_size", type=int, default=16)
    ap.add_argument("--gradient_accumulation_steps", type=int, default=2)
    ap.add_argument("--max_seq_len", type=int, default=4096)
    ap.add_argument("--bf16", action="store_true")
    ap.add_argument("--gradient_checkpointing", action="store_true")
    ap.add_argument("--resume_from", default=None)
    args = ap.parse_args()

    print(f"[train_sft] base={args.base_model}, data={args.data_dir}")
    tok = AutoTokenizer.from_pretrained(args.base_model, trust_remote_code=True)
    if tok.pad_token_id is None: tok.pad_token = tok.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        args.base_model, trust_remote_code=True,
        torch_dtype=torch.bfloat16 if args.bf16 else torch.float16,
        attn_implementation="flash_attention_2",
    )

    train_ds = load_dataset("json", data_files=str(Path(args.data_dir) / "train.jsonl"), split="train")
    eval_ds  = load_dataset("json", data_files=str(Path(args.data_dir) / "eval.jsonl"),  split="train")

    targs = TrainingArguments(
        output_dir=args.output_dir,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        learning_rate=args.learning_rate,
        bf16=args.bf16, fp16=not args.bf16,
        logging_steps=10, save_steps=500, eval_steps=500, eval_strategy="steps",
        save_total_limit=3, warmup_ratio=0.03, lr_scheduler_type="cosine",
        report_to=["tensorboard"],
        gradient_checkpointing=args.gradient_checkpointing,
        ddp_find_unused_parameters=False,
    )

    trainer = SFTTrainer(
        model=model, train_dataset=train_ds, eval_dataset=eval_ds,
        tokenizer=tok, args=targs,
        max_seq_length=args.max_seq_len, dataset_text_field="text",
    )
    trainer.train(resume_from_checkpoint=args.resume_from)
    trainer.save_model(args.output_dir)
    (Path(args.output_dir) / "training_args.json").write_text(json.dumps(vars(args), indent=2), encoding="utf-8")
    print(f"[train_sft] done → {args.output_dir}")


if __name__ == "__main__":
    main()
