from twilio.twiml.messaging_response import MessagingResponse
from flask import request

class TwilioService:
    @staticmethod
    def parse_request(form_data: Dict):
        """
        Extracts relevant information from Twilio's POST request.
        """
        incoming_msg = form_data.get('Body', '').strip()
        sender_phone = form_data.get('From', '')
        
        return {
            "message_body": incoming_msg,
            "sender": sender_phone
        }

    @staticmethod
    def send_simple_reply(text: str):
        """
        Generates TwiML response for simple text replies.
        """
        resp = MessagingResponse()
        resp.message(text)
        return str(resp)

    @staticmethod
    def send_media_reply(text: str, media_url: str):
        """
        Generates TwiML response with an image/media attachment.
        """
        resp = MessagingResponse()
        msg = resp.message(text)
        msg.media(media_url)
        return str(resp)
