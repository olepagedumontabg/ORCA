"""
Email notification system for data updates
Uses SendGrid to send notifications about data update status
"""
import os
import sys
import logging
from datetime import datetime
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('email_notification')

class EmailNotifier:
    """Handles sending email notifications about data update status"""
    
    def __init__(self):
        """Initialize the email notifier"""
        self.sendgrid_key = os.environ.get('SENDGRID_API_KEY')
        self.from_email = os.environ.get('NOTIFICATION_FROM_EMAIL', 'noreply@example.com')
        self.to_email = os.environ.get('NOTIFICATION_TO_EMAIL', 'admin@example.com')
        
        # Check if SendGrid key is available
        if not self.sendgrid_key:
            logger.warning("SENDGRID_API_KEY not found in environment variables. Email notifications will not be sent.")
    
    def _send_email(self, subject, html_content=None, text_content=None):
        """Send an email using SendGrid"""
        if not self.sendgrid_key:
            logger.warning("Cannot send email: SENDGRID_API_KEY not set")
            return False
            
        try:
            sg = SendGridAPIClient(self.sendgrid_key)
            
            message = Mail(
                from_email=Email(self.from_email),
                to_emails=To(self.to_email),
                subject=subject
            )
            
            if html_content:
                message.content = Content("text/html", html_content)
            elif text_content:
                message.content = Content("text/plain", text_content)
            else:
                message.content = Content("text/plain", "This is a notification from the Bathroom Compatibility Finder.")
            
            response = sg.send(message)
            logger.info(f"Email sent successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")
            return False
    
    def send_update_success(self, file_path, num_sheets):
        """Send a notification that the data update succeeded"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        subject = f"✅ Data Update Successful - {timestamp}"
        
        html_content = f"""
        <h2>Data Update Successful</h2>
        <p><strong>Time:</strong> {timestamp}</p>
        <p><strong>File:</strong> {file_path}</p>
        <p><strong>Sheets Loaded:</strong> {num_sheets}</p>
        <p>The bathroom compatibility data has been successfully updated.</p>
        """
        
        return self._send_email(subject, html_content=html_content)
    
    def send_update_failure(self, error_message, file_path=None):
        """Send a notification that the data update failed"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        subject = f"❌ Data Update Failed - {timestamp}"
        
        html_content = f"""
        <h2>Data Update Failed</h2>
        <p><strong>Time:</strong> {timestamp}</p>
        <p><strong>File:</strong> {file_path or 'N/A'}</p>
        <p><strong>Error:</strong> {error_message}</p>
        <p>Please check the system and resolve the issue.</p>
        """
        
        return self._send_email(subject, html_content=html_content)
    
    def send_validation_error(self, file_path, validation_errors):
        """Send a notification about validation errors in the data"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        subject = f"⚠️ Data Validation Errors - {timestamp}"
        
        error_list_html = "".join([f"<li>{error}</li>" for error in validation_errors])
        
        html_content = f"""
        <h2>Data Validation Errors</h2>
        <p><strong>Time:</strong> {timestamp}</p>
        <p><strong>File:</strong> {file_path}</p>
        <p><strong>Errors:</strong></p>
        <ul>
            {error_list_html}
        </ul>
        <p>The data file failed validation checks. Please fix the issues and try again.</p>
        """
        
        return self._send_email(subject, html_content=html_content)
    
    def test_connection(self):
        """Test the email connection by sending a test email"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        subject = f"🧪 Email Notification Test - {timestamp}"
        
        html_content = f"""
        <h2>Test Email</h2>
        <p>This is a test email from the Bathroom Compatibility Finder application.</p>
        <p><strong>Time:</strong> {timestamp}</p>
        <p>If you received this email, the notification system is working correctly.</p>
        """
        
        success = self._send_email(subject, html_content=html_content)
        
        if success:
            logger.info("Test email sent successfully")
        else:
            logger.error("Failed to send test email")
            
        return success

# Main execution
if __name__ == "__main__":
    # If run directly, perform a connection test
    notifier = EmailNotifier()
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        success = notifier.test_connection()
        sys.exit(0 if success else 1)
    else:
        print("Usage: python email_notifications.py test")
        print("This will send a test email to verify the configuration.")
        sys.exit(1)