#!/usr/bin/python3
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

def fetch_problems():
    """Fetch medium and hard problems from LeetCode API."""
    print("Summoning potential challengers...")
    
    try:
        # Fetch both medium and hard problems
        medium_url = "https://alfa-leetcode-api.onrender.com/problems?difficulty=MEDIUM"
        hard_url = "https://alfa-leetcode-api.onrender.com/problems?difficulty=HARD"
        
        medium_response = requests.get(medium_url)
        hard_response = requests.get(hard_url)
        
        medium_response.raise_for_status()
        hard_response.raise_for_status()
        
        medium_data = medium_response.json()
        hard_data = hard_response.json()
        
        if 'problemsetQuestionList' not in medium_data or 'problemsetQuestionList' not in hard_data:
            print("Error: The challengers escape... API response unexpected")
            return [], []
        
        medium_problems = medium_data['problemsetQuestionList']
        hard_problems = hard_data['problemsetQuestionList']
        
        print(f"Found {len(medium_problems)} medium problems and {len(hard_problems)} hard problems.")
        return medium_problems, hard_problems
        
    except requests.RequestException as e:
        print(f"Error summoning challengers: {e}")
        return [], []

def send_test_email(recipient_email, smtp_server, smtp_port, sender_email, sender_password):
    """Send a test email to verify configuration."""
    msg = MIMEMultipart('alternative')
    msg['Subject'] = "⚔️ Weekly Challenge"
    msg['From'] = sender_email
    msg['To'] = recipient_email
    
    text = f"""
Weekly Challenge - Initialization
{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

The hunt begins...

Every Saturday at midnight (Friday night), a new challenge will arrive.
Sometimes a mere peon (Medium).
Sometimes a fearsome villain (Hard).
Face it. Conquer it. Become stronger.

Your weekly challenge is set. ⚔️

The darkness stirs...
"""
    
    html = f"""
    <html>
      <body style="font-family: 'Georgia', serif; max-width: 600px; margin: 0 auto; background: #0a0a0a;">
        <div style="background: linear-gradient(135deg, #1a1a1a 0%, #2d1b1b 100%); padding: 30px; border-radius: 10px 10px 0 0; border-top: 3px solid #8b0000;">
          <h2 style="color: #ff4444; margin: 0; font-size: 28px; text-shadow: 2px 2px 4px #000;">⚔️ Weekly Challenge</h2>
          <p style="color: #999; margin: 5px 0 0 0; font-style: italic;">Initialization</p>
        </div>
        <div style="background: #1a1a1a; padding: 25px; border-radius: 0 0 10px 10px; border-bottom: 3px solid #8b0000;">
          <h3 style="color: #ff6666; margin-top: 0; font-size: 22px;">The hunt begins...</h3>
          <p style="color: #ccc; line-height: 1.6;">Every <strong style="color: #ff4444;">Saturday at midnight</strong> (Friday night), a new challenge will arrive.</p>
          <p style="color: #ccc; line-height: 1.6;">Sometimes a <strong style="color: #ffc01e;">mere peon</strong> (Medium).</p>
          <p style="color: #ccc; line-height: 1.6;">Sometimes a <strong style="color: #ff4444;">fearsome villain</strong> (Hard).</p>
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

def send_challenge_email(problem, is_hard, recipient_email, smtp_server, smtp_port, sender_email, sender_password):
    """Send the weekly challenge problem via email."""
    title = problem.get('title', 'Unknown')
    title_slug = problem.get('titleSlug', '')
    difficulty = problem.get('difficulty', 'Unknown')
    link = f"https://leetcode.com/problems/{title_slug}/"
    
    tags = [tag['name'] for tag in problem.get('topicTags', [])]
    tags_str = ', '.join(tags) if tags else 'Unknown'
    
    msg = MIMEMultipart('alternative')
    msg['Subject'] = "⚔️ Weekly Challenge"
    msg['From'] = sender_email
    msg['To'] = recipient_email
    
    # Different messaging based on difficulty
    if is_hard:
        header_text = "The Villain Emerges"
        intro = "A fearsome adversary stands before you..."
        footer = "Will you defeat it, or will it defeat you?"
        color = "#ef4743"
    else:
        header_text = "A Mere Peon Appears"
        intro = "Ah, it's just this peon. Should be quick work for someone like you."
        footer = "Dispatch it swiftly and move on."
        color = "#ffc01e"
    
    text = f"""
Weekly Challenge
{datetime.now().strftime('%Y-%m-%d')}

{header_text}

This week's challenge: {title}

Difficulty: {difficulty}
Battle Tactics: {tags_str}

Face your challenge: {link}

{footer}

⚔️
"""
    
    html = f"""
    <html>
      <body style="font-family: 'Georgia', serif; max-width: 600px; margin: 0 auto; background: #0a0a0a;">
        <div style="background: linear-gradient(135deg, #1a1a1a 0%, #2d1b1b 100%); padding: 30px; border-radius: 10px 10px 0 0; border-top: 3px solid #8b0000;">
          <h2 style="color: #ff4444; margin: 0; font-size: 28px; text-shadow: 2px 2px 4px #000;">⚔️ Weekly Challenge</h2>
          <p style="color: #999; margin: 5px 0 0 0; font-style: italic;">{header_text}</p>
        </div>
        <div style="background: #1a1a1a; padding: 25px; border-radius: 0 0 10px 10px; border-bottom: 3px solid #8b0000;">
          <p style="color: #ccc; font-style: italic; margin-top: 0;">{intro}</p>
          <h3 style="color: #ff6666; margin-top: 20px; font-size: 24px; border-bottom: 2px solid #333; padding-bottom: 10px;">{title}</h3>
          <div style="margin: 20px 0;">
            <p style="color: #ccc;"><strong style="color: #ff4444;">Difficulty:</strong> <span style="color: {color}; font-weight: bold; font-size: 18px;">{difficulty.upper()}</span></p>
            <p style="color: #ccc;"><strong style="color: #ff4444;">Battle Tactics:</strong> {tags_str}</p>
          </div>
          <a href="{link}" style="display: inline-block; background: linear-gradient(135deg, #8b0000 0%, #660000 100%); color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; margin-top: 15px; font-weight: bold; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">⚔️ Face Your Challenge</a>
          <div style="background: #0f0f0f; border-left: 4px solid #8b0000; padding: 15px; margin: 25px 0; border-radius: 4px;">
            <p style="color: #ff6666; margin: 0; font-style: italic;">{footer}</p>
          </div>
          <p style="color: #666; font-size: 12px; margin-top: 25px; font-style: italic;">⚔️</p>
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
        print(f"✅ Challenge dispatched to {recipient_email}")
        return True
    except Exception as e:
        print(f"❌ Failed to dispatch challenge: {e}")
        return False

def display_challenge(problem, is_hard):
    """Display challenge information in a formatted way."""
    title = problem.get('title', 'Unknown')
    title_slug = problem.get('titleSlug', '')
    difficulty = problem.get('difficulty', 'Unknown')
    tags = [tag['name'] for tag in problem.get('topicTags', [])]
    tags_str = ', '.join(tags) if tags else 'Unknown'
    
    challenge_type = "VILLAIN" if is_hard else "PEON"
    
    print("\n" + "="*60)
    print(f"⚔️  WEEKLY CHALLENGE: {challenge_type}")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    print(f"Challenge: {title}")
    print(f"Difficulty: {difficulty.upper()}")
    print(f"Battle Tactics: {tags_str}")
    print(f"Arena: https://leetcode.com/problems/{title_slug}/")
    print("="*60)
    if is_hard:
        print("Will you defeat it, or will it defeat you?")
    else:
        print("Ah, just a peon. Dispatch it swiftly.")
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
    """Main function to run the weekly challenge dispatcher."""
    print("⚔️  WEEKLY CHALLENGE - LEETCODE PROBLEMS")
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
    
    print("\n⚔️  Initializing Weekly Challenge system...")
    print("Challenges will be dispatched every Saturday at midnight (Friday night)")
    print("1/3 chance: Fearsome Villain (Hard)")
    print("2/3 chance: Mere Peon (Medium)")
    print("Press Ctrl+C to stop\n")
    
    # Fetch problems
    medium_problems, hard_problems = fetch_problems()
    
    if not medium_problems or not hard_problems:
        print("No challenges found. The darkness retreats...")
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
            # 1/3 chance hard, 2/3 chance medium
            is_hard = random.random() < 1/3
            problem = random.choice(hard_problems if is_hard else medium_problems)
            display_challenge(problem, is_hard)
            send_challenge_email(problem, is_hard, recipient_email, smtp_server, smtp_port, sender_email, sender_password)
        
        while True:
            # Calculate time until next Saturday midnight
            wait_time = get_seconds_until_next_saturday()
            days = int(wait_time // 86400)
            hours = int((wait_time % 86400) // 3600)
            
            print(f"Next challenge arrives in {days} days and {hours} hours...")
            time.sleep(wait_time)
            
            # Dispatch the weekly challenge (1/3 hard, 2/3 medium)
            is_hard = random.random() < 1/3
            problem = random.choice(hard_problems if is_hard else medium_problems)
            display_challenge(problem, is_hard)
            send_challenge_email(problem, is_hard, recipient_email, smtp_server, smtp_port, sender_email, sender_password)
            
    except KeyboardInterrupt:
        print("\n\n⚔️  The hunt ends... for now.")
        print("The challenges retreat into the shadows...")

if __name__ == "__main__":
    main()
