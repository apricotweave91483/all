#!/usr/bin/env python3
"""
Weekly Villain - LeetCode Hard Problem
Emails a hard LeetCode problem every Sunday at midnight.
"""

import requests
import random
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta

def fetch_hard_problems():
    """Fetch all hard problems from LeetCode API."""
    print("Summoning the weekly villain...")
    
    try:
        url = "https://alfa-leetcode-api.onrender.com/problems?difficulty=HARD"
        
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        if 'problemsetQuestionList' not in data:
            print("Error: The villain escapes... API response unexpected")
            return []
        
        problems = data['problemsetQuestionList']
        print(f"Found {len(problems)} potential villains.")
        return problems
        
    except requests.RequestException as e:
        print(f"Error summoning villain: {e}")
        return []

def send_test_email(recipient_email, smtp_server, smtp_port, sender_email, sender_password):
    """Send a test email to verify configuration."""
    msg = MIMEMultipart('alternative')
    msg['Subject'] = "⚔️ Weekly Villain - Initialization"
    msg['From'] = sender_email
    msg['To'] = recipient_email
    
    text = f"""
Weekly Villain - Initialization
{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

The hunt begins...

Every Saturday at midnight (Friday night), a new villain will arrive.
A Hard LeetCode problem awaits you.
Face it. Conquer it. Become stronger.

Your weekly challenge is set. ⚔️

The darkness stirs...
"""
    
    html = f"""
    <html>
      <body style="font-family: 'Georgia', serif; max-width: 600px; margin: 0 auto; background: #0a0a0a;">
        <div style="background: linear-gradient(135deg, #1a1a1a 0%, #2d1b1b 100%); padding: 30px; border-radius: 10px 10px 0 0; border-top: 3px solid #8b0000;">
          <h2 style="color: #ff4444; margin: 0; font-size: 28px; text-shadow: 2px 2px 4px #000;">⚔️ Weekly Villain</h2>
          <p style="color: #999; margin: 5px 0 0 0; font-style: italic;">Initialization</p>
        </div>
        <div style="background: #1a1a1a; padding: 25px; border-radius: 0 0 10px 10px; border-bottom: 3px solid #8b0000;">
          <h3 style="color: #ff6666; margin-top: 0; font-size: 22px;">The hunt begins...</h3>
          <p style="color: #ccc; line-height: 1.6;">Every <strong style="color: #ff4444;">Saturday at midnight</strong> (Friday night), a new villain will arrive.</p>
          <p style="color: #ccc; line-height: 1.6;">A <strong style="color: #ff4444;">Hard</strong> LeetCode problem awaits you.</p>
          <p style="color: #ccc; line-height: 1.6; margin-bottom: 20px;">Face it. Conquer it. Become stronger.</p>
          <div style="background: #0f0f0f; border-left: 4px solid #8b0000; padding: 15px; margin: 20px 0; border-radius: 4px;">
            <p style="color: #ff6666; margin: 0; font-weight: bold;">⚔️ Your weekly challenge is set.</p>
          </div>
          <p style="color: #666; font-size: 12px; margin-top: 25px; font-style: italic;">The darkness stirs...</p>
          <p style="color: #444; font-size: 11px; margin-top: 10px;">{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
      </body>
    </html>
    """
    
    msg.attach(MIMEText(text, 'plain'))
    msg.attach(MIMEText(html, 'html'))
    
    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        return False

def send_villain_email(problem, recipient_email, smtp_server, smtp_port, sender_email, sender_password):
    """Send the weekly villain problem via email."""
    title = problem.get('title', 'Unknown')
    title_slug = problem.get('titleSlug', '')
    link = f"https://leetcode.com/problems/{title_slug}/"
    
    tags = [tag['name'] for tag in problem.get('topicTags', [])]
    tags_str = ', '.join(tags) if tags else 'Unknown'
    
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"⚔️ Weekly Villain - {title}"
    msg['From'] = sender_email
    msg['To'] = recipient_email
    
    text = f"""
Weekly Villain Has Arrived
{datetime.now().strftime('%Y-%m-%d')}

This week's villain: {title}

Difficulty: HARD
Battle Tactics: {tags_str}

Face your villain: {link}

Will you defeat it, or will it defeat you?

The clock is ticking... ⚔️
"""
    
    html = f"""
    <html>
      <body style="font-family: 'Georgia', serif; max-width: 600px; margin: 0 auto; background: #0a0a0a;">
        <div style="background: linear-gradient(135deg, #1a1a1a 0%, #2d1b1b 100%); padding: 30px; border-radius: 10px 10px 0 0; border-top: 3px solid #8b0000;">
          <h2 style="color: #ff4444; margin: 0; font-size: 28px; text-shadow: 2px 2px 4px #000;">⚔️ Weekly Villain</h2>
          <p style="color: #999; margin: 5px 0 0 0; font-style: italic;">Has Arrived</p>
        </div>
        <div style="background: #1a1a1a; padding: 25px; border-radius: 0 0 10px 10px; border-bottom: 3px solid #8b0000;">
          <h3 style="color: #ff6666; margin-top: 0; font-size: 24px; border-bottom: 2px solid #333; padding-bottom: 10px;">{title}</h3>
          <div style="margin: 20px 0;">
            <p style="color: #ccc;"><strong style="color: #ff4444;">Difficulty:</strong> <span style="color: #ff6666; font-weight: bold; font-size: 18px;">HARD</span></p>
            <p style="color: #ccc;"><strong style="color: #ff4444;">Battle Tactics:</strong> {tags_str}</p>
          </div>
          <a href="{link}" style="display: inline-block; background: linear-gradient(135deg, #8b0000 0%, #660000 100%); color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; margin-top: 15px; font-weight: bold; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">⚔️ Face Your Villain</a>
          <div style="background: #0f0f0f; border-left: 4px solid #8b0000; padding: 15px; margin: 25px 0; border-radius: 4px;">
            <p style="color: #ff6666; margin: 0; font-style: italic;">Will you defeat it, or will it defeat you?</p>
          </div>
          <p style="color: #666; font-size: 12px; margin-top: 25px; font-style: italic;">The clock is ticking... ⚔️</p>
          <p style="color: #444; font-size: 11px; margin-top: 10px;">{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
      </body>
    </html>
    """
    
    msg.attach(MIMEText(text, 'plain'))
    msg.attach(MIMEText(html, 'html'))
    
    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
        print(f"✅ Villain dispatched to {recipient_email}")
        return True
    except Exception as e:
        print(f"❌ Failed to dispatch villain: {e}")
        return False

def display_villain(problem):
    """Display villain information in a formatted way."""
    title = problem.get('title', 'Unknown')
    title_slug = problem.get('titleSlug', '')
    tags = [tag['name'] for tag in problem.get('topicTags', [])]
    tags_str = ', '.join(tags) if tags else 'Unknown'
    
    print("\n" + "="*60)
    print(f"⚔️  WEEKLY VILLAIN HAS ARRIVED")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    print(f"Villain: {title}")
    print(f"Difficulty: HARD")
    print(f"Battle Tactics: {tags_str}")
    print(f"Arena: https://leetcode.com/problems/{title_slug}/")
    print("="*60)
    print("Will you defeat it, or will it defeat you?")
    print("="*60 + "\n")

def get_seconds_until_next_saturday():
    """Calculate seconds until next Saturday at midnight (Friday night)."""
    now = datetime.now()
    days_ahead = 5 - now.weekday()  # Saturday is 5
    if days_ahead <= 0:  # Already Saturday or past it
        days_ahead += 7
    next_saturday = now + timedelta(days=days_ahead)
    next_saturday_midnight = datetime(next_saturday.year, next_saturday.month, next_saturday.day, 0, 0, 0)
    return (next_saturday_midnight - now).total_seconds()

def main():
    """Main function to run the weekly villain dispatcher."""
    print("⚔️  WEEKLY VILLAIN - HARD LEETCODE PROBLEMS")
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
    
    print("\n⚔️  Initializing Weekly Villain system...")
    print("Hard problems will be dispatched every Saturday at midnight (Friday night)")
    print("Press Ctrl+C to stop\n")
    
    # Fetch hard problems
    problems = fetch_hard_problems()
    
    if not problems:
        print("No villains found. The darkness retreats...")
        return
    
    # Send test email immediately
    print("Sending initialization message...")
    
    if send_test_email(recipient_email, smtp_server, smtp_port, sender_email, sender_password):
        print("✅ Initialization successful! Check your inbox.")
        print("If you didn't receive it, check your spam folder.\n")
    else:
        print("❌ Initialization failed. Check your settings.")
        retry = input("Continue anyway? (y/n): ").lower()
        if retry != 'y':
            print("The hunt is postponed...")
            return
    
    try:
        # Check if it's Saturday and close to midnight
        now = datetime.now()
        if now.weekday() == 5 and now.hour == 0 and now.minute < 5:  # Saturday = 5
            problem = random.choice(problems)
            display_villain(problem)
            send_villain_email(problem, recipient_email, smtp_server, smtp_port, sender_email, sender_password)
        
        while True:
            # Calculate time until next Saturday midnight
            wait_time = get_seconds_until_next_saturday()
            days = int(wait_time // 86400)
            hours = int((wait_time % 86400) // 3600)
            
            print(f"Next villain arrives in {days} days and {hours} hours...")
            time.sleep(wait_time)
            
            # Dispatch the weekly villain
            problem = random.choice(problems)
            display_villain(problem)
            send_villain_email(problem, recipient_email, smtp_server, smtp_port, sender_email, sender_password)
            
    except KeyboardInterrupt:
        print("\n\n⚔️  The hunt ends... for now.")
        print("The villains retreat into the shadows...")

if __name__ == "__main__":
    main()
