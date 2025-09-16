def main():
    from transformers import T5Tokenizer, T5ForConditionalGeneration, Trainer, TrainingArguments,DataCollatorForSeq2Seq
    from datasets import load_dataset, Dataset
    import pandas as pd
    import evaluate, json

    mae_metric = evaluate.load("mae")

    with open("singular.json") as f:
        raw_data = json.load(f)
    def build_input(row):
        parts = [row.get("unit",""), row.get("size",""), row.get("name","")]
        return "Estimate weight: " + " ".join([p.strip() for p in parts if p.strip() !=""])

    data = []
    for item in raw_data:
        if item.get("gram") and str(item["gram"]).strip() !="":
            input_text = build_input(item).lower()
            data.append({
                "input": input_text,
                "target": str(item["gram"]).strip()
            })
    df = pd.DataFrame(data)
    

    # change input and target in to data from which can be trained 
    dataset = Dataset.from_pandas(df)
    dataset = Dataset.from_pandas(df[["input","target"]])

    # Train split 
    dataset = dataset.train_test_split(test_size = 0.1) # 90퍼센트는 훈련용 10퍼센트는 테스트용

    # Tokenizer and Model
    model_name = "google/flan-t5-base"
    tokenizer = T5Tokenizer.from_pretrained(model_name)
    model = T5ForConditionalGeneration.from_pretrained(model_name)

    #Tokenize function 자연어를 숫자로 바꾸는 과정
    def preprocess(example):
        model_inputs = tokenizer(example["input"], padding="max_length", truncation = True, max_length=64)
        with tokenizer.as_target_tokenizer():
            labels = tokenizer(example["target"], padding = "max_length", truncation = True, max_length = 8)
        labels["input_ids"] = [(label_id if label_id != tokenizer.pad_token_id else -100) for label_id in labels["input_ids"]]
        model_inputs["labels"] = labels["input_ids"]
        return model_inputs
    
    def compute_metrics(eval_pred):
        predictions, labels = eval_pred

        # 예외 처리용
        if isinstance(predictions, tuple):
            predictions = predictions[0]

        # predictions: List[List[List[int]]] or List[List[int]]
        flat_preds = [p[0] if isinstance(p[0], list) else p for p in predictions]
        flat_labels = [l[0] if isinstance(l, list) else l for l in labels]

        decoded_preds = tokenizer.batch_decode(flat_preds, skip_special_tokens=True)
        decoded_labels = tokenizer.batch_decode(flat_labels, skip_special_tokens=True)

        try:
            preds = [float(p.strip()) for p in decoded_preds]
            refs = [float(l.strip()) for l in decoded_labels]
        except ValueError as e:
            print("Decode error: ", e)
            preds = refs = [0.0] * len(decoded_preds)

        mae = mae_metric.compute(predictions=preds, references=refs)
        return {"mae": mae}


    #dataset을 preprocess에 넣음
    print("👉 Tokenizing...")
    tokenized = dataset.map(preprocess)
    # df["input_token_len"] = df["input"].apply(lambda x: len(tokenizer(x)["input_ids"]))
    # print("max_token_lenght: ", df["input_token_len"].max())
    # print("mean_token_lenght: ", df["input_token_len"].mean())
    # Training settings
    training_args = TrainingArguments(
        output_dir="/opt/ml/model",
        evaluation_strategy= "epoch",
        # save_strategy="epoch",
        per_device_train_batch_size=8,
        per_device_eval_batch_size=4,
        # fp16=True,
        num_train_epochs= 20,
        save_total_limit = 1,
        logging_dir='./logs',
        logging_steps=10,
        weight_decay = 0.01,
        # label_smoothing_factor=0.1,
        # load_best_model_at_end = True,
        # metric_for_best_model = "mae",
        # greater_is_better = False,
    )
    data_collator = DataCollatorForSeq2Seq(tokenizer=tokenizer, model=model)
    #Trainer
    trainer = Trainer(
        model=model,
        args = training_args,
        train_dataset = tokenized["train"],
        eval_dataset = tokenized["test"],
        tokenizer = tokenizer,
        # compute_metrics = compute_metrics,
        data_collator = data_collator
    )
    #train time
    print("👉 Training started...")
    trainer.train()
    print("✅ Training complete!")

    #save model
    trainer.save_model("./saved_model")
    tokenizer.save_pretrained("./saved_model")

if __name__ == "__main__":
    main()

