"""
License Service - Orchestrates PDF generation, storage, and email delivery
"""

from sqlalchemy.orm import Session
from datetime import datetime
from models.userlicense import UserLicense
from models.order import Order
from models.user import Users
from utils.pdf_generator import PDFGenerator
from utils.s3_manager import S3Manager
from utils.email_service import EmailService
from enums.licensetypesenum import LicenseTypesEnum
import os


class LicenseService:
    """
    High-level service for managing license PDF generation and delivery.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.pdf_generator = PDFGenerator()
        self.s3_manager = S3Manager()
        self.email_service = EmailService()
    
    def generate_and_store_license(
        self,
        user_license_id: int,
        buyer_ip: str = None,
        user_agent: str = None
    ) -> str:
        """
        Generate license PDF, upload to S3, update database, and send emails.
        
        Args:
            user_license_id: ID of the UserLicense record
            buyer_ip: Buyer's IP address (if not already stored)
            user_agent: Buyer's user agent (if not already stored)
            
        Returns:
            str: S3 URL of the generated PDF
            
        Raises:
            ValueError: If user_license not found or form not completed
            Exception: For any other errors during generation
        """
        # Fetch the user license with all relationships
        user_license = self.db.query(UserLicense).filter(
            UserLicense.id == user_license_id
        ).first()
        
        if not user_license:
            raise ValueError(f"UserLicense {user_license_id} not found")
        
        # Verify form is completed
        if not user_license.is_form_filled or not user_license.is_signed:
            raise ValueError("License form must be completed and signed before PDF generation")
        
        # Get related data
        user = user_license.user
        license = user_license.license
        music = license.music
        order = user_license.order
        print(f"[LS] license_type.value={license.license_type.value if license and license.license_type else None}")
        print(f"[LS] form_filled={user_license.is_form_filled}, signed={user_license.is_signed}")
        print(f"[LS] transaction amount={user_license.amount_paid}, currency={user_license.currency}, method={user_license.payment_method}")
        print(f"[LS] buyer_ip={user_license.buyer_ip}, user_agent={user_license.buyer_user_agent}")
        
        # Update buyer metadata if provided
        if buyer_ip:
            user_license.buyer_ip = buyer_ip
        if user_agent:
            user_license.buyer_user_agent = user_agent

        print("flow in generate and store license ")
        
        # Generate formatted license ID if not already generated
        if not user_license.license_id_formatted:
            user_license.license_id_formatted = self._generate_license_id(
                license.license_type,
                order.id if order else user_license.id
            )
        
        # Prepare data for PDF generation
        license_data = {
            'music_name': music.name,
            'license_type': license.license_type.value,
            'artist_name': music.artist if hasattr(music, 'artist') else 'Bujaa Beats',
        }
        
        form_data = {
            'licensee_name': user_license.licensee_name,
            'licensee_email': user_license.licensee_email,
            'project_title': user_license.project_title,
            'artist_stage_name': user_license.artist_stage_name,
            'author_legal_name': user_license.author_legal_name,
            'pro_name': user_license.pro_name,
            'pro_ipi_number': user_license.pro_ipi_number,
            'phone_number': user_license.phone_number,
            'address': user_license.address,
            'publisher_name': user_license.publisher_name,
            'signed_at': user_license.signed_at.strftime('%Y-%m-%d %H:%M:%S %Z') if user_license.signed_at else None,
        }
        
        transaction_data = {
            'license_id_formatted': user_license.license_id_formatted,
            'order_id': user_license.order_id,
            'transaction_id': user_license.transaction_id,
            'amount_paid': user_license.amount_paid,
            'currency': user_license.currency,
            'discount_applied': user_license.discount_applied or 0.0,
            'payment_method': user_license.payment_method,
            'buyer_ip': user_license.buyer_ip,
            'user_agent': user_license.buyer_user_agent,
            'timestamp_utc': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
            'pdf_checksum': None  # Will be updated after generation
        }
        
        # Generate PDF
        print(f"Generating PDF for license {user_license.license_id_formatted}...")
        try:
            pdf_bytes = self.pdf_generator.generate_license_pdf(
                license_type=license.license_type.value,
                license_data=license_data,
                form_data=form_data,
                transaction_data=transaction_data
            )
            
            if pdf_bytes is None:
                raise Exception("PDF generation failed (returned None)")

        except Exception as e:
            import traceback
            print("[LS] PDF generation failed:", str(e))
            traceback.print_exc()
            raise
        
        # Generate checksum
        checksum = self.pdf_generator.generate_checksum(pdf_bytes)
        user_license.pdf_checksum = checksum
        transaction_data['pdf_checksum'] = checksum
        
        print(f"PDF generated. Checksum: {checksum}")
        
        # Upload to S3
        s3_url = self._upload_to_s3(
            pdf_bytes,
            user_license.license_id_formatted,
            user.id,
            music.name,
            license.license_type.value
        )
        
        # Update database
        user_license.license_pdf_path = s3_url
        user_license.pdf_generated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(user_license)
        
        print(f"PDF stored at: {s3_url}")
        
        # Send emails
        try:
            self._send_emails(user, user_license, s3_url)
        except Exception as e:
            print(f"Warning: Email sending failed: {str(e)}")
            # Don't fail the whole operation if email fails
        
        return s3_url
    
    def _generate_license_id(self, license_type: LicenseTypesEnum, order_id: int) -> str:
        """
        Generate formatted license ID: BB-X-YYYY-#####
        
        BB = Bujaa Beats
        X = L (Leasing), E (Exclusive), U (Unlimited)
        YYYY = Year
        ##### = Order ID (zero-padded to 5 digits)
        """
        type_codes = {
            LicenseTypesEnum.leasing: 'L',
            LicenseTypesEnum.exclusive: 'E',
            LicenseTypesEnum.unlimited: 'U',
        }

        type_code = type_codes.get(license_type, 'X')
        year = datetime.now().year
        order_number = str(order_id).zfill(5)

        print("flow in generate license")
        
        return f"BB-{type_code}-{year}-{order_number}"
    
    def _upload_to_s3(
        self,
        pdf_bytes: bytes,
        license_id: str,
        user_id: int,
        music_name: str,
        license_type: str
    ) -> str:
        """
        Upload PDF to S3 and return public URL.
        
        S3 structure: licenses/{user_id}/{license_id}/{music_name}-{license_type}.pdf
        """
        # Create safe filename
        safe_music_name = music_name.replace(' ', '-').lower()
        safe_license_type = license_type.replace(' ', '-').lower()
        filename = f"{safe_music_name}-{safe_license_type}-{license_id}.pdf"
        
        # Generate S3 key
        s3_key = f"licenses/{user_id}/{license_id}/{filename}"
        
        # Upload
        try:
            import io
            pdf_file = io.BytesIO(pdf_bytes)
            
            # Upload using existing S3 manager methods
            self.s3_manager.s3_client.upload_fileobj(
                pdf_file,
                self.s3_manager.bucket_name,
                s3_key,
                ExtraArgs={
                    'ContentType': 'application/pdf',
                    'ContentDisposition': f'attachment; filename="{filename}"'
                }
            )
            
            # Return the S3 URL
            s3_url = f"https://{self.s3_manager.bucket_name}.s3.amazonaws.com/{s3_key}"
            return s3_url
            
        except Exception as e:
            print(f"Error uploading PDF to S3: {str(e)}")
            raise
    
    def _send_emails(self, user: Users, user_license: UserLicense, pdf_s3_url: str):
        """
        Send license PDF to buyer and admin.
        """
        # Generate a presigned URL for download (24 hours expiry)
        s3_key = pdf_s3_url.split('.com/')[-1]
        download_url = self.s3_manager.generate_presigned_url_for_download(s3_key, expiration=86400)
        
        # Send to buyer
        self.email_service.send_license_with_pdf(
            user=user,
            user_license=user_license,
            download_url=download_url
        )
        
        # Send to admin
        admin_email = os.getenv('ADMIN_LICENSE_EMAIL', 'info@bujaabeats.com')
        self.email_service.send_license_to_admin(
            user=user,
            user_license=user_license,
            download_url=download_url,
            admin_email=admin_email
        )
        
        print(f"Emails sent to {user.email} and {admin_email}")
