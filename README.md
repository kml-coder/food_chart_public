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

## 📥 Clone the Repository

First, clone the repository from GitHub and move into the project folder:

```bash
git clone https://github.com/kml-coder/food_chart_public.git
cd food_chart_public
```

Second, download the t5 model from (here)
and unzip it and move "model" folder to food_server folder

---

## 🚀 Running the Backend (food_server)

### 1. Setup Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run Server
```bash
cd food_chart/food_server
python3 server.py
```

- Default port: **5050**
- To change the port: edit `server.py` → update `app.run(port=XXXX)`

---

## Running the Frontend (food_app)

### 1. Start with Expo (Local Development)
```bash
cd food_chart/food_app

# Install dependencies
npm install   # or yarn install

# Start Expo development server
npx expo start
```

---

## 📦 Data scraping from recipe sites
```bash
cd food_chart/food_model/gptgram_model/scrape
python3 scrape_xml.py
python3 scrape.py
python3 clean.py

```

## 🤖 Running the Model (food_model)

### Example: Model execution (need your own dataset)
```bash
cd food_chart/food_model/src
python3 model.py
```

---

## ☁️ Deploying on AWS EC2

### 1. Connect to EC2
```bash
chmod 400 (your own pem)
ssh -i (your own pem) (your own instance ip)
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
cd food_chart
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cd food_chart/food_server

python3 server.py
```

---

## 🔧 Requirements
- Python 3.8+
- Node.js & npm
- Expo
- React
- AWS CLI
- AWS account with S3 + EC2
- Git

---

## 📝 Notes
- Configure AWS CLI before S3 sync:
  ```bash
  aws configure
  ```
- On EC2, ensure the **security group inbound rules** allow your server port (e.g., 5050).  
- Replace `<EC2_PUBLIC_IP>` with the actual instance’s public IPv4 address.  
- Keep sensitive files (`.env`, keys, etc.) excluded from public repositories using `.gitignore`.

---
