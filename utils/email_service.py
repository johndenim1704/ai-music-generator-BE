import os
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from jinja2 import Environment, FileSystemLoader
from models.user import Users
from models.offer import Offer
from models.order import Order

class EmailService:
    def __init__(self):
        self.configuration = sib_api_v3_sdk.Configuration()
        self.configuration.api_key['api-key'] = os.getenv("BREVO_API_KEY")
        self.api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(self.configuration))
        self.sender = {"name": os.getenv("BREVO_SENDER_NAME"), "email": os.getenv("BREVO_SENDER_EMAIL")}  # Change to your verified domain
        
        # Setup Jinja2 for local templates
        self.jinja_env = Environment(loader=FileSystemLoader('templates'))

    def _send_html_email(self, to_email: str, to_name: str, subject: str, html_content: str, params: dict = None):
        """Send HTML email directly without using Brevo templates"""
        to = [{"email": to_email, "name": to_name}]
        
        send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
            to=to,
            sender=self.sender,
            subject=subject,
            html_content=html_content,
            params=params
        )
        
        try:
            response = self.api_instance.send_transac_email(send_smtp_email)
            print(f"✅ Successfully sent email to {to_email}")
            print(f"📧 Subject: {subject}")
            return response
        except ApiException as e:
            print(f"❌ Error sending email to {to_email}: {e}")
            print(f"Status code: {e.status if hasattr(e, 'status') else 'Unknown'}")
            print(f"Response body: {e.body if hasattr(e, 'body') else 'Unknown'}")
            raise e

    def send_purchase_confirmation(self, user: Users, order: Order, items: list):
        """Send purchase confirmation email"""
        try:
            template = self.jinja_env.get_template('purchase_confirmation.html')
            html_content = template.render(
                user_name=user.name,
                order_id=order.id,
                total_amount=f"{order.total_amount:.2f}",
                items=items
            )
            
            self._send_html_email(
                to_email=user.email,
                to_name=user.name,
                subject=f"Purchase Confirmation - Order #{order.id}",
                html_content=html_content
            )
        except Exception as e:
            print(f"Error in send_purchase_confirmation: {e}")
            raise e

    def send_new_offer_to_admin(self, offer: Offer):
        """Send new offer notification to admin"""
        try:
            template = self.jinja_env.get_template('admin_new_offer.html')
            html_content = template.render(
                beat_name=offer.license.music.name,
                user_name=offer.user.name,
                user_email=offer.user.email,
                offer_amount=f"{offer.offered_amount:.2f}",
                admin_link=f"{os.getenv('FRONTEND_URL')}/admin/offers/{offer.id}"
            )
            
            self._send_html_email(
                to_email=os.getenv("ADMIN_EMAIL"),
                to_name="Bujaa Beats Admin",
                subject=f"New Offer: {offer.license.music.name} - ${offer.offered_amount:.2f}",
                html_content=html_content
            )
        except Exception as e:
            print(f"Error in send_new_offer_to_admin: {e}")
            raise e

    def send_offer_accepted(self, offer: Offer):
        """Send offer accepted notification to user"""
        try:
            final_amount = offer.counter_offer_amount if offer.counter_offer_amount else offer.offered_amount
            template = self.jinja_env.get_template('offer-accepted.html')
            params = {
            "user_name": offer.user.name,
            "beat_name": offer.license.music.name,
            "final_amount": f"{final_amount:.2f}",
            "downloads_link": f"{os.getenv('FRONTEND_URL')}/library"
            }
            html_content = template.render(
                user_name=offer.user.name,
                beat_name=offer.license.music.name,
                final_amount=f"{final_amount:.2f}",
                downloads_link=f"{os.getenv('FRONTEND_URL')}/library"
            )
            
            self._send_html_email(
                to_email=offer.user.email,
                to_name=offer.user.name,
                subject=f"Offer Accepted! {offer.license.music.name}",
                html_content=html_content,
                params=params
            )
        except Exception as e:
            print(f"Error in send_offer_accepted: {e}")
            raise e

    def send_offer_rejected(self, offer: Offer):
        """Send offer rejected notification to user"""
        try:
            template = self.jinja_env.get_template('offer-rejected.html')
            html_content = template.render(
                user_name=offer.user.name,
                beat_name=offer.license.music.name,
                browse_link=f"{os.getenv('FRONTEND_URL')}/beats"
            )
            params = {
                "user_name": offer.user.name,
                "beat_name": offer.license.music.name,
                "browse_link": f"{os.getenv('FRONTEND_URL')}/beats"
            }
            
            self._send_html_email(
                to_email=offer.user.email,
                to_name=offer.user.name,
                subject=f"Offer Update: {offer.license.music.name}",
                html_content=html_content,
                params=params
            )
        except Exception as e:
            print(f"Error in send_offer_rejected: {e}")
            raise e
    
    def send_counter_offer(self, offer: Offer, checkout_url: str):
        """Send counter offer notification to user"""
        try:
            template = self.jinja_env.get_template('counter-offer.html')
            html_content = template.render(
                user_name=offer.user.name,
                beat_name=offer.license.music.name,
                counter_amount=f"{offer.counter_offer_amount:.2f}",
                payment_link=checkout_url
            )
            params = {
            "user_name": offer.user.name,
            "beat_name": offer.license.music.name,
            "counter_amount": f"{offer.counter_offer_amount:.2f}",
            "payment_link": checkout_url
            }
            
            self._send_html_email(
                to_email=offer.user.email,
                to_name=offer.user.name,
                subject=f"Counter Offer: {offer.license.music.name} - ${offer.counter_offer_amount:.2f}",
                html_content=html_content,
                params=params
            )
        except Exception as e:
            print(f"Error in send_counter_offer: {e}")
            raise e

    def send_welcome_email(self, user: Users):
        """Send welcome email to new users"""
        try:
            template = self.jinja_env.get_template('welcome.html')
            html_content = template.render(
                user_name=user.name,
                browse_beats_url=f"{os.getenv('FRONTEND_URL')}/beats",
                profile_url=f"{os.getenv('FRONTEND_URL')}/profile"
            )
            
            self._send_html_email(
                to_email=user.email,
                to_name=user.name,
                subject="Welcome to Bujaa Beats! 🎵",
                html_content=html_content
            )
        except Exception as e:
            print(f"Error in send_welcome_email: {e}")
            raise e

    def test_email(self, to_email: str = None):
        """Test email functionality with a simple message"""
        test_email = to_email or os.getenv("ADMIN_EMAIL")
        if not test_email:
            print("❌ No test email provided")
            return
            
        try:
            html_content = """
            <html>
            <body>
                <h2>🎵 Bujaa Beats Test Email</h2>
                <p>This is a test email to verify your email service is working correctly.</p>
                <p>If you received this, your email configuration is working! ✅</p>
                <hr>
                <p><small>Sent from Bujaa Beats Email Service</small></p>
            </body>
            </html>
            """
            
            self._send_html_email(
                to_email=test_email,
                to_name="Test User",
                subject="🧪 Bujaa Beats - Email Test",
                html_content=html_content
            )
        except Exception as e:
            print(f"Error in test_email: {e}")
            raise e

    def send_license_with_pdf(self, user, user_license, download_url: str):
        """Send license PDF to the buyer"""
        try:
            license_type = user_license.license.license_type.value.title()
            music_name = user_license.license.music.name
            license_id = user_license.license_id_formatted
            
            template = self.jinja_env.get_template('license_delivery.html')
            html_content = template.render(
                user_name=user.name,
                music_name=music_name,
                license_type=license_type,
                license_id=license_id,
                download_url=download_url,
                order_id=user_license.order_id,
                amount_paid=f"{user_license.amount_paid:.2f}" if user_license.amount_paid else "N/A",
                currency=user_license.currency.upper() if user_license.currency else "EUR"
            )
            
            params = {
                "user_name": user.name,
                "music_name": music_name,
                "license_type": license_type,
                "license_id": license_id,
                "download_url": download_url
            }
            
            self._send_html_email(
                to_email=user.email,
                to_name=user.name,
                subject=f"🎵 Your {license_type} License - {music_name}",
                html_content=html_content,
                params=params
            )
        except Exception as e:
            print(f"Error in send_license_with_pdf: {e}")
            raise e

    def send_license_to_admin(self, user, user_license, download_url: str, admin_email: str):
        """Send license PDF notification to admin"""
        try:
            license_type = user_license.license.license_type.value.title()
            music_name = user_license.license.music.name
            license_id = user_license.license_id_formatted
            
            template = self.jinja_env.get_template('admin_license_notification.html')
            html_content = template.render(
                user_name=user.name,
                user_email=user.email,
                music_name=music_name,
                license_type=license_type,
                license_id=license_id,
                download_url=download_url,
                order_id=user_license.order_id,
                amount_paid=f"{user_license.amount_paid:.2f}" if user_license.amount_paid else "N/A",
                currency=user_license.currency.upper() if user_license.currency else "EUR",
                transaction_id=user_license.transaction_id
            )
            
            params = {
                "user_name": user.name,
                "music_name": music_name,
                "license_type": license_type,
                "license_id": license_id
            }
            
            self._send_html_email(
                to_email=admin_email,
                to_name="Bujaa Beats Admin",
                subject=f"📄 New License Generated - {license_id}",
                html_content=html_content,
                params=params
            )
        except Exception as e:
            print(f"Error in send_license_to_admin: {e}")
            raise e