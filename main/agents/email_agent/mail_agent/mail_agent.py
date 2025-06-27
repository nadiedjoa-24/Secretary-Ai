import os, sys
sys.path.insert(
    0,
    os.path.abspath(
        os.path.join(__file__,'..','..','..','..')
    )
)
from main.agents.email_agent.mail_handler.mail_handler import MAIL_HANDLER, eMail, EMail
from common.ai.API_client import API_Client
from common.ai.model.BaseAIModel import Message
import openai
from typing import Literal, List




class Mail_Agent:
    
    def __init__(self, EMAIL: str = None, PASSWORD: str = None, backend: Literal["API", "LOCAL"] = "API", API_KEY: str = None):
        self.API_KEY = API_KEY
        
        self.backend = backend
        if EMAIL is not None and PASSWORD is not None:
            self.M = MAIL_HANDLER(EMAIL, PASSWORD)
        else:
            self.M = MAIL_HANDLER()

        self.client = None
        self._init_backend()


    def _init_backend(self):

        # API mode (we use OpenAI's API but it can be extended to other APIs)
        if self.backend == "API":
            if not self.API_KEY:
                try:
                    self.API_KEY = os.getenv("API_KEY")
                except KeyError as e:
                    raise ValueError(f"API_KEY is required for API backend, please provide one at instantiation or in environment: {e}")
            else:
                openai.api_key = self.API_KEY
                # print(f" == API_KEY : {self.API_KEY} ")
            try:
                self.client = API_Client(API_KEY = self.API_KEY)
            except Exception as e:
                raise ValueError(f"Failed to initialize API backend: {e}")

        # LOCAL mode (we use Huggingface's transformers package for local models)
        elif self.backend == "LOCAL":
            pass

        else:
            raise ValueError("Invalid backend. Choose 'API' or 'LOCAL'.")
        
    
    def summarize_email(self, email: eMail) -> str:
        """
        Summarize a single email's content.
        """
        prompt = f"Tu es un assistant utile qui fournit un résumé pertinent du texte suivant. Le résumé doit être court, en français, et contenir les éléments clés. Voici le texte à résumer : {email.content}"
        msg: Message = Message(role="assistant", content=prompt)
        response = self.client.basic([msg]).content
        return response

    
    def summarize_mailbox(self) -> List:
        """
        Summarize inbox's unseen emails.
        """
        unseen_emails: List[eMail] = self.M.get_unread_emails()
        summaries: List[str] = []
        for email in unseen_emails:
            summary = self.summarize_email(email)
            summaries.append(summary)
        return summaries


    def classify_email(self, email: eMail) -> str:
        """
        Classify the content of a given email and assign it to a folder among available ones.
        """
        available_folders = self.M.get_folders()
        prompt = f"You are an helpful assistant that classifies the following email content into one of the available folders: {available_folders}. This is the email content you have to classify : {email.content}. You have to answer with the name of the folder ony."
        msg: Message = Message(role="assistant", content=prompt)
        response = self.client.basic([msg]).content
        return response
    
    
    def classify_mailbox(self) -> List[str]:
        """
        Classify unseen emails and move them to folders.
        """
        unseen_emails: List[eMail] = self.M.get_unread_emails()
        moved_folders: List[str] = []
        for email in unseen_emails:
            target_folder = self.classify_email(email)
            try:
                self.M.move_email(email.id, target_folder)
            except Exception as e:
                raise RuntimeError(f"Failed to move email {email.id} to folder '{target_folder}': {e}")
            moved_folders.append(target_folder)
        return moved_folders
    

    def respond_to_email(self, email: eMail) -> str:
        """
        Generate a response to a given email.
        """
        prompt = f"You are an helpful assistant that generates a response to the following email content. This is the email content you have to respond to : {email.content}."
        msg: Message = Message(role="assistant", content=prompt)
        response = self.client.basic([msg]).content

        email_response = EMail(
            content = response,
            subject = f"Re: {email.subject}",
            sender = email.sender,
        )
        try:
            self.M.send_email(email_response)
        except Exception as e:
            raise RuntimeError(f"Failed to send email response: {e}")
        
        return response
    
    
    def send_email(self, recipient: str, subject: str, content: str):
        """
        Send an email with mail_handler using provided informations.
        """
        if not recipient or not subject or not content:
            raise ValueError("Recipient, subject, and content are required to send an email.")
        
        try:
            self.M.send_email(EMail(
                recipient=recipient,
                subject=subject,
                content=content
            ))
        except Exception as e:
            raise RuntimeError(f"Failed to send email: {e}")
        
        # print(f"Email sent to {recipient} with subject '{subject}'.")



# Test example 

if __name__ == "__main__":
    mail_agent = Mail_Agent(API_KEY = "***REMOVED-OPENAI-KEY-1***")



    # print("== Test de résumé d'une MAILBOX ==")
    # summaries = mail_agent.summarize_mailbox()
    # for idx, summary in enumerate(summaries, 1):
    #     print(f"{idx}, {summary}")
    print("\n=== Test classify_mailbox ===")
    try:
        moved_folders = mail_agent.classify_mailbox()
        print("Classify mailbox result:", moved_folders)
    except Exception as e:
        print("Error classifying mailbox:", e)

    # print("\n=== Send Test Email ===")
    # try:
    #     mail_agent.send_email(
    #         recipient="yanic.rothlingshofer@gmail.com",
    #         subject="Test Email",
    #         content="This is a test email sent by Mail_Agent."
    #     )
    #     print("Test email sent successfully.")
    # except Exception as e:
    #     print("Error sending test email:", e)


    
