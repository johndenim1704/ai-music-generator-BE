import os
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

class MarketingService:
    """
    A service to handle all marketing email operations with the Brevo API,
    including managing contacts and sending dynamic campaigns.
    """
    def __init__(self):
        """
        Initializes the Brevo API configuration using an environment variable.
        """
        api_key = os.getenv("BREVO_API_KEY")
        if not api_key:
            raise ValueError("CRITICAL: BREVO_API_KEY environment variable not set.")

        self.configuration = sib_api_v3_sdk.Configuration()
        self.configuration.api_key['api-key'] = api_key
        self.api_client = sib_api_v3_sdk.ApiClient(self.configuration)
        self.sender_email = "kaustubhraut135@gmail.com" # Replace with your authenticated sender
        self.sender_name = "Bujaa Beats"

    def add_contact_to_list(self, email: str, list_id: int, first_name: str = None, last_name: str = None):
        """
        Adds a contact to a specific marketing list in Brevo. If the contact
        already exists, this will update them and ensure they are in the list.

        Called when a user signs up.
        """
        api_instance = sib_api_v3_sdk.ContactsApi(self.api_client)
        
        attributes = {}
        if first_name:
            attributes["FIRSTNAME"] = first_name
        if last_name:
            attributes["LASTNAME"] = last_name

        create_contact = sib_api_v3_sdk.CreateContact(
            email=email,
            attributes=attributes,
            list_ids=[list_id]
        )
        
        try:
            api_instance.create_contact(create_contact)
            print(f"Successfully added contact '{email}' to Brevo list ID {list_id}.")
        except ApiException as e:
            if e.status == 400 and "Contact already exist" in e.body:
                 print(f"ℹ️ Contact '{email}' already exists in Brevo. Ensured they are in list ID {list_id}.")
            else:
                print(f"Error adding contact '{email}': {e.reason}")
                raise e
            

    def add_new_contact_to_list(self, email: str, list_id: int, first_name: str = None, last_name: str = None):
        """
        Attempts to add a contact to a list and logs any errors without crashing.
        This is the ideal function to call for non-critical operations like a 
        post-registration sync, where the main action (user creation) must not fail.
        """
        try:
            self.add_contact_to_list(
                email=email,
                list_id=list_id,
                first_name=first_name,
                last_name=last_name
            )
        except Exception as e:
            print(f"Error adding new user '{email}' to Brevo list ID {list_id}: {e}")

    def remove_contact_from_brevo(self, email: str):
        """
        Permanently deletes a contact from your Brevo account.

        Called when a user deletes their account from your application.
        """
        api_instance = sib_api_v3_sdk.ContactsApi(self.api_client)
        identifier = email
        
        try:
            api_instance.delete_contact(identifier)
            print(f"Successfully deleted contact '{identifier}' from Brevo.")
        except ApiException as e:
            if e.status == 404:
                print(f"ℹ️ Contact '{identifier}' not found in Brevo. No action needed.")
            else:
                print(f"Error deleting contact '{identifier}': {e.reason}")
                raise e

    def send_marketing_campaign(self, campaign_name: str, subject: str, html_content: str, list_id: int):
        """
        Creates and immediately sends a new email campaign to a specific list.

        Called by the admin endpoint.
        """
        api_instance = sib_api_v3_sdk.EmailCampaignsApi(self.api_client)

        email_campaign = sib_api_v3_sdk.CreateEmailCampaign(
            name=campaign_name,
            subject=subject,
            sender={"name": self.sender_name, "email": self.sender_email},
            html_content=html_content,
            recipients={"listIds": [list_id]}
        )

        try:
            
            create_response = api_instance.create_email_campaign(email_campaign)
            campaign_id = create_response.id
            print(f"Campaign '{campaign_name}' created with ID: {campaign_id}")
            api_instance.send_email_campaign_now(campaign_id)
            print(f"Campaign '{campaign_name}' has been successfully queued for sending!")
        except ApiException as e:
            print(f"A critical error occurred while sending the campaign: {e.reason}")
            print(f"Response body: {e.body}")
            raise e