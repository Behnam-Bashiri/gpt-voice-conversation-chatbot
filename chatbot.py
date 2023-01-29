import gtts
from gtts import gTTS
from playsound import playsound
import os
import json
import openai
import requests
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
from nltk import ne_chunk, pos_tag
from nltk.tokenize import word_tokenize
from datetime import datetime
from langdetect import detect
gtts_languages = set(gtts.lang.tts_langs().keys())

def tts11AI(key: str, text: str, path: str) -> bool:
    """
    This uses ElevenLab's AI to generate text to speech.

    :param key: This is your 11.ai key
    :param text: What you want spoken
    :param path: Where you want your file saved
    """

    # create a session object 
    s = requests.Session()

    # set the headers
    headers = {
        "accept": "audio/mpeg",
        "xi-api-key": key,
        "Content-Type": "application/json",
    }

    # set the payload
    payload = {
        "text": text
    }

    # make the post request
    url = "https://api.elevenlabs.io/v1/text-to-speech/EXAVITQu4vr4xnSDxMaL"
    try:
        r = s.post(url, data=json.dumps(payload), headers=headers, timeout=60)
        if r.status_code != 200:
            return False

        # save the response content
        with open(path, 'wb') as f:
            f.write(r.content)
    except requests.exceptions.Timeout:
        return False

    except Exception as e:
        print(f'[X] Unexpected error: {e}')
        return False
    
    return True

def get_AI_response(text: str) -> str:
    """
    This returns all the text following the first 
    instance of a colon
    """
    sections = text.split('AI:')
    return sections[1]

def hostile_or_personal(text: str) -> bool:
    """
    This tests the text to see if it is hostile
    or references a person. This test is done by
    your computer and should be done before
    testing with OpenAI.
    :param text: This is the text you want to test.
    :return: bool regarding status. If true, reject text
    """

    # Sentiment Analysis
    sid = SentimentIntensityAnalyzer()
    scores = sid.polarity_scores(text)
    negative_score = scores['neg']

    # Named Entity
    named_entities = []
    chunked = ne_chunk(pos_tag(word_tokenize(text)))
    for chunk in chunked:
        if hasattr(chunk, 'label'):
            named_entities.append(chunk.label())

    # Check for manipulation
    if (negative_score > 0.5) or ('PERSON' in named_entities and negative_score > 0.3):
        return True
    else:
        return False

def google_tts(text: str, path: str):

    language = detect(text)
    
    if language in gtts_languages:  # Pronounce correctly if possible
        tts = gTTS(text, lang=language)
        tts.save(path)

    else:  # Otherwise just use English pronounciation
        tts = gTTS(text)
        tts.save(path)

def talk(text: str, name: str, use11: bool = False, key11: str = '') -> bool:
    """
    This will provide a sound file for what ever you enter, then 
    play it using playsound. Saves an mp3 file.

    :param text: This is what you want to be converted to speech
    :param name: This is what you want the mp3 file to be called 
    """

    tts11_okay = False

    # 1. Set up name
    now = datetime.now()
    today = f'{now.month}-{now.day}-{now.year}'
    file = f'./messages/{today}/{name}'

    if not os.path.isdir(f'messages'):  # Make primary dir if not there
        os.mkdir(f'messages')

    if not os.path.isdir(f'./messages/{today}'):
        os.mkdir(f'./messages/{today}')

    if os.path.isfile(file + '.mpeg'):  # Delete file if it's already there
        os.remove(file + '.mpeg')
    
    elif os.path.isfile(file + '.mp3'):
        os.remove(file + '.mp3')

    # 2. Have gtts create file
    try:
        if use11 and tts11AI(key11, text, f'{file}.mpeg'):  
            playsound(file + '.mpeg')
            return True

        else:
            google_tts(text, f'{file}.mp3')
            playsound(file + '.mp3')
            return tts11_okay

    except:
        google_tts(text, f'{file}.mp3')
        playsound(file + '.mp3')
        return tts11_okay

def save_conversation(conversation: str, name):
    
    # 1. Setup directory for conversations
    if not os.path.isdir(f'conversations'):  # Make dir if not there
        os.mkdir(f'conversations')

    # 2. Save file
    with open(f'conversations/{name}', 'w') as file:
        file.write(conversation)

class Chatbot():
    """
    Chatbot that uses GPT-3
    """
    nltk.download('punkt')
    nltk.download('averaged_perceptron_tagger')
    nltk.download('maxent_ne_chunker')
    nltk.download('words')
    api_key = None
    api_key_11 = ''
    use11 = False
    conversation = ''
    memories = 'nothing'
    turns = 0
    conversation_name = datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + '.txt'

    def __init__(self, api_key: str, api_key_11: str = ''):
        
        # 1. Set up apis
        self.api_key = api_key
        openai.api_key = api_key

        if not api_key_11 == '':
            self.api_key_11 = api_key_11
            self.use11 = True

        # 2. Set up bot memories and init prompt
        self.remember()  # This will collect memories
        self.conversation = ("The following is a conversation with an AI assistant. The assistant is helpful, creative," + 
                "clever, and very friendly. The assistant is able to understand numerous languages and will reply" +
                f" to any messsage by the human in the language it was provided in. It has the ability to remember important concepts about the user; it currently remembers: {self.memories}." + 
                "\n\nHuman: Hello, who are you?\nAI: I am an AI created by OpenAI. How" + 
                " can I help you today?")

    def flagged_by_openai(self, text: str) -> bool:
        """
        Tests text using OpenAI api. If it fails or is flagged, return false.
        :param text:
        :return: bool representing if the material is flagged or something else.
        A return of False means the text is good to go
        """
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            data = {"input": text}
            response = requests.post("https://api.openai.com/v1/moderations", headers=headers, json=data)
            return json.loads(response.text)['results'][0]['flagged']  # This is a bool

        except Exception as e:
            print(f'[X] Failed to test with OpenAI. Key might be invalid.')
            return True

    def say_to_chatbot(self, text: str, outloud: bool = True) -> str:
        """
        This translates text into Latin
        :param text: Whatever text you want translated into Latin
        :return: Latin text if accepted or an error message
        """
        if not hostile_or_personal(text) and not self.flagged_by_openai(text):

            # 1. Get response
            start_sequence = "\nAI:"
            restart_sequence = "\nHuman: "
            self.conversation += f'\nHuman: {text}'

            try:
                response = openai.Completion.create(
                model="text-davinci-003",
                prompt=self.conversation,
                temperature=0.9,
                max_tokens=150,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0.6,
                stop=[" Human:", " AI:"]
                )
            except Exception as e:
                print(f'Error communicating with GPT-3: {e}')

            # Cut response and play it
            reply = json.loads(str(response))['choices'][0]['text']
            try:
                if outloud: 
                    self.use11 = talk(get_AI_response(reply), f'{self.turns}',
                                    self.use11, self.api_key_11)  # Speak if setting turned on
            except Exception as e:
                print(f'Error trying to speak: {e}')
                self.use11 = False

            # Keep track of conversation
            self.turns += 1
            self.conversation += reply
            save_conversation(self.conversation, self.conversation_name)

            return reply

        else:
            print('[X] Text flagged, no request sent.')
            return '[X] Text flagged, no request sent.'

    def remember(self):
        """
        Placeholder function. This sees if a memories file exists. If it does, it will return its contents.
        """
        pass

class GPT3(Chatbot):
    """
    This is a barebones tool to request something from 
    GPT-3. It's made into a separate class so as to not
    interfere with the chatbot.
    """

    def request(self, text:str, tokens: int = 150):
        if not hostile_or_personal(text) and not self.flagged_by_openai(text):

            # 1. Get response
            response = openai.Completion.create(
            model="text-davinci-003",
            prompt=text,
            temperature=0.9,
            max_tokens=tokens,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0.6,
            )

            # Cut response and play it
            reply = json.loads(str(response))['choices'][0]['text']
            return reply
