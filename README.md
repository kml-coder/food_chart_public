# Food Chart 🍴

**Food Chart** is a full-stack project for food data visualization, machine learning experiments, and web deployment.  
It combines a frontend app, a backend server, and machine learning scripts to explore food-related data, deploy services, and test recommendation models.

---

## 📂 Project Structure

```
food_app/        # Frontend app (Next.js/React, exported and deployed to S3)
food_server/     # Backend server (Flask-based REST API)
food_model/      # Machine learning model scripts and data processing
```

---

## 🚀 Running the Backend (food_server)

### 1. Setup Virtual Environment
```bash
cd food_chart/food_server
python3 -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run Server
```bash
python3 server.py
```

- Default port: **5000**
- To change the port: edit `server.py` → update `app.run(port=XXXX)`

---

## 📦 Running the Frontend (food_app)

### 1. Build Export
```bash
cd food_chart/food_app
npx export
```

### 2. Upload to S3
```bash
aws s3 sync dist/ s3://food-chart-app
```

---

## 🤖 Running the Model (food_model)

### Example: Data scraping
```bash
cd food_chart/food_model/gptgram_model/scrape
python3 scrape.py
python3 clean.py
python3 scrape_xml.py
```

### Example: Model execution
```bash
cd food_chart/food_model/src
python3 model.py
```

---

## ☁️ Deploying on AWS EC2

### 1. Connect to EC2
```bash
chmod 400 kmlcoder.pem
ssh -i kmlcoder.pem ubuntu@<EC2_PUBLIC_IP>
```

### 2. Install Dependencies
```bash
sudo apt update
sudo apt install git -y
sudo apt install -y python3-pip python3-venv
```

### 3. Clone Repo & Setup
```bash
git clone https://github.com/kml-coder/food_chart_public.git
cd food_chart/food_server

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 server.py
```

---

## 🔧 Requirements
- Python 3.8+
- Node.js & npm
- AWS CLI
- AWS account with S3 + EC2
- Git

---

## 📝 Notes
- Configure AWS CLI before S3 sync:
  ```bash
  aws configure
  ```
- On EC2, ensure the **security group inbound rules** allow your server port (e.g., 5000).  
- Replace `<EC2_PUBLIC_IP>` with the actual instance’s public IPv4 address.  
- Keep sensitive files (`.env`, keys, etc.) excluded from public repositories using `.gitignore`.

---
