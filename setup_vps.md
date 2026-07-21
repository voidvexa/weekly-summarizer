# Setting Up Weekly Company News Summarizer on Hetzner VPS (Ubuntu 24.04 LTS)

## 1. Transfer Files
Clone this repository securely to a directory on your VPS, e.g., `~/invest-summarizer`.
```bash
git clone <your-repo-url> ~/invest-summarizer
```

## 2. Set Up Python Environment
SSH into your VPS and run the following commands:
```bash
sudo apt update
sudo apt install python3-venv python3-pip -y

cd ~/invest-summarizer
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 3. Configure the .env File
Copy the `.env` template or create a new one:
```bash
nano .env
```
Ensure it contains:
```
ANTHROPIC_API_KEY=your_anthropic_key_here
ANTHROPIC_MODEL=claude-3-5-sonnet-20240620
EMAIL_SENDER=your_email@gmail.com
EMAIL_PASSWORD=your_app_password_here
EMAIL_RECIPIENT=your_email@gmail.com
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=465
```
Save and exit. Don't forget to fill out your `tickers.txt`!

## 4. Set Up systemd Service
We will run the summarizer as a continuous systemd service that wakes up every Friday at 18:00 (handled internally by `apscheduler`).

Create a new service file:
```bash
sudo nano /etc/systemd/system/weekly-summarizer.service
```

Paste the following configuration (replace `YOUR_USER` with your actual username, e.g. `ubuntu` or `root`):
```ini
[Unit]
Description=Weekly Moat Investor Summarizer Bot
After=network.target

[Service]
Type=simple
User=YOUR_USER
WorkingDirectory=/home/YOUR_USER/invest-summarizer
ExecStart=/home/YOUR_USER/invest-summarizer/venv/bin/python /home/YOUR_USER/invest-summarizer/weekly_summarizer.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## 5. Enable and Start the Service
Reload the systemd daemon to recognize your new service:
```bash
sudo systemctl daemon-reload
```

Enable it to start automatically on boot:
```bash
sudo systemctl enable weekly-summarizer.service
```

Start the bot:
```bash
sudo systemctl start weekly-summarizer.service
```

Check the status and logs to ensure it started correctly and is waiting for Friday:
```bash
sudo systemctl status weekly-summarizer.service
sudo journalctl -u weekly-summarizer.service -f
```
