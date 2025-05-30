# Install required packages
# !pip install transformers datasets accelerate torchaudio wandb

import torch
import torch.nn as nn
from transformers import (
    AutoProcessor,
    MusicgenForConditionalGeneration,
    TrainingArguments,
    Trainer
)
from datasets import Dataset, Audio
import pandas as pd
import numpy as np
import torchaudio
from tqdm import tqdm
import wandb

# Initialize GPU monitoring
wandb.init(project="musicgen-finetune", settings=wandb.Settings(code_dir="."))

# Load model and processor
model_name = "facebook/musicgen-small"
processor = AutoProcessor.from_pretrained(model_name)
model = MusicgenForConditionalGeneration.from_pretrained(model_name)

# Move model to GPU if available
device = "cuda" if torch.cuda.is_available() else "cpu"
model = model.to(device)
print(f"Using device: {device}")

# Load and prepare dataset
def load_dataset(csv_path, sample_size=100):
    df = pd.read_csv(csv_path)
    df = df.head(sample_size)  # Use smaller subset for minimal training
    dataset = Dataset.from_pandas(df)
    dataset = dataset.cast_column("audio_path", Audio())
    return dataset

dataset = load_dataset("your_dataset.csv", sample_size=100)

# Audio processing functions
def resample_audio(audio_array, original_sr, target_sr=32000):
    if original_sr != target_sr:
        resampler = torchaudio.transforms.Resample(orig_freq=original_sr, new_freq=target_sr)
        audio_tensor = torch.from_numpy(audio_array).float()
        return resampler(audio_tensor).numpy()
    return audio_array

# Process dataset
def preprocess_function(examples):
    processed_data = {"input_ids": [], "attention_mask": [], "labels": []}
    
    for audio, genre in zip(examples["audio_path"], examples["genre"]):
        # Process audio
        audio_array = audio["array"]
        sr = audio["sampling_rate"]
        audio_array = resample_audio(audio_array, sr)
        
        # Process text
        text = f"Genre: {genre}"
        inputs = processor(
            text=[text],
            padding="max_length",
            truncation=True,
            max_length=512,
            return_tensors="pt"
        )
        
        # Store processed data
        processed_data["input_ids"].append(inputs["input_ids"].squeeze(0))
        processed_data["attention_mask"].append(inputs["attention_mask"].squeeze(0))
        
        # Convert audio to tensor (dummy processing for demonstration)
        # Replace with actual audio feature extraction as needed
        audio_tensor = torch.from_numpy(audio_array).float()
        processed_data["labels"].append(audio_tensor)
        
    return processed_data

# Apply preprocessing
dataset = dataset.map(
    preprocess_function,
    batched=True,
    batch_size=2,
    remove_columns=["audio_path", "genre"]
)

# Split dataset
dataset = dataset.train_test_split(test_size=0.1)

# Training configuration
training_args = TrainingArguments(
    output_dir="./results",
    evaluation_strategy="steps",
    eval_steps=50,
    learning_rate=1e-5,
    per_device_train_batch_size=1,
    gradient_accumulation_steps=4,
    per_device_eval_batch_size=1,
    num_train_epochs=1,
    fp16=True,
    logging_dir="./logs",
    report_to="wandb",
    save_total_limit=2,
    optim="adamw_torch",
)

# Custom Trainer for GPU monitoring
class CustomTrainer(Trainer):
    def training_step(self, model, inputs):
        # Monitor GPU usage
        if torch.cuda.is_available():
            gpu_usage = torch.cuda.memory_allocated() / 1024**3
            wandb.log({"GPU Memory (GB)": gpu_usage})
        
        return super().training_step(model, inputs)

# Initialize Trainer
trainer = CustomTrainer(
    model=model,
    args=training_args,
    train_dataset=dataset["train"],
    eval_dataset=dataset["test"],
)

# Start training
print("Starting training...")
trainer.train()

# Save model
model.save_pretrained("./fine-tuned-musicgen")
processor.save_pretrained("./fine-tuned-musicgen")

# Inference function
def generate_music(prompt, max_length=512):
    inputs = processor(
        text=[prompt],
        padding=True,
        truncation=True,
        max_length=512,
        return_tensors="pt"
    ).to(device)
    
    with torch.no_grad():
        audio_values = model.generate(**inputs, max_new_tokens=max_length)
    
    # Convert to numpy array and save
    audio = audio_values[0].cpu().numpy()
    return audio

# Example usage
generated_audio = generate_music("Genre: Jazz")
sampling_rate = model.config.audio_encoder.sampling_rate

# Save output
from scipy.io.wavfile import write
write("generated_music.wav", sampling_rate, generated_audio)
