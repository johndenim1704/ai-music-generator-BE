"""
PDF Placeholder Replacement Module

Handles replacing bracketed placeholders in PDF templates with actual data using PyMuPDF.
"""

import io
import fitz  # PyMuPDF
from typing import Dict
from datetime import datetime


class PDFPlaceholderReplacer:
    """Replaces placeholders in PDF templates with actual data."""
    
    # Placeholder mapping: Maps PDF placeholders to data extraction functions
    PLACEHOLDER_MAPPING = {
        '[Beat Name]': lambda ctx: ctx['license_data'].get('music_name', 'N/A'),
        '[ORDER ID]': lambda ctx: str(ctx['transaction_data'].get('order_id', 'N/A')),
        '[BB-L-YYYY-XXXXX]': lambda ctx: ctx['transaction_data'].get('license_id_formatted', 'N/A'),
        '[BB-E-YYYY-XXXXX]': lambda ctx: ctx['transaction_data'].get('license_id_formatted', 'N/A'),
        '[BB-U-YYYY-XXXXX]': lambda ctx: ctx['transaction_data'].get('license_id_formatted', 'N/A'),
        '[Author Full Legal Name]': lambda ctx: ctx['form_data'].get('author_legal_name', 'N/A'),
        '[Author IPI/CAE Number]': lambda ctx: ctx['form_data'].get('pro_ipi_number') or 'N/A',
        '[Author PRO]': lambda ctx: ctx['form_data'].get('pro_name') or 'N/A',
        '[ Author IPI ]': lambda ctx: ctx['form_data'].get('pro_ipi_number') or 'N/A',
        '[ Author Full legal  \nName and Stage \nName ]': lambda ctx: f"{ctx['form_data'].get('author_legal_name', 'N/A')}\n{ctx['form_data'].get('artist_stage_name', 'N/A')}",
        '[ Publisher Name ]': lambda ctx: ctx['form_data'].get('publisher_name') or 'Self-Published',
        '[ Publisher IPI ]': lambda ctx: 'N/A',  # Not currently collected
        '[Licensee\'s Publisher IPI]': lambda ctx: 'N/A',  # Not currently collected
        '[Licensee\'s PRO]': lambda ctx: ctx['form_data'].get('pro_name') or 'N/A',
        '[PRICE_PAID]': lambda ctx: f"{ctx['transaction_data'].get('amount_paid', 0):.2f}",
        '[Timestamp]': lambda ctx: ctx['form_data'].get('signed_at', datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')),
        '[User IP]': lambda ctx: ctx['transaction_data'].get('buyer_ip') or 'N/A',
        '[Buyer Full Name]': lambda ctx: ctx['form_data'].get('licensee_name', 'N/A'),
        '[Image Signature]': lambda ctx: '[Digital Signature]',  # Placeholder for now
        '[ automatic enter the [Beat Name]': lambda ctx: ctx['license_data'].get('music_name', 'N/A'),  # Unlimited template quirk
    }
    
    def replace_placeholders(
        self,
        template_path: str,
        license_data: Dict,
        form_data: Dict,
        transaction_data: Dict
    ) -> bytes:
        """
        Replace all placeholders in PDF template with actual data.
        
        Args:
            template_path: Path to PDF template file
            license_data: License and music information
            form_data: User-filled form data
            transaction_data: Payment and transaction details
            
        Returns:
            bytes: PDF with placeholders replaced
        """
        # Build data context for mapping
        data_context = {
            'license_data': license_data,
            'form_data': form_data,
            'transaction_data': transaction_data
        }
        
        # Build replacements dictionary
        replacements = {}
        for placeholder, getter_func in self.PLACEHOLDER_MAPPING.items():
            try:
                value = getter_func(data_context)
                replacements[placeholder] = str(value) if value is not None else 'N/A'
            except (KeyError, TypeError, AttributeError) as e:
                print(f"[PlaceholderReplacer] Warning: Could not resolve {placeholder}: {e}")
                replacements[placeholder] = 'N/A'
        
        # Open PDF with PyMuPDF
        doc = fitz.open(template_path)
        
        print(f"[PlaceholderReplacer] Replacing placeholders in {len(doc)} pages...")
        total_replacements = 0
        
        # Process each page
        for page_num, page in enumerate(doc, 1):
            page_replacements = 0
            
            # Replace each placeholder
            for placeholder, replacement_value in replacements.items():
                # Find all instances of this placeholder on the page
                text_instances = page.search_for(placeholder)
                
                if text_instances:
                    for inst in text_instances:
                        # Redact the old text (cover it with white)
                        page.add_redact_annot(inst, fill=(1, 1, 1))
                    
                    # Apply all redactions at once
                    page.apply_redactions()
                    
                    # Insert replacement text at the first instance position
                    # (for multi-line placeholders, this might need adjustment)
                    for inst in text_instances:
                        try:
                            # Estimate font size from rectangle height
                            font_size = max(8, min(12, inst.height * 0.8))
                            
                            page.insert_textbox(
                                inst,
                                replacement_value,
                                fontsize=font_size,
                                fontname="helv",  # Helvetica (Arial equivalent)
                                color=(0, 0, 0),
                                align=fitz.TEXT_ALIGN_LEFT
                            )
                            page_replacements += 1
                        except Exception as e:
                            print(f"[PlaceholderReplacer] Error replacing '{placeholder}' on page {page_num}: {e}")
            
            if page_replacements > 0:
                print(f"[PlaceholderReplacer] Page {page_num}: {page_replacements} replacements made")
                total_replacements += page_replacements
        
        print(f"[PlaceholderReplacer] Total replacements: {total_replacements}")
        
        # Save to bytes
        output_bytes = io.BytesIO()
        doc.save(output_bytes)
        doc.close()
        
        return output_bytes.getvalue()
