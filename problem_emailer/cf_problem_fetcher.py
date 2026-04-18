#!/usr/bin/env python3
"""
Codeforces Random Problem Fetcher
Emails a random problem from Codeforces daily at midnight within a specified difficulty range.
"""

import requests
import random
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta

def fetch_problems(min_rating=800, max_rating=3500):
    """Fetch all problems from Codeforces API within the rating range."""
    print(f"Fetching problems with rating between {min_rating} and {max_rating}...")
    
    try:
        response = requests.get("https://codeforces.com/api/problemset.problems")
        response.raise_for_status()
        data = response.json()
        
        if data['status'] != 'OK':
            print(f"Error: API returned status {data['status']}")
            return []
        
        # Filter problems by rating
        problems = data['result']['problems']
        filtered = [
            p for p in problems 
            if 'rating' in p and min_rating <= p['rating'] <= max_rating
        ]
        
        print(f"Found {len(filtered)} problems in the specified range.")
        return filtered
        
    except requests.RequestException as e:
        print(f"Error fetching problems: {e}")
        return []

def send_email(problem, recipient_email, smtp_server, smtp_port, sender_email, sender_password):
    """Send problem via email."""
    contest_id = problem.get('contestId', 'N/A')
    index = problem.get('index', 'N/A')
    name = problem.get('name', 'Unknown')
    rating = problem.get('rating', 'Unrated')
    tags = ', '.join(problem.get('tags', []))
    link = f"https://codeforces.com/problemset/problem/{contest_id}/{index}"
    
    # Create email
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"🎯 Daily Codeforces Problem - {name}"
    msg['From'] = sender_email
    msg['To'] = recipient_email
    
    # Plain text version
    text = f"""
Daily Codeforces Problem
{datetime.now().strftime('%Y-%m-%d')}

Problem: {name}
Rating: {rating}
Tags: {tags if tags else 'None'}

Solve it here: {link}

Happy coding!
"""
    
    # HTML version
    html = f"""
    <html>
      <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; border-radius: 10px 10px 0 0;">
          <h2 style="color: white; margin: 0;">🎯 Daily Codeforces Problem</h2>
          <p style="color: #e0e0e0; margin: 5px 0 0 0;">{datetime.now().strftime('%B %d, %Y')}</p>
        </div>
        <div style="background: #f5f5f5; padding: 20px; border-radius: 0 0 10px 10px;">
          <h3 style="color: #333; margin-top: 0;">{name}</h3>
          <p style="color: #666;"><strong>Rating:</strong> <span style="color: #667eea; font-weight: bold;">{rating}</span></p>
          <p style="color: #666;"><strong>Tags:</strong> {tags if tags else 'None'}</p>
          <a href="{link}" style="display: inline-block; background: #667eea; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; margin-top: 10px;">Solve Problem</a>
          <p style="color: #999; font-size: 12px; margin-top: 20px;">Happy coding! 💻</p>
        </div>
      </body>
    </html>
    """
    
    msg.attach(MIMEText(text, 'plain'))
    msg.attach(MIMEText(html, 'html'))
    
    try:
        # Send email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
        print(f"✅ Email sent successfully to {recipient_email}")
        return True
    except Exception as e:
        print(f"❌ Error sending email: {e}")
        return False

def display_problem(problem):
    """Display problem information in a formatted way."""
    contest_id = problem.get('contestId', 'N/A')
    index = problem.get('index', 'N/A')
    name = problem.get('name', 'Unknown')
    rating = problem.get('rating', 'Unrated')
    tags = ', '.join(problem.get('tags', []))
    
    print("\n" + "="*60)
    print(f"🎯 RANDOM CODEFORCES PROBLEM")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    print(f"Problem: {name}")
    print(f"Rating: {rating}")
    print(f"Tags: {tags if tags else 'None'}")
    print(f"Link: https://codeforces.com/problemset/problem/{contest_id}/{index}")
    print("="*60 + "\n")

def get_seconds_until_midnight():
    """Calculate seconds until next midnight."""
    now = datetime.now()
    tomorrow = now + timedelta(days=1)
    midnight = datetime(tomorrow.year, tomorrow.month, tomorrow.day, 0, 0, 0)
    return (midnight - now).total_seconds()

def main():
    """Main function to run the daily problem fetcher."""
    print("Codeforces Random Problem Emailer")
    print("="*60)
    
    # Get email configuration
    print("\nEmail Configuration:")
    recipient_email = input("Enter your email address: ")
    sender_email = input("Enter sender email (e.g., your Gmail): ")
    sender_password = input("Enter sender email password/app password: ")
    
    # SMTP configuration (default for Gmail)
    use_gmail = input("Using Gmail? (y/n, default y): ").lower() or 'y'
    if use_gmail == 'y':
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        print("\n⚠️  Note: For Gmail, use an App Password, not your regular password.")
        print("Generate one at: https://myaccount.google.com/apppasswords")
    else:
        smtp_server = input("Enter SMTP server (e.g., smtp.gmail.com): ")
        smtp_port = int(input("Enter SMTP port (default 587): ") or "587")
    
    # Get difficulty range from user
    print("\nDifficulty Range:")
    try:
        min_rating = int(input("Enter minimum difficulty (default 800): ") or "800")
        max_rating = int(input("Enter maximum difficulty (default 3500): ") or "3500")
        
        if min_rating < 800 or max_rating > 3500 or min_rating > max_rating:
            print("Invalid range. Using defaults: 800-3500")
            min_rating, max_rating = 800, 3500
            
    except ValueError:
        print("Invalid input. Using defaults: 800-3500")
        min_rating, max_rating = 800, 3500
    
    print(f"\nStarting daily problem emailer (Range: {min_rating}-{max_rating})")
    print("Problems will be emailed at midnight (12:00 AM)")
    print("Press Ctrl+C to stop\n")
    
    # Fetch problems once at start
    problems = fetch_problems(min_rating, max_rating)
    
    if not problems:
        print("No problems found. Exiting.")
        return
    
    try:
        # Display first problem immediately if starting close to midnight
        # Otherwise wait until midnight
        now = datetime.now()
        if now.hour == 0 and now.minute < 5:
            problem = random.choice(problems)
            display_problem(problem)
            send_email(problem, recipient_email, smtp_server, smtp_port, sender_email, sender_password)
        
        while True:
            # Calculate time until next midnight
            wait_time = get_seconds_until_midnight()
            hours = int(wait_time // 3600)
            minutes = int((wait_time % 3600) // 60)
            
            print(f"Next problem at midnight (in {hours}h {minutes}m)...")
            time.sleep(wait_time)
            
            # Display and email a random problem at midnight
            problem = random.choice(problems)
            display_problem(problem)
            send_email(problem, recipient_email, smtp_server, smtp_port, sender_email, sender_password)
            
    except KeyboardInterrupt:
        print("\n\nStopping problem emailer. Goodbye!")

if __name__ == "__main__":
    main()
