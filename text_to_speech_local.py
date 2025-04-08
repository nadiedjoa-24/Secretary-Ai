import pyttsx3

def text_to_speech(text):
    # Initialize the text-to-speech engine
    engine = pyttsx3.init()
    
    # Set properties (optional)
    engine.setProperty('rate', 150)  # Speed of speech
    engine.setProperty('volume', 0.9)  # Volume (0.0 to 1.0)
    
    # Speak the text
    engine.say(text)
    engine.runAndWait()

if __name__ == "__main__":
    # Example usage
    text = "Hello, this is a text-to-speech test running locally."
    text_to_speech(text)