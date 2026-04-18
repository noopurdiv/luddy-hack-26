# 📦 OCR + Adaptive Compression Pipeline

A two-stage microservice pipeline that performs **Optical Character Recognition (OCR)** on images and then **compresses the extracted text** using a custom **Adaptive Huffman-based codec**.

---

## 🚀 Overview

This project consists of:

- **Stage 1 – OCR Microservice**
  - Extracts text from images using a CNN-based model
- **Stage 2 – Compression Microservice**
  - Compresses and decompresses extracted text using:
    - Burrows-Wheeler Transform (BWT)
    - Move-To-Front (MTF)
    - Adaptive Huffman Encoding

---

## 🏗️ Architecture

### Pipeline Flow



Image Input → OCR Service → Extracted Text → Compression Service → Compressed Output
↓
Decompression → Recovered Text



---

## 🔹 Components

### 🖥️ Frontend
- React (Vite + Nginx)
- Runs on port `3000`
- Sends requests to backend services

---

### 🔍 Stage 1: OCR Service (`service_ocr:8001`)

- Built with **FastAPI**

#### Endpoints:
- `POST /ocr` – Perform OCR
- `POST /ocr/async` – Async OCR via Celery
- `GET /ocr/accuracy` – Model performance

#### Model:
- CNN-based (MNIST-style)
- TensorFlow implementation
- >95% validation accuracy

#### Features:
- Inference routing:
  - MNIST CNN (primary)
  - SimpleHTR (optional)
  - Tesseract fallback
- Async processing with **Celery**

---

### 📦 Stage 2: Compression Service (`service_compress:8002`)

- Built with **FastAPI**

#### Endpoints:
- `POST /compress`
- `POST /decompress`

#### Compression Pipeline:
1. BWT (Burrows-Wheeler Transform)
2. MTF (Move-To-Front Encoding)
3. Adaptive Huffman Encoding

#### Decompression:
- Huffman Decode → Inverse MTF → Inverse BWT

---

### ⚡ Redis (`:6379`)
- Message broker for Celery
- Result backend

---

## 📁 Repository Structure



.
├── stage1_service_ocr/
│   ├── app/
│   ├── models/
│   ├── routes/
│   └── requirements.txt
│
├── stage2_service_compress/
│   ├── app/
│   ├── codecs/
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   └── nginx/
│
├── model_weights/
├── docker-compose.yml
└── README.md



---

## 🧠 Model Weights

### Option 1: Use Pretrained Weights
Place weights inside:


model_weights/

`

### Option 2: Train the Model

1. Prepare dataset (e.g., MNIST or custom OCR dataset)
2. Train:
bash
python train.py
`

3. Save weights:

bash
model.save("model_weights/cnn_model.h5")


---

## ⚙️ Setup Instructions

### 🔧 Prerequisites

* Docker & Docker Compose
* Python 3.9+
* Node.js (for frontend)

---

### 🐳 Run with Docker

bash
docker-compose up --build


Services:

* Frontend → [http://localhost:3000](http://localhost:3000)
* OCR Service → [http://localhost:8001](http://localhost:8001)
* Compression Service → [http://localhost:8002](http://localhost:8002)

---

### 🖥️ Manual Setup

#### Stage 1 (OCR)

bash
cd stage1_service_ocr
pip install -r requirements.txt
uvicorn app.main:app --port 8001


#### Stage 2 (Compression)

bash
cd stage2_service_compress
pip install -r requirements.txt
uvicorn app.main:app --port 8002


---

## 📡 API Usage

### OCR


POST /ocr


**Input:** Image file
**Output:**

json
{
  "text": "recognized text"
}


---

### Compress


POST /compress


**Input:**

json
{
  "text": "your text"
}


**Output:**

json
{
  "compressed": "encoded_string"
}


---

### Decompress


POST /decompress


**Input:**

json
{
  "compressed": "encoded_string"
}


**Output:**

json
{
  "text": "original text"
}


---

## 🎥 Demo

Demonstration should include:

1. Upload image
2. OCR extracts text
3. Text is compressed
4. Decompressed back to original

👉 Demo video link here
https://youtu.be/SG5jX-Gpy_A?si=ITXoZX2btBkLzrD0


## 🎤 3-Minute Presentation (Guide)

* **Problem:** Extract + efficiently store text from images
* **Solution:** OCR + custom compression pipeline
* **Arch## 🎤 3-Minute Presentation (Guide)

* **Problem:** Extract + efficiently store text from images
* **Solution:** OCR + custom compression pipeline
* **Architecture:** React + FastAPI + Redis + Celery
* **Demo:** End-to-end pipeline
* **Impact:** Efficient, scalable, modular system

---

## ✨ Features

* 🔍 High OCR accuracy (>95%)
* ⚡ Async processing (Celery)
* 📦 Custom compression pipeline
* 🔄 Lossless decompression
* 🧩 Microservice architecture

---

## 📌 Future Improvements

* Multi-language OCR
* Improved compression ratios
* Streaming large files
* Enhanced UI
